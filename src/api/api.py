import asyncio
import json
import math
import time
from datetime import datetime, timedelta

import aiohttp


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

    async def get_hursh_events(self, truck_id):
        safety_endpoint = f"v1/fleet/vehicles/{truck_id}/safety/harsh_event"

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

    async def get_truck_details(self, truck_id):
        start_time_ms = int((time.time() - 3600) * 1000)
        end_time_ms = int(time.time() * 1000)
        location_endpoint = f"v1/fleet/vehicles/{truck_id}/locations"
        location_params = {"startMs": start_time_ms, "endMs": end_time_ms}
        location_data = await self.fetch_data(location_endpoint, location_params)
        engine_stats = await self.get_engine_stats(truck_id)
        fuel_percent = await self.get_fuel_percent(truck_id)

        trips_endpoint = "v1/fleet/trips"
        trips_params = {
            "startMs": int((time.time() - 24 * 3600) * 1000),
            "endMs": end_time_ms,
            "vehicleId": str(truck_id)
        }
        trips_data = await self.fetch_data(trips_endpoint, trips_params)
        vehicle_endpoint = f"/fleet/vehicles/{truck_id}"
        vehicle_data = await self.fetch_data(vehicle_endpoint)

        if location_data and len(location_data) > 0:
            truck_location = location_data[-1]
            current_lat = truck_location.get('latitude', 0.0)
            current_lon = truck_location.get('longitude', 0.0)
            speed = truck_location.get('speedMilesPerHour', 0) * 1.60934
            time_str = truck_location.get('timeMs', '')
            if isinstance(time_str, str):
                try:
                    time_obj = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                except ValueError:
                    time_obj = None
            elif isinstance(time_str, int):
                time_obj = datetime.fromtimestamp(time_str / 1000)
            else:
                time_obj = None

            details = {
                "truck_id": truck_id,
                "unit_name": vehicle_data['data'].get('name', 'Unknown'),
                "driver_name": vehicle_data['data'].get('staticAssignedDriver', {}).get('name', 'Unknown'),
                "fuel_percent": fuel_percent.get('fuel_percent', 'Unknown'),
                "coordinates": f"{current_lat}, {current_lon}",
                "speed": speed,
                "engine_state": engine_stats.get('engine_state', 'Unknown'),
                "time": time_obj.isoformat() if time_obj else '',
                "location": truck_location.get('location', 'Unknown')
            }

            if trips_data and "trips" in trips_data and len(trips_data["trips"]) > 0:
                latest_trip = trips_data["trips"][-1]

                start_location = latest_trip.get('startLocation', 'Unknown Start')
                end_location = latest_trip.get('endLocation', 'Unknown End')
                details["route"] = f"From {start_location} to {end_location}"

                end_coords = latest_trip.get('endCoordinates', {})
                end_lat = end_coords.get('latitude', None)
                end_lon = end_coords.get('longitude', None)
                if end_lat and end_lon:
                    def haversine_distance(lat1, lon1, lat2, lon2):
                        R = 6371
                        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
                        dlat = lat2 - lat1
                        dlon = lon2 - lon1
                        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
                        c = 2 * math.asin(math.sqrt(a))
                        return R * c

                    destination_distance = haversine_distance(current_lat, current_lon, end_lat, end_lon)
                    details["remaining_distance"] = round(destination_distance, 2)

                    if details["speed"] > 0:
                        hours_to_destination = destination_distance / details["speed"]
                        arrival_time = datetime.now() + timedelta(hours=hours_to_destination)
                        details["eta"] = arrival_time.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        details["eta"] = "Truck is not moving"
                else:
                    details["remaining_distance"] = "Unknown (no end coordinates)"
                    details["eta"] = "Cannot calculate (no end coordinates)"
            else:
                details["route"] = "No active trip found"
                details["remaining_distance"] = "Unknown"
                details["eta"] = "No active trip"

            return details
        return None

    async def run(self):
        trucks = await self.get_all_trucks()
        print("Number of Trucks:", len(trucks))
        print("All Trucks:", json.dumps(trucks, indent=2))

        companies = await self.get_all_companies()
        print("All Companies (Groups):", json.dumps(companies, indent=2))

        if companies and len(companies) > 0:
            company_id = companies[0].get("id")
            company_trucks = await self.get_company_trucks(company_id)
            print(f"Trucks of Company {company_id}:", json.dumps(company_trucks, indent=2))

        if trucks and len(trucks) > 0:
            for truck in trucks:
                truck_id = truck.get("id")
                safety_score = await self.get_safety_score(truck_id)
                print(f"Truck {truck_id} Safety Score:", json.dumps(safety_score, indent=2))
                crush = await self.get_hursh_events(truck_id)
                print(f"Truck {truck_id} Hursh:", json.dumps(crush, indent=2))
                truck_details = await self.get_truck_details(truck_id)
                if truck_details and truck_details.get("engine_state") == 'Running':
                    print(f"Truck {truck_id} Details:", json.dumps(truck_details, indent=2))
        else:
            print("No trucks found to get details.")


async def main():
    api_token = "dafsdf "

    client = SamsaraClient(api_token)
    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        print(f"Runtime error: {e}")
