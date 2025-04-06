import json
from difflib import get_close_matches

import requests


class RoadSpeedChecker:
    def __init__(self, target_road_name):
        self.target_road_name = target_road_name
        self.lat = None
        self.lon = None
        self.location = None
        self.road_info = {}

    def get_coordinates(self):
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": self.target_road_name,
            "format": "json",
            "limit": 1
        }
        response = requests.get(nominatim_url, params=params, headers={"User-Agent": "RoadSpeedCheckerApp"})
        data = response.json()
        if data:
            self.lat = float(data[0]["lat"])
            self.lon = float(data[0]["lon"])
            self.location = data[0].get("display_name", "")
            return True
        return False

    def fetch_road_data(self):
        query = f"""
        [out:json][timeout:25];
        way["name"](around:10000, {self.lat}, {self.lon});
        out tags;
        """
        overpass_url = "http://overpass-api.de/api/interpreter"
        response = requests.post(overpass_url, data=query)
        data = response.json()

        for element in data.get("elements", []):
            name = element["tags"].get("name")
            if name:
                self.road_info[name] = {
                    "maxspeed": element["tags"].get("maxspeed", None)
                }

    def find_similar_maxspeeds(self):
        all_names = list(self.road_info.keys())
        similar = get_close_matches(self.target_road_name, all_names, n=10, cutoff=0.4)
        results = {}

        for name in similar:
            maxspeed = self.road_info[name]["maxspeed"]
            if maxspeed:
                results[name] = maxspeed

        return results

    def get_maxspeed_json(self):
        if not self.get_coordinates():
            return json.dumps({"error": f"Yo‘l '{self.target_road_name}' bo‘yicha koordinata topilmadi."})

        self.fetch_road_data()
        results = self.find_similar_maxspeeds()

        if not results:
            return json.dumps(
                {"message": f"'{self.target_road_name}' ga o‘xshash yo‘l topilmadi yoki maksimal tezlik yo‘q."})

        return json.dumps(results, indent=4)


if __name__ == "__main__":
    checker = RoadSpeedChecker("Gerald R. Ford Memorial Highway")
