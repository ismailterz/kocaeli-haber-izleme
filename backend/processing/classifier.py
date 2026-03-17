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
        ],
        "secondary": [
            "çarpışma", "çarpıştı", "çarptı", "takla attı",
            "şarampole yuvarlandı", "devrildi", "sürücü yaralandı",
            "yaralı kaldırıldı", "ambulans sevk edildi",
            "bariyerlere çarptı", "refüje çıktı", "kafa kafaya",
            "otomobil ile", "kamyon ile", "tır ile",
            "sürücüsü hayatını kaybetti", "makas atan",
            "fren yapamadı", "kontrolden çıktı",
            "hız sınırını aştı", "alkollü sürücü",
        ],
    },
    NewsCategory.YANGIN: {
        "primary": [
            "yangın çıktı", "yangın meydana geldi", "yangında",
            "alevlere teslim", "alevler sardı", "alev alev yandı",
            "yangın haberi", "yangınla mücadele", "itfaiye ekipleri",
            "yangın söndürme", "yangına müdahale",
        ],
        "secondary": [
            "yanarak", "yandı", "alevler", "itfaiye",
            "dumana teslim", "duman yükseldi", "kül oldu",
            "söndürüldü", "söndürme çalışması",
            "kundaklama", "kundaklandı", "yangın ihbarı",
            "ev yangını", "fabrika yangını", "orman yangını",
            "oto yangın", "araç yandı",
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
            "hırsızlık", "hırsız yakalandı", "çaldı", "çalıntı",
            "soygun", "gasp", "gasp edildi", "kapkaç",
            "ev soyan", "dükkan soyan", "iş yeri soyan",
            "hırsızlık şüphelisi", "hırsız", "hırsızlar",
        ],
        "secondary": [
            "çalınmış", "ele geçirildi", "suç üstü yakalandı",
            "parmak izi", "güvenlik kamerası", "suçüstü",
            "oto hırsızlık", "motosiklet çalındı",
            "dolandırıcılık", "dolandırıcı", "sahte",
            "yağma", "silahlı yağma", "uyuşturucu",
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
    def _calculate_score(text: str, keywords: dict) -> float:
        text_lower = text.lower()
        score = 0.0
        for keyword in keywords.get("primary", []):
            if keyword.lower() in text_lower:
                score += 3.0
        for keyword in keywords.get("secondary", []):
            if keyword.lower() in text_lower:
                score += 1.0
        return score

    @classmethod
    def classify(cls, title: str, content: str) -> tuple[NewsCategory, dict]:
        combined_text = f"{title} {title} {content}"

        scores = {}
        for category in PRIORITY_ORDER:
            keywords = CATEGORY_KEYWORDS[category]
            scores[category] = cls._calculate_score(combined_text, keywords)

        best_category = max(scores, key=scores.get)
        if scores[best_category] < 2.0:
            return NewsCategory.DIGER, scores

        tied = [c for c, s in scores.items() if s == scores[best_category]]
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
