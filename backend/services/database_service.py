"""
MongoDB veritabanı katmanı.
CRUD işlemleri ve indeksler.
"""

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
        query = {}
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("district"):
                query["location.district"] = filters["district"]
            if filters.get("start_date") and filters.get("end_date"):
                query["publish_date"] = {
                    "$gte": filters["start_date"],
                    "$lte": filters["end_date"]
                }
            elif filters.get("start_date"):
                query["publish_date"] = {"$gte": filters["start_date"]}
            elif filters.get("end_date"):
                query["publish_date"] = {"$lte": filters["end_date"]}

        cursor = self.db.news.find(
            query,
            {"embedding": 0}
        ).sort("publish_date", DESCENDING).skip(skip).limit(limit)

        results = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def get_news_for_map(self, filters: dict = None) -> list:
        query = {"location.coordinates": {"$exists": True, "$ne": None}}
        if filters:
            if filters.get("category"):
                query["category"] = filters["category"]
            if filters.get("district"):
                query["location.district"] = filters["district"]
            if filters.get("start_date") and filters.get("end_date"):
                query["publish_date"] = {
                    "$gte": filters["start_date"],
                    "$lte": filters["end_date"]
                }
            elif filters.get("start_date"):
                query["publish_date"] = {"$gte": filters["start_date"]}
            elif filters.get("end_date"):
                query["publish_date"] = {"$lte": filters["end_date"]}

        cursor = self.db.news.find(
            query,
            {
                "title": 1, "category": 1, "location": 1,
                "publish_date": 1, "sources": 1
            }
        ).sort("publish_date", DESCENDING)

        results = []
        for doc in cursor:
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

    def get_stats(self) -> dict:
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        category_stats = list(self.db.news.aggregate(pipeline))

        district_pipeline = [
            {"$match": {"location.district": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$location.district", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        district_stats = list(self.db.news.aggregate(district_pipeline))

        total = self.db.news.count_documents({})

        return {
            "total": total,
            "by_category": {s["_id"]: s["count"] for s in category_stats},
            "by_district": {s["_id"]: s["count"] for s in district_stats},
        }

    def get_recent_news(self, days: int = 3, limit: int = 20) -> list:
        since = datetime.now() - timedelta(days=days)
        return self.get_all_news(
            filters={"start_date": since},
            limit=limit
        )

    def clear_all(self):
        self.db.news.drop()
        self.db.geocoding_cache.drop()
        self._ensure_indexes()
