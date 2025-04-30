# generator.py

import random
import os
from datetime import date
from typing import Optional
from templates import (
    weather_caption_templates,
    news_caption_templates,
    opinion_caption_templates,
    event_caption_templates,
    fallback_event_captions
)
from fetchers import fetch_weather, fetch_news_rss, fetch_predicthq_event as fetch_event

def _relative_label(iso_dt: str) -> Optional[str]:
    if not iso_dt or len(iso_dt) < 10:
        return None
    try:
        d = date.fromisoformat(iso_dt[:10])
    except:
        return None

    today = date.today()
    delta = (d - today).days
    if delta < -2:
        return None
    if delta == -2:
        return "2 days ago"
    if delta == -1:
        return "yesterday"
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if delta < 7:
        return d.strftime("this %A")
    if delta < 14:
        return d.strftime("next %A")
    return f"{d.strftime('%B')} {d.day}"

def generate_baity_prompt(location: str, bio: str = "") -> str:
    from data import load_captions
    reference_captions, _ = load_captions()

    if not reference_captions:
        return random.choice(fallback_event_captions)

    personal = f"As a {bio}, " if bio and random.random() < 0.2 else ""
    bias = random.uniform(-5, 5)

    loc_caps = []
    path = os.path.join(os.path.dirname(__file__), "data", "location_captions.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            loc_caps = [l.strip() for l in f if l.strip()]

    choice = random.choices(
        ["weather", "news", "location", "generic"],
        weights=[15 + bias, 15 + bias, 30 + bias, 40 + bias],
        k=1
    )[0]

    if choice == "weather":
        try:
            cond, city, _ = fetch_weather(location)
            if cond and city:
                tpl = random.choice(weather_caption_templates)
                return personal + tpl.format(weather_condition=cond, city_name=city)
        except:
            pass
        choice = "reference"

    if choice == "news":
        try:
            head = fetch_news_rss(location)
            if head:
                tpl = random.choice(news_caption_templates)
                return personal + tpl.format(news_summary=head)
        except:
            pass
        choice = "reference"

    if choice == "location" and loc_caps:
        try:
            lc = random.choice(loc_caps)
            return personal + lc.replace("{city_name}", location)
        except:
            pass
        choice = "reference"

    if choice == "generic":
        gens = [c for c in reference_captions if "{" not in c]
        if gens:
            return personal + random.choice(random.sample(gens, min(len(gens), 10)))

    cap = random.choice(random.sample(reference_captions, min(len(reference_captions), 15)))
    for ph, val in [
        ("{city_name}", location),
        ("{weather_condition}", "amazing"),
        ("{news_summary}", "the latest happenings")
    ]:
        cap = cap.replace(ph, val)
    return personal + cap

def generate_opinion_prompt(base_prompt: str, location: str) -> str:
    head = fetch_news_rss(location)
    tpl = random.choice(opinion_caption_templates)
    return tpl.format(base_prompt=base_prompt, news_summary=head)

def generate_event_prompt_with_location(
    base_prompt: str, location: str, bio: str = ""
) -> str:
    ev = fetch_event(location)
    lbl = _relative_label(ev.get("date", ""))
    if ev.get("valid") and ev.get("artist") and lbl:
        artist = ev["artist"]
        venue = ev.get("venue", "")
        city_n = ev.get("city", location.split(",")[0])
        if venue:
            tpl = random.choice(event_caption_templates)
            return tpl.format(
                base_prompt=base_prompt,
                artist=artist,
                venue=venue,
                city=city_n,
                date=lbl,
                event=ev.get("event", artist)
            )
        return f"{base_prompt}\n\n{artist} in {city_n} {lbl}"

    # fallback to baity if no event
    return generate_baity_prompt(location, bio)

