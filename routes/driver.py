import sqlite3
import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash, current_app
from services.notification_service import NotificationService
from datetime import datetime
from functools import wraps

driver_bp = Blueprint('driver', __name__, url_prefix='/driver')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'campus_transport.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def driver_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'DRIVER':
            flash('Access restricted to drivers only.', 'danger')
            return redirect(url_for('auth.login_driver'))
        return f(*args, **kwargs)
    return decorated_function

@driver_bp.route('/dashboard')
@driver_required
def dashboard():
    user_id = session['user_id']
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, driver_id, name, phone, license_number, status FROM drivers WHERE id = ?;", (user_id,))
        driver_row = cursor.fetchone()

        # Get assigned bus
        cursor.execute("""
        SELECT b.id, b.bus_number, b.registration_number, b.status, r.route_name
        FROM buses b
        LEFT JOIN bus_routes br ON b.id = br.bus_id
        LEFT JOIN routes r ON br.route_id = r.id
        WHERE b.current_driver_id = ?;
        """, (user_id,))
        bus_row = cursor.fetchone()
    finally:
        conn.close()

    driver_data = {
        'id': driver_row[0],
        'driver_id': driver_row[1],
        'name': driver_row[2],
        'phone': driver_row[3],
        'license_number': driver_row[4],
        'status': driver_row[5]
    }

    bus_data = None
    if bus_row:
        bus_data = {
            'id': bus_row[0],
            'bus_number': bus_row[1],
            'registration_number': bus_row[2],
            'status': bus_row[3],
            'route_name': bus_row[4] or 'Unassigned'
        }

    return render_template('driver_dashboard.html', driver=driver_data, bus=bus_data)

@driver_bp.route('/api/start_trip', methods=['POST'])
@driver_required
def start_trip():
    user_id = session['user_id']
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, bus_number, current_driver_id FROM buses WHERE current_driver_id = ?;", (user_id,))
        bus_row = cursor.fetchone()

        if not bus_row:
            return jsonify({'success': False, 'message': 'No bus assigned to your account.'}), 400

        bus_id, bus_number, _ = bus_row
        cursor.execute("UPDATE buses SET status = 'ACTIVE' WHERE id = ?;", (bus_id,))
        cursor.execute("INSERT INTO trips (bus_id, driver_id, status) VALUES (?, ?, 'IN_PROGRESS');", (bus_id, user_id))
        conn.commit()
    finally:
        conn.close()

    socketio = current_app.extensions.get('socketio')
    msg = f"{bus_number} has started its trip."
    
    NotificationService.create_notification(
        type_name='BUS_STARTED',
        message=msg,
        bus_id=bus_id,
        socketio=socketio
    )

    if socketio:
        socketio.emit('bus_status_change', {
            'bus_id': bus_id,
            'bus_number': bus_number,
            'status': 'ACTIVE',
            'message': msg
        })

    return jsonify({'success': True, 'message': msg, 'status': 'ACTIVE'})

@driver_bp.route('/api/stop_trip', methods=['POST'])
@driver_required
def stop_trip():
    user_id = session['user_id']
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, bus_number FROM buses WHERE current_driver_id = ?;", (user_id,))
        bus_row = cursor.fetchone()

        if not bus_row:
            return jsonify({'success': False, 'message': 'No bus assigned.'}), 400

        bus_id, bus_number = bus_row
        cursor.execute("UPDATE buses SET status = 'STOPPED' WHERE id = ?;", (bus_id,))
        cursor.execute("UPDATE trips SET status = 'COMPLETED', end_time = CURRENT_TIMESTAMP WHERE bus_id = ? AND status = 'IN_PROGRESS';", (bus_id,))
        conn.commit()
    finally:
        conn.close()

    socketio = current_app.extensions.get('socketio')
    msg = f"{bus_number} has stopped."
    
    NotificationService.create_notification(
        type_name='BUS_STOPPED',
        message=msg,
        bus_id=bus_id,
        socketio=socketio
    )

    if socketio:
        socketio.emit('bus_status_change', {
            'bus_id': bus_id,
            'bus_number': bus_number,
            'status': 'STOPPED',
            'message': msg
        })

    return jsonify({'success': True, 'message': msg, 'status': 'STOPPED'})

@driver_bp.route('/api/emergency', methods=['POST'])
@driver_required
def emergency():
    user_id = session['user_id']
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, bus_number, current_latitude, current_longitude FROM buses WHERE current_driver_id = ?;", (user_id,))
        bus_row = cursor.fetchone()

        if not bus_row:
            return jsonify({'success': False, 'message': 'No assigned bus.'}), 400

        bus_id, bus_number, lat, lng = bus_row
        cursor.execute("UPDATE buses SET status = 'EMERGENCY' WHERE id = ?;", (bus_id,))
        cursor.execute("INSERT INTO emergency_alerts (bus_id, driver_id, message, status) VALUES (?, ?, ?, 'ACTIVE');",
                       (bus_id, user_id, f"Emergency reported on {bus_number}!"))
        conn.commit()
    finally:
        conn.close()

    socketio = current_app.extensions.get('socketio')
    msg = f"Emergency alert: {bus_number} has reported an emergency."
    voice_msg = f"Emergency alert. {bus_number} has reported an emergency."

    NotificationService.create_notification(
        type_name='EMERGENCY',
        message=msg,
        bus_id=bus_id,
        socketio=socketio
    )

    if socketio:
        socketio.emit('emergency_alert', {
            'bus_id': bus_id,
            'bus_number': bus_number,
            'message': msg,
            'voice_message': voice_msg,
            'status': 'EMERGENCY'
        })

    return jsonify({'success': True, 'message': msg, 'status': 'EMERGENCY'})

