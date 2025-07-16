import os
from typing import List

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

tracks = []

def add_track(name: str):
    if name not in tracks:
        tracks.append(name)

def remove_track(name: str):
    if name in tracks:
        tracks.remove(name)

def list_tracks():
    return tracks

def search_tracks(query: str):
    return [track for track in tracks if query.lower() in track.lower()]