// 1. Initialize Map (Default: India Center)
const map = L.map('map').setView([23.2599, 77.4126], 10); // Center near Bhopal/Sehore

// 2. Add High-Quality Map Tiles (CartoDB Voyager - looks cleaner than default OSM)
L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

let routeLayer = L.layerGroup().addTo(map);

async function analyzeRoute() {
    const startInput = document.getElementById('start');
    const endInput = document.getElementById('end');
    const btn = document.getElementById('searchBtn');
    const loading = document.getElementById('loading');
    const results = document.getElementById('results');

    // Basic Validation
    if(!startInput.value || !endInput.value) {
        alert("Please enter both Start and End locations.");
        return;
    }

    // UI State: Loading
    btn.disabled = true;
    btn.innerHTML = `<div class="spinner" style="width:16px;height:16px;border-width:2px;margin:0;"></div> Analyzing...`;
    loading.classList.remove('hidden');
    results.classList.add('hidden');
    routeLayer.clearLayers();

    try {
        // CALL BACKEND
        const response = await fetch('http://127.0.0.1:5000/api/get-route', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start: startInput.value, end: endInput.value })
        });

        const data = await response.json();

        if (data.error) {
            alert("Error: " + data.error);
        } else {
            // SUCCESS: Process Data
            let bounds = [];
            let uniqueHazards = new Set();
            let hazardHtml = "";

            data.segments.forEach(seg => {
                // Draw Line
                const poly = L.polyline(seg.positions, {
                    color: seg.color,
                    weight: 6,
                    opacity: 0.85,
                    lineCap: 'round'
                }).addTo(routeLayer);
                
                // Popup Info
                poly.bindPopup(`
                    <div style="font-family:Inter, sans-serif;">
                        <strong style="color:${seg.color}">${seg.risk} Risk</strong><br>
                        ${seg.info}
                    </div>
                `);

                bounds.push(...seg.positions);

                // Collect Hazards for Sidebar
                if (seg.risk !== 'Low') {
                    // Create a unique key to prevent duplicate warnings
                    const key = `${seg.risk}|${seg.info}`;
                    if (!uniqueHazards.has(key)) {
                        uniqueHazards.add(key);
                        const cssClass = seg.risk === 'High' ? 'h-red' : 'h-orange';
                        hazardHtml += `
                            <li class="hazard-item ${cssClass}">
                                <i class="fa-solid fa-triangle-exclamation"></i>
                                <div>
                                    <strong>${seg.risk} Risk</strong>
                                    <div style="font-size:12px; opacity:0.8;">${seg.info}</div>
                                </div>
                            </li>
                        `;
                    }
                }
            });

            // Update Stats
            document.getElementById('high-count').innerText = data.stats.High;
            document.getElementById('mod-count').innerText = data.stats.Moderate;
            document.getElementById('safe-count').innerText = data.stats.Low;

            // Update Hazard List
            const list = document.getElementById('hazard-list');
            if (hazardHtml === "") {
                list.innerHTML = `<li class="hazard-item h-green"><i class="fa-solid fa-check-circle"></i> No major hazards detected.</li>`;
            } else {
                list.innerHTML = hazardHtml;
            }

            // Show Results
            results.classList.remove('hidden');
            if (bounds.length > 0) map.fitBounds(bounds, { padding: [50, 50] });
        }

    } catch (error) {
        console.error(error);
        alert("Failed to connect to AI Server. Is run.bat open?");
    } finally {
        // Reset UI
        btn.disabled = false;
        btn.innerHTML = `<span>Find Safe Route</span> <i class="fa-solid fa-arrow-right"></i>`;
        loading.classList.add('hidden');
    }
}