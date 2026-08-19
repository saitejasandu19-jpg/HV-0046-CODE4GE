import os
import sqlite3
from flask import Flask, render_template, jsonify, session, request
from flask_socketio import SocketIO, emit, join_room
from config import Config
from services.bus_simulator import BusSimulator
from services.notification_service import NotificationService

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent' if os.environ.get('USE_GEVENT') else 'threading')
    app.extensions['socketio'] = socketio

    # Initialize Bus Simulator
    simulator = BusSimulator(app, socketio)
    app.config['SIMULATION_SERVICE'] = simulator

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.driver import driver_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(admin_bp)

    DB_PATH = os.path.join(app.config['BASE_DIR'], 'database', 'campus_transport.db')

    # Landing Page Route
    @app.route('/')
    def index():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM buses;")
        total_buses = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM buses WHERE status = 'ACTIVE';")
        active_buses = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM routes;")
        active_routes = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM emergency_alerts WHERE status = 'ACTIVE';")
        active_emergencies = cursor.fetchone()[0]

        conn.close()

        return render_template(
            'index.html',
            total_buses=total_buses,
            active_buses=active_buses,
            active_routes=active_routes,
            active_emergencies=active_emergencies,
            safety_status='SECURE' if active_emergencies == 0 else 'ALERT'
        )

    # Public API Endpoints
    @app.route('/api/buses', methods=['GET'])
    def get_buses():
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT b.id, b.bus_number, b.registration_number, b.qr_code_value, b.status, b.current_latitude, b.current_longitude, 
               b.speed, b.heading, d.name, d.phone, r.route_name
        FROM buses b
        LEFT JOIN drivers d ON b.current_driver_id = d.id
        LEFT JOIN bus_routes br ON b.id = br.bus_id
        LEFT JOIN routes r ON br.route_id = r.id;
        """)
        rows = cursor.fetchall()
        conn.close()

        buses = [
            {
                'id': r[0],
                'bus_number': r[1],
                'registration_number': r[2],
                'qr_code_value': r[3] or f"VCT-BUS-00{r[0]}",
                'status': r[4],
                'current_latitude': r[5],
                'current_longitude': r[6],
                'speed': r[7],
                'heading': r[8],
                'driver_name': r[9] or 'Unassigned',
                'driver_phone': r[10] or 'N/A',
                'route_name': r[11] or 'Unassigned'
            } for r in rows
        ]

        return jsonify({'buses': buses})


    @app.route('/api/routes', methods=['GET'])
    def get_routes():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, route_name FROM routes;")
        route_rows = cursor.fetchall()

        routes_list = []
        for r_id, r_name in route_rows:
            cursor.execute("SELECT id, stop_name, latitude, longitude, sequence_number FROM stops WHERE route_id = ? ORDER BY sequence_number;", (r_id,))
            stops = [
                {
                    'id': s[0],
                    'stop_name': s[1],
                    'latitude': s[2],
                    'longitude': s[3],
                    'sequence_number': s[4]
                } for s in cursor.fetchall()
            ]

            # Road geometry points
            waypoints = [{'lat': s['latitude'], 'lng': s['longitude']} for s in stops]
            from services.gps_service import GPSService
            geometry = GPSService.get_road_geometry(waypoints)

            routes_list.append({
                'id': r_id,
                'route_name': r_name,
                'stops': stops,
                'road_geometry': geometry
            })

        conn.close()
        return jsonify({'routes': routes_list})

    @app.route('/api/notifications', methods=['GET'])
    def get_notifications():
        bus_id = request.args.get('bus_id')
        notifs = NotificationService.get_recent_notifications(bus_id=bus_id)
        return jsonify({'notifications': notifs})

    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM buses;")
        total_buses = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM buses WHERE status = 'ACTIVE';")
        active_buses = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM emergency_alerts WHERE status = 'ACTIVE';")
        active_emergencies = cursor.fetchone()[0]
        conn.close()

        return jsonify({
            'total_buses': total_buses,
            'active_buses': active_buses,
            'active_emergencies': active_emergencies,
            'safety_status': 'SECURE' if active_emergencies == 0 else 'ALERT'
        })

    @app.route('/api/directions', methods=['GET'])
    def get_directions():
        bus_id = request.args.get('bus_id', type=int)
        dest_stop_id = request.args.get('dest_stop_id', type=int)
        dest_lat = request.args.get('dest_lat', type=float)
        dest_lng = request.args.get('dest_lng', type=float)

        if not bus_id:
            return jsonify({'success': False, 'message': 'bus_id required'}), 400

        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        cursor = conn.cursor()

        try:
            cursor.execute("""
            SELECT b.id, b.bus_number, b.current_latitude, b.current_longitude, b.speed, r.route_name, r.id
            FROM buses b
            LEFT JOIN bus_routes br ON b.id = br.bus_id
            LEFT JOIN routes r ON br.route_id = r.id
            WHERE b.id = ?;
            """, (bus_id,))
            bus_row = cursor.fetchone()

            if not bus_row or not bus_row[2] or not bus_row[3]:
                return jsonify({'success': False, 'message': 'Bus location unavailable'}), 404

            b_id, b_num, bus_lat, bus_lng, speed, route_name, r_id = bus_row

            # Determine destination coordinates & stop name
            target_lat, target_lng, target_stop_name = None, None, "Selected Pickup Stop"
            if dest_stop_id:
                cursor.execute("SELECT stop_name, latitude, longitude FROM stops WHERE id = ?;", (dest_stop_id,))
                s_row = cursor.fetchone()
                if s_row:
                    target_stop_name, target_lat, target_lng = s_row[0], s_row[1], s_row[2]
            
            if not target_lat or not target_lng:
                if dest_lat and dest_lng:
                    target_lat, target_lng = dest_lat, dest_lng
                else:
                    # Default to Vignan Campus Gate stop
                    cursor.execute("SELECT stop_name, latitude, longitude FROM stops WHERE route_id = ? ORDER BY sequence_number LIMIT 1 OFFSET 2;", (r_id or 1,))
                    s_row = cursor.fetchone()
                    if s_row:
                        target_stop_name, target_lat, target_lng = s_row[0], s_row[1], s_row[2]
                    else:
                        target_lat, target_lng = 16.2330, 80.5490

            # Calculate road geometry using OSRM
            from services.gps_service import GPSService
            from services.eta_service import ETAService

            waypoints = [{'lat': bus_lat, 'lng': bus_lng}, {'lat': target_lat, 'lng': target_lng}]
            road_geometry = GPSService.get_road_geometry(waypoints)

            # Calculate distance & ETA
            dist_km = ETAService.haversine_distance(bus_lat, bus_lng, target_lat, target_lng)
            eta_min = ETAService.calculate_eta_minutes(dist_km, speed or 25.0)

            # Fetch route stops for turn-by-turn directions
            cursor.execute("SELECT stop_name FROM stops WHERE route_id = ? ORDER BY sequence_number;", (r_id or 1,))
            stop_rows = cursor.fetchall()
            stops_chain = [st[0] for st in stop_rows] if stop_rows else ['Campus Entrance', 'Main Hall', 'Vignan Campus']

            BUS_COLORS = { 1: '#1E88E5', 2: '#E53935', 3: '#43A047', 4: '#FB8C00', 5: '#8E24AA', 6: '#00ACC1' }

            directions_steps = [
                f"1. Start at {b_num} current GPS location ({round(bus_lat, 4)}, {round(bus_lng, 4)}).",
                f"2. Follow road geometry along {route_name or 'Campus Corridor'}.",
                f"3. Pass through intermediate stops: {', '.join(stops_chain[:3])}.",
                f"4. Turn towards {target_stop_name}.",
                f"5. Arrive at {target_stop_name} (Destination)."
            ]

            return jsonify({
                'success': True,
                'bus_id': b_id,
                'bus_number': b_num,
                'bus_color': BUS_COLORS.get(b_id, '#1E88E5'),
                'destination_stop': target_stop_name,
                'distance_km': dist_km,
                'eta_minutes': eta_min,
                'road_geometry': road_geometry,
                'directions_steps': directions_steps
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'Unable to calculate road directions right now: {str(e)}'}), 500
        finally:
            conn.close()

    # SocketIO Event Handlers

    @socketio.on('connect')
    def handle_connect():
        pass

    @socketio.on('join_bus')
    def on_join_bus(data):
        bus_id = data.get('bus_id')
        if bus_id:
            room = f"bus_{bus_id}"
            join_room(room)
            emit('joined_room', {'room': room, 'message': f'Subscribed to telemetry for Bus {bus_id}'})

    return app, socketio

app, socketio = create_app()

if __name__ == '__main__':
    # Initialize database if not present
    db_file = os.path.join(app.config['BASE_DIR'], 'database', 'campus_transport.db')
    if not os.path.exists(db_file):
        from database.init_db import init_database
        init_database()

    # Start simulation engine
    simulator = app.config['SIMULATION_SERVICE']
    simulator.start()

    print("Starting VIGNAN CAMPUS TRANSPORT SYSTEM on http://127.0.0.1:8082 ...")
    socketio.run(app, host="127.0.0.1", port=8082, debug=True, allow_unsafe_werkzeug=True)

