# fetchers.py

import os
import requests
import feedparser
from urllib.parse import quote_plus
from typing import Optional, Tuple

from config import URL_WEATHER, WEATHER_API_KEY

def fetch_weather(location: str) -> Tuple[str, str, str]:
    url_call = f"{URL_WEATHER}?key={WEATHER_API_KEY}&q={location}&aqi=no"
    resp = requests.get(url_call, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        city = data['location']['name']
        cond = data['current']['condition']['text'].lower()
        desc = {
            "sunny": "bright and sunny",
            "cloudy": "a bit cloudy",
            "rainy": "a little rainy",
            "clear": "clear and beautiful",
            "snowy": "a winter wonderland"
        }.get(cond, cond)
        return desc, city, data['location']['region']
    return "unknown weather", "", ""

def fetch_news_rss(city: str) -> str:
    url = f"https://news.google.com/rss/search?q={quote_plus(city)}+news&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    return feed.entries[0].title if feed.entries else f"No trending news in {city}."

def geocode(location: str) -> Optional[Tuple[float, float]]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": location, "format": "json", "limit": 1}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        return None

PREDICTHQ_TOKEN = os.getenv("PREDICTHQ_TOKEN", "")

def fetch_predicthq_event(location: str, radius_km: int = 25) -> dict:
    coords = geocode(location)
    if not coords:
        return {"valid": False}
    lat, lon = coords
    url = "https://api.predicthq.com/v1/events/"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {PREDICTHQ_TOKEN}"}
    params = {"within": f"{radius_km}km@{lat},{lon}", "active": "true", "limit": 1}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        ev = resp.json().get("results", [])[0]
        return {
            "valid": True,
            "artist": ev.get("title", ""),
            "venue": ev.get("venue", {}).get("label", ""),
            "city": location.split(",")[0],
            "date": ev.get("start", ""),
            "event": ev.get("title", "")
        }
    except:
        return {"valid": False}
