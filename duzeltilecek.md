# Kocaeli Haber İzleme - Proje Düzeltme ve Geliştirme Yönergesi

## 1. Proje Özeti ve Mevcut Teknik Altyapı
Bu bölüm, sistemi okuyacak ajanların tüm projeyi analiz etme maliyetini sıfırlamak için özetlenmiştir:
- **Backend:** Python, Flask, MongoDB. (Scraping için BeautifulSoup/lxml kullanılıyor).
- **Frontend:** Vanilla JS, HTML, CSS (Leaflet veya benzeri harita kütüphanesi).
- **Mevcut Durum:** Konum çıkarma (`backend/processing/location_extractor.py`) ve Kategori sınıflandırma (`backend/processing/classifier.py`) işlemleri tamamen **Kural Tabanlı (Rule-Based)**, hardcoded listeler ve dize eşleştirme (Regex) kullanılarak yapılmaktadır.
- **Beklenti:** Mevcut kurallar çöpe atılmadan, hatalı eşleşmeleri çözmek adına Hibrit NLP modelinin entegre edilmesi ve aşağıdaki spesifik UI/Mantıksal hataların sırasıyla çözülmesidir.

## 2. Mimari Geliştirme: Hibrit NLP Entegrasyonu (Öncelikli)
Hoca geri bildirimi doğrultusunda, mevcut kural tabanlı sistem bozulmadan "Fallback (Destek)" mantığıyla NLP sisteme entegre edilecektir:
- **[ ] Görev:** `classifier.py` ve `location_extractor.py` dosyalarında, mevcut regex ve kural eşleşmesi başarısız olduğunda veya şüpheli (Diğer, belirsiz cümle vb.) sonuçlar döndüğünde **spaCy** (NER - Konum tespiti için) veya **sentence-transformers** (Metin Bağlamı/Sınıflandırma için) çalışmalıdır.
- **[ ] Fayda:** Film özetindeki hırsızlık kelimeleri ile gerçek hırsızlık haberlerini ayırt etme, daha esnek adres/nokta tespiti sağlama.

## 3. UI ve Harita Optimizasyonları (Frontend)
- **[ ] Manuel Başlatma Butonu:** Arayüze "Haberleri Çek" tarzında estetik duran bir buton eklenecek. Bu butona tıklandığında önce Veritabanı (DB) sıfırlanacak, ardından scraper pipeline tetiklenip harita güncellenecek.
- **[ ] 'Son Haberler' Kartlarının Düzenlenmesi:** Sağ/Sol paneldeki haber listesi sadece başlık olarak kalmayacak. Haberler tıklanabilir olacak, konum bilgisi de net şekilde görünecek. (`.claude/rules` klasöründeki frontend standartlarına uyulacak).
- **[ ] Filtre/Harita Senkronizasyonu Hatalarının Giderilmesi:** Örn; Trafik kazası filtresinde 10 haber sayılmasına rağmen haritada 4 marker çıkması durumu çözülecek. Haberin detayı yoksa listede de mi gösterilmeyecek, yoksa aynı konumdaki haberler tek marker üst üste mi biniyor mantığı (optimizasyon sıkıntısı) analiz edilip düzeltilecek.

## 4. Mantıksal Sınıflandırma Hata Ayıklaması (False-Positive Engelleme)
- **[ ] Kültürel Etkinlikler Optimizasyonu:** `classifier.py` içindeki etkinlik kelime listeleri optimize edilecek. Gerçek dışı eşleşmeler engellenecek.
- **[ ] Hırsızlık vs. Genel Haber Çakışması:** "Sinema salonunda 6 yeni film" gibi bağlam dışı haberlerin Hırsızlık kategorisine düşmesi NLP entegrasyonu (semantic analiz) ile filtrelenip engellenecek.
- **[ ] Yangın Haberleri Hataları:** Yangın kategorisine düşen alakasız, başlıksız ve tıklandığında genel panele atan bozuk veri kaynakları tespit edilecek; scraper veya classifier düzeyinde bu hatalı metinler drop edilecek (atlanacak).

## 5. Duplicate (Kopya) Haberlerin Birleştirilmesi
- **[ ] Aynı Olayı Anlatan Haberlerin Gruplanması:** Farklı haber sitelerinin yayınladığı aynı olaylar (Örn: İki ayrı başlıkla paylaşılan "Gebze'de Kurye Kazası") tespit edilip tek bir olay olarak veritabanında veya backend servisinde birleştirilecek (`services/duplicate_detector.py` optimize edilecek).
- **[ ] InfoWindow (Harita Pop-up) Kurallarının Uygulanması:** (KRİTİK KURAL). Gruplanan haberler haritada tek marker altında toplanacak. Marker tıklandığında frontend tarafında `sources` dizisi (array) `.map()` fonksiyonu ile dönülerek, mevcut tüm gazeteler/başlıklar alt alta, her biri için "Habere Git" butonu bulunacak şekilde basılmak zorundadır.

## 6. Proje Standartları
- **[ ] Kural Dosyası Kontrolü:** Tüm görevler yapılırken `.claude/rules` klasörü içerisindeki yapı analiz edilmeli ve yeni kodlar bu kural dokümanlarına/yapısına harfiyen uymalıdır. Hatasız clean code prensibi uygulanmalıdır. 