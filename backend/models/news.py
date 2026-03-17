from datetime import datetime


class NewsModel:
    """Haber veri modeli"""

    @staticmethod
    def create(title, content, raw_content, category, location, sources, publish_date, embedding=None):
        return {
            "title": title,
            "content": content,
            "raw_content": raw_content,
            "category": category,
            "location": location,
            "sources": sources if isinstance(sources, list) else [sources],
            "publish_date": publish_date,
            "embedding": embedding,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

    @staticmethod
    def create_source(site_name, url):
        return {
            "site_name": site_name,
            "url": url,
            "scraped_at": datetime.now(),
        }

    @staticmethod
    def create_location(text=None, district=None, latitude=None, longitude=None):
        loc = {
            "text": text,
            "district": district,
            "coordinates": None,
        }
        if latitude is not None and longitude is not None:
            loc["coordinates"] = {
                "type": "Point",
                "coordinates": [longitude, latitude],
            }
        return loc
