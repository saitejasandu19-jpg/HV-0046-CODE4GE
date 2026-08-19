import time
import threading
import sqlite3
import os
import logging
from services.gps_service import GPSService
from services.eta_service import ETAService
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'campus_transport.db')

class BusSimulator:
    def __init__(self, app=None, socketio=None):
        self.app = app
        self.socketio = socketio
        self.is_running = False
        self.is_paused = False
        self.speed_multiplier = 1.0
        self.thread = None
        
        self.route_geometries = {}
        self.bus_states = {}

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.thread.start()
            logger.info("Vignan Bus Simulator background thread started.")

    def stop(self):
        self.is_running = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def set_speed(self, multiplier):
        self.speed_multiplier = float(multiplier)

    def _get_db_connection(self):
        conn = sqlite3.connect(DB_PATH, timeout=20.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn


    def _load_route_geometry(self, route_id, conn):
        if route_id in self.route_geometries:
            return self.route_geometries[route_id]

        cursor = conn.cursor()
        cursor.execute("SELECT latitude, longitude FROM stops WHERE route_id = ? ORDER BY sequence_number;", (route_id,))
        rows = cursor.fetchall()

        if len(rows) < 2:
            return []

        waypoints = [{'lat': r[0], 'lng': r[1]} for r in rows]
        geometry = GPSService.get_road_geometry(waypoints)
        self.route_geometries[route_id] = geometry
        return geometry

    def _simulation_loop(self):
        # Starting index offsets for buses so each starts at a DIFFERENT stop
        start_offsets = { 1: 0, 2: 12, 3: 25, 4: 8, 5: 18 }

        while self.is_running:
            time.sleep(1.0 / self.speed_multiplier)
            if self.is_paused:
                continue

            conn = None
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()

                # Get all active buses
                cursor.execute("""
                SELECT b.id, b.bus_number, b.status, b.current_latitude, b.current_longitude, 
                       br.route_id, d.name, d.phone, d.id
                FROM buses b
                JOIN bus_routes br ON b.id = br.bus_id
                LEFT JOIN drivers d ON b.current_driver_id = d.id
                WHERE b.status = 'ACTIVE';
                """)
                active_buses = cursor.fetchall()

                for b in active_buses:
                    bus_id, bus_number, status, curr_lat, curr_lng, route_id, driver_name, driver_phone, driver_id = b

                    geometry = self._load_route_geometry(route_id, conn)
                    if not geometry or len(geometry) < 2:
                        continue

                    # Initialize starting offset if missing
                    if bus_id not in self.bus_states:
                        init_idx = start_offsets.get(bus_id, 0) % len(geometry)
                        self.bus_states[bus_id] = {'coord_index': init_idx, 'last_stop_id': None}

                    state = self.bus_states[bus_id]
                    idx = state['coord_index']

                    next_idx = (idx + 1) % len(geometry)
                    state['coord_index'] = next_idx

                    curr_pt = geometry[idx]
                    next_pt = geometry[next_idx]

                    new_lat, new_lng = curr_pt[0], curr_pt[1]
                    heading = ETAService.calculate_bearing(curr_pt[0], curr_pt[1], next_pt[0], next_pt[1])
                    speed = round(28.0 * self.speed_multiplier, 1)

                    # Get route stops
                    cursor.execute("SELECT id, stop_name, latitude, longitude, sequence_number FROM stops WHERE route_id = ? ORDER BY sequence_number;", (route_id,))
                    stops = cursor.fetchall()

                    # Find nearest stop & next stop
                    closest_stop = min(stops, key=lambda s: ETAService.haversine_distance(new_lat, new_lng, s[2], s[3]))
                    dist_to_closest = ETAService.haversine_distance(new_lat, new_lng, closest_stop[2], closest_stop[3])

                    curr_stop_seq = closest_stop[4]
                    next_stop = min(stops, key=lambda s: (s[4] - curr_stop_seq) % len(stops) if s[0] != closest_stop[0] else 999)

                    dist_to_next = ETAService.haversine_distance(new_lat, new_lng, next_stop[2], next_stop[3])
                    eta_next = ETAService.calculate_eta_minutes(dist_to_next, speed)

                    # Update bus location in DB
                    cursor.execute("""
                    UPDATE buses 
                    SET current_latitude = ?, current_longitude = ?, speed = ?, heading = ?, current_stop_id = ?
                    WHERE id = ?;
                    """, (new_lat, new_lng, speed, heading, closest_stop[0], bus_id))

                    # Log to bus_locations history table
                    cursor.execute("INSERT INTO bus_locations (bus_id, latitude, longitude) VALUES (?, ?, ?);",
                                   (bus_id, new_lat, new_lng))

                    # Trigger arrival notification when bus is <= 50m (0.05 km) from stop
                    if dist_to_closest <= 0.05 and state['last_stop_id'] != closest_stop[0]:
                        state['last_stop_id'] = closest_stop[0]
                        arr_msg = f"{bus_number} has arrived at {closest_stop[1]}."
                        NotificationService.create_notification(
                            type_name='BUS_ARRIVED',
                            message=arr_msg,
                            bus_id=bus_id,
                            socketio=self.socketio
                        )

                    conn.commit()

                    # Emit Socket.IO telemetry payload
                    payload = {
                        'bus_id': bus_id,
                        'bus_number': bus_number,
                        'status': status,
                        'current_latitude': new_lat,
                        'current_longitude': new_lng,
                        'speed': speed,
                        'heading': heading,
                        'route_id': route_id,
                        'current_stop_name': closest_stop[1],
                        'next_stop_name': next_stop[1],
                        'dist_to_next_km': dist_to_next,
                        'eta_to_next_min': eta_next,
                        'driver': {
                            'id': driver_id,
                            'name': driver_name or 'Unassigned',
                            'phone': driver_phone or 'N/A'
                        }
                    }

                    if self.socketio:
                        self.socketio.emit('bus_location_update', payload)

            except Exception as e:
                logger.error(f"Error in bus simulation thread: {e}")
            finally:
                if conn:
                    conn.close()

