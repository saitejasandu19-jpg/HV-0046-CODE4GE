/**
 * Driver Cockpit Logic for Vignan Campus Transport System
 */
document.addEventListener('DOMContentLoaded', () => {
    const mapEl = document.getElementById('driver-map');
    if (mapEl) {
        window.driverMap = new MapManager('driver-map', 16.2330, 80.5490, 14);
        initDriverGps();
    }

    if (typeof io !== 'undefined') {
        window.socket = io();
        socket.on('bus_location_update', (data) => {
            if (window.driverMap) window.driverMap.updateBusPosition(data);
            const latEl = document.getElementById('driver-lat');
            const lngEl = document.getElementById('driver-lng');
            if (latEl && data.current_latitude) latEl.innerText = data.current_latitude.toFixed(5);
            if (lngEl && data.current_longitude) lngEl.innerText = data.current_longitude.toFixed(5);
        });
    }
});

function initDriverGps() {
    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(pos => {
            const lat = pos.coords.latitude;
            const lng = pos.coords.longitude;
            const speed = pos.coords.speed ? Math.round(pos.coords.speed * 3.6) : 25.0;

            if (window.driverMap && window.DRIVER_DATA && window.DRIVER_DATA.bus_id) {
                window.driverMap.updateBusPosition({
                    bus_id: window.DRIVER_DATA.bus_id,
                    bus_number: window.DRIVER_DATA.bus_number,
                    latitude: lat,
                    longitude: lng,
                    status: 'ACTIVE',
                    speed: speed
                });
            }

            const speedEl = document.getElementById('driver-current-speed');
            if (speedEl) speedEl.innerText = `${speed} km/h`;

            const latEl = document.getElementById('driver-lat');
            const lngEl = document.getElementById('driver-lng');
            if (latEl) latEl.innerText = lat.toFixed(5);
            if (lngEl) lngEl.innerText = lng.toFixed(5);

            const gpsStatusEl = document.getElementById('gps-tracking-status');
            if (gpsStatusEl) gpsStatusEl.innerText = '🟢 LIVE';
        }, err => {
            console.warn("GPS error:", err.message);
        }, { enableHighAccuracy: true });
    }
}


async function driverStartTrip() {
    try {
        const res = await fetch('/driver/api/start_trip', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert("▶ TRIP STARTED!\n\nLive GPS telemetry active. Subscribed students have been notified.");
            const badge = document.getElementById('driver-status-badge');
            if (badge) {
                badge.innerText = 'ACTIVE';
                badge.className = 'badge bg-success';
            }
        } else {
            alert(`⚠️ Error: ${data.message}`);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to connect to trip start server.");
    }
}

async function driverStopTrip() {
    try {
        const res = await fetch('/driver/api/stop_trip', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert("⏹ TRIP STOPPED.\n\nLive telemetry ended.");
            const badge = document.getElementById('driver-status-badge');
            if (badge) {
                badge.innerText = 'STOPPED';
                badge.className = 'badge bg-secondary';
            }
        } else {
            alert(`⚠️ Error: ${data.message}`);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to connect to trip stop server.");
    }
}

async function triggerEmergencyAlert() {
    if (!confirm("🚨 CONFIRM EMERGENCY ALERT BROADCAST?\n\nThis will immediately alert Vignan campus security and all students on your route.")) {
        return;
    }

    try {
        const res = await fetch('/driver/api/emergency', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert("🚨 EMERGENCY ALERT BROADCASTED SUCCESSFULLY!");
            const badge = document.getElementById('driver-status-badge');
            if (badge) {
                badge.innerText = 'EMERGENCY';
                badge.className = 'badge bg-danger';
            }
        } else {
            alert(`⚠️ Emergency Error: ${data.message}`);
        }
    } catch (e) {
        console.error(e);
        alert("Failed to broadcast emergency alert.");
    }
}
