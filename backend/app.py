"""
Flask uygulama giriş noktası.
"""

from flask import Flask, send_from_directory
from flask_cors import CORS

from config import Config
from routes.api import api_bp


def create_app():
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    CORS(app)

    app.register_blueprint(api_bp)

    @app.after_request
    def add_no_cache(response):
        if response.content_type and ("javascript" in response.content_type or "text/html" in response.content_type):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

    @app.route("/")
    def index():
        import os
        path = os.path.join(app.static_folder, "index.html")
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        key = Config.GOOGLE_MAPS_API_KEY or ""
        html = html.replace("GOOGLE_MAPS_API_KEY", key)
        return html

    @app.route("/<path:path>")
    def serve_static(path):
        return send_from_directory(app.static_folder, path)

    return app


def fix_data_on_startup():
    try:
        from services.database_service import DatabaseService
        db = DatabaseService()
        result = db.fix_sea_coordinates()
        print(f"[Startup] Koordinat kontrolü: {result}")
        district_result = db.fix_districts_by_coordinates()
        print(f"[Startup] İlçe düzeltme (koordinata göre): {district_result}")
        reclass_result = db.reclassify_all_news()
        print(f"[Startup] Kategori düzeltme: {reclass_result}")
    except Exception as e:
        print(f"[Startup] Startup hatası: {e}")


if __name__ == "__main__":
    app = create_app()
    fix_data_on_startup()
    app.run(
        host="0.0.0.0",
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
