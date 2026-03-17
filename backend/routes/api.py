"""
Flask API endpoint'leri.
Haberler, filtreleme, istatistik.
"""

from datetime import datetime
from flask import Blueprint, jsonify, request

from services.database_service import DatabaseService

api_bp = Blueprint("api", __name__, url_prefix="/api")

db_service = None


def init_db():
    global db_service
    if db_service is None:
        db_service = DatabaseService()
    return db_service


@api_bp.route("/news", methods=["GET"])
def get_news():
    try:
        db = init_db()
        filters = _parse_filters(request.args)
        limit = request.args.get("limit", 100, type=int)
        skip = request.args.get("skip", 0, type=int)

        news = db.get_all_news(filters=filters, limit=limit, skip=skip)
        _serialize_dates(news)

        return jsonify({"status": "ok", "data": news, "count": len(news)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": [], "count": 0})


@api_bp.route("/news/map", methods=["GET"])
def get_news_for_map():
    try:
        db = init_db()
        filters = _parse_filters(request.args)

        news = db.get_news_for_map(filters=filters)
        _serialize_dates(news)

        return jsonify({"status": "ok", "data": news, "count": len(news)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e), "data": [], "count": 0})


@api_bp.route("/news/<news_id>", methods=["GET"])
def get_news_by_id(news_id):
    try:
        db = init_db()
        news = db.get_news_by_id(news_id)
        if not news:
            return jsonify({"status": "error", "message": "Haber bulunamadı"}), 404

        _serialize_dates([news])
        return jsonify({"status": "ok", "data": news})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    try:
        db = init_db()
        stats = db.get_stats()
        return jsonify({"status": "ok", "data": stats})
    except Exception as e:
        return jsonify({"status": "ok", "data": {"total": 0, "by_category": {}, "by_district": {}}})


@api_bp.route("/districts", methods=["GET"])
def get_districts():
    from config import Config
    return jsonify({
        "status": "ok",
        "data": Config.KOCAELI_DISTRICTS
    })


@api_bp.route("/categories", methods=["GET"])
def get_categories():
    from processing.classifier import NewsCategory
    categories = [c.value for c in NewsCategory if c != NewsCategory.DIGER]
    return jsonify({"status": "ok", "data": categories})


@api_bp.route("/scrape", methods=["POST"])
def trigger_scrape():
    from services.scraping_pipeline import ScrapingPipeline
    pipeline = ScrapingPipeline()
    result = pipeline.run()
    return jsonify({"status": "ok", "data": result})


def _parse_filters(args) -> dict:
    filters = {}

    category = args.get("category")
    if category:
        filters["category"] = category

    district = args.get("district")
    if district:
        filters["district"] = district

    start_date = args.get("start_date")
    if start_date:
        try:
            filters["start_date"] = datetime.fromisoformat(start_date)
        except ValueError:
            pass

    end_date = args.get("end_date")
    if end_date:
        try:
            filters["end_date"] = datetime.fromisoformat(end_date)
        except ValueError:
            pass

    return filters


def _serialize_dates(news_list: list):
    for news in news_list:
        for key in ["publish_date", "created_at", "updated_at"]:
            if key in news and isinstance(news[key], datetime):
                news[key] = news[key].isoformat()
        if "sources" in news:
            for source in news["sources"]:
                if "scraped_at" in source and isinstance(source["scraped_at"], datetime):
                    source["scraped_at"] = source["scraped_at"].isoformat()
