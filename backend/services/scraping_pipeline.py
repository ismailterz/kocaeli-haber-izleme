"""
Scraping Pipeline - Tüm süreçleri birleştiren ana pipeline.
Scraping → Temizleme → Sınıflandırma → Konum Çıkarımı → Geocoding → Duplicate → DB
"""

from datetime import datetime

import random

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
            "errors": 0,
            "sites": {},
        }

        for scraper in self.scrapers:
            site_stats = {"scraped": 0, "new": 0, "duplicate": 0, "errors": 0}
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

        if not coordinates:
            coordinates = self._get_fallback_coordinates(district)

        if not district:
            district = self._guess_district_from_text(title, content)
            if district and not coordinates:
                coordinates = self._get_fallback_coordinates(district)

        location = NewsModel.create_location(
            text=location_info["text"] if location_info else (f"{district}, Kocaeli" if district else "Kocaeli"),
            district=district,
            latitude=coordinates["latitude"] if coordinates else Config.KOCAELI_CENTER["lat"],
            longitude=coordinates["longitude"] if coordinates else Config.KOCAELI_CENTER["lng"],
        )

        source_doc = NewsModel.create_source(
            site_name=source.get("site_name", ""),
            url=url,
        )

        duplicate = self.duplicate_detector.find_duplicate(title, content)

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

        news_doc = NewsModel.create(
            title=title,
            content=content,
            raw_content=raw_content,
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

    @staticmethod
    def _get_fallback_coordinates(district: str | None) -> dict | None:
        if not district:
            return None
        center = Config.DISTRICT_CENTERS.get(district)
        if not center:
            return None
        offset_lat = random.uniform(-0.008, 0.008)
        offset_lng = random.uniform(-0.008, 0.008)
        return {
            "latitude": center["lat"] + offset_lat,
            "longitude": center["lng"] + offset_lng,
        }

    @staticmethod
    def _guess_district_from_text(title: str, content: str) -> str | None:
        combined = f"{title} {content}".lower()
        for district in Config.KOCAELI_DISTRICTS:
            if district.lower() in combined:
                return district
        return None
