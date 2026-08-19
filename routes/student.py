import sqlite3
import os
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, flash
from functools import wraps

student_bp = Blueprint('student', __name__, url_prefix='/student')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'campus_transport.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'STUDENT':
            flash('Access restricted to students only.', 'danger')
            return redirect(url_for('auth.login_student'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@student_required
def dashboard():
    user_id = session['user_id']
    conn = get_db()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, student_id, name, phone, selected_bus_id, pickup_stop_id FROM students WHERE id = ?;", (user_id,))
        student_row = cursor.fetchone()

        # Get all buses
        cursor.execute("""
        SELECT b.id, b.bus_number, b.registration_number, b.status, r.route_name
        FROM buses b
        LEFT JOIN bus_routes br ON b.id = br.bus_id
        LEFT JOIN routes r ON br.route_id = r.id;
        """)
        buses = cursor.fetchall()
        buses_list = [
            {
                'id': b[0],
                'bus_number': b[1],
                'registration_number': b[2],
                'status': b[3],
                'route_name': b[4] or 'Unassigned'
            } for b in buses
        ]

        selected_bus = None
        if student_row and student_row[4]:
            cursor.execute("""
            SELECT b.id, b.bus_number, b.registration_number, b.qr_code_value, b.status, b.speed, r.route_name, d.name, d.phone
            FROM buses b
            LEFT JOIN bus_routes br ON b.id = br.bus_id
            LEFT JOIN routes r ON br.route_id = r.id
            LEFT JOIN drivers d ON b.current_driver_id = d.id
            WHERE b.id = ?;
            """, (student_row[4],))
            sb_row = cursor.fetchone()
            if sb_row:
                qr_val = sb_row[3] or f"VCT-BUS-00{sb_row[0]}"
                selected_bus = {
                    'id': sb_row[0],
                    'bus_number': sb_row[1],
                    'registration_number': sb_row[2],
                    'qr_code_value': qr_val,
                    'qr_image_url': f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_val}",
                    'status': sb_row[4],
                    'speed': sb_row[5],
                    'route_name': sb_row[6],
                    'driver_name': sb_row[7] or 'Unassigned',
                    'driver_phone': sb_row[8] or 'N/A'
                }
    finally:
        conn.close()

    student_data = {
        'id': student_row[0],
        'student_id': student_row[1],
        'name': student_row[2],
        'phone': student_row[3],
        'selected_bus_id': student_row[4],
        'pickup_stop_id': student_row[5]
    }

    return render_template(
        'student_dashboard.html',
        student=student_data,
        buses=buses_list,
        selected_bus=selected_bus
    )

@student_bp.route('/api/select_bus', methods=['POST'])
@student_required
def select_bus():
    data = request.get_json() or {}
    bus_id = data.get('bus_id')
    user_id = session['user_id']

    conn = get_db()
    selected_bus = None
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET selected_bus_id = ? WHERE id = ?;", (bus_id, user_id))
        conn.commit()

        cursor.execute("""
        SELECT b.id, b.bus_number, b.registration_number, b.qr_code_value, b.status, r.route_name, d.name, d.phone
        FROM buses b
        LEFT JOIN bus_routes br ON b.id = br.bus_id
        LEFT JOIN routes r ON br.route_id = r.id
        LEFT JOIN drivers d ON b.current_driver_id = d.id
        WHERE b.id = ?;
        """, (bus_id,))
        sb_row = cursor.fetchone()

        if sb_row:
            qr_val = sb_row[3] or f"VCT-BUS-00{sb_row[0]}"
            
            # Get route stops
            cursor.execute("""
            SELECT s.id, s.stop_name, s.latitude, s.longitude, s.sequence_number
            FROM stops s
            JOIN bus_routes br ON s.route_id = br.route_id
            WHERE br.bus_id = ?
            ORDER BY s.sequence_number;
            """, (bus_id,))
            stops_list = [
                {
                    'id': st[0],
                    'stop_name': st[1],
                    'latitude': st[2],
                    'longitude': st[3],
                    'sequence_number': st[4]
                } for st in cursor.fetchall()
            ]

            selected_bus = {
                'id': sb_row[0],
                'bus_number': sb_row[1],
                'registration_number': sb_row[2],
                'qr_code_value': qr_val,
                'qr_image_url': f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_val}",
                'status': sb_row[4],
                'route_name': sb_row[5],
                'driver_name': sb_row[6] or 'Unassigned',
                'driver_phone': sb_row[7] or 'N/A',
                'stops': stops_list
            }
    finally:
        conn.close()

    return jsonify({'success': True, 'selected_bus': selected_bus})

@student_bp.route('/api/select_pickup_stop', methods=['POST'])
@student_required
def select_pickup_stop():
    data = request.get_json() or {}
    stop_id = data.get('pickup_stop_id')
    user_id = session['user_id']

    conn = get_db()
    stop_data = None
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE students SET pickup_stop_id = ? WHERE id = ?;", (stop_id, user_id))
        conn.commit()

        cursor.execute("SELECT id, stop_name, latitude, longitude FROM stops WHERE id = ?;", (stop_id,))
        stop_row = cursor.fetchone()
        if stop_row:
            stop_data = {
                'id': stop_row[0],
                'stop_name': stop_row[1],
                'latitude': stop_row[2],
                'longitude': stop_row[3]
            }
    finally:
        conn.close()

    return jsonify({'success': True, 'pickup_stop': stop_data})

@student_bp.route('/api/scan_qr', methods=['POST'])
@student_required
def scan_qr():
    data = request.get_json() or {}
    qr_code = data.get('qr_code', '').strip().upper()

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, bus_number, qr_code_value FROM buses;")
        all_buses = cursor.fetchall()

        matched_bus_id = None
        for b_id, b_num, qr_val in all_buses:
            num_digit = ''.join(filter(str.isdigit, b_num))
            if (qr_val and qr_val.upper() in qr_code) or (f"VCT-BUS-00{b_id}" in qr_code) or (f"BUS00{b_id}" in qr_code) or (f"BUS0{b_id}" in qr_code) or (b_num.upper() in qr_code) or (num_digit == qr_code):
                matched_bus_id = b_id
                break

        if not matched_bus_id and qr_code.isdigit():
            matched_bus_id = int(qr_code)

        if not matched_bus_id:
            return jsonify({'success': False, 'message': f'This QR code "{qr_code}" is not registered with Vignan Campus Transport System.'}), 404

        # Update selected bus for student
        user_id = session['user_id']
        cursor.execute("UPDATE students SET selected_bus_id = ? WHERE id = ?;", (matched_bus_id, user_id))
        conn.commit()

        cursor.execute("""
        SELECT b.id, b.bus_number, b.registration_number, b.qr_code_value, b.status, r.route_name, d.name, d.phone
        FROM buses b
        LEFT JOIN bus_routes br ON b.id = br.bus_id
        LEFT JOIN routes r ON br.route_id = r.id
        LEFT JOIN drivers d ON b.current_driver_id = d.id
        WHERE b.id = ?;
        """, (matched_bus_id,))
        sb_row = cursor.fetchone()

        qr_val = sb_row[3] or f"VCT-BUS-00{sb_row[0]}"
        selected_bus = {
            'id': sb_row[0],
            'bus_number': sb_row[1],
            'registration_number': sb_row[2],
            'qr_code_value': qr_val,
            'qr_image_url': f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={qr_val}",
            'status': sb_row[4],
            'route_name': sb_row[5],
            'driver_name': sb_row[6] or 'Unassigned',
            'driver_phone': sb_row[7] or 'N/A'
        }
    finally:
        conn.close()

    return jsonify({
        'success': True,
        'message': f"Scanned & Selected {selected_bus['bus_number']} (QR: {qr_val}) successfully!",
        'selected_bus': selected_bus
    })


