"""
Konum bilgisi çıkarımı modülü.
Haber metninden adres, mahalle, ilçe, sokak bilgisi çıkarır.
Hibrit: Regex tabanlı konum + Türkçe ek/context tabanlı NER fallback.
spaCy gerektirmez; sentence-transformers ile uyumludur.
"""

import re
from config import Config


KOCAELI_NEIGHBORHOODS = {
    "İzmit": [
        "Akçakoca", "Alikahya", "Arslanbey", "Bekirdere", "Cedit",
        "Çubuklubala", "Durhasan", "Erenler", "Gündoğdu", "Hacıhızır",
        "Kadıköy", "Karabaş", "Kemalpaşa", "Kozluk", "M. Alipaşa",
        "Orhan", "Ömerağa", "Tepeköy", "Topçular", "Yahyakaptan",
        "Yenidoğan", "Yenişehir", "Yeşilova", "28 Haziran",
        "Akmeşe", "Fatih", "Hatipköy", "Körfez",
        "Serdar", "Tavşantepe", "Tepecik", "Şirintepe",
    ],
    "Gebze": [
        "Adem Yavuz", "Balçık", "Beylikbağı", "Çayırova", "Darıca",
        "Eskihisar", "Güzeller", "Hacıhalil", "Kirazpınar",
        "Köşklüçeşme", "Mevlana", "Mustafapaşa", "Osman Yılmaz",
        "Pelitli", "Sultan Orhan", "Yavuz Selim",
    ],
    "Darıca": [
        "Abdi İpekçi", "Bağlarbaşı", "Bayramoğlu", "Fevzi Çakmak",
        "Kazım Karabekir", "Nene Hatun", "Osmangazi", "Piri Reis",
        "Sırasöğütler", "Taşköprü",
    ],
    "Körfez": [
        "Çiftlik", "Hereke", "Kuzuluk", "Yarımca",
        "Halıdere", "İleri", "Kirazlıyalı",
    ],
    "Gölcük": [
        "Değirmendere", "Halıdere", "İhsaniye", "Saraylı",
        "Ulaşlı", "Yeniköy", "Merkez",
    ],
    "Başiskele": [
        "Başiskele", "Kullar", "Yuvacık", "Damlar", "Seymen",
        "Ovacık", "Yeşilyurt",
    ],
    "Kartepe": [
        "Arslanbey", "Ataevler", "Maşukiye", "Nusretiye",
        "Sarımeşe", "Uzuntarla", "Acısu",
    ],
    "Çayırova": [
        "Emek", "Fatih", "Özgürlük", "Akse", "Şekerpınar",
        "Turgut Özal",
    ],
    "Dilovası": [
        "Diliskelesi", "Köseler", "Tavşancıl", "Tepecik",
        "Muallimköy",
    ],
    "Derince": [
        "Çınarlı", "Deniz", "İbn-i Sina", "Sırrıpaşa",
        "Yavuz Sultan Selim", "Çenedağ",
    ],
    "Kandıra": [
        "Akçabeyli", "Karaağaç", "Kefken", "Sarısu",
    ],
    "Karamürsel": [
        "Akçat", "Ereğli", "Fulacık", "Hayriye",
        "İnönü", "Yalakdere",
    ],
}

# Türkçe konum eklerini yakalayan ek desen listesi
# Örn: "Gebze'de", "İzmit'te", "Darıca'da"
_DISTRICT_SUFFIX_PATTERN = r"['\u2019']?(?:de|da|te|ta|den|dan|ten|tan|ye|ya|e|a|nin|nın|nün|nun|in|ın|ün|un)?\b"


class LocationExtractor:

    @staticmethod
    def extract_district(text: str) -> str | None:
        if not text:
            return None
        text_lower = text.lower()
        for district in Config.KOCAELI_DISTRICTS:
            d_lower = district.lower()
            patterns = [
                rf'\b{re.escape(d_lower)}\b',
                rf"\b{re.escape(d_lower)}['\u2019]",
            ]
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return district
        return None

    @staticmethod
    def extract_neighborhood(text: str, district: str = None) -> str | None:
        if not text:
            return None

        search_districts = [district] if district else Config.KOCAELI_DISTRICTS

        for d in search_districts:
            neighborhoods = KOCAELI_NEIGHBORHOODS.get(d, [])
            for neighborhood in neighborhoods:
                pattern = rf'\b{re.escape(neighborhood)}\b'
                if re.search(pattern, text, re.IGNORECASE):
                    return neighborhood
        return None

    @staticmethod
    def extract_street_address(text: str) -> str | None:
        if not text:
            return None

        patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+)*\s+(?:Caddesi|Cad\.?))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+)*\s+(?:Sokak|Sok\.?|Sokağı))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+)*\s+(?:Bulvarı|Bul\.?))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def extract_specific_location(text: str) -> str | None:
        """Spesifik yer isimleri (park, stadyum, hastane, üniversite vb.)"""
        if not text:
            return None

        # Regex N-Gram Adres Sözlüğü Yaklaşımı (Hızlı spaCy alternatifi)
        # Kocaeli'deki önemli merkezleri ve nokta atış yerleri doğrudan yakalar
        specific_landmarks = [
            r"Kocaeli Üniversitesi Araştırma ve Uygulama Hastanesi",
            r"Kocaeli Üniversitesi Hastanesi",
            r"Kocaeli Üniversitesi", r"KOÜ",
            r"Kocaeli Şehir Hastanesi", r"Şehir Hastanesi",
            r"Seka Devlet Hastanesi", r"Derince Eğitim ve Araştırma Hastanesi",
            r"Körfez Devlet Hastanesi", r"Gölcük Necati Çelik Devlet Hastanesi",
            r"Karamürsel Devlet Hastanesi", r"Kandıra M. Kazım Dinç Devlet Hastanesi",
            r"Gebze Fatih Devlet Hastanesi", r"Darıca Farabi Eğitim ve Araştırma Hastanesi",
            r"Kocaeli Adliyesi", r"Gebze Adliyesi",
            r"Kocaeli Valiliği", r"Kocaeli Büyükşehir Belediyesi",
            r"İzmit Belediyesi", r"Gebze Belediyesi", r"Derince Belediyesi",
            r"Gölcük Belediyesi", r"Körfez Belediyesi", r"Kartepe Belediyesi",
            r"Başiskele Belediyesi", r"Çayırova Belediyesi", r"Darıca Belediyesi",
            r"Dilovası Belediyesi", r"Karamürsel Belediyesi", r"Kandıra Belediyesi",
            r"Kocaelispor Tesisleri", r"Kocaeli Stadyumu", r"İsmetpaşa Stadyumu",
            r"SEKA Park", r"Seka Park", r"Kent Meydanı", r"Anıtpark Meydanı",
            r"Cumhuriyet Parkı", r"Yürüyüş Yolu", r"Belsa Plaza",
            r"Symbol AVM", r"Ncity AVM", r"41 Burda AVM", r"Arasta Park",
            r"Gebze Center", r"Körfez Center", r"Gölcük Kavaklı Sahili",
            r"Değirmendere Sahili", r"Karamürsel Sahili", r"Kefken Sahili",
            r"Kerpe Sahili", r"Cebeci Sahili", r"Kandıra Sahilleri",
            r"Ormanya", r"Maşukiye", r"Kartepe Kayak Merkezi", r"Kuzuyayla",
            r"Yuvacık Barajı", r"Sapanca Gölü", r"İzmit Körfezi", r"İzmit Sanayi Sitesi",
            r"Gebze Organize Sanayi Bölgesi", r"GOSB", r"TOSB", r"Dilovası OSB",
            r"Arslanbey OSB", r"Kandıra Gıda OSB", r"Körfez Sanayi Sitesi",
        ]

        for landmark in specific_landmarks:
            if re.search(rf'\b{landmark}\b', text, re.IGNORECASE):
                # Orijinal metindeki eşleşmeyi döndür
                match = re.search(rf'\b({landmark})\b', text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        # Genel Regex Desenleri (Büyük harfle başlayan Hastane, Park, vb. otoyollar)
        patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Hastanesi|Hastanesi\'nde))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Stadyumu|Stadı))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Parkı|Park))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Meydanı))',
            r'(D-100|TEM|O-4|Anadolu Otoyolu|Kuzey Marmara Otoyolu)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @staticmethod
    def _context_extract_district(text: str) -> str | None:
        """
        Regex Fallback:
        Türkçe konum bağlamı kalıplarıyla ilçe tespit eder.
        Örn: "Gebze ilçesinde", "İzmit'te meydana gelen", "Darıca'daki olay"
        """
        if not text:
            return None

        for district in Config.KOCAELI_DISTRICTS:
            d_esc = re.escape(district)
            # Türkçe ek varlığıyla birlikte konum bağlamı kalıpları
            context_patterns = [
                # "Gebze ilçesinde / ilçesindeki"
                rf'\b{d_esc}\s+ilçesi',
                # "Gebze'de, Gebze'deki, Gebze'nin"
                rf"{d_esc}['\u2019][a-züşöçığ]{{1,5}}\b",
                # "Gebze sınırları içinde / merkezi"
                rf'\b{d_esc}\s+(?:sınırları|merkezi|bölgesi|semtinde)',
            ]
            for pattern in context_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return district

        return None

    @classmethod
    def extract(cls, title: str, content: str) -> dict:
        combined = f"{title} {content}"

        # --- Adım 1: Doğrudan regex eşleme ---
        district = cls.extract_district(combined)
        neighborhood = cls.extract_neighborhood(combined, district)
        street = cls.extract_street_address(combined)
        specific = cls.extract_specific_location(combined)

        # --- Adım 2: İlçe bulunamadıysa bağlam tabanlı NER fallback ---
        if not district:
            district = cls._context_extract_district(combined)
            # Yeni bulunan ilçeye göre mahalle aramasını tekrar dene
            if district and not neighborhood:
                neighborhood = cls.extract_neighborhood(combined, district)

        # --- Sonuç oluştur ---
        location_text_parts = []
        if specific:
            location_text_parts.append(specific)
        if street:
            location_text_parts.append(street)
        if neighborhood:
            location_text_parts.append(f"{neighborhood} Mahallesi")
        if district:
            location_text_parts.append(district)

        if not location_text_parts:
            return None

        location_text = ", ".join(location_text_parts)
        if district:
            location_text += ", Kocaeli"

        return {
            "text": location_text,
            "district": district,
            "neighborhood": neighborhood,
            "street": street,
            "specific": specific,
        }
