import json
import time
from datetime import datetime, timedelta

import aiohttp
import pytz

from src.api.RoadSpeedChecker import RoadSpeedChecker


class SamsaraClient:
    def __init__(self, api_token):
        self.base_url = "https://api.samsara.com"
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    async def fetch_data(self, endpoint, params=None):
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{endpoint}"
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"Error: {response.status} - {error_text} at {url}")
                        return None
            except aiohttp.ClientError as e:
                print(f"Network error: {e}")
                return None

    async def post_data(self, endpoint, data):
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{endpoint}"
            try:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"Error: {response.status} - {error_text} at {url}")
                        return None
            except aiohttp.ClientError as e:
                print(f"Network error: {e}")
                return None

    async def create_webhook(self, webhook_url):
        endpoint = "v1/webhooks"
        data = {
            "version": "2024-02-27",
            "eventTypes": ["SuddenFuelLevelDrop", "SevereSpeedingStarted", "EngineFaultOff", "EngineFaultOn",
                           "SuddenFuelLevelRise", "SevereSpeedingEnded", "RouteStopResequence", "RouteStopDeparture",
                           "RouteStopArrival", "IssueCreated"],
            "name": "Test",
            "url": "https://www.Webhook-123.com/webhook/listener"}
        return await self.post_data(endpoint, data)

    async def get_all_trucks(self):
        endpoint = "/fleet/vehicles"
        data = await self.fetch_data(endpoint)
        if data and "data" in data:
            return data["data"]
        return []

    async def get_all_companies(self):
        endpoint = "v1/fleet/list"
        data = await self.fetch_data(endpoint)
        if data and "data" in data:
            return data["data"]
        return []

    async def get_harsh_event(self, truck_id, timestamp):
        safety_endpoint = f"v1/fleet/vehicles/{truck_id}/safety/harsh_event"
        stats_params = {"timestamp": timestamp}

        return await self.fetch_data(safety_endpoint, stats_params)

    async def get_company_trucks(self, company_id):
        endpoint = "v1/fleet/vehicles"
        params = {"groupId": company_id}
        data = await self.fetch_data(endpoint, params)
        if data and "data" in data:
            return data["data"]
        return []

    async def get_engine_stats(self, truck_id):
        stats_endpoint = "v1/fleet/vehicles/stats"
        start_time_ms = int((time.time() - 3600) * 1000)
        end_time_ms = int(time.time() * 1000)
        stats_params = {
            "types": "engineStates",
            "vehicleId": str(truck_id),
            "startMs": start_time_ms, "endMs": end_time_ms
        }
        stats_data = await self.fetch_data(stats_endpoint, stats_params)
        if stats_data and "vehicleStats" in stats_data and len(stats_data["vehicleStats"]) > 0:
            for vehicle in stats_data["vehicleStats"]:

                if int(vehicle["vehicleId"]) == int(truck_id):

                    engine_states = vehicle.get("engineState", [])
                    if engine_states:
                        latest_state = engine_states[-1]
                        engine_state = latest_state.get("value", "Unknown")
                        return {"engine_state": engine_state}

                    break
        return None

    async def get_fuel_percent(self, truck_id):
        stats_endpoint = "/fleet/vehicles/stats"
        start_time_ms = int((time.time() - 3600) * 1000)
        end_time_ms = int(time.time() * 1000)
        stats_params = {
            "types": "fuelPercents",
            "vehicleId": str(truck_id),
            "startMs": start_time_ms,
            "endMs": end_time_ms
        }
        stats_data = await self.fetch_data(stats_endpoint, stats_params)
        if stats_data and "data" in stats_data and len(stats_data["data"]) > 0:
            for vehicle in stats_data["data"]:
                if int(vehicle["id"]) == int(truck_id):
                    fuel_percents = vehicle.get("fuelPercent", {})
                    if fuel_percents:
                        fuel_percent = fuel_percents.get("value", "Unknown")
                        return {"fuel_percent": fuel_percent}
                    break
        return None

    async def get_safety_score(self, truck_id):
        safety_endpoint = f"v1/fleet/vehicles/{truck_id}/safety/score"
        start_time_ms = int((time.time() - 24 * 3600) * 1000)
        end_time_ms = int(time.time() * 1000)
        stats_params = {
            "vehicleId": str(truck_id),
            "startMs": start_time_ms,
            "endMs": end_time_ms
        }
        safety_data = await self.fetch_data(safety_endpoint, stats_params)

        if safety_data:
            return safety_data
        return None

    async def get_location_stats(self, truck_id, start_time):
        location_endpoint = f"fleet/vehicles/stats/history"
        start_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        end_dt = start_dt + timedelta(seconds=2)
        end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        stats_params = {
            "vehicleIds": str(truck_id),
            "startTime": start_time,
            "endTime": end_time,
            "types": "gps"
        }
        location_data = await self.fetch_data(location_endpoint, stats_params)
        location = location_data["data"][0]["gps"][0]['reverseGeo']['formattedLocation']
        speed = location_data["data"][0]["gps"][0]['speedMilesPerHour']

        max_speed = RoadSpeedChecker(location).get_maxspeed_json()
        max_speed = json.loads(max_speed)
        if location_data:
            return {
                "location": location,
                "speed": f"{int(speed)} mph",
                "max_speed": list(max_speed.values())[0]}
        return None

    async def get_truck_details(self, truck_id):
        print(f"Fetching details for truck ID: {truck_id}")
        start_time_ms = int((time.time() - 3600) * 1000)
        end_time_ms = int(time.time() * 1000)

        location_endpoint = f"v1/fleet/vehicles/{truck_id}/locations"
        location_params = {"startMs": start_time_ms, "endMs": end_time_ms}
        location_data = await self.fetch_data(location_endpoint, location_params)
        if not location_data:
            vehicle_locations = await self.fetch_data("fleet/vehicles/locations")
            if vehicle_locations:
                vehicle_locations = vehicle_locations["data"]
                for vh_location in vehicle_locations:
                    if int(vh_location["id"]) == truck_id:
                        location_data = [{
                            "id": int(vh_location["id"]),
                            "location": vh_location["location"]["reverseGeo"]["formattedLocation"]
                        }]
                        break

        engine_stats = await self.get_engine_stats(truck_id)
        fuel_percent = await self.get_fuel_percent(truck_id)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)

        start_time_rfc3339 = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_rfc3339 = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        trips_endpoint = f"fleet/routes"

        trips_params = {
            "startTime": start_time_rfc3339,
            "endTime": end_time_rfc3339,
        }
        trips_data = await self.fetch_data(trips_endpoint, trips_params)
        print(trips_data)
        vehicle_endpoint = f"/fleet/vehicles/{truck_id}"
        vehicle_data = await self.fetch_data(vehicle_endpoint)

        if not location_data or len(location_data) == 0:
            return None

        truck_location = location_data[-1]
        current_lat = truck_location.get('latitude', 0.0)
        current_lon = truck_location.get('longitude', 0.0)
        speed = truck_location.get('speedMilesPerHour', 0)
        time_str = truck_location.get('timeMs', '')

        if isinstance(time_str, str):
            try:
                time_obj = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                time_obj = pytz.utc.localize(time_obj)
                est_timezone = pytz.timezone("America/New_York")
                time_obj = time_obj.astimezone(est_timezone)
            except ValueError:
                time_obj = None
        elif isinstance(time_str, int):
            time_obj = datetime.fromtimestamp(time_str / 1000, tz=pytz.utc)
            est_timezone = pytz.timezone("America/New_York")
            time_obj = time_obj.astimezone(est_timezone)
        else:
            time_obj = None

        details = {
            "truck_id": truck_id,
            "unit_name": vehicle_data['data'].get('name', 'Unknown'),
            "driver_name": vehicle_data['data'].get('staticAssignedDriver', {}).get('name', 'Unknown'),
            "fuel_percent": fuel_percent.get('fuel_percent', 'Unknown'),
            "coordinates": f"{current_lat}, {current_lon}",
            "speed": int(speed),
            "engine_state": engine_stats.get('engine_state', 'Unknown'),
            "time": time_obj.isoformat() if time_obj else '',
            "location": truck_location.get('location', 'Unknown')
        }

        details["route"] = "No active trip found"
        details["remaining_distance"] = "Unknown"
        details["eta"] = "No active trip"

        return details


async def run():
    api = SamsaraClient(api_token="samsara_api_iQ9uNP0KqJfP3oEx1yI9LMBZFKign6")
    details = await api.get_location_stats("281474992397558", "2025-03-24T09:02:05.987Z")
    print(details)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
