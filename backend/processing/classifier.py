"""
Haber türü sınıflandırma modülü.
Anahtar kelime tabanlı otomatik sınıflandırma (öncelik sırası ile).
"""

from enum import Enum


class NewsCategory(str, Enum):
    TRAFIK_KAZASI = "Trafik Kazası"
    YANGIN = "Yangın"
    ELEKTRIK_KESINTISI = "Elektrik Kesintisi"
    HIRSIZLIK = "Hırsızlık"
    KULTUREL_ETKINLIK = "Kültürel Etkinlikler"
    DIGER = "Diğer"


CATEGORY_KEYWORDS = {
    NewsCategory.TRAFIK_KAZASI: {
        "primary": [
            "trafik kazası", "trafik kazasi", "kaza sonucu", "araç kazası",
            "zincirleme kaza", "feci kaza", "kaza meydana geldi",
            "tır kazası", "otobüs kazası", "motosiklet kazası",
            "kaza yapan", "kazada yaralanan", "kazada ölen",
            "kazada hayatını kaybetti", "trafik kazasında",
            "kaza:", "kazada",
        ],
        "secondary": [
            "çarpışma", "çarpıştı", "çarptı", "takla attı",
            "şarampole yuvarlandı", "devrildi", "sürücü yaralandı",
            "yaralı kaldırıldı", "ambulans sevk edildi",
            "bariyerlere çarptı", "refüje çıktı", "kafa kafaya",
            "otomobil ile", "kamyon ile", "tır ile",
            "sürücüsü hayatını kaybetti", "makas atan",
            "fren yapamadı", "kontrolden çıktı", "kaldırıma çıktı",
            "hız sınırını aştı", "alkollü sürücü",
        ],
    },
    NewsCategory.YANGIN: {
        "primary": [
            "yangın çıktı", "yangın meydana geldi", "yangında",
            "alevlere teslim", "alevler sardı", "alev alev yandı",
            "yangın haberi", "yangınla mücadele", "itfaiye ekipleri",
            "yangın söndürme", "yangına müdahale",
            "alev aldı", "yangın", "çatısında yangın",
        ],
        "secondary": [
            "yanarak", "yandı", "alevler", "itfaiye",
            "dumana teslim", "duman yükseldi", "kül oldu",
            "söndürüldü", "söndürme çalışması",
            "kundaklama", "kundaklandı", "yangın ihbarı",
            "ev yangını", "fabrika yangını", "orman yangını",
            "oto yangın", "araç yandı", "şofben",
        ],
    },
    NewsCategory.ELEKTRIK_KESINTISI: {
        "primary": [
            "elektrik kesintisi", "elektriksiz kalacak", "elektrik kesilecek",
            "enerji kesintisi", "planlı kesinti", "plansız kesinti",
            "elektrik arızası", "trafo arızası", "elektrik verildi",
            "elektrikler kesildi", "elektrikler gitti",
        ],
        "secondary": [
            "elektriksiz", "karanlığa büründü", "karanlıkta kaldı",
            "enerji nakil hattı", "trafo patladı", "trafo arızası",
            "SEDAŞ", "enerji kesintisi", "elektrik dağıtım",
            "kesinti yaşanacak", "kesintiden etkilenecek",
        ],
    },
    NewsCategory.HIRSIZLIK: {
        "primary": [
            "hırsızlık", "hırsız yakalandı", "hırsızlık şüphelisi",
            "hırsız", "hırsızlar", "ev soyan", "dükkan soyan",
            "iş yeri soyan", "soygun", "kapkaç",
            "gasp etti", "gasp edildi", "gasp olayı",
            "dolandırıcılık", "dolandırıcı", "dolandırıldı",
        ],
        "secondary": [
            "çaldı", "çalıntı", "çalınmış", "çalınan",
            "oto hırsızlık", "motosiklet çalındı", "araç çalındı",
            "suç üstü yakalandı", "suçüstü",
            "sahte belge", "sahte para",
            "yağma", "silahlı yağma",
        ],
    },
    NewsCategory.KULTUREL_ETKINLIK: {
        "primary": [
            "konser", "festival", "sergi", "tiyatro",
            "etkinlik", "gösteri", "şenlik", "panayır",
            "kutlama", "anma töreni", "bayram kutlaması",
            "kültür merkezi", "sanat etkinliği", "müzik dinletisi",
        ],
        "secondary": [
            "sahne alacak", "sahneye çıkacak", "biletler satışa",
            "ücretsiz etkinlik", "söyleşi", "imza günü",
            "kültürel program", "sanat galerisi",
            "halk oyunları", "dans gösterisi",
            "sinema", "film gösterimi", "müze",
            "kitap fuarı", "fuar", "kongre",
        ],
    },
}

PRIORITY_ORDER = [
    NewsCategory.TRAFIK_KAZASI,
    NewsCategory.YANGIN,
    NewsCategory.ELEKTRIK_KESINTISI,
    NewsCategory.HIRSIZLIK,
    NewsCategory.KULTUREL_ETKINLIK,
]


class NewsClassifier:

    @staticmethod
    def _calculate_score(text: str, keywords: dict) -> tuple[float, bool]:
        """Skor ve en az bir primary eşleşmesi olup olmadığını döner."""
        text_lower = text.lower()
        score = 0.0
        has_primary = False
        for keyword in keywords.get("primary", []):
            if keyword.lower() in text_lower:
                score += 3.0
                has_primary = True
        for keyword in keywords.get("secondary", []):
            if keyword.lower() in text_lower:
                score += 1.0
        return score, has_primary

    @classmethod
    def classify(cls, title: str, content: str) -> tuple[NewsCategory, dict]:
        combined_text = f"{title} {title} {content}"

        scores = {}
        has_primary_map = {}
        for category in PRIORITY_ORDER:
            keywords = CATEGORY_KEYWORDS[category]
            score, has_primary = cls._calculate_score(combined_text, keywords)
            scores[category] = score
            has_primary_map[category] = has_primary

        # En az bir primary keyword eşleşmesi olan kategoriler arasından seç
        candidates = {c: s for c, s in scores.items() if has_primary_map.get(c)}

        if not candidates:
            return NewsCategory.DIGER, scores

        best_category = max(candidates, key=candidates.get)
        if candidates[best_category] < 3.0:
            return NewsCategory.DIGER, scores

        tied = [c for c, s in candidates.items() if s == candidates[best_category]]
        if len(tied) > 1:
            for category in PRIORITY_ORDER:
                if category in tied:
                    return category, scores

        return best_category, scores

    @classmethod
    def get_keywords_used(cls, title: str, content: str, category: NewsCategory) -> list[str]:
        if category == NewsCategory.DIGER:
            return []
        combined_text = f"{title} {content}".lower()
        keywords = CATEGORY_KEYWORDS.get(category, {})
        found = []
        for kw in keywords.get("primary", []) + keywords.get("secondary", []):
            if kw.lower() in combined_text:
                found.append(kw)
        return found
