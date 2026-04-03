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
    NewsCategory.TRAFIK_KAZASI: [
        "trafik kazası", "kaza yaptı", "kazası", "kazada", "kazaya", "kaza!", "kaza",
        "çarpıştı", "çarpışma", "çarpışması", "zincirleme kaza", "bariyerlere çarptı", 
        "araç devrildi", "tır devrildi", "kamyon devrildi", "motosiklet devrildi",
        "araç kazası", "otomobil çarpıştı", "feci kaza", "şarampole", "yoldan çıktı", "takla attı", "motosiklet kazası", "trafik"
    ],
    NewsCategory.YANGIN: [
        "yangın", "yandı", "alev aldı", "alev alev", "itfaiye müdahale", "alev", "itfaiye",
        "söndürüldü", "soğutma çalışması", "çatıda yangın", "trafo yangını", 
        "alevlere teslim", "kül oldu", "kundaklama", "kundaklandı", "orman yangını", "kundak"
    ],
    NewsCategory.ELEKTRIK_KESINTISI: [
        "elektrik kesintisi", "planlı kesinti", "elektrikler kesilecek", 
        "elektrikler kesildi", "enerji verilemeyecek", "trafo arızası", 
        "sedaş duyurdu", "karanlıkta kaldı", "elektriksiz", "sedaş", "elektrikler", "elektrik", "kesinti"
    ],
    NewsCategory.HIRSIZLIK: [
        "hırsız", "hırsızlık", "çaldı", "çalındı", "çaldılar", "yağma", "çalan",
        "dolandırıcılık", "dolandırıcı", "dolandırıldı", "kablo vurgunu", 
        "soygun", "gasp", "kapkaç", "dolandır"
    ],
    NewsCategory.KULTUREL_ETKINLIK: [
        "konseri", "konser", "tiyatro", "sergi", "festival", "sahne alacak", 
        "SDKM", "Kongre Merkezi", "Kütüphane Haftası", "sanat etkinliği", 
        "müzik dinletisi", "imza günü", "atölye çalışması", "oyun sahnelendi", "kütüphane", "etkinlik", "gösteri"
    ],
}

# Çakışma durumunda öncelik sırası: Yangın > Trafik Kazası > Hırsızlık > Elektrik Kesintisi > Kültürel Etkinlikler
PRIORITY_ORDER = [
    NewsCategory.YANGIN,
    NewsCategory.TRAFIK_KAZASI,
    NewsCategory.HIRSIZLIK,
    NewsCategory.ELEKTRIK_KESINTISI,
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
    def _calculate_score(title: str, first_sentence: str, rest_content: str, keywords: list) -> tuple[float, bool]:
        """Ağırlıklı (Konumsal) skor hesaplar: Başlık (10), İlk Cümle (4), Kalan İçerik (1)"""
        import re
        score = 0.0
        has_match = False
        
        # Olasılık ve şart bildiren negatif kullanımları çıkar ("yangın çıksa", "kaza olursa" vb.)
        neg_patterns = [
            r'(?i)\b\w+\s+(?:riski|tehlikesi|çıksa|olursa|çıkarsa|tatbikatı|şüphesi|iddiası|önlemi|ihtimali|edebilirdi)\b',
            r'(?i)\b(?:yangın|kaza|kesinti|hırsızlık)\s+(?:çıksa|olursa|tehlikesi|riski|tatbikatı|ihtimali)\b'
        ]
        
        def _clean_text(txt):
            for p in neg_patterns:
                txt = re.sub(p, "", txt)
            return txt

        title = _clean_text(title)
        first_sentence = _clean_text(first_sentence)
        rest_content = _clean_text(rest_content)
        
        def _match(word, txt):
            if " " in word or not word.isalnum() or "-" in word:
                return word.lower() in txt.lower()
            pattern = r'(?u)\b' + re.escape(word) + r'\b'
            return bool(re.search(pattern, txt, re.IGNORECASE))

        for keyword in keywords:
            matched = False
            # Başlık (10 Puan)
            if _match(keyword, title):
                score += 10.0
                matched = True
            
            # İlk Cümle (4 Puan)
            if _match(keyword, first_sentence):
                score += 4.0
                matched = True
                
            # Kalan İçerik (1 Puan)
            if _match(keyword, rest_content):
                score += 1.0
                matched = True
                
            if matched:
                has_match = True
                
        return score, has_match

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

        # Cümleleri ayırma ve ilk cümleyi bulma
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        first_sentence = sentences[0] if sentences else ""
        rest_content = " ".join(sentences[1:]) if len(sentences) > 1 else ""

        scores = {}
        has_primary_map = {}
        for category in PRIORITY_ORDER:
            keywords = CATEGORY_KEYWORDS[category]
            score, has_match = cls._calculate_score(title, first_sentence, rest_content, keywords)
            scores[category] = score
            has_primary_map[category] = has_match

        # En az bir eşleşmesi (ve en az 4.0 puan) olan kategoriler arasından seç
        # Bu sayede sadece 3. veya 4. paragrafta geçen tek bir kelime haberi kategorize edemez.
        # Ya başlıkta geçmeli (10p), ya ilk cümlede geçmeli (4p).
        candidates = {c: s for c, s in scores.items() if has_primary_map.get(c) and s >= 1.0}

        if not candidates:
            return NewsCategory.DIGER, scores

        best_category = max(candidates, key=candidates.get)

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
        
        # Cümleleri ayırma ve ilk cümleyi bulma
        import re
        sentences = re.split(r'(?<=[.!?])\s+', content.strip())
        first_sentence = sentences[0] if sentences else ""
        rest_content = " ".join(sentences[1:]) if len(sentences) > 1 else ""

        keywords = CATEGORY_KEYWORDS.get(category, [])
        found = []
        for kw in keywords:
            if kw.lower() in title.lower() or kw.lower() in first_sentence.lower() or kw.lower() in rest_content.lower():
                found.append(kw)
        return found
