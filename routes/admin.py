import sqlite3
import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash, current_app
from services.notification_service import NotificationService
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'campus_transport.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'ADMIN':
            flash('Access restricted to administrators only.', 'danger')
            return redirect(url_for('auth.login_admin'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("""
        SELECT b.id, b.bus_number, b.registration_number, b.qr_code_value, b.status, d.name, d.phone, r.route_name
        FROM buses b
        LEFT JOIN drivers d ON b.current_driver_id = d.id
        LEFT JOIN bus_routes br ON b.id = br.bus_id
        LEFT JOIN routes r ON br.route_id = r.id;
        """)
        rows = cursor.fetchall()
        buses = []
        for row in rows:
            qr_val = row[3] if row[3] else f"VCT-BUS-00{row[0]}"
            buses.append({
                'id': row[0],
                'bus_number': row[1],
                'registration_number': row[2],
                'qr_code_value': qr_val,
                'qr_image_url': f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_val}",
                'status': row[4],
                'driver_name': row[5] or 'Unassigned',
                'driver_phone': row[6] or 'N/A',
                'route_name': row[7] or 'Unassigned'
            })

        cursor.execute("SELECT id, driver_id, name, phone, license_number, status FROM drivers;")
        drivers = [
            {
                'id': row[0],
                'driver_id': row[1],
                'name': row[2],
                'phone': row[3],
                'license_number': row[4],
                'status': row[5]
            } for row in cursor.fetchall()
        ]

        cursor.execute("SELECT id, student_id, name, phone, selected_bus_id FROM students;")
        students = [
            {
                'id': row[0],
                'student_id': row[1],
                'name': row[2],
                'phone': row[3],
                'selected_bus_id': row[4]
            } for row in cursor.fetchall()
        ]

        cursor.execute("SELECT id, route_name FROM routes;")
        routes = [{'id': row[0], 'route_name': row[1]} for row in cursor.fetchall()]

        cursor.execute("""
        SELECT e.id, b.bus_number, d.name, d.phone, e.message, e.created_at, e.status
        FROM emergency_alerts e
        JOIN buses b ON e.bus_id = b.id
        LEFT JOIN drivers d ON e.driver_id = d.id
        ORDER BY e.id DESC;
        """)
        emergencies = [
            {
                'id': row[0],
                'bus_number': row[1],
                'driver_name': row[2] or 'Unknown',
                'driver_phone': row[3] or '',
                'message': row[4],
                'created_at': row[5],
                'status': row[6]
            } for row in cursor.fetchall()
        ]
    finally:
        conn.close()

    stats = {
        'total_buses': len(buses),
        'active_buses': sum(1 for b in buses if b['status'] == 'ACTIVE'),
        'stopped_buses': sum(1 for b in buses if b['status'] == 'STOPPED'),
        'emergency_buses': sum(1 for b in buses if b['status'] == 'EMERGENCY'),
        'total_students': len(students),
        'total_drivers': len(drivers),
        'total_routes': len(routes),
        'active_emergencies': sum(1 for e in emergencies if e['status'] == 'ACTIVE')
    }

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        buses=buses,
        drivers=drivers,
        students=students,
        routes=routes,
        emergencies=emergencies
    )

@admin_bp.route('/api/assign_driver', methods=['POST'])
@admin_required
def assign_driver():
    data = request.get_json() or {}
    bus_id = data.get('bus_id')
    driver_id = data.get('driver_id')

    if not bus_id or not driver_id:
        return jsonify({'success': False, 'message': 'Bus ID and Driver ID required'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE buses SET current_driver_id = ? WHERE id = ?;", (driver_id, bus_id))
        cursor.execute("SELECT bus_number FROM buses WHERE id = ?;", (bus_id,))
        bus_row = cursor.fetchone()
        cursor.execute("SELECT name, phone FROM drivers WHERE id = ?;", (driver_id,))
        driver_row = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()

    bus_number = bus_row[0] if bus_row else 'Bus'
    driver_name = driver_row[0] if driver_row else 'Driver'
    driver_phone = driver_row[1] if driver_row else ''

    socketio = current_app.extensions.get('socketio')
    msg = f"{bus_number} driver has been updated to {driver_name}."
    
    NotificationService.create_notification(
        type_name='DRIVER_REASSIGNED',
        message=msg,
        bus_id=bus_id,
        socketio=socketio
    )

    if socketio:
        socketio.emit('driver_reassigned', {
            'bus_id': bus_id,
            'bus_number': bus_number,
            'driver_name': driver_name,
            'driver_phone': driver_phone
        })

    return jsonify({'success': True, 'message': msg})

@admin_bp.route('/api/arrange_replacement_bus', methods=['POST'])
@admin_required
def arrange_replacement_bus():
    data = request.get_json() or {}
    orig_bus_id = data.get('original_bus_id')
    repl_bus_id = data.get('replacement_bus_id')

    if not orig_bus_id or not repl_bus_id:
        return jsonify({'success': False, 'message': 'Original bus and Replacement bus required'}), 400

    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT bus_number, (SELECT route_id FROM bus_routes WHERE bus_id = buses.id) FROM buses WHERE id = ?;", (orig_bus_id,))
        orig_row = cursor.fetchone()
        cursor.execute("SELECT bus_number FROM buses WHERE id = ?;", (repl_bus_id,))
        repl_row = cursor.fetchone()

        orig_num = orig_row[0] if orig_row else 'Bus 2'
        route_id = orig_row[1] if orig_row and orig_row[1] else 1
        repl_num = repl_row[0] if repl_row else 'Bus 6'

        # Update statuses
        cursor.execute("UPDATE buses SET status = 'STOPPED' WHERE id = ?;", (orig_bus_id,))
        cursor.execute("UPDATE buses SET status = 'ACTIVE' WHERE id = ?;", (repl_bus_id,))

        cursor.execute("""
        INSERT INTO replacement_buses (original_bus_id, replacement_bus_id, route_id, reason, status)
        VALUES (?, ?, ?, 'Breakdown / Emergency Dispatch', 'ACTIVE');
        """, (orig_bus_id, repl_bus_id, route_id))

        conn.commit()
    finally:
        conn.close()

    socketio = current_app.extensions.get('socketio')
    popup_msg = f"Replacement bus arranged for Route {route_id}."
    voice_msg = f"Replacement bus has been arranged for Route {route_id}."

    NotificationService.create_notification(
        type_name='REPLACEMENT_BUS',
        message=popup_msg,
        bus_id=orig_bus_id,
        socketio=socketio
    )

    if socketio:
        socketio.emit('replacement_bus_arranged', {
            'original_bus_id': orig_bus_id,
            'original_bus_number': orig_num,
            'replacement_bus_id': repl_bus_id,
            'replacement_bus_number': repl_num,
            'popup_message': popup_msg,
            'voice_message': voice_msg
        })

    return jsonify({'success': True, 'message': popup_msg})

@admin_bp.route('/api/resolve_emergency/<int:emergency_id>', methods=['POST'])
@admin_required
def resolve_emergency(emergency_id):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT bus_id FROM emergency_alerts WHERE id = ?;", (emergency_id,))
        row = cursor.fetchone()
        if row:
            bus_id = row[0]
            cursor.execute("UPDATE emergency_alerts SET status = 'RESOLVED' WHERE id = ?;", (emergency_id,))
            cursor.execute("UPDATE buses SET status = 'STOPPED' WHERE id = ?;", (bus_id,))
            conn.commit()

            socketio = current_app.extensions.get('socketio')
            if socketio:
                socketio.emit('emergency_resolved', {'emergency_id': emergency_id, 'bus_id': bus_id})
    finally:
        conn.close()

    return jsonify({'success': True, 'message': 'Emergency resolved.'})

@admin_bp.route('/api/simulation/control', methods=['POST'])
@admin_required
def simulation_control():
    data = request.get_json() or {}
    action = data.get('action')

    simulation = current_app.config.get('SIMULATION_SERVICE')
    if not simulation:
        return jsonify({'success': False, 'message': 'Simulation service uninitialized'}), 500

    if action == 'start':
        simulation.start()
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE buses SET status = 'ACTIVE';")
            conn.commit()
        finally:
            conn.close()
    elif action == 'stop':
        simulation.stop()
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE buses SET status = 'STOPPED';")
            conn.commit()
        finally:
            conn.close()
    elif action == 'pause':
        simulation.pause()
    elif action == 'resume':
        simulation.resume()
    elif action == 'set_speed':
        simulation.set_speed(data.get('speed', 1.0))

    return jsonify({'success': True, 'action': action})

