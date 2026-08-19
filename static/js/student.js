/**
 * Student Dashboard & Camera QR Code Scanner Logic
 */
let html5QrScanner = null;

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Student Map
    const mapEl = document.getElementById('student-map');
    if (mapEl) {
        window.studentMap = new MapManager('student-map', 16.2330, 80.5490, 14);
        initStudentDashboard();
    }

    // 2. Connect WebSockets
    if (typeof io !== 'undefined') {
        window.socket = io();

        socket.on('connect', () => {
            console.log("Connected to Vignan Socket.IO server.");
            if (window.STUDENT_DATA && window.STUDENT_DATA.selected_bus_id) {
                socket.emit('join_bus', { bus_id: window.STUDENT_DATA.selected_bus_id });
            }
        });

        socket.on('bus_location_update', (data) => {
            if (window.studentMap) window.studentMap.updateBusPosition(data);

            if (window.STUDENT_DATA && parseInt(data.bus_id) === parseInt(window.STUDENT_DATA.selected_bus_id)) {
                updateStudentMetrics(data);
                const now = Date.now();
                if (now - lastRouteFetchTime > 8000) {
                    lastRouteFetchTime = now;
                    fetchAndHighlightSelectedRoute(data.bus_id);
                }
            }
        });


        socket.on('bus_status_change', (data) => {
            if (window.STUDENT_DATA && parseInt(data.bus_id) === parseInt(window.STUDENT_DATA.selected_bus_id)) {
                const badge = document.getElementById('status-badge');
                if (badge) {
                    badge.innerText = data.status;
                    badge.className = `badge ${data.status === 'ACTIVE' ? 'bg-success' : 'bg-secondary'}`;
                }

                const msg = `${data.bus_number} has ${data.status === 'ACTIVE' ? 'started its trip' : 'stopped'}.`;
                window.voiceManager.speakAndNotify(msg, 'BUS_STATUS', data.bus_id);
            }
        });

        socket.on('new_notification', (notif) => {
            if (window.STUDENT_DATA && window.STUDENT_DATA.selected_bus_id) {
                if (!notif.bus_id || parseInt(notif.bus_id) === parseInt(window.STUDENT_DATA.selected_bus_id)) {
                    window.voiceManager.speakAndNotify(notif.message, notif.type, notif.bus_id);
                }
            }
        });

        socket.on('emergency_alert', (alertData) => {
            if (window.studentMap) window.studentMap.updateBusPosition({ ...alertData, status: 'EMERGENCY' });

            const msg = alertData.message || `Emergency alert from ${alertData.bus_number}!`;
            window.voiceManager.speakAndNotify(msg, 'EMERGENCY', alertData.bus_id, true);

            if (window.STUDENT_DATA && parseInt(alertData.bus_id) === parseInt(window.STUDENT_DATA.selected_bus_id)) {
                alert(`🚨 EMERGENCY ALERT FROM ${alertData.bus_number}\n\n${msg}`);
            }
        });

        socket.on('replacement_bus_arranged', (data) => {
            if (window.STUDENT_DATA && parseInt(data.original_bus_id) === parseInt(window.STUDENT_DATA.selected_bus_id)) {
                window.voiceManager.speakAndNotify(data.popup_message, 'REPLACEMENT_BUS', data.original_bus_id, true);
                alert(`🚌 REPLACEMENT BUS ALERT:\n\n${data.popup_message}`);
            }
        });
    }
});

async function initStudentDashboard() {
    // Request student browser geolocation
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(pos => {
            if (window.studentMap) {
                window.studentMap.setStudentLocation(pos.coords.latitude, pos.coords.longitude, 'Your Location');
            }
        }, () => {
            if (window.studentMap) window.studentMap.setStudentLocation(16.2330, 80.5490, 'Vignan Main Gate (Default)');
        });
    }

    if (window.studentMap) {
        window.studentMap.setDestinationLocation(16.2330, 80.5490, '🎓 VIGNAN COLLEGE — Destination');
        window.studentMap.setPickupLocation(16.2150, 80.5200, 'Stop 3 (Pickup Point)');
    }

    if (window.STUDENT_DATA && window.STUDENT_DATA.selected_bus_id) {
        onStudentSelectBus(window.STUDENT_DATA.selected_bus_id, false);
    }
}



let lastRouteFetchTime = 0;

async function fetchAndHighlightSelectedRoute(busId) {
    if (!busId) return;

    const pickupStopId = window.STUDENT_DATA ? window.STUDENT_DATA.pickup_stop_id : null;
    const url = `/api/directions?bus_id=${busId}${pickupStopId ? `&dest_stop_id=${pickupStopId}` : ''}`;

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.success && data.road_geometry) {
            if (window.studentMap) {
                window.studentMap.highlightSelectedBusRoute(busId, data.road_geometry, data.bus_color);
            }

            const cardDist = document.getElementById('card-bus-distance');
            const cardEta = document.getElementById('card-bus-eta');
            if (cardDist) cardDist.innerText = `${data.distance_km} km`;
            if (cardEta) cardEta.innerText = `${data.eta_minutes} min`;

            const stepsList = document.getElementById('directions-steps-list');
            if (stepsList && data.directions_steps) {
                stepsList.innerHTML = data.directions_steps.map(s => `<li class="small text-dark mb-1">${s}</li>`).join('');
            }

            const dirNext = document.getElementById('dir-next-stop');
            if (dirNext && data.destination_stop) {
                dirNext.innerText = data.destination_stop;
            }
        } else {
            console.warn("Directions warning:", data.message);
        }
    } catch (e) {
        console.warn("Unable to calculate road directions right now:", e);
    }
}

async function onStudentSelectPickupStop(stopId) {
    if (!stopId) return;

    try {
        const res = await fetch('/student/api/select_pickup_stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pickup_stop_id: stopId })
        });
        const data = await res.json();
        if (data.success && data.pickup_stop) {
            window.STUDENT_DATA.pickup_stop_id = parseInt(stopId);
            if (window.studentMap) {
                window.studentMap.setPickupLocation(data.pickup_stop.latitude, data.pickup_stop.longitude, data.pickup_stop.stop_name);
            }
            const selBus = window.STUDENT_DATA.selected_bus_id || 2;
            fetchAndHighlightSelectedRoute(selBus);
            window.voiceManager.speakAndNotify(`Pickup location updated to ${data.pickup_stop.stop_name}.`, 'PICKUP_UPDATED');
        }
    } catch (e) {
        console.error("Error updating pickup stop:", e);
    }
}

async function onStudentSelectBus(busId, triggerSave = true) {
    if (!busId) return;

    try {
        if (triggerSave) {
            const res = await fetch('/student/api/select_bus', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bus_id: busId })
            });
            const data = await res.json();
            if (data.selected_bus) {
                updateSelectedBusCard(data.selected_bus);
            }
        }

        window.STUDENT_DATA.selected_bus_id = parseInt(busId);
        const selector = document.getElementById('bus-selector');
        if (selector) selector.value = busId;

        const busText = selector ? selector.options[selector.selectedIndex].text : `Bus ${busId}`;
        const busNumStr = busText.split('(')[0].trim();

        if (window.studentMap) {
            window.studentMap.setSelectedBusId(busId);
            window.studentMap.focusOnBus(busId);
        }

        fetchAndHighlightSelectedRoute(busId);

        window.voiceManager.setSelectedBus(busId, busNumStr);

        if (window.socket) {
            window.socket.emit('join_bus', { bus_id: busId });
        }

        const selMsg = `Selected ${busNumStr} for live tracking.`;
        window.voiceManager.speakAndNotify(selMsg, 'BUS_SELECTED', busId);
    } catch (e) {
        console.error("Error selecting bus:", e);
    }
}


function openLiveSelectedBus() {
    const selectedBusId = window.STUDENT_DATA.selected_bus_id || 2;
    onStudentSelectBus(selectedBusId, true);
    
    const liveCard = document.getElementById('live-tracking-card');
    if (liveCard) {
        liveCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    if (window.studentMap) {
        window.studentMap.focusOnBus(selectedBusId);
    }

    window.voiceManager.speakAndNotify(`Opened live tracking for Bus ${selectedBusId}.`, 'LIVE_OPENED', selectedBusId);
}

function toggleDirectionsCard() {
    const panel = document.getElementById('directions-panel');
    if (panel) {
        panel.classList.toggle('d-none');
    }
}

function updateSelectedBusCard(bus) {
    document.getElementById('card-selected-bus').innerText = bus.bus_number;
    const badge = document.getElementById('status-badge');
    badge.innerText = bus.status;
    badge.className = `badge ${bus.status === 'ACTIVE' ? 'bg-success' : (bus.status === 'EMERGENCY' ? 'bg-danger' : 'bg-secondary')}`;

    document.getElementById('driver-card-name').innerText = bus.driver_name;
    document.getElementById('driver-card-phone').innerText = bus.driver_phone;
    document.getElementById('driver-card-phone-link').href = `tel:${bus.driver_phone}`;
    document.getElementById('driver-card-route').innerText = bus.route_name || 'N/A';

    // Add Bus Color Accent Class to Card
    const liveCard = document.getElementById('live-tracking-card');
    if (liveCard) {
        liveCard.className = `card selected-bus-card bus-card-accent-${bus.id}`;
    }

    // Update QR Code Card Elements
    const qrVal = bus.qr_code_value || `VCT-BUS-00${bus.id}`;
    const qrImgUrl = bus.qr_image_url || `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${qrVal}`;

    const qrBadge = document.getElementById('card-qr-code-val');
    const qrTitle = document.getElementById('card-qr-title');
    const qrImg = document.getElementById('card-qr-img');

    const dirSelBus = document.getElementById('dir-selected-bus');
    if (dirSelBus) dirSelBus.innerText = bus.bus_number;

    if (qrBadge) qrBadge.innerText = qrVal;
    if (qrTitle) qrTitle.innerHTML = `<strong>${bus.bus_number} QR CODE</strong>`;
    if (qrImg) qrImg.src = qrImgUrl;


    // Update Directions Panel if stops are returned
    if (bus.stops && bus.stops.length > 0) {
        const stopNames = bus.stops.map(s => s.stop_name).join(' &rarr; ');
        const dirSeq = document.getElementById('route-direction-seq');
        if (dirSeq) dirSeq.innerHTML = stopNames;
    }
}


function updateStudentMetrics(busData) {
    const cardDistance = document.getElementById('card-bus-distance');
    const cardEta = document.getElementById('card-bus-eta');
    const cardCurrStop = document.getElementById('card-current-stop');
    const cardNextStop = document.getElementById('card-next-stop');
    const mapNextStop = document.getElementById('map-next-stop');

    if (busData.dist_to_next_km !== undefined) {
        if (cardDistance) cardDistance.innerText = `${busData.dist_to_next_km} km`;
        if (cardEta) cardEta.innerText = `${busData.eta_to_next_min} min`;
        if (cardCurrStop) cardCurrStop.innerText = busData.current_stop_name || 'In Transit';
        if (cardNextStop) cardNextStop.innerText = busData.next_stop_name || 'In Transit';
        if (mapNextStop) mapNextStop.innerText = busData.next_stop_name || 'In Transit';

        const dirNext = document.getElementById('dir-next-stop');
        if (dirNext) dirNext.innerText = busData.next_stop_name || 'In Transit';

        // Voice threshold triggers & 50m auto-off
        window.voiceManager.processDistanceTelemetry(busData.dist_to_next_km, busData.next_stop_name || "your stop");

        const proxStatus = document.getElementById('prox-status');
        if (proxStatus) {
            if (busData.dist_to_next_km <= 0.05) {
                proxStatus.innerText = 'OFF (Arrived <= 50m)';
                proxStatus.className = 'text-warning';
            } else {
                proxStatus.innerText = 'MONITORING';
                proxStatus.className = '';
            }
        }
    }
}


function toggleVoiceSystem() {
    if (window.voiceManager.isEnabled) {
        window.voiceManager.disableVoice('OFF (User)');
    } else {
        window.voiceManager.enableVoice();
    }
}

function silenceVoiceManual() {
    window.voiceManager.stopSpeaking();
}

// ==========================================================================
// 📷 CAMERA QR CODE SCANNER MODAL CONTROLS
// ==========================================================================
function openQrScannerModal() {
    const modal = document.getElementById('qr-modal');
    if (!modal) return;

    modal.classList.add('active');

    if (typeof Html5Qrcode !== 'undefined') {
        if (!html5QrScanner) {
            html5QrScanner = new Html5Qrcode("qr-reader");
        }

        const config = { fps: 10, qrbox: { width: 250, height: 250 } };

        html5QrScanner.start({ facingMode: "environment" }, config, (decodedText) => {
            console.log("QR Code Scanned:", decodedText);
            onQrCodeScanned(decodedText);
        }, (errorMessage) => {
            // Ignore scan parse errors while camera is searching
        }).catch(err => {
            console.warn("Camera unavailable/permission denied. Use manual input:", err);
            document.getElementById('qr-reader').innerHTML = `
                <div style="padding: 20px; color: #ffffff; text-align: center;">
                    <i class="fa-solid fa-camera-slash fa-2x mb-2" style="color: #f59e0b;"></i>
                    <p style="margin: 0;">Camera permission denied or camera unreadable.<br>Please type the bus code (e.g. <code>BUS001</code>) below.</p>
                </div>
            `;
        });
    }
}

function closeQrScannerModal() {
    const modal = document.getElementById('qr-modal');
    if (modal) modal.classList.remove('active');

    if (html5QrScanner) {
        html5QrScanner.stop().then(() => {
            console.log("QR Camera stopped.");
        }).catch(err => console.warn(err));
    }
}

function submitManualQrCode() {
    const input = document.getElementById('manual-qr-input');
    if (!input || !input.value.trim()) return;
    onQrCodeScanned(input.value.trim());
}

async function onQrCodeScanned(qrCodeText) {
    closeQrScannerModal();

    try {
        const res = await fetch('/student/api/scan_qr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ qr_code: qrCodeText })
        });
        const data = await res.json();

        if (data.success) {
            alert(`📷 SCAN SUCCESSFUL!\n\n${data.message}`);
            if (data.selected_bus) {
                updateSelectedBusCard(data.selected_bus);
                onStudentSelectBus(data.selected_bus.id, false);
            }
        } else {
            alert(`⚠️ QR Scan Error: ${data.message}`);
        }
    } catch (e) {
        console.error("Error submitting QR code:", e);
        alert("Failed to connect to QR server.");
    }
}
