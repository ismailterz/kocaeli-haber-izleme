"""
Veri temizleme ve ön işleme modülü.
HTML tag temizliği, boşluk normalizasyonu, özel karakter temizliği, reklam çıkarma.
"""

import re
import unicodedata
from bs4 import BeautifulSoup


class TextCleaner:

    AD_PATTERNS = [
        r'(?i)reklam\s*içeriği',
        r'(?i)sponsorlu\s*içerik',
        r'(?i)advertorial',
        r'(?i)google_ad',
        r'(?i)adsense',
        r'(?i)banner[\s_-]?ad',
        r'(?i)ilgili\s+haberler?\s*:',
        r'(?i)benzer\s+haberler?\s*:',
        r'(?i)kaynak\s*:\s*\w+\s*haber\s*ajansı',
    ]

    IRRELEVANT_PATTERNS = [
        r'(?i)haberi\s+paylaş',
        r'(?i)yorum\s+yap',
        r'(?i)tweet(?:le|lemek)',
        r'(?i)facebook[\'\u2019](?:ta|da)\s+paylaş',
        r'(?i)whatsapp[\'\u2019](?:ta|dan)\s+paylaş',
        r'(?i)haber\s+ihbar',
        r'(?i)künye\s+bilgileri',
        r'(?i)iletişim\s+bilgileri',
        r'(?i)tüm\s+hakları\s+saklıdır',
        r'(?i)copyright\s*©',
    ]

    @staticmethod
    def clean_html(text: str) -> str:
        if not text:
            return ""
        soup = BeautifulSoup(text, "lxml")
        for tag in soup.find_all(["script", "style", "iframe", "noscript", "svg"]):
            tag.decompose()
        return soup.get_text(separator=" ")

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'[\t\r]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        return text.strip()

    @staticmethod
    def remove_special_characters(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = re.sub(r'[\u200b\u200c\u200d\ufeff\u00ad]', '', text)
        return text

    @classmethod
    def remove_ads(cls, text: str) -> str:
        if not text:
            return ""
        for pattern in cls.AD_PATTERNS:
            text = re.sub(pattern + r'.*?(?:\n|$)', '', text)
        return text

    @classmethod
    def remove_irrelevant(cls, text: str) -> str:
        if not text:
            return ""
        for pattern in cls.IRRELEVANT_PATTERNS:
            text = re.sub(pattern + r'.*?(?:\n|$)', '', text)
        
        # Fazla ve alakasız JS parçaları kalıntıları da silinebilir
        text = re.sub(r'(?:^|\n)\s*r\]\s*(?:\n|$)', '\n', text)
        return text

    @staticmethod
    def normalize_turkish(text: str) -> str:
        if not text:
            return ""
        replacements = {
            '\u0130': 'İ',  # İ
            '\u0131': 'ı',  # ı
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @classmethod
    def clean(cls, text: str) -> str:
        text = cls.clean_html(text)
        text = cls.remove_special_characters(text)
        text = cls.normalize_turkish(text)
        text = cls.remove_ads(text)
        text = cls.remove_irrelevant(text)
        text = cls.normalize_whitespace(text)
        return text
