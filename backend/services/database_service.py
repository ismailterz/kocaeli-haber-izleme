"""
MongoDB veritabanı katmanı.
CRUD işlemleri ve indeksler.
"""

import random
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT

from config import Config


class DatabaseService:

    def __init__(self):
        self.client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
        self.db = self.client[Config.MONGO_DB_NAME]
        try:
            self._ensure_indexes()
        except Exception as e:
            print(f"[DB] İndeks oluşturma uyarısı (muhtemelen auth gerekli): {e}")

    def _ensure_indexes(self):
        self.db.news.create_index([("title", TEXT), ("content", TEXT)])
        self.db.news.create_index([("category", ASCENDING)])
        self.db.news.create_index([("publish_date", DESCENDING)])
        self.db.news.create_index([("location.district", ASCENDING)])
        self.db.news.create_index([("sources.url", ASCENDING)], unique=True, sparse=True)
        self.db.news.create_index([("location.coordinates", "2dsphere")], sparse=True)
        self.db.news.create_index([("created_at", DESCENDING)])

        self.db.geocoding_cache.create_index([("location_text", ASCENDING)], unique=True)

    def insert_news(self, news_doc: dict) -> str:
        result = self.db.news.insert_one(news_doc)
        return str(result.inserted_id)

    def update_news_sources(self, news_id, new_source: dict):
        self.db.news.update_one(
            {"_id": ObjectId(news_id) if isinstance(news_id, str) else news_id},
            {
                "$push": {"sources": new_source},
                "$set": {"updated_at": datetime.now()}
            }
        )

    def news_url_exists(self, url: str) -> bool:
        return self.db.news.find_one({"sources.url": url}) is not None

    def get_all_news(self, filters: dict = None, limit: int = 100, skip: int = 0) -> list:
        query = self._build_query(filters)

        cursor = self.db.news.find(
            query,
            {"embedding": 0}
        ).sort("publish_date", DESCENDING).skip(skip).limit(limit)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def count_news(self, filters: dict = None) -> int:
        query = self._build_query(filters)
        return self.db.news.count_documents(query)

    def get_news_for_map(self, filters: dict = None) -> list:
        query = {"location.coordinates": {"$exists": True, "$ne": None}}
        query.update(self._build_query(filters))

        cursor = self.db.news.find(
            query,
            {
                "title": 1, "category": 1, "location": 1,
                "publish_date": 1, "sources": 1
            }
        ).sort("publish_date", DESCENDING)

        results = []
        for doc in cursor:
            coords = doc.get("location", {}).get("coordinates", {}).get("coordinates", [])
            if coords and len(coords) >= 2:
                lng, lat = coords
                if not self._is_on_land(lat, lng):
                    continue
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def get_news_by_id(self, news_id: str) -> dict | None:
        doc = self.db.news.find_one(
            {"_id": ObjectId(news_id)},
            {"embedding": 0}
        )
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def get_stats(self, filters: dict = None) -> dict:
        query = self._build_query(filters)

        pipeline = [
            {"$match": query} if query else {"$match": {}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        category_stats = list(self.db.news.aggregate(pipeline))

        district_query = dict(query) if query else {}
        district_query["location.district"] = {"$exists": True, "$ne": None}
        district_pipeline = [
            {"$match": district_query},
            {"$group": {"_id": "$location.district", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        district_stats = list(self.db.news.aggregate(district_pipeline))

        total = self.db.news.count_documents(query if query else {})

        return {
            "total": total,
            "by_category": {s["_id"]: s["count"] for s in category_stats},
            "by_district": {s["_id"]: s["count"] for s in district_stats},
        }

    def get_source_category_stats(self, filters: dict | None) -> dict:
        """Her kaynak sitesi × kategori için sayım (birleşik haberde her kaynak ayrı satır)."""
        query = self._build_query(filters)
        match_stage = {"$match": query} if query else {"$match": {}}
        pipeline = [
            match_stage,
            {"$unwind": "$sources"},
            {
                "$group": {
                    "_id": {
                        "site": {"$ifNull": ["$sources.site_name", "Bilinmeyen"]},
                        "category": {"$ifNull": ["$category", "Diğer"]},
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.site": 1, "_id.category": 1}},
        ]
        rows_raw = list(self.db.news.aggregate(pipeline))
        rows = [
            {
                "site": r["_id"]["site"],
                "category": r["_id"]["category"],
                "count": r["count"],
            }
            for r in rows_raw
        ]
        by_site: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for r in rows:
            by_site[r["site"]] = by_site.get(r["site"], 0) + r["count"]
            by_category[r["category"]] = by_category.get(r["category"], 0) + r["count"]
        return {
            "rows": rows,
            "by_site": by_site,
            "by_category": by_category,
        }

    @staticmethod
    def _build_query(filters: dict | None) -> dict:
        query: dict = {}
        if not filters:
            return query
        # category: single veya çoklu
        categories = filters.get("categories")
        category = filters.get("category")
        if categories and isinstance(categories, list):
            query["category"] = {"$in": categories}
        elif category:
            query["category"] = category

        # Tarih aralığı
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        if start_date and end_date:
            query["publish_date"] = {"$gte": start_date, "$lte": end_date}
        elif start_date:
            query["publish_date"] = {"$gte": start_date}
        elif end_date:
            query["publish_date"] = {"$lte": end_date}

        district = filters.get("district")
        if district:
            query["location.district"] = district

        return query

    def fix_sea_coordinates(self) -> dict:
        """Deniz üzerine düşen koordinatları ilçe merkezine taşır."""
        stats = {"fixed": 0, "removed": 0, "ok": 0}
        for doc in self.db.news.find({"location.coordinates": {"$ne": None}},
                                     {"_id": 1, "location": 1}):
            coords = doc.get("location", {}).get("coordinates", {})
            if not coords or not coords.get("coordinates"):
                continue
            lng, lat = coords["coordinates"]
            if self._is_on_land(lat, lng):
                stats["ok"] += 1
                continue

            district = doc.get("location", {}).get("district")
            if district:
                center = Config.DISTRICT_CENTERS.get(district)
                if center:
                    new_lat = center["lat"] + random.uniform(-0.005, 0.005)
                    new_lng = center["lng"] + random.uniform(-0.005, 0.005)
                    self.db.news.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"location.coordinates.coordinates": [new_lng, new_lat]}}
                    )
                    stats["fixed"] += 1
                    continue

            self.db.news.update_one(
                {"_id": doc["_id"]},
                {"$set": {"location.coordinates": None}}
            )
            stats["removed"] += 1

        return stats

    def fix_districts_by_coordinates(self) -> dict:
        """Her haberin koordinatına göre en yakın ilçe merkezini bularak district alanını günceller."""
        import math
        stats = {"updated": 0, "already_ok": 0}

        for doc in self.db.news.find(
            {"location.coordinates": {"$ne": None}},
            {"_id": 1, "location": 1}
        ):
            coords = doc.get("location", {}).get("coordinates", {})
            if not coords or not coords.get("coordinates"):
                continue
            lng, lat = coords["coordinates"]

            min_dist = float("inf")
            nearest = None
            for district, center in Config.DISTRICT_CENTERS.items():
                dlat = lat - center["lat"]
                dlng = lng - center["lng"]
                dist = math.sqrt(dlat ** 2 + dlng ** 2)
                if dist < min_dist:
                    min_dist = dist
                    nearest = district

            current = doc.get("location", {}).get("district")
            if nearest == current:
                stats["already_ok"] += 1
            else:
                self.db.news.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"location.district": nearest}}
                )
                stats["updated"] += 1

        return stats

    @staticmethod
    def _is_on_land(lat: float, lng: float) -> bool:
        if not ((40.4 <= lat <= 41.2) and (29.2 <= lng <= 30.5)):
            return False
        if 29.35 <= lng <= 29.97:
            south = 40.700 + (lng - 29.35) * 0.025
            north = 40.745 + (lng - 29.35) * 0.03
            if south < lat < north:
                return False
        return True

    def reclassify_all_news(self) -> dict:
        """Tüm haberleri güncel sınıflandırıcı ile yeniden kategorize eder."""
        from processing.classifier import NewsClassifier, NewsCategory

        stats = {"updated": 0, "skipped_diger": 0, "unchanged": 0}

        for doc in self.db.news.find({}, {"_id": 1, "title": 1, "content": 1, "category": 1}):
            title = doc.get("title", "")
            content = doc.get("content", "")
            old_category = doc.get("category", "")

            new_category, _ = NewsClassifier.classify(title, content)

            # Diğer: kaydı silme (yanlış sınıflandırma veya boş DB ile haritayı bozmamak için)
            if new_category == NewsCategory.DIGER:
                stats["skipped_diger"] += 1
                continue
            if new_category.value != old_category:
                self.db.news.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"category": new_category.value}}
                )
                stats["updated"] += 1
            else:
                stats["unchanged"] += 1

        return stats

    def clear_all(self):
        self.db.news.drop()
        self.db.geocoding_cache.drop()
        self._ensure_indexes()
