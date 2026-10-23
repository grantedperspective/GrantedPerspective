#!/usr/bin/env python3
"""
build.py — bakes site-data.json into index.html (between the DATA markers).

  python build.py

The editor's PUBLISH button calls this for you, so you only need to run it by
hand if you edit site-data.json directly.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.resolve()
DATA_FILE = BASE / "site-data.json"
INDEX = BASE / "index.html"

START, END = "/*DATA_START*/", "/*DATA_END*/"
_PATTERN = re.compile(re.escape(START) + r"[\s\S]*?" + re.escape(END))

HV_DESC = ("An episodic YouTube series breaking down the invisible systems inside games — "
           "matchmaking, algorithms, rendering, psychology. Every episode is written, shot, "
           "and edited solo.")
DD_DESC = ("Student news show produced in partnership with the Northwest Missourian. I handle "
           "social media production — short-form content, reels, and segment clips for KNWT's platforms.")

DEFAULT_BIO = [
    "I'm **Grant Hughes** — a broadcast production student at Northwest Missouri State University balancing technical storytelling, live sports production, and independent content creation. Expected graduation Spring 2027.",
    "At **Catvision — NWMSU Athletics**, I operate broadcast cameras for NCAA Division II football, basketball, soccer, volleyball, and baseball. I serve as the **High Wide camera for Bearcat Football**, delivering the primary field-wide program angle under live director instruction — including off-campus at Children's Mercy Soccer Stadium.",
    "I produce **Hidden Variables** segments for KNWT TV — 3-minute technical pieces translating complex gaming systems into accessible visual narratives, managed from concept through final export in Adobe Creative Suite.",
    "I also develop social media content for **Digging Deeper** to extend broadcast reach.",
    "I've taken my camera everywhere — race tracks, coastlines, airport tarmacs, and everywhere in between.",
]


def migrate(data):
    """Upgrade the old flat schema (videoFiles/hvFiles/...) to tabs + subsections."""
    d = dict(data)
    if "tabs" not in d:
        d["tabs"] = [
            {"id": "video", "label": "VIDEO", "dir": "video", "kind": "video",
             "files": d.pop("videoFiles", []),
             "subsections": [
                 {"id": "hv", "title": "HIDDEN VARIABLES", "desc": HV_DESC, "files": d.pop("hvFiles", [])},
                 {"id": "dd", "title": "DIGGING DEEPER", "desc": DD_DESC, "files": d.pop("ddFiles", [])},
             ]},
            {"id": "photo", "label": "PHOTO", "dir": "photo", "kind": "photo",
             "files": d.pop("photoFiles", []), "subsections": []},
            {"id": "broadcast", "label": "BROADCAST", "dir": "broadcast", "kind": "broadcast",
             "files": d.pop("broadcastFiles", []), "subsections": []},
        ]
    for t in d["tabs"]:
        t.setdefault("dir", t["id"])
        t.setdefault("kind", "video")
        t.setdefault("files", [])
        t.setdefault("subsections", [])
        for s in t["subsections"]:
            s.setdefault("desc", "")
            s.setdefault("files", [])
    d.setdefault("aboutBio", list(DEFAULT_BIO))
    return d


def inject(site_data, html):
    if not _PATTERN.search(html):
        raise ValueError("Could not find the /*DATA_START*/ ... /*DATA_END*/ markers in index.html")
    payload = json.dumps(site_data, indent=2, ensure_ascii=False).replace("</", "<\\/")
    # lambda => the payload is inserted literally (no backslash processing)
    return _PATTERN.sub(lambda m: START + payload + END, html, count=1)


def read_baked(html):
    """Pull the data currently baked into index.html (used if site-data.json is missing)."""
    m = _PATTERN.search(html)
    if not m:
        raise ValueError("No baked data found in index.html")
    return json.loads(m.group(0)[len(START):-len(END)])


def build():
    """Returns a list of log lines. Raises on failure."""
    log = []
    if not INDEX.exists():
        raise FileNotFoundError(f"index.html not found at {INDEX}")
    html = INDEX.read_text(encoding="utf-8")
    if DATA_FILE.exists():
        data = migrate(json.loads(DATA_FILE.read_text(encoding="utf-8")))
        log.append(f"Read {DATA_FILE.name}")
    else:
        data = migrate(read_baked(html))
        log.append(f"{DATA_FILE.name} missing — using data already in index.html")
    INDEX.write_text(inject(data, html), encoding="utf-8")
    n_entries = sum(len(t["files"]) + sum(len(s["files"]) for s in t["subsections"]) for t in data["tabs"])
    log.append(f"Baked into index.html — {len(data['tabs'])} tabs, {n_entries} entries, "
               f"{len(data.get('heroImages', []))} hero images")
    return log


if __name__ == "__main__":
    try:
        for line in build():
            print("✓", line)
        print("\n✅ BUILD COMPLETE → commit & push index.html (or use PUBLISH in the editor)")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)
