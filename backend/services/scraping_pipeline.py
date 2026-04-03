"""
Scraping Pipeline - Tüm süreçleri birleştiren ana pipeline.
Scraping → Temizleme → Sınıflandırma → Konum Çıkarımı → Geocoding → Duplicate → DB
"""

import math
import random
from datetime import datetime

from scraper.common_cms_scraper import (
    CagdasKocaeliScraper,
    OzgurKocaeliScraper,
    SesKocaeliScraper,
    BizimYakaScraper,
)
from scraper.yenikocaeli_scraper import YeniKocaeliScraper
from processing.text_cleaner import TextCleaner
from processing.classifier import NewsClassifier, NewsCategory
from processing.location_extractor import LocationExtractor
from services.geocoding_service import GeocodingService
from services.duplicate_detector import DuplicateDetector
from services.database_service import DatabaseService
from models.news import NewsModel
from config import Config


class ScrapingPipeline:

    def __init__(self):
        self.db_service = DatabaseService()
        self.geocoding_service = GeocodingService(db=self.db_service.db)
        self.duplicate_detector = DuplicateDetector(db=self.db_service.db)
        self.scrapers = [
            CagdasKocaeliScraper(),
            OzgurKocaeliScraper(),
            SesKocaeliScraper(),
            BizimYakaScraper(),
            YeniKocaeliScraper(),
        ]

    def run(self) -> dict:
        print("=" * 60)
        print(f"[Pipeline] Scraping başlatılıyor... {datetime.now()}")
        print("=" * 60)

        stats = {
            "total_scraped": 0,
            "new_articles": 0,
            "duplicates_merged": 0,
            "skipped_existing": 0,
            "skipped_no_category": 0,
            "skipped_no_location": 0,
            "errors": 0,
            "sites": {},
        }

        for scraper in self.scrapers:
            site_stats = {"scraped": 0, "new": 0, "duplicate": 0, "errors": 0, "no_location": 0}
            try:
                articles = scraper.scrape()
                site_stats["scraped"] = len(articles)
                stats["total_scraped"] += len(articles)

                for article in articles:
                    try:
                        self._process_article(article, stats, site_stats)
                    except Exception as e:
                        print(f"  [Pipeline] Haber işleme hatası: {e}")
                        site_stats["errors"] += 1
                        stats["errors"] += 1

            except Exception as e:
                print(f"[Pipeline] {scraper.site_name} scraping hatası: {e}")
                stats["errors"] += 1

            stats["sites"][scraper.site_name] = site_stats

        print("=" * 60)
        print(f"[Pipeline] Tamamlandı. Sonuçlar: {stats}")
        print("=" * 60)

        return stats

    @staticmethod
    def _nearest_district(lat: float, lng: float) -> str:
        min_dist = float("inf")
        nearest = "İzmit"
        for district, center in Config.DISTRICT_CENTERS.items():
            d = math.sqrt((lat - center["lat"]) ** 2 + (lng - center["lng"]) ** 2)
            if d < min_dist:
                min_dist = d
                nearest = district
        return nearest

    # Bozuk / genel kategori sayfası URL'lerini filtrele
    _BROKEN_URL_PATTERNS = [
        r'/kategori/', r'/category/', r'/etiket/', r'/tag/',
        r'/sayfa/', r'/page/', r'/?$',
    ]

    @classmethod
    def _is_valid_article_url(cls, url: str) -> bool:
        """Genel kategori/tag sayfası olan URL'leri filtrele."""
        if not url:
            return False
        import re
        for pattern in cls._BROKEN_URL_PATTERNS:
            if re.search(pattern, url):
                # Sadece path'in sonu bu pattern ise filtrele
                # Haber URL'leri genelde /haber/baslik-123.html gibi olur
                from urllib.parse import urlparse
                path = urlparse(url).path
                if path.rstrip('/') == '' or re.search(pattern + r'$', path):
                    return False
        return True

    def _process_article(self, article: dict, stats: dict, site_stats: dict):
        source = article.get("source", {})
        url = source.get("url", "")

        if self.db_service.news_url_exists(url):
            stats["skipped_existing"] += 1
            return

        title = article.get("title", "")
        raw_content = article.get("raw_content", "")
        content = TextCleaner.clean(article.get("content", "") or raw_content)

        if not title or not content:
            return

        # Minimum içerik uzunluğu kontrolü (bozuk veri kaynakları drop)
        if len(title.strip()) < 10:
            print(f"  [Drop] Başlık çok kısa: '{title[:30]}'")
            stats["errors"] += 1
            return

        if len(content.strip()) < 50:
            print(f"  [Drop] İçerik çok kısa: '{title[:50]}'")
            stats["errors"] += 1
            return

        category, scores = NewsClassifier.classify(title, content)

        if category == NewsCategory.DIGER:
            stats["skipped_no_category"] += 1
            return

        location_info = LocationExtractor.extract(title, content)

        coordinates = None
        district = None

        if location_info:
            district = location_info.get("district")
            geo_result = self.geocoding_service.geocode(location_info["text"])
            if geo_result:
                coordinates = geo_result

        if not coordinates and district:
            center = Config.DISTRICT_CENTERS.get(district)
            if center:
                coordinates = {
                    "latitude": center["lat"],
                    "longitude": center["lng"],
                }

        # Eğer hiçbir şekilde koordinat üretilemediyse, gereksinime göre bu haber işlenmez
        if not coordinates:
            stats["skipped_no_location"] += 1
            site_stats["no_location"] += 1
            return

        # Koordinata göre en yakın ilçeyi belirle
        district = self._nearest_district(coordinates["latitude"], coordinates["longitude"])

        location = NewsModel.create_location(
            text=location_info["text"] if location_info else None,
            district=district,
            latitude=coordinates["latitude"],
            longitude=coordinates["longitude"],
        )

        source_doc = NewsModel.create_source(
            site_name=source.get("site_name", ""),
            url=url,
        )

        duplicate = self.duplicate_detector.find_duplicate(title, content, category=category.value)

        if duplicate:
            self.db_service.update_news_sources(
                duplicate["news_id"], source_doc
            )
            stats["duplicates_merged"] += 1
            site_stats["duplicate"] += 1
            print(f"  [Duplicate] Birleştirildi: '{title[:50]}...' "
                  f"(benzerlik: {duplicate['similarity']:.2%})")
            return

        embedding = self.duplicate_detector.compute_embedding_for_text(title, content)
        if not embedding:
            embedding = None

        news_doc = NewsModel.create(
            title=title,
            content=content,
            category=category.value,
            location=location,
            sources=[source_doc],
            publish_date=article.get("publish_date", datetime.now()),
            embedding=embedding,
        )

        self.db_service.insert_news(news_doc)
        stats["new_articles"] += 1
        site_stats["new"] += 1
        print(f"  [Yeni] Kaydedildi: '{title[:50]}...' [{category.value}]")
