import sys
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.kocaeli_haber

news = list(db.news.find({"category": "Trafik Kazası"}, {"title": 1, "embedding": 1}))
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

for i in range(len(news)):
    for j in range(i+1, len(news)):
        if "embedding" in news[i] and "embedding" in news[j]:
            sim = cosine_similarity([news[i]["embedding"]], [news[j]["embedding"]])[0][0]
            if sim > 0.75:
                print(f"{sim:.3f} | {news[i]['title']} <--> {news[j]['title']}")
