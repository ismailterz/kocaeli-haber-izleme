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
        self._cloudscraper = None

    def fetch_text(self, url: str, timeout_s: int = 30) -> str | None:
        """
        URL içeriğini ham metin olarak getirir.
        Sitemap/RSS gibi XML kaynakları için kullanılır.
        """
        def _get_with_requests():
            response = self.session.get(url, timeout=timeout_s, allow_redirects=True)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text

        def _get_with_cloudscraper():
            if self._cloudscraper is None:
                try:
                    import cloudscraper  # type: ignore
                except Exception:
                    return None
                self._cloudscraper = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "darwin", "mobile": False}
                )
                self._cloudscraper.headers.update(dict(self.session.headers))
            resp = self._cloudscraper.get(url, timeout=timeout_s, allow_redirects=True)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text

        try:
            return _get_with_requests()
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status == 403:
                try:
                    return _get_with_cloudscraper()
                except Exception:
                    return None
            return None
        except requests.RequestException:
            return None

    def fetch_page(self, url):
        """Safya HTML'ini çek ve BeautifulSoup objesi döndür"""
        def _get_with_requests(timeout_s: int):
            response = self.session.get(url, timeout=timeout_s, allow_redirects=True)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text

        def _get_with_cloudscraper(timeout_s: int):
            if self._cloudscraper is None:
                try:
                    import cloudscraper  # type: ignore
                except Exception:
                    return None
                self._cloudscraper = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "darwin", "mobile": False}
                )
                self._cloudscraper.headers.update(dict(self.session.headers))
            resp = self._cloudscraper.get(url, timeout=timeout_s, allow_redirects=True)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return resp.text

        last_err = None
        for attempt in range(3):
            timeout_s = 20 + attempt * 10
            try:
                html = _get_with_requests(timeout_s)
                return BeautifulSoup(html, "lxml")
            except requests.HTTPError as e:
                last_err = e
                status = getattr(e.response, "status_code", None)
                if status == 403:
                    try:
                        html = _get_with_cloudscraper(timeout_s)
                        if html:
                            return BeautifulSoup(html, "lxml")
                    except Exception as ce:
                        last_err = ce
                break
            except requests.RequestException as e:
                last_err = e
                time.sleep(1 + attempt)

        print(f"[{self.site_name}] Sayfa çekilemedi: {url} - {last_err}")
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

        # Performans: her sitede link sayısını limitli tut
        max_links = getattr(Config, "MAX_LINKS_PER_SITE", 500) or 500
        links = links[:max_links]

        articles = []
        start_dt = Config.parse_iso_datetime(getattr(Config, "SCRAPE_START_DATE", None))
        end_dt = Config.parse_iso_datetime(getattr(Config, "SCRAPE_END_DATE", None))

        cutoff_date = None
        if not start_dt and getattr(Config, "SCRAPE_DAYS", 0) and Config.SCRAPE_DAYS > 0:
            cutoff_date = datetime.now() - timedelta(days=Config.SCRAPE_DAYS)

        for i, link in enumerate(links):
            try:
                # Rate limiting
                if i > 0:
                    time.sleep(getattr(Config, "REQUEST_DELAY_SECONDS", 0.4))

                article = self.parse_article(link)
                if article is None:
                    continue

                # Son N günlük haberleri filtrele (SCRAPE_DAYS<=0 ise filtre yok)
                pub_date = article.get("publish_date")
                if cutoff_date and pub_date and pub_date < cutoff_date:
                    continue
                if start_dt and pub_date and pub_date < start_dt:
                    continue
                if end_dt and pub_date and pub_date > end_dt:
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
