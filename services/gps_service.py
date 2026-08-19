import requests
import math
import logging

logger = logging.getLogger(__name__)

class GPSService:
    @staticmethod
    def get_road_geometry(waypoints):
        """
        waypoints: List of (lat, lng) tuples or dicts [{'lat': y, 'lng': x}]
        Returns list of [lat, lng] coordinates following actual roads
        """
        if len(waypoints) < 2:
            return [[wp['lat'], wp['lng']] if isinstance(wp, dict) else [wp[0], wp[1]] for wp in waypoints]

        formatted = []
        for wp in waypoints:
            lat = wp['lat'] if isinstance(wp, dict) else wp[0]
            lng = wp['lng'] if isinstance(wp, dict) else wp[1]
            formatted.append(f"{lng},{lat}")

        coord_str = ";".join(formatted)
        url = f"http://router.project-osrm.org/route/v1/driving/{coord_str}?overview=full&geometries=geojson"

        try:
            res = requests.get(url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                if data.get('code') == 'Ok' and len(data.get('routes', [])) > 0:
                    geometry = data['routes'][0]['geometry']['coordinates']
                    return [[pt[1], pt[0]] for pt in geometry]
        except Exception as e:
            logger.warning(f"OSRM fallback: {e}")

        return GPSService._generate_fallback_points(waypoints)

    @staticmethod
    def _generate_fallback_points(waypoints):
        coords = []
        parsed = []
        for wp in waypoints:
            parsed.append((wp['lat'], wp['lng']) if isinstance(wp, dict) else (wp[0], wp[1]))

        for i in range(len(parsed) - 1):
            p1, p2 = parsed[i], parsed[i+1]
            steps = 15
            for s in range(steps):
                t = s / float(steps)
                curve = math.sin(t * math.pi) * 0.0004
                lat = p1[0] + (p2[0] - p1[0]) * t + curve
                lng = p1[1] + (p2[1] - p1[1]) * t + (curve if (i % 2 == 0) else -curve)
                coords.append([lat, lng])

        coords.append([parsed[-1][0], parsed[-1][1]])
        return coords
