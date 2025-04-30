# api.py

import random
import requests
import re
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from config import URL_DEEPSEEK, HEADERS
from data import load_captions
from generator import (
    generate_baity_prompt,
    generate_opinion_prompt,
    generate_event_prompt_with_location,
)

def load_openers(filename: str, default: list[str]) -> list[str]:
    path = os.path.join(os.path.dirname(__file__), 'data', filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            return lines or default
    except Exception:
        return default

girlfriend_openers = load_openers('girlfriend_openers.txt', [
    # (you should populate data/girlfriend_openers.txt with 50+ entries)
    "Omg, did you hear", "Can't believe", "So, guess what", "Yikes,",
    "Wait, no way", "Hot take:", "No shade, but", "Okay, real talk",
    "Just read", "PSA:"
])

baity_references = load_openers('baity_references.txt', load_captions()[0])

app = FastAPI(title="Caption Generator API")

used_baity, used_opinion, used_events = set(), set(), set()

class CaptionRequest(BaseModel):
    location: str
    description: str   # e.g. "24-year-old foodie who loves jazz"

class CaptionResponse(BaseModel):
    caption: str
    caption_type: str

@app.get("/")
def root():
    return {"message": "Caption Generator API is running."}

@app.post("/generate", response_model=CaptionResponse)
def generate_caption(request: CaptionRequest):
    loc = request.location.strip()
    bio = request.description.strip()
    if not loc or not bio:
        raise HTTPException(
            status_code=400,
            detail="Both location and description are required"
        )

    style = random.choice([1, 2, 3])

    if style == 1:
        # Baity
        pool = load_captions()[0]
        subset = random.sample(pool, min(len(pool), max(5, len(pool)//3)))
        base = random.choice([b for b in subset if b not in used_baity] or subset)
        used_baity.add(base)

        dynamic = generate_baity_prompt(loc, bio)
        reference = random.choice(baity_references)
        system = (
            f"You are posting as “{bio}”. "
            f"Here’s a style example: {reference}. "
            "Write an original, cheeky 2-line caption—"
            "weave in weather or news naturally, one emoji max, no hashtags."
        )
        user_msg = dynamic
        caption_type = "baity"

    elif style == 2:
        # Opinion
        pool = load_captions()[1]
        subset = random.sample(pool, min(len(pool), max(5, len(pool)//3)))
        base = random.choice([b for b in subset if b not in used_opinion] or subset)
        used_opinion.add(base)

        dynamic = generate_opinion_prompt(base, loc)
        opener = random.choice(girlfriend_openers)
        system = (
            f"You are a witty girlfriend (“{bio}”) sharing a hot take. "
            "Start with the provided opener, mention the real news headline casually, "
            "and keep it under 2 lines with one emoji."
        )
        user_msg = f"{opener} {dynamic}"
        caption_type = "opinion"

    else:
        # Event
        pool = load_captions()[1]
        subset = random.sample(pool, min(len(pool), max(5, len(pool)//3)))
        base = random.choice([b for b in subset if b not in used_events] or subset)
        used_events.add(base)

        dynamic = generate_event_prompt_with_location(base, loc, bio)
        system = (
            f"You are a flirty gal (“{bio}”) telling friends about a real event. "
            "Name the event, city & when (today/tomorrow) in a smooth 2-line post with one emoji—no ad tone."
        )
        user_msg = dynamic
        caption_type = "event"

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg}
        ],
        "n": 1,
        "max_tokens": 60,
        "temperature": random.uniform(0.7, 0.85),
        "top_p": 0.9
    }

    try:
        resp = requests.post(URL_DEEPSEEK, json=payload, headers=HEADERS)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()

        # cleanup
        text = re.sub(r"\([^)]*\)", "", text)
        for q in ['"', "“", "”", "'"]:
            text = text.replace(q, "")
        text = re.sub(r"\s{2,}", " ", text).strip()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        text = "\n".join(lines[:2])

        return CaptionResponse(caption=text, caption_type=caption_type)

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"API Error: {e}")
