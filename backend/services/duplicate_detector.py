"""
Duplicate tespiti modülü.
Embedding tabanlı benzerlik analizi ile tekrar haberleri tespit eder.
Eşik: %90
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from config import Config


class DuplicateDetector:

    def __init__(self, db=None):
        self.db = db
        self.model = None
        self.threshold = getattr(Config, "SIMILARITY_THRESHOLD", 0.9)
        # Hız için NLP/Embedding modeli varsayılan olarak devre dışı bırakıldı
        self.enabled = getattr(Config, "EMBEDDINGS_ENABLED", False)

    def _get_model(self):
        if not self.enabled:
            return None
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("emrecan/bert-base-turkish-cased-mean-nli-stsb-tr")
        return self.model

    def get_embedding(self, text: str) -> list[float]:
        if not self.enabled:
            return []
        model = self._get_model()
        if model is None:
            return []
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()

    def find_duplicate(self, title: str, content: str, category: str = None) -> dict | None:
        """
        Veritabanındaki mevcut haberlere karşı benzerlik kontrolü yapar.
        Aynı kategori için eşiği düşürerek (örn: 0.82) tekrar haberleri daha agresif tespit eder.
        """
        if (self.db is None) or (not self.enabled):
            return None

        # Başlık farklılıklarının benzerliği düşürmemesi için saf haber içeriği kullanılıyor
        text = f"{content[:1000]}"
        new_embedding = self.get_embedding(text)

        # Sadece aynı kategorideki haberlerle karşılaştırarak hem hız hem doğruluk sağlarız
        query = {"embedding": {"$exists": True, "$ne": None}}
        if category:
            query["category"] = category
            
        existing_news = list(self.db.news.find(
            query,
            {"_id": 1, "title": 1, "embedding": 1, "sources": 1}
        ))

        if not existing_news:
            return None

        existing_embeddings = []
        valid_news = []
        for news in existing_news:
            if news.get("embedding"):
                existing_embeddings.append(news["embedding"])
                valid_news.append(news)

        if not existing_embeddings:
            return None

        new_emb_array = np.array([new_embedding])
        existing_emb_array = np.array(existing_embeddings)

        similarities = cosine_similarity(new_emb_array, existing_emb_array)[0]

        max_idx = np.argmax(similarities)
        max_similarity = similarities[max_idx]

        # Proje kurallarına göre %90 ve üzeri benzerlik baz alınmalıdır.
        effective_threshold = 0.90

        if max_similarity >= effective_threshold:
            return {
                "news_id": valid_news[max_idx]["_id"],
                "title": valid_news[max_idx]["title"],
                "similarity": float(max_similarity),
                "sources": valid_news[max_idx].get("sources", []),
            }

        return None

    def compute_embedding_for_text(self, title: str, content: str) -> list[float]:
        if not self.enabled:
            return []
        text = f"{content[:1000]}"
        return self.get_embedding(text)
