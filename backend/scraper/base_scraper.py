"""
Temel Scraper sınıfı.
Tüm site-spesifik scraperlar bu sınıftan türetilir.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup

from config import Config


class BaseScraper(ABC):
    """Tüm haber sitesi scraperlarının temel sınıfı"""

    def __init__(self, site_name, base_url):
        self.site_name = site_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        })

    def fetch_page(self, url):
        """Safya HTML'ini çek ve BeautifulSoup objesi döndür"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            print(f"[{self.site_name}] Sayfa çekilemedi: {url} - {e}")
            return None

    @abstractmethod
    def get_article_links(self) -> list:
        """Ana sayfa veya kategori sayfalarından haber linklerini çek"""
        pass

    @abstractmethod
    def parse_article(self, url) -> dict:
        """
        Tek bir haber sayfasını parse et.

        Döndürmesi gereken dict:
        {
            'title': str,
            'content': str,
            'raw_content': str,
            'publish_date': datetime,
            'url': str,
        }
        """
        pass

    def scrape(self) -> list:
        """Tüm haberleri çek ve döndür"""
        print(f"[{self.site_name}] Haber linkleri toplanıyor...")
        links = self.get_article_links()
        print(f"[{self.site_name}] {len(links)} haber linki bulundu.")

        articles = []
        cutoff_date = datetime.now() - timedelta(days=Config.SCRAPE_DAYS)

        for i, link in enumerate(links):
            try:
                # Rate limiting: siteler arası bekleme
                if i > 0:
                    time.sleep(1)

                article = self.parse_article(link)
                if article is None:
                    continue

                # Son 3 günlük haberleri filtrele
                pub_date = article.get("publish_date")
                if pub_date and pub_date < cutoff_date:
                    continue

                article["source"] = {
                    "site_name": self.site_name,
                    "url": link,
                    "scraped_at": datetime.now(),
                }
                articles.append(article)
                print(f"  [{i+1}/{len(links)}] ✓ {article.get('title', 'Başlık yok')[:60]}")
            except Exception as e:
                print(f"  [{i+1}/{len(links)}] ✗ Hata: {link} - {e}")

        print(f"[{self.site_name}] Toplam {len(articles)} haber çekildi.")
        return articles
