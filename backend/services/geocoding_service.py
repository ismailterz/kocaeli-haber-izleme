"""
Geocoding servisi.
Konum metninden koordinat dönüşümü yapar. Aynı konum için cache kullanır.
"""

import time

from geopy.geocoders import Nominatim, GoogleV3
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from pymongo import MongoClient

from config import Config


class GeocodingService:

    def __init__(self, db=None):
        self.db = db
        self.provider = Config.GEOCODING_PROVIDER

        if self.provider == "google" and Config.GOOGLE_MAPS_API_KEY:
            self.geocoder = GoogleV3(api_key=Config.GOOGLE_MAPS_API_KEY)
        else:
            self.geocoder = Nominatim(
                user_agent="kocaeli-haber-izleme/1.0",
                timeout=10
            )

    def _get_cached(self, location_text: str) -> dict | None:
        if self.db is None:
            return None
        cache = self.db.geocoding_cache.find_one({"location_text": location_text})
        if cache:
            return {
                "latitude": cache["latitude"],
                "longitude": cache["longitude"],
            }
        return None

    def _set_cache(self, location_text: str, latitude: float, longitude: float):
        if self.db is None:
            return
        self.db.geocoding_cache.update_one(
            {"location_text": location_text},
            {"$set": {
                "location_text": location_text,
                "latitude": latitude,
                "longitude": longitude,
            }},
            upsert=True
        )

    def geocode(self, location_text: str) -> dict | None:
        if not location_text:
            return None

        cached = self._get_cached(location_text)
        if cached:
            if self._is_on_land(cached["latitude"], cached["longitude"]):
                return cached
            return None

        if self.provider != "google":
            time.sleep(1.1)

        try:
            location = self.geocoder.geocode(
                location_text,
                exactly_one=True,
                language="tr"
            )

            if location:
                lat = location.latitude
                lng = location.longitude

                if not self._is_in_kocaeli_region(lat, lng):
                    kocaeli_text = f"{location_text}, Kocaeli, Türkiye"
                    if self.provider != "google":
                        time.sleep(1.1)
                    location = self.geocoder.geocode(
                        kocaeli_text,
                        exactly_one=True,
                        language="tr"
                    )
                    if location:
                        lat = location.latitude
                        lng = location.longitude

                if location and self._is_on_land(lat, lng):
                    self._set_cache(location_text, lat, lng)
                    return {"latitude": lat, "longitude": lng}

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"[Geocoding] Hata: {location_text} - {e}")
        except Exception as e:
            print(f"[Geocoding] Beklenmeyen hata: {location_text} - {e}")

        return None

    @staticmethod
    def _is_in_kocaeli_region(lat: float, lng: float) -> bool:
        return (40.4 <= lat <= 41.1) and (29.2 <= lng <= 30.4)

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
