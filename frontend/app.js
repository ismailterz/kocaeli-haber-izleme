const API_BASE = "/api";

const CATEGORY_CONFIG = {
    "Trafik Kazası": {
        color: "#e74c3c",
        icon: "directions_car",
        cssClass: "trafik",
        markerPath: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
    },
    "Yangın": {
        color: "#e67e22",
        icon: "local_fire_department",
        cssClass: "yangin",
        markerPath: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
    },
    "Elektrik Kesintisi": {
        color: "#f1c40f",
        icon: "flash_off",
        cssClass: "elektrik",
        markerPath: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
    },
    "Hırsızlık": {
        color: "#8e44ad",
        icon: "warning",
        cssClass: "hirsizlik",
        markerPath: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
    },
    "Kültürel Etkinlikler": {
        color: "#2ecc71",
        icon: "celebration",
        cssClass: "kultur",
        markerPath: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
    },
};

const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };

let map;
let markers = [];
let infoWindow;

/* ===== Harita Başlatma ===== */
function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: KOCAELI_CENTER,
        zoom: 11,
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
        },
        streetViewControl: false,
        fullscreenControl: true,
        zoomControl: true,
        styles: [
            {
                featureType: "poi",
                elementType: "labels",
                stylers: [{ visibility: "off" }],
            },
        ],
    });

    infoWindow = new google.maps.InfoWindow();

    setDefaultDates();
    loadDistricts();
    loadStats();
    loadAndDisplayNews();
}

/* ===== Tarih Yardımcıları ===== */
function setDefaultDates() {
    const now = new Date();
    const threeDaysAgo = new Date(now);
    threeDaysAgo.setHours(0, 0, 0, 0);
    threeDaysAgo.setDate(threeDaysAgo.getDate() - 2);

    document.getElementById("endDate").value = formatDateForInput(now);
    document.getElementById("startDate").value = formatDateForInput(threeDaysAgo);
}

function formatDateForInput(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

/* ===== API ===== */
async function apiCall(endpoint, params = {}) {
    const url = new URL(`${API_BASE}${endpoint}`, window.location.origin);
    Object.entries(params).forEach(([key, val]) => {
        if (val !== null && val !== undefined && val !== "") {
            url.searchParams.append(key, val);
        }
    });

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API error (${endpoint}):`, error);
        return null;
    }
}

/* ===== Filtreler ===== */
function getSelectedCategories() {
    const checkboxes = document.querySelectorAll("#categoryFilters input:checked");
    return Array.from(checkboxes).map((cb) => cb.value);
}

function getFilters() {
    const filters = {};

    const district = document.getElementById("districtFilter").value;
    if (district) filters.district = district;

    const startEl = document.getElementById("startDate");
    const endEl = document.getElementById("endDate");
    const startDate = startEl.value;
    const endDate = endEl.value;

    const now = new Date();
    const windowStart = new Date(now);
    windowStart.setHours(0, 0, 0, 0);
    windowStart.setDate(windowStart.getDate() - 2);

    const parsedStart = startDate ? new Date(startDate + "T00:00:00") : null;
    const parsedEnd = endDate ? new Date(endDate + "T23:59:59") : null;

    let clampedStart = parsedStart || windowStart;
    let clampedEnd = parsedEnd || now;

    if (clampedStart < windowStart) clampedStart = windowStart;
    if (clampedEnd > now) clampedEnd = now;
    if (clampedEnd < clampedStart) clampedEnd = clampedStart;

    startEl.value = formatDateForInput(clampedStart);
    endEl.value = formatDateForInput(clampedEnd);

    filters.start_date = startEl.value;
    filters.end_date = endEl.value + "T23:59:59";

    return filters;
}

/* ===== İlçeler ===== */
async function loadDistricts() {
    const result = await apiCall("/districts");
    if (!result || !result.data) return;

    const select = document.getElementById("districtFilter");
    result.data.forEach((district) => {
        const option = document.createElement("option");
        option.value = district;
        option.textContent = district;
        select.appendChild(option);
    });
}

/* ===== İstatistikler ===== */
async function loadStats(mapMarkerCount) {
    const filters = getFilters();
    const selectedCategories = getSelectedCategories();
    const result = await apiCall("/stats", {
        ...filters,
        categories: selectedCategories.join(","),
    });
    if (!result || !result.data) return;

    const grid = document.getElementById("statsGrid");
    const stats = result.data;

    const mapCountHtml = mapMarkerCount !== undefined
        ? `<div class="stat-card">
               <div class="stat-value" style="color: #34a853">${mapMarkerCount}</div>
               <div class="stat-label">Haritada Görünen</div>
           </div>`
        : "";

    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.total || 0}</div>
            <div class="stat-label">Toplam Haber</div>
        </div>
        ${mapCountHtml}
        ${Object.entries(stats.by_category || {})
            .map(
                ([cat, count]) => `
            <div class="stat-card">
                <div class="stat-value" style="color: ${CATEGORY_CONFIG[cat]?.color || '#666'}">${count}</div>
                <div class="stat-label">${cat}</div>
            </div>
        `
            )
            .join("")}
    `;
}

/* ===== Ana Yükleme ===== */
async function loadAndDisplayNews() {
    const filters = getFilters();
    const selectedCategories = getSelectedCategories();

    clearMarkers();

    // Harita verisi
    const mapResult = await apiCall("/news/map", filters);
    let mapMarkerCount = 0;
    let mappedNewsIds = new Set();
    
    if (mapResult && mapResult.data) {
        const filteredMapData = mapResult.data.filter((news) =>
            selectedCategories.includes(news.category)
        );
        filteredMapData.forEach((news) => {
            addMarker(news);
            // Sadece koordinatı düzgün (haritada gösterilen) haberlerin ID'sini alıyoruz
            const coords = news.location?.coordinates?.coordinates;
            if (coords && coords.length >= 2 && isOnLand(coords[1], coords[0])) {
                mappedNewsIds.add(news._id);
            }
        });
        mapMarkerCount = markers.length;
    }

    // Liste verisi
    const listResult = await apiCall("/news", { ...filters, limit: 50 });
    if (listResult && listResult.data) {
        // Haritada eksik çıkan noktalarla senkronizasyon için listeyi sadece haritada var olanlarla kısıtlıyoruz
        const filteredListData = listResult.data.filter((news) =>
            selectedCategories.includes(news.category) && mappedNewsIds.has(news._id)
        );
        displayNewsList(filteredListData);
    }

    // İstatistikleri güncelle (harita marker sayısını da gönder)
    loadStats(mapMarkerCount);
}

/* ===== Harita – Kara Parçası Kontrolü ===== */
function isOnLand(lat, lng) {
    if (lat < 40.4 || lat > 41.2 || lng < 29.2 || lng > 30.5) return false;
    if (lng >= 29.35 && lng <= 29.97) {
        const south = 40.700 + (lng - 29.35) * 0.025;
        const north = 40.745 + (lng - 29.35) * 0.03;
        if (lat > south && lat < north) return false;
    }
    return true;
}

/* ===== Marker Ekleme ===== */
function addMarker(news) {
    const coords = news.location?.coordinates?.coordinates;
    if (!coords || coords.length < 2) return;

    const [lng, lat] = coords;
    if (!isOnLand(lat, lng)) return;

    const config = CATEGORY_CONFIG[news.category] || CATEGORY_CONFIG["Trafik Kazası"];

    const marker = new google.maps.Marker({
        position: { lat, lng },
        map: map,
        title: news.title,
        newsId: news._id, // Haritada var olanları listeyle eşlemek için ID'sini tutuyoruz
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            fillColor: config.color,
            fillOpacity: 0.9,
            strokeColor: "#fff",
            strokeWeight: 2,
            scale: 10,
        },
        animation: google.maps.Animation.DROP,
    });

    marker.addListener("click", () => {
        const sources = news.sources || [];
        const publishDate = news.publish_date
            ? new Date(news.publish_date).toLocaleDateString("tr-TR", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
              })
            : "Tarih bilinmiyor";

        const locationText = (news.location && news.location.text) ? String(news.location.text) : "";

        // KRİTİK: sources dizisini .map() ile dönüp tüm kaynakları listele
        const sourcesListHtml = sources
            .map(
                (s) => `
                <div class="info-source-row">
                    <span class="info-source-name">📰 ${s.site_name || "Bilinmeyen Kaynak"}</span>
                    ${s.url
                        ? `<a href="${s.url}" target="_blank" class="info-window-btn">Habere Git →</a>`
                        : ""
                    }
                </div>`
            )
            .join("");

        const content = `
            <div class="info-window">
                <h3>${news.title}</h3>
                <div class="info-window-meta">
                    <span>📅 ${publishDate}</span>
                </div>
                ${
                    locationText
                        ? `<div style="margin-top:8px; font-size:12px; color:#3c4043;">📍 ${locationText}</div>`
                        : ""
                }
                <div class="info-sources-list">
                    ${sourcesListHtml}
                </div>
            </div>
        `;

        infoWindow.setContent(content);
        infoWindow.open(map, marker);
    });

    markers.push(marker);
}

function clearMarkers() {
    markers.forEach((marker) => marker.setMap(null));
    markers = [];
}

/* ===== Haber Listesi (Son Haberler Kartları) ===== */
function displayNewsList(newsList) {
    const container = document.getElementById("newsList");

    if (!newsList || newsList.length === 0) {
        container.innerHTML = '<div class="loading">Haber bulunamadı</div>';
        return;
    }

    container.innerHTML = newsList
        .map((news) => {
            const config = CATEGORY_CONFIG[news.category] || {};
            const publishDate = news.publish_date
                ? new Date(news.publish_date).toLocaleDateString("tr-TR", {
                      day: "numeric",
                      month: "short",
                  })
                : "";
            const source = news.sources?.[0]?.site_name || "";
            const sourceUrl = news.sources?.[0]?.url || "";
            const sourceCount = (news.sources || []).length;
            const sourceCountBadge = sourceCount > 1
                ? `<span class="source-count-badge">${sourceCount} kaynak</span>`
                : "";

            // Konum bilgisi
            const district = news.location?.district || "";
            const locationText = news.location?.text || "";
            const locationDisplay = district || locationText;

            const hasCoords = news.location?.coordinates?.coordinates?.length >= 2;
            const lat = hasCoords ? news.location.coordinates.coordinates[1] : null;
            const lng = hasCoords ? news.location.coordinates.coordinates[0] : null;

            return `
            <div class="news-item ${config.cssClass || ""}" 
                 onclick="focusOnNews('${news._id}', ${lat}, ${lng})">
                <div class="news-item-title">${news.title}</div>
                ${locationDisplay
                    ? `<div class="news-item-location">
                        <span class="material-icons-round" style="font-size:12px;">location_on</span>
                        ${locationDisplay}
                       </div>`
                    : ""
                }
                <div class="news-item-meta">
                    <span class="news-item-category" 
                          style="background: ${config.color || "#666"}">${news.category}</span>
                    <span>${publishDate}</span>
                    <span>${source}</span>
                    ${sourceCountBadge}
                    ${sourceUrl
                        ? `<a href="${sourceUrl}" target="_blank" class="news-item-link" 
                              onclick="event.stopPropagation()" title="Habere git">↗</a>`
                        : ""
                    }
                </div>
            </div>
        `;
        })
        .join("");
}

/* ===== Habere Odaklan ===== */
function focusOnNews(newsId, lat, lng) {
    if (lat && lng) {
        map.panTo({ lat, lng });
        map.setZoom(14);

        const targetMarker = markers.find(
            (m) =>
                Math.abs(m.getPosition().lat() - lat) < 0.0001 &&
                Math.abs(m.getPosition().lng() - lng) < 0.0001
        );

        if (targetMarker) {
            google.maps.event.trigger(targetMarker, "click");
        }
    }
}

/* ===== Haberleri Çek (Scrape Fresh) ===== */
async function triggerScrape() {
    const btn = document.getElementById("scrapeBtn");
    const spinner = document.getElementById("scrapeSpinner");
    const icon = btn.querySelector(".scrape-icon");
    const label = btn.querySelector(".scrape-label");

    // Zaten çalışıyorsa engelle
    if (btn.classList.contains("loading")) return;

    btn.classList.add("loading");
    icon.style.display = "none";
    spinner.style.display = "inline-block";
    label.textContent = "Çekiliyor...";
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/scrape`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        const result = await response.json();

        if (result.status === "ok") {
            const data = result.data || {};
            label.textContent = `✓ ${data.new_articles || 0} haber`;
            // Haritayı güncelle
            await loadAndDisplayNews();
        } else {
            label.textContent = "Hata!";
            console.error("Scrape error:", result.message);
        }
    } catch (error) {
        label.textContent = "Bağlantı hatası";
        console.error("Scrape fetch error:", error);
    }

    // 3 saniye sonra butonu sıfırla
    setTimeout(() => {
        btn.classList.remove("loading");
        icon.style.display = "";
        spinner.style.display = "none";
        label.textContent = "Haberleri Çek";
        btn.disabled = false;
    }, 3000);
}

/* ===== Event Listeners ===== */
document.getElementById("filterBtn").addEventListener("click", () => {
    loadAndDisplayNews();
});

document.getElementById("resetBtn").addEventListener("click", () => {
    document.getElementById("districtFilter").value = "";
    document.querySelectorAll("#categoryFilters input").forEach((cb) => {
        cb.checked = true;
    });
    setDefaultDates();
    loadAndDisplayNews();
});

document.getElementById("scrapeBtn").addEventListener("click", () => {
    triggerScrape();
});

document.getElementById("mobileMenuBtn").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
});

document.getElementById("map").addEventListener("click", () => {
    document.getElementById("sidebar").classList.remove("open");
});
