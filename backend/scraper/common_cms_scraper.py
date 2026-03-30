"""
Ortak CMS scraper sınıfı.
cagdaskocaeli, ozgurkocaeli, seskocaeli ve bizimyaka aynı CMS altyapısını
kullanıyor. Bu sınıf ortak parse mantığını içerir.
"""

import re
from datetime import datetime
from urllib.parse import urljoin

from scraper.base_scraper import BaseScraper


TURKISH_MONTHS = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
    "oca": 1, "şub": 2, "mar": 3, "nis": 4,
    "may": 5, "haz": 6, "tem": 7, "ağu": 8,
    "eyl": 9, "eki": 10, "kas": 11, "ara": 12,
}


def parse_turkish_date(date_str: str) -> datetime | None:
    if not date_str:
        return None

    date_str = date_str.strip()

    patterns = [
        r"(\d{1,2})\s+(\w+)\s+(\d{4})\s*[-–]\s*(\d{2}):(\d{2})",
        r"(\d{1,2})\s+(\w+)\s+(\d{4})\s+(\d{2}):(\d{2})",
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{2}):(\d{2})",
        r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})",
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, date_str)
        if match:
            groups = match.groups()
            try:
                if i <= 1:
                    day = int(groups[0])
                    month_str = groups[1].lower()
                    month = TURKISH_MONTHS.get(month_str)
                    if not month:
                        continue
                    year = int(groups[2])
                    hour = int(groups[3])
                    minute = int(groups[4])
                elif i == 2:
                    day = int(groups[0])
                    month = int(groups[1])
                    year = int(groups[2])
                    hour = int(groups[3])
                    minute = int(groups[4])
                else:
                    year = int(groups[0])
                    month = int(groups[1])
                    day = int(groups[2])
                    hour = int(groups[3])
                    minute = int(groups[4])

                return datetime(year, month, day, hour, minute)
            except (ValueError, TypeError):
                continue

    return None


class CommonCMSScraper(BaseScraper):
    """
    cagdaskocaeli, ozgurkocaeli, seskocaeli, bizimyaka
    için ortak CMS scraper.
    """

    def get_article_links(self) -> list:
        soup = self.fetch_page(self.base_url)
        if not soup:
            # Cloudflare vb. ana sayfayı engellerse sitemap/rss üzerinden link topla
            links: list[str] = []
            seen: set[str] = set()
            for url in self._get_links_from_sitemap():
                if url not in seen:
                    seen.add(url)
                    links.append(url)
            for url in self._get_links_from_rss():
                if url not in seen:
                    seen.add(url)
                    links.append(url)
            return links

        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/haber/" in href and href.count("/") >= 3:
                full_url = urljoin(self.base_url, href)
                if self.base_url.rstrip("/") in full_url:
                    if not any(x in href for x in ["/basin_ilan", "/resmi-ilan"]):
                        links.add(full_url)

        category_pages = self._get_category_pages()
        for cat_url in category_pages:
            cat_soup = self.fetch_page(cat_url)
            if cat_soup:
                for a_tag in cat_soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "/haber/" in href and href.count("/") >= 3:
                        full_url = urljoin(self.base_url, href)
                        if self.base_url.rstrip("/") in full_url:
                            if not any(x in href for x in ["/basin_ilan", "/resmi-ilan"]):
                                links.add(full_url)

        return list(links)

    def _get_links_from_sitemap(self) -> list[str]:
        from bs4 import BeautifulSoup

        sitemap_url = f"{self.base_url.rstrip('/')}/sitemap.xml"
        xml = self.fetch_text(sitemap_url, timeout_s=40)
        if not xml:
            return []

        soup = BeautifulSoup(xml, "xml")
        # url -> lastmod (varsa)
        links: dict[str, datetime | None] = {}
        start_dt: datetime | None = None
        end_dt: datetime | None = None
        try:
            from config import Config
            start_dt = Config.parse_iso_datetime(getattr(Config, "SCRAPE_START_DATE", None))
            end_dt = Config.parse_iso_datetime(getattr(Config, "SCRAPE_END_DATE", None))
        except Exception:
            pass

        # sitemapindex ise child sitemap'leri dolaş
        if soup.find("sitemapindex"):
            sitemap_tags = soup.find_all("sitemap")
            for sm in sitemap_tags:
                loc_tag = sm.find("loc")
                if not loc_tag:
                    continue
                child = (loc_tag.get_text() or "").strip()
                if not child:
                    continue

                # Birçok sitede child sitemap isimleri "sitemap-YYYY-MM.xml" şeklinde.
                # Tarih aralığı varsa, URL'den ayı okuyup sadece o ayları çek.
                if (start_dt or end_dt):
                    m = re.search(r"sitemap-(\d{4})-(\d{2})\.xml", child)
                    if m:
                        yy = int(m.group(1))
                        mm = int(m.group(2))
                        month_start = datetime(yy, mm, 1)
                        month_end = datetime(yy + (1 if mm == 12 else 0), (1 if mm == 12 else mm + 1), 1)
                        if start_dt and month_end <= start_dt:
                            continue
                        if end_dt and month_start > end_dt:
                            continue

                child_xml = self.fetch_text(child, timeout_s=60)
                if not child_xml:
                    continue
                child_soup = BeautifulSoup(child_xml, "xml")
                for u in child_soup.find_all("url"):
                    loc2 = u.find("loc")
                    if not loc2:
                        continue
                    url = (loc2.get_text() or "").strip()
                    if not url or "/haber/" not in url:
                        continue
                    lastmod_tag = u.find("lastmod")
                    lm_dt = None
                    if lastmod_tag:
                        lm = (lastmod_tag.get_text() or "").strip()
                        try:
                            lm_dt = datetime.fromisoformat(lm.replace("Z", "+00:00"))
                        except Exception:
                            lm_dt = None

                    # URL bazlı filtre
                    if start_dt and lm_dt and lm_dt < start_dt:
                        continue
                    if end_dt and lm_dt and lm_dt > end_dt:
                        continue

                    links[url] = links.get(url) or lm_dt

            # backfill: eskiden yeniye doğru sırala (lastmod yoksa sona)
            return [u for (u, _) in sorted(links.items(), key=lambda kv: (kv[1] is None, kv[1] or datetime.max))]

        # urlset ise direkt linkleri al
        for u in soup.find_all("url"):
            loc_tag = u.find("loc")
            if not loc_tag:
                continue
            url = (loc_tag.get_text() or "").strip()
            if not url or "/haber/" not in url:
                continue
            lastmod_tag = u.find("lastmod")
            lm_dt = None
            if lastmod_tag:
                lm = (lastmod_tag.get_text() or "").strip()
                try:
                    lm_dt = datetime.fromisoformat(lm.replace("Z", "+00:00"))
                except Exception:
                    lm_dt = None
            if start_dt and lm_dt and lm_dt < start_dt:
                continue
            if end_dt and lm_dt and lm_dt > end_dt:
                continue
            links[url] = links.get(url) or lm_dt

        return [u for (u, _) in sorted(links.items(), key=lambda kv: (kv[1] is None, kv[1] or datetime.max))]

    def _get_links_from_rss(self) -> set[str]:
        rss_url = f"{self.base_url.rstrip('/')}/rss"
        soup = self.fetch_page(rss_url)
        if not soup:
            return set()

        links: set[str] = set()
        # RSS: <item><link>...</link></item>
        for item in soup.find_all("item"):
            link = item.find("link")
            if not link:
                continue
            url = (link.get_text() or "").strip()
            if url and "/haber/" in url:
                links.add(url)
        # Bazı RSS'lerde <link> yerine <guid> olabilir
        if not links:
            for guid in soup.find_all("guid"):
                url = (guid.get_text() or "").strip()
                if url and "/haber/" in url:
                    links.add(url)
        return links

    def _get_category_pages(self) -> list:
        categories = [
            "kocaeli-asayis-haberleri",
            "kocaeli-son-dakika-haberler",
            "kocaeli-gundem-haberleri",
        ]
        return [f"{self.base_url.rstrip('/')}/{cat}" for cat in categories]

    def parse_article(self, url: str) -> dict | None:
        soup = self.fetch_page(url)
        if not soup:
            return None

        title = self._extract_title(soup)
        if not title:
            return None

        content, raw_content = self._extract_content(soup)
        publish_date = self._extract_date(soup)

        return {
            "title": title,
            "content": content,
            "raw_content": raw_content,
            "publish_date": publish_date or datetime.now(),
            "url": url,
        }

    def _extract_title(self, soup) -> str | None:
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        og_title = soup.find("meta", property="og:title")
        if og_title:
            return og_title.get("content", "").strip()

        return None

    def _extract_content(self, soup) -> tuple[str, str]:
        content_selectors = [
            {"class_": re.compile(r"article[_-]?content|news[_-]?content|haber[_-]?icerik", re.I)},
            {"class_": re.compile(r"article[_-]?body|news[_-]?body|content[_-]?body", re.I)},
            {"class_": "entry-content"},
            {"itemprop": "articleBody"},
        ]

        content_div = None
        for selector in content_selectors:
            content_div = soup.find("div", **selector)
            if content_div:
                break

        if not content_div:
            content_div = soup.find("article")

        if not content_div:
            paragraphs = soup.find_all("p")
            text_parts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40]
            content = "\n".join(text_parts)
            return content, content

        raw_content = str(content_div)
        content = content_div.get_text(separator="\n", strip=True)

        return content, raw_content

    def _extract_date(self, soup) -> datetime | None:
        time_tag = soup.find("time")
        if time_tag:
            datetime_attr = time_tag.get("datetime")
            if datetime_attr:
                parsed = parse_turkish_date(datetime_attr)
                if parsed:
                    return parsed
            text = time_tag.get_text(strip=True)
            parsed = parse_turkish_date(text)
            if parsed:
                return parsed

        og_date = soup.find("meta", property="article:published_time")
        if og_date:
            parsed = parse_turkish_date(og_date.get("content", ""))
            if parsed:
                return parsed

        date_selectors = [
            {"class_": re.compile(r"date|tarih|zaman|time", re.I)},
            {"class_": re.compile(r"article[_-]?date|news[_-]?date", re.I)},
        ]
        for selector in date_selectors:
            date_el = soup.find(["span", "div", "p", "time"], **selector)
            if date_el:
                parsed = parse_turkish_date(date_el.get_text(strip=True))
                if parsed:
                    return parsed

        text = soup.get_text()
        date_patterns = [
            r"(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}\s*[-–]\s*\d{2}:\d{2})",
            r"(\d{1,2}\s+(?:Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)\s+\d{4}\s*[-–]\s*\d{2}:\d{2})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed = parse_turkish_date(match.group(1))
                if parsed:
                    return parsed

        return None


class CagdasKocaeliScraper(CommonCMSScraper):
    def __init__(self):
        super().__init__("Çağdaş Kocaeli", "https://www.cagdaskocaeli.com.tr")


class OzgurKocaeliScraper(CommonCMSScraper):
    def __init__(self):
        super().__init__("Özgür Kocaeli", "https://www.ozgurkocaeli.com.tr")


class SesKocaeliScraper(CommonCMSScraper):
    def __init__(self):
        super().__init__("Ses Kocaeli", "https://www.seskocaeli.com")


class BizimYakaScraper(CommonCMSScraper):
    def __init__(self):
        super().__init__("Bizim Yaka", "https://www.bizimyaka.com")
