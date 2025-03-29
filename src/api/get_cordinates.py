import asyncio
import datetime
from typing import Dict, Optional
import aiohttp
from geopy.distance import geodesic


class AsyncLocationFinder:
    def __init__(self, tomtom_api_key: Optional[str] = None):
        self.tomtom_api_key = tomtom_api_key
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"

    async def get_coordinates(self, session: aiohttp.ClientSession, place_name: str) -> Optional[Dict]:
        params = {
            "q": place_name,
            "format": "json",
            "limit": 1
        }
        async with session.get(self.nominatim_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data and len(data) > 0:
                    return {
                        "address": data[0].get("display_name"),
                        "latitude": float(data[0].get("lat")),
                        "longitude": float(data[0].get("lon"))
                    }
            return None

    async def get_real_time_traffic(self, session: aiohttp.ClientSession, start_coords: Dict, end_coords: Dict) -> \
            Optional[tuple]:
        if not self.tomtom_api_key:
            return None

        url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
        params = {
            "key": self.tomtom_api_key,
            "point": f"{start_coords['latitude']},{start_coords['longitude']}"
        }
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                current_speed_kmh = data.get("flowSegmentData", {}).get("currentSpeed", 0)
                free_flow_speed_kmh = data.get("flowSegmentData", {}).get("freeFlowSpeed", 0)
                current_speed_mph = current_speed_kmh * 0.621371
                free_flow_speed_mph = free_flow_speed_kmh * 0.621371
                return current_speed_mph, free_flow_speed_mph
            return None

    def calculate_distance(self, start_coords: Dict, end_coords: Dict) -> float:
        distance_km = geodesic(
            (start_coords["latitude"], start_coords["longitude"]),
            (end_coords["latitude"], end_coords["longitude"])
        ).kilometers
        return distance_km * 0.621371

    def estimate_travel_time(self, distance_miles: float, speed_mph: float = 37.2823,
                             traffic_factor: float = 1.0) -> float:
        adjusted_speed = speed_mph / traffic_factor
        travel_time_hours = distance_miles / adjusted_speed
        return travel_time_hours * 60

    async def get_travel_info(self, start_place: str, end_place: str, speed_mph: float = 37.2823) -> Dict:
        async with aiohttp.ClientSession() as session:
            start_task = self.get_coordinates(session, start_place)
            end_task = self.get_coordinates(session, end_place)
            start_location, end_location = await asyncio.gather(start_task, end_task)

            if not start_location or not end_location:
                return {"error": "Joylardan biri topilmadi."}

            distance_miles = self.calculate_distance(start_location, end_location)

            traffic_factor = 1.0
            if self.tomtom_api_key:
                traffic_data = await self.get_real_time_traffic(session, start_location, end_location)
                if traffic_data:
                    current_speed_mph, free_flow_speed_mph = traffic_data
                    if current_speed_mph > 0:
                        speed_mph = current_speed_mph
                        traffic_factor = free_flow_speed_mph / current_speed_mph if free_flow_speed_mph > 0 else 1.0

            travel_time_minutes = self.estimate_travel_time(distance_miles, speed_mph, traffic_factor)
            current_time = datetime.datetime.now()
            arrival_time = current_time + datetime.timedelta(minutes=travel_time_minutes)

            return {
                "start_address": start_location["address"],
                "end_address": end_location["address"],
                "distance_miles": round(distance_miles, 2),
                "travel_time_minutes": round(travel_time_minutes, 2),
                "estimated_arrival": arrival_time.strftime("%Y-%m-%d %H:%M:%S"),
                "used_speed_mph": speed_mph,
                "traffic_factor": traffic_factor
            }


# async def main():
#     tomtom_api_key = "FiiZ05B8AwLfXVod7rolBkKrrUcTmZlv"
#     finder = AsyncLocationFinder(tomtom_api_key)
#
#     start_place = input("Joriy joylashuvni kiriting (masalan, Toshkent): ")
#     end_place = input("Maqsad joylashuvni kiriting (masalan, Samarqand): ")
#     speed_mph = float(input("Avtomobil tezligini kiriting (mph, masalan, 37.28): "))
#
#     result = await finder.get_travel_info(start_place, end_place, speed_mph)
#     print(result)
#
# if __name__ == "__main__":
#     asyncio.run(main())