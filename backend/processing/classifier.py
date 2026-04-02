"""
Haber türü sınıflandırma modülü.
Anahtar kelime tabanlı otomatik sınıflandırma (öncelik sırası ile).
Hibrit NLP: Kural tabanlı sonuç yetersiz kaldığında sentence-transformers fallback.
"""

import numpy as np
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
            "gösteri", "şenlik", "panayır",
            "anma töreni", "bayram kutlaması",
            "kültür merkezi", "sanat etkinliği", "müzik dinletisi",
        ],
        "secondary": [
            "sahne alacak", "sahneye çıkacak", "biletler satışa",
            "ücretsiz etkinlik", "söyleşi", "imza günü",
            "kültürel program", "sanat galerisi",
            "halk oyunları", "dans gösterisi",
            "film gösterimi", "müze",
            "kitap fuarı", "fuar", "kongre",
        ],
    },
}

# "etkinlik", "kutlama", "sinema" primary'den secondary'ye taşındı / çıkarıldı
# "çaldı" hırsızlık primary'den çıkarıldı (bağlam dışı eşleşme riski: müzik çaldı vb.)

PRIORITY_ORDER = [
    NewsCategory.TRAFIK_KAZASI,
    NewsCategory.YANGIN,
    NewsCategory.ELEKTRIK_KESINTISI,
    NewsCategory.HIRSIZLIK,
    NewsCategory.KULTUREL_ETKINLIK,
]

# Hibrit NLP: Her kategori için semantik referans cümleler
CATEGORY_ANCHORS = {
    NewsCategory.TRAFIK_KAZASI: [
        "Trafik kazasında araçlar çarpıştı, yaralılar hastaneye kaldırıldı.",
        "Otomobil ile kamyon çarpışması sonucu sürücü hayatını kaybetti.",
        "Zincirleme trafik kazası meydana geldi, yol trafiğe kapatıldı.",
    ],
    NewsCategory.YANGIN: [
        "Evde çıkan yangın itfaiye ekiplerince söndürüldü.",
        "Fabrikada büyük yangın, alevler saatlerce kontrol altına alınamadı.",
        "Orman yangınında hektar alan kül oldu, itfaiye müdahale etti.",
    ],
    NewsCategory.ELEKTRIK_KESINTISI: [
        "Planlı elektrik kesintisi nedeniyle birçok mahalle karanlıkta kaldı.",
        "Trafo arızası sonucu elektrikler kesildi, SEDAŞ ekipleri çalışıyor.",
        "Elektrik kesintisi saatlerce sürdü, vatandaşlar mağdur oldu.",
    ],
    NewsCategory.HIRSIZLIK: [
        "Hırsızlar evi soydu, polis güvenlik kameralarını inceliyor.",
        "Kapkaççı yakalandı, çalınan cüzdan sahibine teslim edildi.",
        "Oto hırsızlığı şüphelisi suçüstü yakalanarak gözaltına alındı.",
    ],
    NewsCategory.KULTUREL_ETKINLIK: [
        "Büyük konser etkinliği düzenlendi, binlerce kişi katıldı.",
        "Tiyatro festivali başladı, birçok oyun sahnelenecek.",
        "Sanat sergisi açıldı, eserler ücretsiz ziyaret edilebilecek.",
    ],
}


class NewsClassifier:

    _nlp_model = None
    _anchor_embeddings = None

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
    def _get_nlp_model(cls):
        """Lazy-load sentence-transformers modeli (DuplicateDetector ile aynı model)."""
        if cls._nlp_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._nlp_model = SentenceTransformer(
                    "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr"
                )
                print("[Classifier] NLP modeli yüklendi (sentence-transformers).")
            except Exception as e:
                print(f"[Classifier] NLP modeli yüklenemedi: {e}")
                return None
        return cls._nlp_model

    @classmethod
    def _get_anchor_embeddings(cls):
        """Anchor cümlelerinin embedding'lerini hesapla ve cache'le."""
        if cls._anchor_embeddings is not None:
            return cls._anchor_embeddings

        model = cls._get_nlp_model()
        if model is None:
            return None

        cls._anchor_embeddings = {}
        for category, anchors in CATEGORY_ANCHORS.items():
            embeddings = model.encode(anchors, show_progress_bar=False)
            # Ortalama embedding (centroid)
            cls._anchor_embeddings[category] = np.mean(embeddings, axis=0)

        return cls._anchor_embeddings

    @classmethod
    def _nlp_classify(cls, title: str, content: str) -> tuple[NewsCategory | None, float]:
        """
        sentence-transformers ile semantik sınıflandırma.
        Kural tabanlı sonuç yetersiz kaldığında fallback olarak çalışır.
        """
        model = cls._get_nlp_model()
        anchor_embeddings = cls._get_anchor_embeddings()
        if model is None or anchor_embeddings is None:
            return None, 0.0

        # Performans için NLP'ye gönderilen metni daha da kısa tutuyoruz (500 -> 250 karakter)
        text = f"{title} {content[:250]}"
        text_embedding = model.encode(text, show_progress_bar=False)

        from sklearn.metrics.pairwise import cosine_similarity

        best_category = None
        best_score = -1.0

        for category, anchor_emb in anchor_embeddings.items():
            sim = cosine_similarity(
                [text_embedding], [anchor_emb]
            )[0][0]
            if sim > best_score:
                best_score = sim
                best_category = category

        # Minimum benzerlik eşiği: 0.35
        if best_score < 0.35:
            return None, best_score

        return best_category, float(best_score)

    @classmethod
    def classify(cls, title: str, content: str) -> tuple[NewsCategory, dict]:
        # Çöp / Genel Başlık Filtresi (örn: sadece "Yangın", "Asayiş", "Foto Galeri")
        if not title or len(title.strip()) < 8 or "kategori" in title.lower() or "galeri" in title.lower():
            return NewsCategory.DIGER, {"_reason": "Çok kısa veya genel/alakasız başlık tespit edildi"}

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

        return NewsCategory.DIGER, scores

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
