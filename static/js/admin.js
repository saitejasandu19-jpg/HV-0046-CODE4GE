/**
 * Admin Operations Panel Script for Vignan Campus Transport System
 */
document.addEventListener('DOMContentLoaded', async () => {
    const adminMapEl = document.getElementById('admin-map');
    if (adminMapEl) {
        window.adminMap = new MapManager('admin-map', 16.2330, 80.5490, 13);
        loadAdminMapData();
    }

    if (typeof io !== 'undefined') {
        window.socket = io();

        socket.on('bus_location_update', (data) => {
            if (window.adminMap) window.adminMap.updateBusPosition(data);
        });

        socket.on('emergency_alert', (alertData) => {
            if (window.adminMap) window.adminMap.updateBusPosition({ ...alertData, status: 'EMERGENCY' });
            alert(`🚨 NEW EMERGENCY ALERT INCOMING!\n\nBus: ${alertData.bus_number}\nMessage: ${alertData.message}`);
            window.location.reload();
        });
    }
});

async function loadAdminMapData() {
    try {
        const res = await fetch('/api/buses');
        const data = await res.json();
        if (data.buses) {
            data.buses.forEach(b => {
                if (window.adminMap) window.adminMap.updateBusPosition(b);
            });
        }
    } catch (e) {
        console.error("Error loading admin map data:", e);
    }
}

async function adminAssignDriver(e) {
    e.preventDefault();
    const busId = document.getElementById('assign-bus-id').value;
    const driverId = document.getElementById('assign-driver-id').value;

    try {
        const res = await fetch('/admin/api/assign_driver', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bus_id: busId, driver_id: driverId })
        });
        const data = await res.json();
        alert(data.message);
        if (data.success) window.location.reload();
    } catch (err) {
        console.error(err);
        alert("Failed to assign driver.");
    }
}

async function adminArrangeReplacement(e) {
    e.preventDefault();
    const origBus = document.getElementById('rep-orig-bus').value;
    const replBus = document.getElementById('rep-replacement-bus').value;

    try {
        const res = await fetch('/admin/api/arrange_replacement_bus', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ original_bus_id: origBus, replacement_bus_id: replBus })
        });
        const data = await res.json();
        alert(`🚌 REPLACEMENT BUS DISPATCHED:\n\n${data.message}`);
        if (data.success) window.location.reload();
    } catch (err) {
        console.error(err);
        alert("Failed to arrange replacement bus.");
    }
}

async function resolveEmergency(emergencyId) {
    if (!confirm("Mark this emergency incident RESOLVED?")) return;

    try {
        const res = await fetch(`/admin/api/resolve_emergency/${emergencyId}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            alert("Emergency resolved successfully.");
            window.location.reload();
        }
    } catch (err) {
        console.error(err);
        alert("Failed to resolve emergency.");
    }
}

async function adminSimControl(action) {
    try {
        const res = await fetch('/admin/api/simulation/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });
        const data = await res.json();
        if (data.success) console.log(`Simulation control: ${action}`);
    } catch (e) {
        console.error(e);
    }
}

async function adminSimSpeed(multiplier) {
    try {
        await fetch('/admin/api/simulation/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'set_speed', speed: multiplier })
        });
        alert(`Simulation speed set to x${multiplier}`);
    } catch (e) {
        console.error(e);
    }
}
