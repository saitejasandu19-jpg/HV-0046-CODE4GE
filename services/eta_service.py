import math

class ETAService:
    @staticmethod
    def haversine_distance(lat1, lng1, lat2, lng2):
        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            return 0.0
        R = 6371.0 # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)

    @staticmethod
    def calculate_eta_minutes(distance_km, speed_kmh=25.0):
        if speed_kmh <= 1.0:
            speed_kmh = 25.0
        if distance_km <= 0.05: # <= 50 meters
            return 0
        hours = distance_km / speed_kmh
        return max(1, int(math.ceil(hours * 60)))

    @staticmethod
    def calculate_bearing(lat1, lng1, lat2, lng2):
        if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
            return 0.0
        d_lng = math.radians(lng2 - lng1)
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)

        y = math.sin(d_lng) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lng))

        initial_bearing = math.atan2(y, x)
        return round((math.degrees(initial_bearing) + 360) % 360, 1)
