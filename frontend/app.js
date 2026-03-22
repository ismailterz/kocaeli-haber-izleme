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

function setDefaultDates() {
    const now = new Date();
    const threeDaysAgo = new Date(now);
    threeDaysAgo.setDate(now.getDate() - 3);

    document.getElementById("endDate").value = formatDateForInput(now);
    document.getElementById("startDate").value = formatDateForInput(threeDaysAgo);
}

function formatDateForInput(date) {
    return date.toISOString().split("T")[0];
}

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

function getSelectedCategories() {
    const checkboxes = document.querySelectorAll("#categoryFilters input:checked");
    return Array.from(checkboxes).map((cb) => cb.value);
}

function getFilters() {
    const filters = {};

    const district = document.getElementById("districtFilter").value;
    if (district) filters.district = district;

    const startDate = document.getElementById("startDate").value;
    if (startDate) filters.start_date = startDate;

    const endDate = document.getElementById("endDate").value;
    if (endDate) filters.end_date = endDate + "T23:59:59";

    return filters;
}

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

async function loadStats() {
    const result = await apiCall("/stats");
    if (!result || !result.data) return;

    const grid = document.getElementById("statsGrid");
    const stats = result.data;

    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.total || 0}</div>
            <div class="stat-label">Toplam Haber</div>
        </div>
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

async function loadAndDisplayNews() {
    const filters = getFilters();
    const selectedCategories = getSelectedCategories();

    clearMarkers();

    const mapResult = await apiCall("/news/map", filters);
    if (mapResult && mapResult.data) {
        const filteredMapData = mapResult.data.filter((news) =>
            selectedCategories.includes(news.category)
        );
        filteredMapData.forEach((news) => addMarker(news));
    }

    const listResult = await apiCall("/news", { ...filters, limit: 50 });
    if (listResult && listResult.data) {
        const filteredListData = listResult.data.filter((news) =>
            selectedCategories.includes(news.category)
        );
        displayNewsList(filteredListData);
    }

    loadStats();
}

function isOnLand(lat, lng) {
    if (lat < 40.4 || lat > 41.2 || lng < 29.2 || lng > 30.5) return false;
    if (lng >= 29.35 && lng <= 29.97) {
        const south = 40.700 + (lng - 29.35) * 0.025;
        const north = 40.745 + (lng - 29.35) * 0.03;
        if (lat > south && lat < north) return false;
    }
    return true;
}

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
        const firstSource = sources[0] || {};
        const publishDate = news.publish_date
            ? new Date(news.publish_date).toLocaleDateString("tr-TR", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
              })
            : "Tarih bilinmiyor";

        const sourcesHtml = sources
            .map(
                (s) =>
                    `<span style="font-size:11px; color:#5f6368;">📰 ${s.site_name}</span>`
            )
            .join("<br>");

        const content = `
            <div class="info-window">
                <h3>${news.title}</h3>
                <div class="info-window-meta">
                    <span>📅 ${publishDate}</span>
                    ${sourcesHtml}
                </div>
                ${
                    firstSource.url
                        ? `<a href="${firstSource.url}" target="_blank" class="info-window-btn">
                            Habere Git →
                           </a>`
                        : ""
                }
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

            return `
            <div class="news-item ${config.cssClass || ""}" 
                 onclick="focusOnNews('${news._id}', ${
                news.location?.coordinates?.coordinates?.[1] || "null"
            }, ${news.location?.coordinates?.coordinates?.[0] || "null"})">
                <div class="news-item-title">${news.title}</div>
                <div class="news-item-meta">
                    <span class="news-item-category" 
                          style="background: ${config.color || "#666"}">${news.category}</span>
                    <span>${publishDate}</span>
                    <span>${source}</span>
                </div>
            </div>
        `;
        })
        .join("");
}

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

// Event listeners
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

document.getElementById("mobileMenuBtn").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
});

document.getElementById("map").addEventListener("click", () => {
    document.getElementById("sidebar").classList.remove("open");
});
