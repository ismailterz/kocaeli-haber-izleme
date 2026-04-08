# Kocaeli Haber İzleme (Haber Haritası)

Kocaeli’deki haber sitelerinden içerikleri toplayıp **MongoDB**’ye kaydeden; haberleri **kategori** ve **ilçe** bazında zenginleştirip **Google Maps** üzerinde harita olarak gösteren bir izleme uygulaması.

## Özellikler

- **Harita arayüzü**: Haberleri konuma göre marker’larla gösterir.
- **Filtreleme**: Tarih aralığı, ilçe ve (çoklu) kategori filtreleri.
- **İstatistikler**: Toplam, kategori/ilçe kırılımı.
- **Kaynak özeti**: Kaynak sitesi × kategori dağılımı tablosu.
- **Scraping pipeline**: Kaynaklardan haber toplama, çoklu kaynak birleştirme ve tekrar kontrolü.
- **Otomatik çalışma**: Backend açıldığında **6 saatte bir** scraping tetiklenir.
- **Veri düzeltme işleri**: Uygulama açılışında koordinat/ilçe/kategori düzeltmeleri çalışır.

## Teknoloji

- **Backend**: Flask + PyMongo
- **Frontend**: Vanilla JS + HTML/CSS (Flask static üzerinden servis edilir)
- **DB**: MongoDB
- **Harita**: Google Maps JavaScript API

## Kurulum

### 1) Gereksinimler

- Python 3.11+ (önerilir)
- MongoDB (lokalde veya remote)
- Google Maps API Key (harita için)

### 2) Ortam değişkenleri (`.env`)

Proje kökünde bir `.env` dosyası kullanılabilir. Backend `dotenv` ile otomatik yükler.

Zorunlu/opsiyonel değişkenler:

- **MONGO_URI**: Mongo bağlantısı (varsayılan: `mongodb://localhost:27017`)
- **MONGO_DB_NAME**: DB adı (varsayılan: `kocaeli_haber`)
- **GOOGLE_MAPS_API_KEY**: Google Maps JS API anahtarı (varsayılan: boş)
- **FLASK_PORT**: Backend portu (varsayılan: `5001`)
- **FLASK_DEBUG**: `True/False` (varsayılan: `True`)
- **SCRAPE_DAYS**: Son kaç gün taransın (varsayılan: `3`)
- **SCRAPE_START_DATE / SCRAPE_END_DATE**: ISO datetime ile özel aralık (opsiyonel)
- **REQUEST_DELAY_SECONDS**: İstekler arası gecikme (varsayılan: `0.4`)
- **MAX_LINKS_PER_SITE**: Site başına maksimum link (varsayılan: `500`)
- **EMBEDDINGS_ENABLED**: Duplicate tespiti için embedding aç/kapat (varsayılan: `true`)

### 3) Backend’i çalıştırma

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Uygulama varsayılan olarak `http://localhost:5001` adresinde ayağa kalkar.

> Frontend ayrıca ayrı build gerektirmez; Flask, `frontend/` klasörünü statik olarak servis eder.

## Kullanım

### Web arayüzü

- Ana sayfa: `GET /`
- Filtreler (tarih/ilçe/kategori) sol panelden uygulanır.
- “**Veritabanını sıfırla ve tara**” butonu tüm kayıtları temizleyip yeniden tarama başlatır.

### API

Base path: `/api`

- **GET `/api/news`**: Liste (query: `category`, `categories`, `district`, `start_date`, `end_date`, `limit`, `skip`)
- **GET `/api/news/map`**: Harita için optimize liste
- **GET `/api/news/<id>`**: Tek haber
- **GET `/api/stats`**: Toplam + kategori/ilçe istatistikleri
- **GET `/api/source-stats`**: Kaynak × tür dağılımı
- **GET `/api/districts`**: İlçe listesi
- **GET `/api/categories`**: Kategori listesi
- **POST `/api/scrape`**: Scraping tetikle
  - Body (opsiyonel): `{"reset_database": true}`

## Proje yapısı

```text
.
├─ backend/
│  ├─ app.py                  # Flask giriş noktası + scheduler
│  ├─ config.py               # Ortam ayarları
│  ├─ routes/api.py           # API endpoint’leri
│  ├─ services/               # DB, scraping pipeline, duplicate detection vb.
│  └─ processing/             # Sınıflandırma, konum çıkarımı vb.
└─ frontend/
   ├─ index.html
   ├─ app.js
   └─ style.css
```

## Notlar

- **Scheduler**: Backend çalışırken scraping otomatik olarak **6 saatte bir** başlatılır.
- **Tarih filtresi kuralı**: API tarafında start/end verilmezse “**son 3 takvim günü**” penceresi uygulanır.

