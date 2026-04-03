#!/usr/bin/env python3
"""
GrantedPerspective Site Editor (v2.0)
Run from your WebPubPortfolio folder: python editor.py
Then open http://localhost:5173

All data is saved to site-data.json (next to this script).
index.html is never modified.
"""

import json, os, sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, Response

app = Flask(__name__)
BASE = Path(__file__).parent
DATA_FILE = BASE / "site-data.json"
INDEX = BASE / "index.html"

# ── ENSURE DATA FILE EXISTS ──────────────────────────────────────────────────

def get_default_data():
    """Returns the default data structure."""
    return {
        "heroTag": "// broadcaster · content creator · photographer",
        "heroSubtitle": "NORTHWEST MISSOURI STATE UNIVERSITY · KNWT · HIDDEN VARIABLES · DIGGING DEEPER",
        "contactBlurb": "Broadcast production student seeking opportunities in media. Available for freelance video, photography, and broadcast work.",
        "contactEmail": "grantedperspective@gmail.com",
        "contactYoutube": "https://www.youtube.com/@grantedperspective",
        "contactInstagram": "https://www.instagram.com/grantedperspective/",
        "contactLinkedin": "https://www.linkedin.com/in/grant-hughes-media/",
        "skillRole": "Camera Operator · Broadcast Producer · Video Editor · Photographer",
        "skillAffil": "Catvision / NWMSU Athletics · KNWT Channel 8 · Northwest Missourian",
        "skillTools": "Adobe Creative Cloud · DaVinci Resolve · OBS Studio · NewBlue · Blackmagic Design · TriCaster",
        "skillLive": "Multi-camera directing · Live shot selection · Headset coordination · Scorebug integration · Lower thirds · Director timing",
        "skillSpec": "Sports broadcast · Short-form edit · Motion graphics · News packages",
        "resumeFile": "GrantHughesResume.pdf",
        "heroImages": [
            "./img/Image00001.JPG","./img/Image00002.JPG","./img/Image00003.JPG",
            "./img/Image00004.JPG","./img/Image00005.JPG","./img/Image00006.JPG",
            "./img/Image00007.JPG","./img/Image00008.JPG","./img/Image00009.JPG",
            "./img/Image00010.JPG","./img/Image00011.JPG","./img/Image00012.JPG",
            "./img/Image00013.JPG","./img/Image00015.JPG","./img/Image00016.JPG",
            "./img/Image00017.JPG","./img/Image00018.JPG","./img/Image00019.JPG",
            "./img/Image00020.JPG","./img/Image00021.JPG","./img/Image00022.JPG",
            "./img/Image00023.JPG","./img/Image00024.JPG","./img/Image00025.JPG"
        ],
        "videoFiles": [
            {
                "title": "SLICE OF LIFE — MINI DOC",
                "description": "Dean Snepp — Owner of three similar Mercury Cougars",
                "thumb": "https://img.youtube.com/vi/41iuG390s18/maxresdefault.jpg",
                "link": "https://youtu.be/41iuG390s18?si=sVsbDnzQieertxcy"
            },
            {
                "title": "PLAYBACK — SHORT FILM",
                "description": "12 min · First short film · School project",
                "thumb": "https://img.youtube.com/vi/LEAzeHEbfbM/maxresdefault.jpg",
                "link": "https://youtu.be/LEAzeHEbfbM?si=dvI79buYHKGQbe3b"
            }
        ],
        "hvFiles": [
            {
                "title": "HIDDEN VARIABLES EP.8",
                "description": "3D Spatial Audio & HRTF",
                "thumb": "",
                "link": "",
                "placeholder": True,
                "placeholderTitle": "[ IN PRODUCTION ]",
                "placeholderMsg": "THIS EPISODE IS CURRENTLY IN PRODUCTION.\nCHECK BACK SOON."
            },
            {
                "title": "HIDDEN VARIABLES EP.7",
                "description": "PC Components & CPU-GPU Communication",
                "thumb": "",
                "link": "",
                "placeholder": True,
                "placeholderTitle": "[ SCRAPPED ]",
                "placeholderMsg": "THIS EPISODE WAS SCRAPPED.\nEP.8 IS IN PRODUCTION."
            },
            {
                "title": "HIDDEN VARIABLES EP.6",
                "description": "The System That Keeps You Playing — MMR, Elo & EOMM",
                "thumb": "",
                "link": "",
                "placeholder": True,
                "placeholderTitle": "[ UNLISTED ]",
                "placeholderMsg": "LINK NOT YET ADDED.\nUPDATE VIA EDITOR."
            },
            {
                "title": "HIDDEN VARIABLES EP.5",
                "description": "The World Behind Your Back — Frustum Culling, Occlusion & LOD",
                "thumb": "",
                "link": "",
                "placeholder": True,
                "placeholderTitle": "[ UNLISTED ]",
                "placeholderMsg": "LINK NOT YET ADDED.\nUPDATE VIA EDITOR."
            },
            {
                "title": "HIDDEN VARIABLES EP.4",
                "description": "Why Battle Passes Feel Hard to Ignore — Goal-Gradient, Loss Aversion & Sunk Cost",
                "thumb": "https://img.youtube.com/vi/C0moU5GKMvo/maxresdefault.jpg",
                "link": "https://youtu.be/C0moU5GKMvo?si=aJQc3sJySB1CXiTO"
            },
            {
                "title": "HIDDEN VARIABLES EP.3",
                "description": "YouTube's Secret File on You — Clusters, Collaborative Filtering & Prediction",
                "thumb": "https://img.youtube.com/vi/VM68CZKuAgI/maxresdefault.jpg",
                "link": "https://youtu.be/VM68CZKuAgI?si=DkQKeXkFl7G80CFn"
            },
            {
                "title": "HIDDEN VARIABLES EP.2",
                "description": "How Speedrunners Break Games — TAS, Glitches, Routing & RNG",
                "thumb": "https://img.youtube.com/vi/nEr4Iz_sNq8/maxresdefault.jpg",
                "link": "https://youtu.be/nEr4Iz_sNq8?si=JAjzQRqd5GYCMCru"
            },
            {
                "title": "HIDDEN VARIABLES EP.1",
                "description": "Latency Isn't Just Ping — End-to-End Latency & Peeker's Advantage",
                "thumb": "",
                "link": "",
                "placeholder": True,
                "placeholderTitle": "[ ACCESS RESTRICTED ]",
                "placeholderMsg": "THIS FILE IS NOT PUBLICLY AVAILABLE.\nCONTACT FOR ACCESS."
            }
        ],
        "ddFiles": [
            {"title": "DIGGING DEEPER — REEL #1", "description": "Social media content · KNWT Instagram", "thumb": "", "link": "https://www.instagram.com/reel/DUoPzLEkYet/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="},
            {"title": "DIGGING DEEPER — REEL #2", "description": "Social media content · KNWT Instagram", "thumb": "", "link": "https://www.instagram.com/reel/DU1ZqZGDSEu/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="},
            {"title": "DIGGING DEEPER — REEL #3", "description": "Social media content · KNWT Instagram", "thumb": "", "link": "https://www.instagram.com/reel/DVJiV6uCd18/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="},
            {"title": "DIGGING DEEPER — REEL #4", "description": "Social media content · KNWT Instagram", "thumb": "", "link": "https://www.instagram.com/reel/DWY4eEahI-n/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="},
            {"title": "DIGGING DEEPER — REEL #5", "description": "Social media content · KNWT Instagram", "thumb": "", "link": "https://www.instagram.com/reel/DWgxbmpkdNS/?utm_source=ig_web_copy_link&igsh=MzRlODBiNWFlZA=="}
        ],
        "photoFiles": [
            {"title": "MOTORSPORT — TRACK & ROAD", "description": "Race cars, road cars, track days", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."},
            {"title": "MIAMI — JAN 2025", "description": "193 items · Street & travel photography", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."},
            {"title": "COASTAL VIEWS", "description": "Maritime & waterfront photography", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."},
            {"title": "PLANE SPOTTING — DEC 2025", "description": "Airport & tarmac photography", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."},
            {"title": "E&K — ENGAGEMENT SESSION", "description": "Jun 2025 · Portrait & lifestyle", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."},
            {"title": "CAR SHOW", "description": "Show floor coverage", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."},
            {"title": "COFFEE BEAN — VARIOUS", "description": "Lifestyle & product photography", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ COMING SOON ]", "placeholderMsg": "GALLERY UPLOAD IN PROGRESS.\nCHECK BACK SOON."}
        ],
        "broadcastFiles": [
            {"title": "CATVISION — BEARCAT FOOTBALL", "description": "High Wide angle · NCAA Div II · Main program angle", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ BROADCAST ARCHIVE ]", "placeholderMsg": "BROADCAST FOOTAGE IS ARCHIVED INTERNALLY.\nCONTACT FOR REEL ACCESS."},
            {"title": "CATVISION — 2025 SEASON", "description": "Football, basketball, soccer, volleyball, baseball", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ BROADCAST ARCHIVE ]", "placeholderMsg": "BROADCAST FOOTAGE IS ARCHIVED INTERNALLY.\nCONTACT FOR REEL ACCESS."},
            {"title": "NW VS PITT STATE — CMSS", "description": "Off-campus · Children's Mercy Soccer Stadium · Graphics op", "thumb": "", "link": "", "placeholder": True, "placeholderTitle": "[ BROADCAST ARCHIVE ]", "placeholderMsg": "BROADCAST FOOTAGE IS ARCHIVED INTERNALLY.\nCONTACT FOR REEL ACCESS."},
            {"title": "BEARCAT DOWNHILL 200 — PITCH", "description": "Mobile production site survey · Remote/live production concept", "thumb": "", "link": "./BeardownhillPitch.pdf", "placeholder": False, "tag": "pitch"}
        ]
    }

def init_data_file():
    """Create site-data.json if it doesn't exist."""
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps(get_default_data(), indent=2, ensure_ascii=False), encoding="utf-8")

# ── API ROUTES ────────────────────────────────────────────────────────────────

@app.route("/api/data", methods=["GET"])
def api_get():
    """Return current data from site-data.json."""
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/data", methods=["POST"])
def api_post():
    """Save updated data to site-data.json."""
    try:
        data = request.get_json(force=True)
        DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Serve site files (for preview iframe)
@app.route("/preview")
@app.route("/preview/<path:path>")
def preview(path="index.html"):
    return send_from_directory(BASE, path)

# Serve editor UI
@app.route("/")
def editor():
    return Response(EDITOR_HTML, mimetype="text/html")

# ── EDITOR UI ─────────────────────────────────────────────────────────────────

EDITOR_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GP Editor</title>
<link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=VT323&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {
    --purple:#5A00AA; --purple-dark:#360066; --purple-mid:#7b2fbe; --purple-dim:#0d0018;
    --bg:#080808; --surface:#0f0f0f; --surface2:#141414;
    --border:#1e1e1e; --border-accent:#360066;
    --text:#ddd; --text-dim:#666; --text-faint:#2a2a2a;
    --green:#39ff14; --red:#ff4444; --yellow:#ffcc00;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:var(--bg);color:var(--text);font-family:'Space Mono',monospace;display:flex;height:100vh;overflow:hidden;}

  .sidebar{width:196px;flex-shrink:0;background:#000;border-right:1px solid var(--border-accent);display:flex;flex-direction:column;}
  .logo{padding:.9rem 1rem;border-bottom:1px solid var(--border-accent);}
  .logo h1{font-family:'VT323',monospace;font-size:1.3rem;color:var(--purple);letter-spacing:2px;line-height:1;}
  .logo p{font-size:.48rem;color:var(--text-dim);letter-spacing:2px;margin-top:.2rem;}
  .nav-scroll{flex:1;overflow-y:auto;}
  .nav-group{padding:.4rem 0;border-bottom:1px solid #0d0d0d;}
  .nav-group-label{font-family:'Share Tech Mono',monospace;font-size:.44rem;letter-spacing:3px;color:#2a2a2a;text-transform:uppercase;padding:.2rem 1rem .35rem;}
  .nav-item{display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:1px;text-transform:uppercase;color:var(--text-dim);border-left:2px solid transparent;transition:all .15s;user-select:none;}
  .nav-item:hover{color:var(--text);background:#0d0d0d;}
  .nav-item.active{color:var(--purple);border-left-color:var(--purple);background:#0a0018;}
  .nav-icon{font-size:.7rem;width:14px;text-align:center;}
  .badge{margin-left:auto;background:var(--purple-dark);color:#999;font-size:.44rem;padding:1px 5px;border-radius:2px;}
  .sidebar-bottom{padding:.7rem;border-top:1px solid var(--border-accent);display:flex;flex-direction:column;gap:.4rem;}
  .btn-save{width:100%;padding:.55rem;background:var(--purple);color:#fff;border:none;cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:2px;text-transform:uppercase;transition:background .2s;}
  .btn-save:hover{background:var(--purple-mid);}
  .btn-save:disabled{background:#222;color:#555;cursor:not-allowed;}
  .status-line{font-size:.48rem;text-align:center;color:var(--text-dim);letter-spacing:1px;min-height:12px;font-family:'Share Tech Mono',monospace;}
  .status-line.ok{color:var(--green);}.status-line.err{color:var(--red);}.status-line.saving{color:var(--yellow);}

  .main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;}
  .topbar{background:#000;border-bottom:1px solid var(--border);padding:.55rem 1.1rem;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
  .topbar-left{display:flex;align-items:baseline;gap:.7rem;}
  .topbar-title{font-family:'VT323',monospace;font-size:1.2rem;color:#fff;letter-spacing:2px;}
  .topbar-desc{font-size:.52rem;color:var(--text-dim);letter-spacing:1px;font-family:'Share Tech Mono',monospace;}
  .btn-add{display:flex;align-items:center;gap:.35rem;padding:.38rem .8rem;background:var(--purple-dim);border:1px solid var(--purple-dark);color:var(--purple);font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:all .15s;}
  .btn-add:hover{background:var(--purple-dark);color:#fff;}

  .scroll{flex:1;overflow-y:auto;padding:.9rem 1.1rem 3rem;}
  .panel{display:none;}.panel.active{display:block;}

  .card-list{display:flex;flex-direction:column;gap:.35rem;}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:3px;overflow:hidden;transition:border-color .15s;}
  .card.drag-over{border-color:var(--purple)!important;}.card.dragging{opacity:.35;}
  .card-head{display:flex;align-items:center;gap:.55rem;padding:.55rem .7rem;cursor:pointer;transition:background .15s;user-select:none;}
  .card-head:hover{background:var(--surface2);}
  .drag-handle{color:#2a2a2a;cursor:grab;font-size:.85rem;flex-shrink:0;padding:0 2px;transition:color .15s;}
  .card-head:hover .drag-handle{color:#555;}
  .drag-handle:active{cursor:grabbing;}
  .dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
  .dot-live{background:var(--green);box-shadow:0 0 4px var(--green);}.dot-unlisted{background:var(--yellow);}.dot-placeholder{background:#555;}
  .dot-restricted{background:var(--red);}.dot-production{background:#ff8800;}.dot-scrapped{background:#333;}
  .card-title{font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--purple);letter-spacing:1px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .card-sub{font-size:.48rem;color:var(--text-dim);letter-spacing:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;}
  .toggle{color:var(--text-faint);font-size:.65rem;flex-shrink:0;transition:transform .15s;}
  .card.open .toggle{transform:rotate(90deg);}
  .btn-del{background:none;border:none;color:#1a0000;cursor:pointer;font-size:.8rem;flex-shrink:0;transition:color .15s;padding:0 2px;}
  .btn-del:hover{color:var(--red);}
  .card-body{display:none;padding:.7rem;border-top:1px solid var(--border);background:#080808;}
  .card.open .card-body{display:block;}

  .frow{display:grid;grid-template-columns:1fr 1fr;gap:.55rem;margin-bottom:.55rem;}
  .frow.full{grid-template-columns:1fr;}
  .f{display:flex;flex-direction:column;gap:.22rem;}
  .f label{font-family:'Share Tech Mono',monospace;font-size:.48rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase;}
  .f input,.f textarea,.f select{background:#050505;border:1px solid var(--border);color:var(--text);font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:.38rem .45rem;outline:none;transition:border-color .15s;border-radius:2px;width:100%;}
  .f input:focus,.f textarea:focus,.f select:focus{border-color:var(--purple);}
  .f textarea{min-height:48px;resize:vertical;}
  .f select{cursor:pointer;}.f select option{background:#050505;}
  .checkrow{display:flex;align-items:center;gap:.45rem;margin-bottom:.55rem;}
  .checkrow input[type=checkbox]{accent-color:var(--purple);width:13px;height:13px;cursor:pointer;flex-shrink:0;}
  .checkrow label{font-family:'Share Tech Mono',monospace;font-size:.52rem;color:var(--text-dim);letter-spacing:1px;cursor:pointer;}
  .ph-fields{border-left:2px solid var(--purple-dark);padding-left:.7rem;margin-top:.45rem;display:none;}
  .ph-fields.on{display:block;}
  .thumb-row{display:flex;gap:.5rem;align-items:flex-start;margin-top:.45rem;}
  .thumb-box{width:80px;height:45px;background:#111;border:1px solid var(--border);border-radius:2px;overflow:hidden;flex-shrink:0;}
  .thumb-box img{width:100%;height:100%;object-fit:cover;display:block;}
  .thumb-none{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:'Share Tech Mono',monospace;font-size:.4rem;color:#2a2a2a;}

  .img-list{display:flex;flex-direction:column;gap:.3rem;}
  .img-row{display:flex;align-items:center;gap:.45rem;background:var(--surface);border:1px solid var(--border);padding:.32rem .5rem;border-radius:2px;}
  .img-thumb{width:44px;height:33px;object-fit:cover;border-radius:2px;background:#111;flex-shrink:0;border:1px solid var(--border);}
  .img-row input{flex:1;background:transparent;border:none;color:var(--text);font-family:'Share Tech Mono',monospace;font-size:.6rem;outline:none;min-width:0;}
  .img-row input::placeholder{color:#2a2a2a;}

  .fc{background:var(--surface);border:1px solid var(--border);border-radius:3px;padding:.9rem;margin-bottom:.7rem;}
  .fc-title{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:3px;color:var(--purple);text-transform:uppercase;margin-bottom:.7rem;padding-bottom:.35rem;border-bottom:1px solid var(--border-accent);}
  .fc .f{margin-bottom:.55rem;}.fc .f:last-child{margin-bottom:0;}

  .preview{width:360px;flex-shrink:0;border-left:1px solid var(--border-accent);display:flex;flex-direction:column;background:#000;}
  .pbar{border-bottom:1px solid var(--border);padding:.5rem .7rem;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
  .pbar-label{font-family:'Share Tech Mono',monospace;font-size:.52rem;color:var(--text-dim);letter-spacing:2px;}
  .pnav{display:flex;gap:.3rem;}
  .pnav-btn{font-family:'Share Tech Mono',monospace;font-size:.48rem;letter-spacing:1px;padding:.22rem .45rem;background:none;border:1px solid var(--border);color:var(--text-dim);cursor:pointer;text-transform:uppercase;transition:all .15s;}
  .pnav-btn:hover,.pnav-btn.active{border-color:var(--purple);color:var(--purple);background:var(--purple-dim);}
  .pframe-wrap{flex:1;overflow:hidden;position:relative;}
  .pframe{width:1280px;height:800px;border:none;transform-origin:top left;transform:scale(0.28125);pointer-events:none;}
  .btn-refresh{position:absolute;bottom:.6rem;right:.6rem;font-family:'Share Tech Mono',monospace;font-size:.48rem;letter-spacing:1px;padding:.28rem .55rem;background:rgba(0,0,0,.85);border:1px solid var(--border-accent);color:var(--purple);cursor:pointer;text-transform:uppercase;transition:all .15s;}
  .btn-refresh:hover{background:var(--purple-dark);color:#fff;}

  .empty{padding:1.5rem;text-align:center;font-family:'Share Tech Mono',monospace;font-size:.58rem;color:#222;border:1px dashed var(--border);border-radius:3px;}

  ::-webkit-scrollbar{width:3px;} ::-webkit-scrollbar-track{background:#000;} ::-webkit-scrollbar-thumb{background:var(--purple-dark);}
</style>
</head>
<body>

<div class="sidebar">
  <div class="logo">
    <h1>GP EDITOR</h1>
    <p>SITE MANAGER v2.0</p>
  </div>
  <div class="nav-scroll">
    <div class="nav-group">
      <p class="nav-group-label">Home</p>
      <div class="nav-item active" onclick="show('hero')" data-p="hero"><span class="nav-icon">⊞</span>Hero Images<span class="badge" id="b-hero">0</span></div>
    </div>
    <div class="nav-group">
      <p class="nav-group-label">Video Tab</p>
      <div class="nav-item" onclick="show('video')" data-p="video"><span class="nav-icon">▶</span>Video<span class="badge" id="b-video">0</span></div>
      <div class="nav-item" onclick="show('hv')" data-p="hv"><span class="nav-icon">◈</span>Hidden Variables<span class="badge" id="b-hv">0</span></div>
      <div class="nav-item" onclick="show('dd')" data-p="dd"><span class="nav-icon">◉</span>Digging Deeper<span class="badge" id="b-dd">0</span></div>
    </div>
    <div class="nav-group">
      <p class="nav-group-label">Other Tabs</p>
      <div class="nav-item" onclick="show('photo')" data-p="photo"><span class="nav-icon">◻</span>Photo<span class="badge" id="b-photo">0</span></div>
      <div class="nav-item" onclick="show('broadcast')" data-p="broadcast"><span class="nav-icon">◎</span>Broadcast<span class="badge" id="b-broadcast">0</span></div>
    </div>
    <div class="nav-group">
      <p class="nav-group-label">Site</p>
      <div class="nav-item" onclick="show('about')" data-p="about"><span class="nav-icon">▣</span>About</div>
      <div class="nav-item" onclick="show('contact')" data-p="contact"><span class="nav-icon">◆</span>Contact</div>
    </div>
  </div>
  <div class="sidebar-bottom">
    <button class="btn-save" id="btn-save" onclick="saveData()">[ SAVE ]</button>
    <p class="status-line" id="status"></p>
  </div>
</div>

<div class="main">
  <div class="topbar">
    <div class="topbar-left">
      <span class="topbar-title" id="t-title">HERO IMAGES</span>
      <span class="topbar-desc" id="t-desc">Images that cycle through the CRT TV grid</span>
    </div>
    <button class="btn-add" id="btn-add" onclick="addItem()">+ ADD IMAGE</button>
  </div>
  <div class="scroll">
    <div class="panel active" id="panel-hero"><div class="img-list" id="list-hero"></div></div>
    <div class="panel" id="panel-video"><div class="card-list" id="list-video"></div></div>
    <div class="panel" id="panel-hv"><div class="card-list" id="list-hv"></div></div>
    <div class="panel" id="panel-dd"><div class="card-list" id="list-dd"></div></div>
    <div class="panel" id="panel-photo"><div class="card-list" id="list-photo"></div></div>
    <div class="panel" id="panel-broadcast"><div class="card-list" id="list-broadcast"></div></div>
    <div class="panel" id="panel-about">
      <div class="fc">
        <p class="fc-title">Hero</p>
        <div class="f"><label>Tag Line</label><input id="h-tag" type="text"></div>
        <div class="f"><label>Subtitle</label><input id="h-sub" type="text"></div>
        <div class="f"><label>Resume Filename</label><input id="h-resume" type="text" placeholder="GrantHughesResume.pdf"></div>
      </div>
      <div class="fc">
        <p class="fc-title">Skills</p>
        <div class="f"><label>Role</label><input id="s-role" type="text"></div>
        <div class="f"><label>Affiliation</label><input id="s-affil" type="text"></div>
        <div class="f"><label>Software</label><input id="s-tools" type="text"></div>
        <div class="f"><label>Live Production</label><input id="s-live" type="text"></div>
        <div class="f"><label>Specialties</label><input id="s-spec" type="text"></div>
      </div>
    </div>
    <div class="panel" id="panel-contact">
      <div class="fc">
        <p class="fc-title">Links</p>
        <div class="f"><label>Email</label><input id="c-email" type="text"></div>
        <div class="f"><label>YouTube URL</label><input id="c-yt" type="text"></div>
        <div class="f"><label>Instagram URL</label><input id="c-ig" type="text"></div>
        <div class="f"><label>LinkedIn URL</label><input id="c-li" type="text"></div>
      </div>
      <div class="fc">
        <p class="fc-title">Copy</p>
        <div class="f"><label>Contact Blurb</label><textarea id="c-blurb" rows="3"></textarea></div>
      </div>
    </div>
  </div>
</div>

<div class="preview">
  <div class="pbar">
    <span class="pbar-label">// LIVE PREVIEW</span>
    <div class="pnav">
      <button class="pnav-btn active" onclick="pNav('home',this)">HOME</button>
      <button class="pnav-btn" onclick="pNav('about',this)">ABOUT</button>
      <button class="pnav-btn" onclick="pNav('projects',this)">PROJ</button>
      <button class="pnav-btn" onclick="pNav('contact',this)">CONT</button>
    </div>
  </div>
  <div class="pframe-wrap">
    <iframe class="pframe" id="pframe" src="/preview/index.html"></iframe>
    <button class="btn-refresh" onclick="refreshPreview()">↺ REFRESH</button>
  </div>
</div>

<script>
const PANELS = {
  hero:{title:'HERO IMAGES',desc:'Images that cycle in the CRT TV grid',add:'ADD IMAGE'},
  video:{title:'VIDEO',desc:'General video — docs, short films, misc',add:'ADD VIDEO'},
  hv:{title:'HIDDEN VARIABLES',desc:'Episodes — most recent first',add:'ADD EPISODE'},
  dd:{title:'DIGGING DEEPER',desc:'Social reels and clips',add:'ADD REEL'},
  photo:{title:'PHOTO',desc:'Photo galleries and collections',add:'ADD GALLERY'},
  broadcast:{title:'BROADCAST',desc:'Broadcast work, pitches, archived productions',add:'ADD ENTRY'},
  about:{title:'ABOUT',desc:'Bio copy and skill fields',add:null},
  contact:{title:'CONTACT',desc:'Contact links and copy',add:null},
};
const FILE_KEYS = {video:'videoFiles',hv:'hvFiles',dd:'ddFiles',photo:'photoFiles',broadcast:'broadcastFiles'};
let state = {};
let cur = 'hero';

async function loadData(){
  try{
    const r = await fetch('/api/data');
    state = await r.json();
    if(state.error){setStatus('ERROR: '+state.error,'err');return;}
    renderAll();
    setStatus('LOADED','ok');
    setTimeout(()=>setStatus('',''),2500);
  }catch(e){setStatus('LOAD FAILED','err');}
}

async function saveData(){
  collectFields();
  const btn = document.getElementById('btn-save');
  btn.disabled = true;
  setStatus('SAVING...','saving');
  try{
    const r = await fetch('/api/data',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(state)});
    const j = await r.json();
    if(j.ok){setStatus('SAVED ✓','ok');refreshPreview();}
    else setStatus('ERROR: '+j.error,'err');
  }catch(e){setStatus('SAVE FAILED','err');}
  btn.disabled = false;
  setTimeout(()=>setStatus('',''),3000);
}

function setStatus(msg,cls=''){
  const el = document.getElementById('status');
  el.textContent = msg;el.className = 'status-line '+(cls||'');
}

function show(id){
  cur = id;
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  document.getElementById('panel-'+id).classList.add('active');
  document.querySelector('.nav-item[data-p="'+id+'"]')?.classList.add('active');
  const m = PANELS[id];
  document.getElementById('t-title').textContent = m.title;
  document.getElementById('t-desc').textContent = m.desc;
  const ab = document.getElementById('btn-add');
  if(m.add){ab.style.display='flex';ab.textContent='+ '+m.add;}
  else ab.style.display='none';
  if(id==='about') fillAboutFields();
  if(id==='contact') fillContactFields();
}

function renderAll(){
  renderHero();
  Object.keys(FILE_KEYS).forEach(s=>renderFiles(s));
  updateBadges();
}

function updateBadges(){
  document.getElementById('b-hero').textContent = (state.heroImages||[]).length;
  Object.entries(FILE_KEYS).forEach(([s,k])=>{
    document.getElementById('b-'+s).textContent = (state[k]||[]).length;
  });
}

function renderHero(){
  const list = document.getElementById('list-hero');
  list.innerHTML='';
  const imgs = state.heroImages||[];
  if(!imgs.length){list.innerHTML='<div class="empty">NO IMAGES YET.</div>';return;}
  imgs.forEach((src,i)=>{
    const row = document.createElement('div');
    row.className='img-row';row.draggable=true;row.dataset.i=i;
    row.innerHTML=`
      <span class="drag-handle">⠿</span>
      <img class="img-thumb" src="${src}" onerror="this.style.opacity='.15'">
      <input type="text" value="${escH(src)}" placeholder="./img/filename.jpg"
        oninput="state.heroImages[${i}]=this.value;this.closest('.img-row').querySelector('img').src=this.value;updateBadges();">
      <button class="btn-del" onclick="delHero(${i})">✕</button>`;
    addDrag(row,'hero');
    list.appendChild(row);
  });
}

function delHero(i){state.heroImages.splice(i,1);renderHero();updateBadges();}

function dotClass(file){
  if(!file.placeholder && file.link) return 'dot-live';
  const t=(file.placeholderTitle||'').toLowerCase();
  if(t.includes('scrapped')) return 'dot-scrapped';
  if(t.includes('production')) return 'dot-production';
  if(t.includes('restricted')) return 'dot-restricted';
  if(t.includes('unlisted')) return 'dot-unlisted';
  return 'dot-placeholder';
}

function renderFiles(section){
  const key = FILE_KEYS[section];
  const files = state[key]||[];
  const list = document.getElementById('list-'+section);
  list.innerHTML='';
  if(!files.length){list.innerHTML='<div class="empty">NO ENTRIES YET.</div>';return;}
  files.forEach((file,i)=>{
    const card = document.createElement('div');
    card.className='card';card.draggable=true;card.dataset.i=i;
    const ph = file.placeholder===true;
    card.innerHTML=`
      <div class="card-head" onclick="toggleCard(this.parentElement)">
        <span class="drag-handle">⠿</span>
        <span class="dot ${dotClass(file)}"></span>
        <span class="card-title">${escH(file.title||'UNTITLED')}</span>
        <span class="card-sub">${escH(file.description||'')}</span>
        <span class="toggle">›</span>
        <button class="btn-del" onclick="event.stopPropagation();delFile('${section}',${i})">✕</button>
      </div>
      <div class="card-body">
        <div class="frow">
          <div class="f"><label>Title</label><input type="text" value="${escH(file.title||'')}" onchange="state.${key}[${i}].title=this.value;refreshCardHead(this)"></div>
          <div class="f"><label>Description</label><input type="text" value="${escH(file.description||'')}" onchange="state.${key}[${i}].description=this.value;refreshCardHead(this)"></div>
        </div>
        <div class="frow">
          <div class="f"><label>Link URL</label><input type="text" value="${escH(file.link||'')}" onchange="state.${key}[${i}].link=this.value"></div>
          <div class="f"><label>Thumbnail URL</label><input type="text" id="thumb-${section}-${i}" value="${escH(file.thumb||'')}" oninput="state.${key}[${i}].thumb=this.value;updateThumbPreview(this,'${section}',${i})"></div>
        </div>
        <div class="thumb-row">
          <div class="thumb-box" id="thumbbox-${section}-${i}">
            ${file.thumb ? `<img src="${escH(file.thumb)}" onerror="this.style.opacity='.1'">` : '<div class="thumb-none">NO THUMB</div>'}
          </div>
          <div class="f" style="flex:1;">
            <label>YouTube ID shortcut</label>
            <input type="text" placeholder="e.g. C0moU5GKMvo" oninput="applyYTId(this,'${section}',${i})">
          </div>
        </div>
        <div class="checkrow">
          <input type="checkbox" id="ph-${section}-${i}" ${ph?'checked':''} onchange="state.${key}[${i}].placeholder=this.checked;togglePH(this,'${section}',${i})">
          <label for="ph-${section}-${i}">Placeholder (no live link)</label>
        </div>
        <div class="ph-fields ${ph?'on':''}" id="phf-${section}-${i}">
          <div class="frow">
            <div class="f"><label>Overlay Title</label><input type="text" value="${escH(file.placeholderTitle||'')}" onchange="state.${key}[${i}].placeholderTitle=this.value"></div>
            <div class="f"><label>Overlay Message</label><input type="text" value="${escH(file.placeholderMsg||'')}" onchange="state.${key}[${i}].placeholderMsg=this.value"></div>
          </div>
        </div>
      </div>`;
    addDrag(card,section);
    list.appendChild(card);
  });
}

function toggleCard(card){card.classList.toggle('open');}
function togglePH(cb,section,i){document.getElementById('phf-'+section+'-'+i).classList.toggle('on',cb.checked);}
function refreshCardHead(input){
  const card = input.closest('.card');
  const titleEl = card.querySelector('.card-title');
  const descEl = card.querySelector('.card-sub');
  const label = input.closest('.f').querySelector('label').textContent;
  if(label==='Title') titleEl.textContent = input.value||'UNTITLED';
  if(label==='Description') descEl.textContent = input.value;
}
function updateThumbPreview(input,section,i){
  const box = document.getElementById('thumbbox-'+section+'-'+i);
  if(input.value){
    box.innerHTML=`<img src="${escH(input.value)}" onerror="this.style.opacity='.1'">`;
  }else{
    box.innerHTML='<div class="thumb-none">NO THUMB</div>';
  }
}
function applyYTId(input,section,i){
  const id = input.value.trim();
  if(!id) return;
  const key = FILE_KEYS[section];
  const thumb = `https://img.youtube.com/vi/${id}/maxresdefault.jpg`;
  const link = `https://youtu.be/${id}`;
  state[key][i].thumb = thumb;
  state[key][i].link = link;
  const card = input.closest('.card');
  card.querySelector('input[onchange*=".link="]').value = link;
  const thumbInput = document.getElementById('thumb-'+section+'-'+i);
  if(thumbInput){thumbInput.value = thumb;updateThumbPreview(thumbInput,section,i);}
}

function delFile(section,i){state[FILE_KEYS[section]].splice(i,1);renderFiles(section);updateBadges();}

function fillAboutFields(){
  const map = {'s-role':'skillRole','s-affil':'skillAffil','s-tools':'skillTools','s-live':'skillLive','s-spec':'skillSpec','h-tag':'heroTag','h-sub':'heroSubtitle','h-resume':'resumeFile'};
  Object.entries(map).forEach(([id,key])=>{const el=document.getElementById(id);if(el) el.value=state[key]||'';});
}
function fillContactFields(){
  const map = {'c-email':'contactEmail','c-yt':'contactYoutube','c-ig':'contactInstagram','c-li':'contactLinkedin','c-blurb':'contactBlurb'};
  Object.entries(map).forEach(([id,key])=>{const el=document.getElementById(id);if(el) el.value=state[key]||'';});
}
function collectFields(){
  const amap = {'s-role':'skillRole','s-affil':'skillAffil','s-tools':'skillTools','s-live':'skillLive','s-spec':'skillSpec','h-tag':'heroTag','h-sub':'heroSubtitle','h-resume':'resumeFile'};
  Object.entries(amap).forEach(([id,key])=>{const el=document.getElementById(id);if(el&&el.value!=='') state[key]=el.value;});
  const cmap = {'c-email':'contactEmail','c-yt':'contactYoutube','c-ig':'contactInstagram','c-li':'contactLinkedin','c-blurb':'contactBlurb'};
  Object.entries(cmap).forEach(([id,key])=>{const el=document.getElementById(id);if(el&&el.value!=='') state[key]=el.value;});
}

function addItem(){
  if(cur==='hero'){state.heroImages.push('./img/new-image.jpg');renderHero();updateBadges();return;}
  if(FILE_KEYS[cur]){
    const key = FILE_KEYS[cur];
    state[key].unshift({title:'NEW ENTRY',description:'',thumb:'',link:'',placeholder:true,placeholderTitle:'[ COMING SOON ]',placeholderMsg:'CONTENT COMING SOON.'});
    renderFiles(cur);updateBadges();
    const first = document.querySelector('#list-'+cur+' .card');
    if(first) first.classList.add('open');
  }
}

let dragSrc=null, dragSection=null;
function addDrag(el,section){
  el.addEventListener('dragstart',e=>{dragSrc=el;dragSection=section;el.classList.add('dragging');e.dataTransfer.effectAllowed='move';});
  el.addEventListener('dragend',()=>el.classList.remove('dragging'));
  el.addEventListener('dragover',e=>{e.preventDefault();el.classList.add('drag-over');});
  el.addEventListener('dragleave',()=>el.classList.remove('drag-over'));
  el.addEventListener('drop',e=>{
    e.preventDefault();el.classList.remove('drag-over');
    if(!dragSrc||dragSrc===el||dragSection!==section) return;
    const fromI = parseInt(dragSrc.dataset.i);
    const toI   = parseInt(el.dataset.i);
    if(isNaN(fromI)||isNaN(toI)) return;
    if(section==='hero'){
      const arr=state.heroImages;const [item]=arr.splice(fromI,1);arr.splice(toI,0,item);
      renderHero();
    }else{
      const arr=state[FILE_KEYS[section]];const [item]=arr.splice(fromI,1);arr.splice(toI,0,item);
      renderFiles(section);updateBadges();
    }
  });
}

function pNav(page,btn){
  document.querySelectorAll('.pnav-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  const frame = document.getElementById('pframe');
  try{frame.contentWindow.navigateTo(page);}catch(e){frame.src='/preview/index.html';}
}
function refreshPreview(){
  const f = document.getElementById('pframe');
  f.src = f.src;
}

function escH(s){return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

loadData();
</script>
</body>
</html>
"""

# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not INDEX.exists():
        print(f"ERROR: index.html not found at {INDEX}")
        print(f"Run this script from your WebPubPortfolio folder.")
        sys.exit(1)

    init_data_file()
    
    port = 5173
    print(f"\n  GP EDITOR v2.0 running at http://localhost:{port}")
    print(f"  Data file: {DATA_FILE.resolve()}")
    print(f"  Preview: {INDEX.resolve()}")
    print(f"  Press Ctrl+C to stop\n")
    app.run(port=port, debug=False)