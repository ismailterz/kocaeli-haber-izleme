import sys
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.kocaeli_haber

news = list(db.news.find({"category": "Trafik Kazası"}, {"title": 1, "sources": 1}))
for n in news:
    print(f"Title: {n['title']}")
    for s in n['sources']:
        print(f"  - {s['site_name']}")
    print("-" * 30)
