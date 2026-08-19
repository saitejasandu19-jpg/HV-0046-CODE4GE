import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'campus_transport.db')

class NotificationService:
    @staticmethod
    def create_notification(type_name, message, bus_id=None, user_id=None, socketio=None):
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=20.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            cursor = conn.cursor()
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
            INSERT INTO notifications (user_id, bus_id, type, message, created_at, read_status)
            VALUES (?, ?, ?, ?, ?, 0);
            """, (user_id, bus_id, type_name, message, now_str))
            
            notif_id = cursor.lastrowid
            conn.commit()

            notif_payload = {
                'id': notif_id,
                'user_id': user_id,
                'bus_id': bus_id,
                'type': type_name,
                'message': message,
                'created_at': now_str,
                'read_status': 0
            }

            if socketio:
                socketio.emit('new_notification', notif_payload)

            return notif_payload
        except Exception as e:
            print(f"Error saving notification: {e}")
            return None
        finally:
            if conn:
                conn.close()


    @staticmethod
    def get_recent_notifications(bus_id=None, limit=25):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=20.0)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=5000;")

            cursor = conn.cursor()
            
            if bus_id:
                cursor.execute("""
                SELECT id, user_id, bus_id, type, message, created_at, read_status
                FROM notifications
                WHERE bus_id = ? OR bus_id IS NULL
                ORDER BY id DESC LIMIT ?;
                """, (bus_id, limit))
            else:
                cursor.execute("""
                SELECT id, user_id, bus_id, type, message, created_at, read_status
                FROM notifications
                ORDER BY id DESC LIMIT ?;
                """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    'id': r[0],
                    'user_id': r[1],
                    'bus_id': r[2],
                    'type': r[3],
                    'message': r[4],
                    'created_at': r[5],
                    'read_status': r[6]
                } for r in rows
            ]
        except Exception as e:
            print(f"Error fetching notifications: {e}")
            return []
