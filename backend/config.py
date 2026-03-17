import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "kocaeli_haber")

    # Google Maps & Geocoding
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GEOCODING_PROVIDER = os.getenv("GEOCODING_PROVIDER", "nominatim")

    # Flask
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # Scraping
    SCRAPE_DAYS = 3  # Son kaç günün haberlerini çek
    SIMILARITY_THRESHOLD = 0.90  # Duplicate algılama eşiği

    # Kocaeli ilçeleri
    KOCAELI_DISTRICTS = [
        "İzmit", "Gebze", "Darıca", "Körfez", "Gölcük",
        "Başiskele", "Kartepe", "Çayırova", "Dilovası",
        "Derince", "Kandıra", "Karamürsel"
    ]

    # Kocaeli merkez koordinatları
    KOCAELI_CENTER = {
        "lat": 40.7654,
        "lng": 29.9408
    }
