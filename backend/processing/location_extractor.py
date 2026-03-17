"""
Konum bilgisi çıkarımı modülü.
Haber metninden adres, mahalle, ilçe, sokak bilgisi çıkarır.
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

LOCATION_INDICATORS = [
    r"(?:Mah(?:allesi)?\.?)",
    r"(?:Cad(?:desi)?\.?)",
    r"(?:Sok(?:ak|ağı)?\.?)",
    r"(?:Bul(?:varı)?\.?)",
    r"(?:Mevki(?:i|si)?)",
    r"(?:Semti?)",
]


class LocationExtractor:

    @staticmethod
    def extract_district(text: str) -> str | None:
        if not text:
            return None
        text_lower = text.lower()
        for district in Config.KOCAELI_DISTRICTS:
            patterns = [
                rf'\b{re.escape(district.lower())}\b',
                rf'\b{re.escape(district.lower())}[\'\u2019]',
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
        """Spesifik yer isimleri (park, stadyum, hastane vb.)"""
        if not text:
            return None

        patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Hastanesi|Hastanesi\'nde))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Stadyumu|Stadı))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Parkı|Park))',
            r'([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)*\s+(?:Meydanı))',
            r'(D-100|TEM|O-4)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def extract(cls, title: str, content: str) -> dict:
        combined = f"{title} {content}"

        district = cls.extract_district(combined)
        neighborhood = cls.extract_neighborhood(combined, district)
        street = cls.extract_street_address(combined)
        specific = cls.extract_specific_location(combined)

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
