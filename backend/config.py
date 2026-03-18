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

    DISTRICT_CENTERS = {
        "İzmit":      {"lat": 40.7654, "lng": 29.9408},
        "Gebze":      {"lat": 40.8027, "lng": 29.4307},
        "Darıca":     {"lat": 40.7693, "lng": 29.3725},
        "Körfez":     {"lat": 40.7245, "lng": 29.7390},
        "Gölcük":     {"lat": 40.7175, "lng": 29.8195},
        "Başiskele":  {"lat": 40.7213, "lng": 29.8830},
        "Kartepe":    {"lat": 40.6849, "lng": 30.0536},
        "Çayırova":   {"lat": 40.8258, "lng": 29.3750},
        "Dilovası":   {"lat": 40.7789, "lng": 29.5369},
        "Derince":    {"lat": 40.7553, "lng": 29.8130},
        "Kandıra":    {"lat": 41.0700, "lng": 30.1500},
        "Karamürsel": {"lat": 40.6911, "lng": 29.6140},
    }
