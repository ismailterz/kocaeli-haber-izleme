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
        self.threshold = Config.SIMILARITY_THRESHOLD
        self.enabled = getattr(Config, "EMBEDDINGS_ENABLED", True)

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

    def find_duplicate(self, title: str, content: str) -> dict | None:
        """
        Veritabanındaki mevcut haberlere karşı benzerlik kontrolü yapar.
        %90 veya üzerinde benzerlik varsa duplicate olarak işaretler.
        """
        if (self.db is None) or (not self.enabled):
            return None

        text = f"{title} {content[:500]}"
        new_embedding = self.get_embedding(text)

        existing_news = list(self.db.news.find(
            {"embedding": {"$exists": True, "$ne": None}},
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

        if max_similarity >= self.threshold:
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
        text = f"{title} {content[:500]}"
        return self.get_embedding(text)
