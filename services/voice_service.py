class VoiceService:
    @staticmethod
    def format_distance_message(bus_number, distance_km):
        return f"{bus_number} is {distance_km:.1f} kilometers away from you."

    @staticmethod
    def format_eta_message(bus_number, stop_name, minutes):
        return f"{bus_number} will reach {stop_name} in approximately {minutes} minutes."

    @staticmethod
    def format_approaching_message(bus_number, stop_name):
        return f"{bus_number} is approaching {stop_name}."

    @staticmethod
    def format_arrival_message(bus_number, stop_name):
        return f"{bus_number} has arrived at {stop_name}."

    @staticmethod
    def format_start_trip_message(bus_number):
        return f"{bus_number} has started its trip."

    @staticmethod
    def format_stop_trip_message(bus_number):
        return f"{bus_number} has stopped."

    @staticmethod
    def format_emergency_message(bus_number):
        return f"Emergency alert. {bus_number} has reported an emergency."

    @staticmethod
    def format_replacement_message(route_name, replacement_bus_number):
        return f"Replacement bus has been arranged for {route_name}. {replacement_bus_number} is now serving your route."
