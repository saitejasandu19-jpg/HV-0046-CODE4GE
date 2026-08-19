/**
 * Leaflet Map Controller for Vignan Campus Transport System
 */
class MapManager {
    constructor(elementId, centerLat = 16.2330, centerLng = 80.5490, zoom = 14) {
        this.elementId = elementId;
        this.map = L.map(elementId).setView([centerLat, centerLng], zoom);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        }).addTo(this.map);

        this.busMarkers = {};
        this.stopMarkers = [];
        this.routePolylines = {};
        this.studentMarker = null;
        this.pickupMarker = null;
        this.selectedBusId = null;
        this.selectedRouteLayer = null;

        this.BUS_COLORS = {
            1: '#1E88E5', // Blue
            2: '#E53935', // Red
            3: '#43A047', // Green
            4: '#FB8C00', // Orange
            5: '#8E24AA', // Purple
            6: '#00ACC1'  // Teal
        };

        this.initIcons();
    }

    initIcons() {
        this.getBusIconHtml = (busId, busNumber, status, heading = 0) => {
            const hexColor = this.BUS_COLORS[busId] || '#1E88E5';
            const isSelected = String(busId) === String(this.selectedBusId);
            const pulseClass = isSelected ? 'selected-bus-marker-icon' : '';
            const busScale = isSelected ? 'scale(1.2)' : 'scale(1.0)';

            return `
                <div class="custom-bus-image-marker ${pulseClass}" style="text-align: center; transform: ${busScale}; transition: transform 0.3s ease;">
                    <div class="bus-svg-icon" style="display: inline-block; filter: drop-shadow(0px 3px 6px rgba(0,0,0,0.35));">
                        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <rect x="3" y="4" width="18" height="14" rx="3" fill="${hexColor}"/>
                            <rect x="5" y="6" width="6" height="4" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
                            <rect x="13" y="6" width="6" height="4" rx="1" fill="#FFFFFF" fill-opacity="0.9"/>
                            <circle cx="7" cy="15" r="1.5" fill="#1E293B"/>
                            <circle cx="17" cy="15" r="1.5" fill="#1E293B"/>
                            <path d="M7 18V19.5C7 19.7761 6.77614 20 6.5 20H5.5C5.22386 20 5 19.7761 5 19.5V18H7Z" fill="#334155"/>
                            <path d="M19 18V19.5C19 19.7761 18.7761 20 18.5 20H17.5C17.2239 20 17 19.7761 17 19.5V18H19Z" fill="#334155"/>
                        </svg>
                    </div>
                    <div class="bus-label-tag" style="background-color: ${hexColor}; color: #ffffff; padding: 2px 7px; font-size: 10px; font-weight: 700; border-radius: 10px; border: 1.5px solid #ffffff; display: block; white-space: nowrap; margin-top: -6px; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                        ${busNumber} ${isSelected ? '🟢' : ''}
                    </div>
                </div>
            `;
        };

        this.stopIcon = L.divIcon({
            className: 'custom-stop-marker',
            html: '<div style="color: #475569; font-size: 16px;"><i class="fa-solid fa-location-dot"></i></div>',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        this.studentIcon = L.divIcon({
            className: 'custom-student-marker',
            html: '<div style="color: #1e40af; font-size: 20px; background: #ffffff; border-radius: 50%; width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(0,0,0,0.4); border: 2px solid #1e40af;"><i class="fa-solid fa-user"></i></div>',
            iconSize: [34, 34],
            iconAnchor: [17, 17]
        });

        // 👤 Student / Pickup Point Marker Icon
        this.pickupIcon = L.divIcon({
            className: 'custom-pickup-marker',
            html: '<div style="color: #dc2626; font-size: 20px; background: #ffffff; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 10px rgba(0,0,0,0.4); border: 2.5px solid #dc2626;"><i class="fa-solid fa-user"></i></div>',
            iconSize: [38, 38],
            iconAnchor: [19, 19]
        });

        // 🎓 VIGNAN COLLEGE Destination Marker Icon
        this.destinationIcon = L.divIcon({
            className: 'custom-destination-marker',
            html: '<div style="color: #7e22ce; font-size: 22px; background: #ffffff; border-radius: 50%; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.4); border: 2.5px solid #7e22ce;"><i class="fa-solid fa-graduation-cap"></i></div>',
            iconSize: [42, 42],
            iconAnchor: [21, 21]
        });
    }

    setDestinationLocation(lat = 16.2330, lng = 80.5490, label = '🎓 VIGNAN COLLEGE — Destination') {
        if (!lat || !lng) return;
        if (this.destinationMarker) {
            this.destinationMarker.setLatLng([lat, lng]);
        } else {
            this.destinationMarker = L.marker([lat, lng], { icon: this.destinationIcon }).addTo(this.map);
            this.destinationMarker.bindPopup(`<strong>🎓 VIGNAN COLLEGE</strong><br>${label}`);
        }
    }


    setSelectedBusId(busId) {
        if (String(this.selectedBusId) !== String(busId)) {
            this.clearSelectedRoute();
        }
        this.selectedBusId = busId;
        // Refresh all bus markers to update icon selection scaling
        Object.keys(this.busMarkers).forEach(bId => {
            if (this.busMarkers[bId]) {
                const markerData = this.busMarkers[bId].busData;
                if (markerData) this.updateBusPosition(markerData);
            }
        });
    }


    clearSelectedRoute() {
        if (this.selectedRouteLayer) {
            this.map.removeLayer(this.selectedRouteLayer);
            this.selectedRouteLayer = null;
        }
    }

    highlightSelectedBusRoute(busId, coords, color = null) {
        // Ensure ONLY ONE selected bus route layer exists at a time
        this.clearSelectedRoute();

        if (!coords || coords.length < 2) return;

        const routeColor = color || (this.BUS_COLORS[busId] || '#1E88E5');

        this.selectedRouteLayer = L.polyline(coords, {
            color: routeColor,
            weight: 7,
            opacity: 0.9,
            lineCap: 'round',
            lineJoin: 'round',
            dashArray: '1, 2' // Distinct dotted-dash styling for selected route
        }).addTo(this.map);

        try {
            this.map.fitBounds(this.selectedRouteLayer.getBounds(), { padding: [50, 50] });
        } catch (e) {
            // Ignore fitBounds if zero area
        }
    }


    setStudentLocation(lat, lng, label = 'Your Location') {
        if (!lat || !lng) return;
        if (this.studentMarker) {
            this.studentMarker.setLatLng([lat, lng]);
        } else {
            this.studentMarker = L.marker([lat, lng], { icon: this.studentIcon }).addTo(this.map);
            this.studentMarker.bindPopup(`<strong>${label}</strong><br>Vignan Student Position`);
        }
    }

    setPickupLocation(lat, lng, label = 'Pickup Stop') {
        if (!lat || !lng) return;
        if (this.pickupMarker) {
            this.pickupMarker.setLatLng([lat, lng]);
        } else {
            this.pickupMarker = L.marker([lat, lng], { icon: this.pickupIcon }).addTo(this.map);
            this.pickupMarker.bindPopup(`<strong>📍 Selected Pickup Stop</strong><br>${label}`);
        }
        this.pickupMarker.openPopup();
    }

    drawRoute(routeId, coords, color = null, stops = []) {
        if (this.routePolylines[routeId]) {
            this.map.removeLayer(this.routePolylines[routeId]);
        }

        const routeColor = color || (this.BUS_COLORS[routeId] || '#1E88E5');

        if (coords && coords.length >= 2) {
            const polyline = L.polyline(coords, {
                color: routeColor,
                weight: 6,
                opacity: 0.85,
                lineJoin: 'round'
            }).addTo(this.map);

            this.routePolylines[routeId] = polyline;
        }

        stops.forEach(stop => {
            const lat = stop.latitude || stop.lat;
            const lng = stop.longitude || stop.lng;
            if (lat && lng) {
                const marker = L.marker([lat, lng], { icon: this.stopIcon }).addTo(this.map);
                marker.bindPopup(`<strong>Stop ${stop.sequence_number || ''}: ${stop.stop_name}</strong>`);
                this.stopMarkers.push(marker);
            }
        });
    }

    updateBusPosition(busData) {
        const bus_id = busData.bus_id || busData.id;
        const bus_number = busData.bus_number;
        const lat = busData.current_latitude || busData.latitude || busData.lat;
        const lng = busData.current_longitude || busData.longitude || busData.lng;
        const status = busData.status || 'ACTIVE';
        const heading = busData.heading || 0;

        if (!lat || !lng) return;

        const iconHtml = this.getBusIconHtml(bus_id, bus_number, status, heading);
        const customIcon = L.divIcon({
            className: 'bus-marker-wrap',
            html: iconHtml,
            iconSize: [60, 45],
            iconAnchor: [30, 22]
        });

        if (this.busMarkers[bus_id]) {
            const marker = this.busMarkers[bus_id];
            marker.setLatLng([lat, lng]);
            marker.setIcon(customIcon);
            marker.busData = busData;
        } else {
            const marker = L.marker([lat, lng], { icon: customIcon }).addTo(this.map);
            marker.busData = busData;
            this.busMarkers[bus_id] = marker;
        }


        const driverName = busData.driver ? busData.driver.name : (busData.driver_name || 'Unassigned');
        const driverPhone = busData.driver ? busData.driver.phone : (busData.driver_phone || 'N/A');

        this.busMarkers[bus_id].bindPopup(`
            <div style="padding: 4px;">
                <h4 style="margin: 0 0 4px; color: ${this.BUS_COLORS[bus_id] || '#1E88E5'};"><i class="fa-solid fa-bus"></i> ${bus_number}</h4>
                <p style="margin: 0; font-size: 12px;"><strong>Status:</strong> <span class="badge ${status === 'ACTIVE' ? 'bg-success' : (status === 'EMERGENCY' ? 'bg-danger' : 'bg-secondary')}">${status}</span></p>
                <p style="margin: 2px 0; font-size: 12px;"><strong>Speed:</strong> ${busData.speed || 0} km/h</p>
                <p style="margin: 2px 0; font-size: 12px;"><strong>Driver:</strong> ${driverName} (${driverPhone})</p>
                <p style="margin: 2px 0; font-size: 12px;"><strong>Next Stop:</strong> ${busData.next_stop_name || 'In Transit'}</p>
            </div>
        `);
    }

    focusOnBus(busId) {
        if (this.busMarkers[busId]) {
            const pos = this.busMarkers[busId].getLatLng();
            this.map.setView(pos, 15, { animate: true });
        }
    }

    invalidateSize() {
        this.map.invalidateSize();
    }
}

