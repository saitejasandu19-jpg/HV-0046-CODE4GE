# VIGNAN CAMPUS TRANSPORT SYSTEM
> **Smart • Safe • Live • Connected**
> *Official Vignan Engineering College Smart Campus Bus Tracking & Transport Management Platform*

---

## 📌 Features & System Overview

The **Vignan Campus Transport System** is a full-stack, production-grade web application built for Vignan Engineering College students, bus drivers, and transport administrators.

### Key Capabilities:
- **Separate Role Portals & Authentication**:
  - 👨🎓 **Student Portal**: Student ID (`STU001`) & Password.
  - 👨✈️ **Driver Portal**: Driver Login ID (`DRV001` / `DRV002`) & Password.
  - 👨💼 **Admin Portal**: Admin ID (`ADMIN001`) & Password.
- **📷 Unique Bus QR Code Scanner**:
  - Every bus has a unique QR code (`BUS001`, `BUS002`, `BUS003`, `BUS004`, `BUS005`).
  - Scanning `BUS002` automatically identifies Bus 2, selects it for tracking, centers the map, and streams live telemetry.
- **🔊 Synchronized Popup Toast & Voice Announcement Engine**:
  - *Voice + Popup ALWAYS match*: Every voice announcement is accompanied by an exact corresponding popup toast notification on screen.
  - Spoken & popup alerts at **2.0 km**, **1.0 km**, and **500 m** distance thresholds.
- **🛑 50-Meter Voice Auto-Off Rule**:
  - When the bus reaches <= 50 meters from the student/stop, speaks *"Your bus has arrived."*, displays popup *"Your bus has arrived. Voice notifications turned off."*, and automatically sets **Voice Notifications: OFF**.
- **🛣️ OSRM Road-Following 5-Bus Simulation**:
  - 5 buses starting from 5 DIFFERENT stops moving smoothly along actual road coordinates.
- **🚨 Driver Cockpit & Emergency System**:
  - **START TRIP**, **STOP TRIP**, and 🚨 **EMERGENCY** broadcast.
- **🚌 Admin Emergency Replacement Bus System**:
  - Dispatch Replacement Bus 6 for broken Bus 2 -> Popup: *"Replacement bus arranged for Route 2."* & Voice: *"Replacement bus has been arranged for Route 2."*
- **🔄 Dynamic Driver Assignment**:
  - Reassign Driver B (Suresh) to Bus 2 without changing the Bus 2 identity seen by students.

---

## 📂 Project Structure

```
vignan-campus-transport/
│
├── app.py                      # Flask Server & Socket.IO Entrypoint
├── config.py                   # App Configuration & DB URI
├── requirements.txt            # Python Dependencies
├── README.md                   # Comprehensive Documentation
│
├── database/                   # SQLite Database & Seed Engine
│   ├── campus_transport.db     # SQLite Database File
│   └── init_db.py              # DB Initialization & Seed Script
│
├── routes/                     # Blueprint Handlers
│   ├── __init__.py
│   ├── auth.py                 # Login / Logout for Student, Driver, Admin
│   ├── student.py              # Student Dashboard & QR Code APIs
│   ├── driver.py               # Driver Cockpit, Start/Stop Trip & Emergency APIs
│   └── admin.py                # Admin Panel, Driver Reassignment & Replacement Bus APIs
│
├── services/                   # Business Logic & Algorithms
│   ├── __init__.py
│   ├── eta_service.py          # Haversine distance, speed, bearing & ETA calculator
│   ├── gps_service.py          # OSRM road geometry fetcher & fallback generator
│   ├── notification_service.py # SQLite Notification recorder & SocketIO dispatcher
│   ├── voice_service.py        # Voice alert text formatter
│   └── bus_simulator.py        # 5-bus multi-thread road movement simulator
│
├── templates/                  # Jinja2 HTML Templates
│   ├── index.html              # Vignan Landing Page with 3 portal cards
│   ├── login_student.html      # Student Login Page
│   ├── login_driver.html       # Driver Login Page
│   ├── login_admin.html        # Admin Login Page
│   ├── student_dashboard.html  # Student Dashboard (Live Map, QR Scanner, Bus Card)
│   ├── driver_dashboard.html   # Driver Cockpit (Start/Stop Trip, Emergency)
│   └── admin_dashboard.html    # Admin Control Panel (Fleet Map, Reassignment, Replacement)
│
└── static/                     # Web Assets
    ├── css/
    │   └── style.css           # Modern Vignan CSS Stylesheet
    └── js/
        ├── map.js              # Leaflet Map Manager (buses, student, routes, stops)
        ├── notifications.js    # Synchronized Popup Toast Notification Manager
        ├── voice.js            # Web Speech API Manager (threshold alerts & 50m auto-off)
        ├── student.js          # Student Dashboard & html5-qrcode Reader
        ├── driver.js           # Driver Cockpit Controls & GPS Transmitter
        └── admin.js            # Admin Operations Panel Controls
```

---

## 🔑 Demo Test Login Credentials

| Portal | Login Page URL | Username / ID | Password | Role & Details |
| :--- | :--- | :--- | :--- | :--- |
| **Student Portal** | `/login/student` | `STU001` | `password123` | Student Roll No &bull; Tracked: **Bus 2** |
| **Driver Portal (Driver A)** | `/login/driver` | `DRV001` | `password123` | Driver A &bull; Assigned: **Bus 1** |
| **Driver Portal (Driver B)** | `/login/driver` | `DRV002` | `password123` | Driver B &bull; Assigned: **Bus 2** |
| **Admin Portal** | `/login/admin` | `ADMIN001` | `admin123` | Transport Operations Admin |

---

## ⚡ Step-by-Step Execution & Testing Guide

### 1. Installation Command
```bash
python -m pip install -r requirements.txt
```

### 2. Database Initialization Command
```bash
python database/init_db.py
```

### 3. Start Flask Server
```bash
python app.py
```
*Server starts on `http://127.0.0.1:8000`.*

---

## 🧪 Testing Features

### 1. Student Tracking & Bus QR Code Scanning
- Visit `http://127.0.0.1:8000` and click **STUDENT PORTAL**.

- Log in with `STU001` / `password123`.
- Click **📷 Scan Bus QR** button.
- Scan or type `BUS002`. Confirm Bus 2 is selected, map centers, and driver details populate.

### 2. Voice Notifications & 50m Auto-Off Rule
- Ensure **Voice Notifications: ON** is active in the toolbar.
- As Bus 2 travels along the road, listen to threshold alerts at 2km, 1km, 500m.
- When Bus 2 reaches <= 50m of the stop/student location, observe:
  - Voice: *"Your bus has arrived."*
  - Popup: *"Your bus has arrived. Voice notifications turned off."*
  - Status automatically sets to **Voice Notifications: OFF**.

### 3. Driver Start / Stop / Emergency
- Log in to Driver Portal with `DRV001` / `password123`.
- Click **START TRIP** -> Bus status becomes `ACTIVE`, student receives popup + voice alert *"Bus 1 has started its trip."*
- Click **🚨 EMERGENCY** -> Bus status becomes `EMERGENCY`, student receives popup + voice alert *"Emergency alert: Bus 1 has reported an emergency."*, admin emergency panel highlights incident.

### 4. Admin Driver Reassignment & Replacement Bus Dispatch
- Log in to Admin Panel with `ADMIN001` / `admin123`.
- Go to **Driver Assignments** tab: Reassign Driver B (Suresh) to Bus 2. Student dashboard updates driver name without altering Bus 2 identity.
- Go to **Replacement Bus Wizard** tab: Select Bus 2 and Replacement Bus 6 -> Click **Dispatch**.
  - Student receives Popup: *"Replacement bus arranged for Route 2."*
  - Student receives Voice: *"Replacement bus has been arranged for Route 2."*
# HV-0046-CODE4GE
"Real-Time College Bus Tracking, Route Management and Student Notification System"
