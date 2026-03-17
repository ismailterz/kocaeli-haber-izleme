"""
Yeni Kocaeli scraper.
Farklı CMS altyapısı kullanıyor: /haber/{category}/{slug}/{id}.html
"""

import re
from datetime import datetime
from urllib.parse import urljoin

from scraper.base_scraper import BaseScraper
from scraper.common_cms_scraper import parse_turkish_date


class YeniKocaeliScraper(BaseScraper):
    def __init__(self):
        super().__init__("Yeni Kocaeli", "https://www.yenikocaeli.com")

    def get_article_links(self) -> list:
        soup = self.fetch_page(self.base_url)
        if not soup:
            return []

        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "/haber/" in href and href.endswith(".html"):
                full_url = urljoin(self.base_url, href)
                if "yenikocaeli.com" in full_url:
                    links.add(full_url)

        category_pages = [
            f"{self.base_url}/haber/polis-adliye.html",
            f"{self.base_url}/haber/guncel.html",
            f"{self.base_url}/haber/asayis.html",
        ]

        for cat_url in category_pages:
            cat_soup = self.fetch_page(cat_url)
            if cat_soup:
                for a_tag in cat_soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if "/haber/" in href and href.endswith(".html"):
                        full_url = urljoin(self.base_url, href)
                        if "yenikocaeli.com" in full_url:
                            links.add(full_url)

        return list(links)

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
            {"class_": re.compile(r"news[_-]?content|article[_-]?content|haber[_-]?detay", re.I)},
            {"class_": re.compile(r"content[_-]?body|article[_-]?body", re.I)},
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

        og_date = soup.find("meta", property="article:published_time")
        if og_date:
            parsed = parse_turkish_date(og_date.get("content", ""))
            if parsed:
                return parsed

        text = soup.get_text()
        date_patterns = [
            r"(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}\s+\d{2}:\d{2})",
            r"(\d{1,2}\s+(?:Oca|Şub|Mar|Nis|May|Haz|Tem|Ağu|Eyl|Eki|Kas|Ara)\s+\d{4}\s+\d{2}:\d{2})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                parsed = parse_turkish_date(match.group(1))
                if parsed:
                    return parsed

        return None
