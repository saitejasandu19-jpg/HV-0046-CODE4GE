import os
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), 'campus_transport.db')

def init_database():
    print(f"Initializing SQLite database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    cursor = conn.cursor()


    # Drop existing tables
    tables = [
        'students', 'drivers', 'buses', 'routes', 'stops', 'bus_routes',
        'trips', 'notifications', 'emergency_alerts', 'replacement_buses',
        'bus_locations', 'admins'
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")

    # 1. students
    cursor.execute("""
    CREATE TABLE students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        password TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        selected_bus_id INTEGER,
        pickup_stop_id INTEGER
    );
    """)

    # 2. drivers
    cursor.execute("""
    CREATE TABLE drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        password TEXT NOT NULL,
        license_number TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE'
    );
    """)

    # 3. buses
    cursor.execute("""
    CREATE TABLE buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_number TEXT UNIQUE NOT NULL,
        registration_number TEXT UNIQUE NOT NULL,
        qr_code_value TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'STOPPED',
        current_driver_id INTEGER,
        current_latitude REAL,
        current_longitude REAL,
        current_stop_id INTEGER,
        speed REAL DEFAULT 0.0,
        heading REAL DEFAULT 0.0,
        FOREIGN KEY(current_driver_id) REFERENCES drivers(id)
    );
    """)


    # 4. routes
    cursor.execute("""
    CREATE TABLE routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_name TEXT NOT NULL
    );
    """)

    # 5. stops
    cursor.execute("""
    CREATE TABLE stops (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL,
        stop_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        sequence_number INTEGER NOT NULL,
        FOREIGN KEY(route_id) REFERENCES routes(id)
    );
    """)

    # 6. bus_routes
    cursor.execute("""
    CREATE TABLE bus_routes (
        bus_id INTEGER NOT NULL,
        route_id INTEGER NOT NULL,
        PRIMARY KEY(bus_id, route_id),
        FOREIGN KEY(bus_id) REFERENCES buses(id),
        FOREIGN KEY(route_id) REFERENCES routes(id)
    );
    """)

    # 7. trips
    cursor.execute("""
    CREATE TABLE trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER NOT NULL,
        driver_id INTEGER NOT NULL,
        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_time TIMESTAMP,
        status TEXT DEFAULT 'IN_PROGRESS',
        FOREIGN KEY(bus_id) REFERENCES buses(id),
        FOREIGN KEY(driver_id) REFERENCES drivers(id)
    );
    """)

    # 8. notifications
    cursor.execute("""
    CREATE TABLE notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bus_id INTEGER,
        type TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read_status INTEGER DEFAULT 0
    );
    """)

    # 9. emergency_alerts
    cursor.execute("""
    CREATE TABLE emergency_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER NOT NULL,
        driver_id INTEGER,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'ACTIVE',
        FOREIGN KEY(bus_id) REFERENCES buses(id)
    );
    """)

    # 10. replacement_buses
    cursor.execute("""
    CREATE TABLE replacement_buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_bus_id INTEGER NOT NULL,
        replacement_bus_id INTEGER NOT NULL,
        route_id INTEGER NOT NULL,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'ACTIVE'
    );
    """)

    # 11. bus_locations
    cursor.execute("""
    CREATE TABLE bus_locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(bus_id) REFERENCES buses(id)
    );
    """)

    # 12. admins
    cursor.execute("""
    CREATE TABLE admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    );
    """)

    print("Created database schema tables successfully.")

    # ----------------------------------------------------
    # SEED INITIAL TEST DATA
    # ----------------------------------------------------
    hashed_pwd = generate_password_hash('password123')
    hashed_admin_pwd = generate_password_hash('admin123')

    # Seed Admin
    cursor.execute("INSERT INTO admins (admin_id, name, password) VALUES (?, ?, ?);",
                   ('ADMIN001', 'Transport Administrator', hashed_admin_pwd))

    # Seed 2 Routes
    cursor.execute("INSERT INTO routes (route_name) VALUES ('Route 1: Guntur City Express');")
    route1_id = cursor.lastrowid
    cursor.execute("INSERT INTO routes (route_name) VALUES ('Route 2: Tenali Highway Corridor');")
    route2_id = cursor.lastrowid

    # Seed 5 Stops per Route
    stops_r1 = [
        ('Guntur Collectorate Square', 16.3060, 80.4360, 1),
        ('Guntur RTC Bus Station', 16.3000, 80.4430, 2),
        ('Autonagar Junction', 16.2850, 80.4650, 3),
        ('Chebrolu X Roads', 16.2080, 80.5280, 4),
        ('Vignan Campus Main Gate', 16.2330, 80.5490, 5)
    ]
    stops_r2 = [
        ('Tenali Junction', 16.2430, 80.6400, 1),
        ('Tenali Market Flyover', 16.2410, 80.6300, 2),
        ('Sangam Jagarlamudi', 16.2380, 80.5890, 3),
        ('Vejendla Terminal', 16.2420, 80.5650, 4),
        ('Vignan North Gate', 16.2345, 80.5480, 5)
    ]

    r1_stop_ids = []
    for name, lat, lng, seq in stops_r1:
        cursor.execute("INSERT INTO stops (route_id, stop_name, latitude, longitude, sequence_number) VALUES (?, ?, ?, ?, ?);",
                       (route1_id, name, lat, lng, seq))
        r1_stop_ids.append(cursor.lastrowid)

    r2_stop_ids = []
    for name, lat, lng, seq in stops_r2:
        cursor.execute("INSERT INTO stops (route_id, stop_name, latitude, longitude, sequence_number) VALUES (?, ?, ?, ?, ?);",
                       (route2_id, name, lat, lng, seq))
        r2_stop_ids.append(cursor.lastrowid)

    # Seed 6 Drivers
    drivers_list = [
        ('DRV001', 'Ramesh Kumar (Driver A)', '+91 98765 11111', 'DL-2018-001'),
        ('DRV002', 'Suresh Reddy (Driver B)', '+91 98765 22222', 'DL-2019-002'),
        ('DRV003', 'Anita Deshmukh', '+91 98765 33333', 'DL-2020-003'),
        ('DRV004', 'Kumar Swamy', '+91 98765 44444', 'DL-2017-004'),
        ('DRV005', 'Vikram Singh', '+91 98765 55555', 'DL-2021-005'),
        ('DRV006', 'Rajesh Varma (Standby)', '+91 98765 66666', 'DL-2022-006')
    ]
    driver_ids = []
    for d_id, name, phone, lic in drivers_list:
        cursor.execute("INSERT INTO drivers (driver_id, name, phone, password, license_number) VALUES (?, ?, ?, ?, ?);",
                       (d_id, name, phone, hashed_pwd, lic))
        driver_ids.append(cursor.lastrowid)

    # Seed 6 Buses starting from DIFFERENT stops
    # Bus 1 -> Stop 1, Bus 2 -> Stop 3, Bus 3 -> Stop 5, Bus 4 -> Stop 2, Bus 5 -> Stop 4
    buses_list = [
        ('Bus 1', 'AP-07-VT-1001', 'VCT-BUS-001', 'ACTIVE', driver_ids[0], stops_r1[0][1], stops_r1[0][2], r1_stop_ids[0]),
        ('Bus 2', 'AP-07-VT-1002', 'VCT-BUS-002', 'ACTIVE', driver_ids[1], stops_r2[2][1], stops_r2[2][2], r2_stop_ids[2]),
        ('Bus 3', 'AP-07-VT-1003', 'VCT-BUS-003', 'ACTIVE', driver_ids[2], stops_r1[4][1], stops_r1[4][2], r1_stop_ids[4]),
        ('Bus 4', 'AP-07-VT-1004', 'VCT-BUS-004', 'ACTIVE', driver_ids[3], stops_r2[1][1], stops_r2[1][2], r2_stop_ids[1]),
        ('Bus 5', 'AP-07-VT-1005', 'VCT-BUS-005', 'ACTIVE', driver_ids[4], stops_r1[3][1], stops_r1[3][2], r1_stop_ids[3]),
        ('Bus 6', 'AP-07-VT-1006 (Spare)', 'VCT-BUS-006', 'STOPPED', driver_ids[5], stops_r2[0][1], stops_r2[0][2], r2_stop_ids[0])
    ]

    bus_ids = []
    for num, reg, qr_val, status, d_id, lat, lng, stop_id in buses_list:
        cursor.execute("""
        INSERT INTO buses (bus_number, registration_number, qr_code_value, status, current_driver_id, current_latitude, current_longitude, current_stop_id, speed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 25.0);
        """, (num, reg, qr_val, status, d_id, lat, lng, stop_id))
        b_id = cursor.lastrowid
        bus_ids.append(b_id)


        # bus_routes association
        r_id = route1_id if '1' in num or '3' in num or '5' in num else route2_id
        cursor.execute("INSERT INTO bus_routes (bus_id, route_id) VALUES (?, ?);", (b_id, r_id))

    # Seed 10 Students
    students_list = [
        ('STU001', 'Aarav Sharma', '+91 91111 00001', bus_ids[1], r2_stop_ids[1]), # Selected Bus 2
        ('STU002', 'Ananya Rao', '+91 91111 00002', bus_ids[0], r1_stop_ids[0]),
        ('STU003', 'Rohan Patel', '+91 91111 00003', bus_ids[1], r2_stop_ids[2]),
        ('STU004', 'Priya Iyer', '+91 91111 00004', bus_ids[2], r1_stop_ids[3]),
        ('STU005', 'Siddharth Verma', '+91 91111 00005', bus_ids[3], r2_stop_ids[1]),
        ('STU006', 'Sneha Reddy', '+91 91111 00006', bus_ids[4], r1_stop_ids[0]),
        ('STU007', 'Aditya Nair', '+91 91111 00007', bus_ids[0], r1_stop_ids[1]),
        ('STU008', 'Meera Joshi', '+91 91111 00008', bus_ids[1], r2_stop_ids[3]),
        ('STU009', 'Varun Mehta', '+91 91111 00009', bus_ids[2], r1_stop_ids[2]),
        ('STU010', 'Kavya Gupta', '+91 91111 00010', bus_ids[3], r2_stop_ids[0])
    ]

    for s_id, name, phone, b_id, stop_id in students_list:
        cursor.execute("""
        INSERT INTO students (student_id, name, phone, password, latitude, longitude, selected_bus_id, pickup_stop_id)
        VALUES (?, ?, ?, ?, 16.2330, 80.5490, ?, ?);
        """, (s_id, name, phone, hashed_pwd, b_id, stop_id))

    # Initial Notifications
    cursor.execute("INSERT INTO notifications (user_id, bus_id, type, message) VALUES (NULL, 1, 'BUS_STARTED', 'Bus 1 has started its trip.');")
    cursor.execute("INSERT INTO notifications (user_id, bus_id, type, message) VALUES (NULL, 2, 'BUS_STARTED', 'Bus 2 has started its trip.');")

    conn.commit()
    conn.close()
    print("Database initial seed completed successfully!")

if __name__ == '__main__':
    init_database()
