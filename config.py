import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vignan-campus-transport-key-2026'
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_DIR = os.path.join(BASE_DIR, 'database')
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)
        
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{os.path.join(DB_DIR, 'campus_transport.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    OSRM_ROUTING_URL = "http://router.project-osrm.org/route/v1/driving"
    VIGNAN_CAMPUS_LAT = 16.2330
    VIGNAN_CAMPUS_LNG = 80.5490
