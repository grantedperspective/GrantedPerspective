#!/usr/bin/env python3
"""
GrantedPerspective Site Editor (v3.0)

Run from your WebPubPortfolio folder:   python editor.py
Then open http://localhost:5173

What it does
  - Edit every part of the site (hero text, bio, skills, contact, media browser)
  - Upload photos straight into img/ and manage the 24-ish rolling hero images
  - Add / delete / reorder media tabs, sections and entries
  - Click things in the live preview to jump to their field
  - PUBLISH = save -> rebuild index.html -> git commit -> git push

Data lives in site-data.json. Optional: pip install pillow  (auto-shrinks uploaded photos)
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

import build as sitebuild

try:
    from PIL import Image, ImageOps
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False

BASE = Path(__file__).parent.resolve()
DATA_FILE = BASE / "site-data.json"
BACKUP_FILE = BASE / "site-data.backup.json"
INDEX = BASE / "index.html"
IMG_DIR = BASE / "img"
IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_IMG_EDGE = 2200  # px, only used when Pillow is installed

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024


# ── SAFETY: localhost only, and POSTs must come from the editor page ─────────

@app.before_request
def guard():
    host = request.host.split(":")[0]
    if host not in ("localhost", "127.0.0.1"):
        abort(403)
    if request.method == "POST" and request.headers.get("X-GP-Editor") != "1":
        abort(403)


@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ── DATA ──────────────────────────────────────────────────────────────────────

def load_data():
    if DATA_FILE.exists():
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    else:
        raw = sitebuild.read_baked(INDEX.read_text(encoding="utf-8"))
    return sitebuild.migrate(raw)


def write_json_atomic(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def save_data(data):
    if not isinstance(data, dict) or not isinstance(data.get("tabs"), list):
        raise ValueError("Refusing to save: data is missing the 'tabs' list")
    if DATA_FILE.exists():
        try:
            BACKUP_FILE.write_text(DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            pass
    write_json_atomic(DATA_FILE, data)


@app.route("/api/data", methods=["GET"])
def api_get():
    try:
        return jsonify(load_data())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/data", methods=["POST"])
def api_post():
    try:
        save_data(request.get_json(force=True))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ── IMAGES / UPLOADS ──────────────────────────────────────────────────────────

@app.route("/api/images", methods=["GET"])
def api_images():
    if not IMG_DIR.exists():
        return jsonify([])
    names = sorted(p.name for p in IMG_DIR.iterdir() if p.suffix.lower() in IMG_EXT)
    return jsonify(["./img/" + n for n in names])


def unique_name(folder, name):
    stem, ext = os.path.splitext(name)
    candidate, n = name, 2
    while (folder / candidate).exists():
        candidate = f"{stem}-{n}{ext}"
        n += 1
    return candidate


def save_image(file_storage):
    IMG_DIR.mkdir(exist_ok=True)
    name = secure_filename(file_storage.filename or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in IMG_EXT:
        return None, f"{file_storage.filename}: not a supported image (jpg, png, gif, webp)"
    name = unique_name(IMG_DIR, name)
    dest = IMG_DIR / name
    if HAVE_PIL and ext in (".jpg", ".jpeg", ".png", ".webp"):
        try:
            im = Image.open(file_storage.stream)
            im = ImageOps.exif_transpose(im)
            im.thumbnail((MAX_IMG_EDGE, MAX_IMG_EDGE))
            if ext in (".jpg", ".jpeg"):
                im.convert("RGB").save(dest, "JPEG", quality=88, optimize=True)
            else:
                im.save(dest)
            return "./img/" + name, None
        except Exception:
            file_storage.stream.seek(0)
    file_storage.save(dest)
    return "./img/" + name, None


@app.route("/api/upload", methods=["POST"])
def api_upload():
    dest = request.form.get("dest", "img")
    paths, skipped = [], []
    for f in request.files.getlist("files"):
        if dest == "root":  # PDFs only (resume, pitch decks, ...)
            name = secure_filename(f.filename or "")
            if not name.lower().endswith(".pdf"):
                skipped.append(f"{f.filename}: only PDFs can be uploaded here")
                continue
            f.save(BASE / name)
            paths.append("./" + name)
        else:
            p, err = save_image(f)
            (paths.append(p) if p else skipped.append(err))
    return jsonify({"ok": bool(paths), "paths": paths, "skipped": skipped})


# ── PUBLISH (save -> build -> git commit -> git push) ─────────────────────────

def git(*args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git", *args], cwd=BASE, capture_output=True, text=True, timeout=180, env=env)


@app.route("/api/publish", methods=["POST"])
def api_publish():
    log = []

    def fail(msg):
        log.append("✗ " + msg)
        return jsonify({"ok": False, "log": log})

    try:
        body = request.get_json(silent=True)
        if body:
            save_data(body)
            log.append("✓ Saved site-data.json")
        log += ["✓ " + l for l in sitebuild.build()]
    except Exception as e:
        return fail(f"Build failed: {e}")

    try:
        if git("rev-parse", "--is-inside-work-tree").returncode != 0:
            return fail("This folder isn't a git repository, so there's nothing to push. "
                        "(Your site files were still saved and built.)")
        paths = ["index.html", "site-data.json"]
        paths += [p.name for p in BASE.glob("*.pdf")]
        for extra in ("img", "logo.png"):
            if (BASE / extra).exists():
                paths.append(extra)
        r = git("add", "-A", "--", *paths)
        if r.returncode != 0:
            return fail("git add failed: " + (r.stderr or r.stdout).strip())
        if git("diff", "--cached", "--quiet").returncode == 0:
            log.append("✓ Nothing new to commit — site is already up to date")
            return jsonify({"ok": True, "log": log})
        msg = "Update site via editor " + time.strftime("%Y-%m-%d %H:%M")
        r = git("commit", "-m", msg)
        if r.returncode != 0:
            return fail("git commit failed: " + (r.stderr or r.stdout).strip())
        log.append("✓ Committed: " + msg)
        r = git("push")
        if r.returncode != 0:
            return fail("git push failed (committed locally, not pushed): " + (r.stderr or r.stdout).strip())
        log.append("✓ Pushed — GitHub Pages usually updates within a minute or two")
        return jsonify({"ok": True, "log": log})
    except Exception as e:
        return fail(f"Git error: {e}")


# ── PREVIEW + UI ──────────────────────────────────────────────────────────────

@app.route("/preview")
@app.route("/preview/<path:path>")
def preview(path="index.html"):
    return send_from_directory(BASE, path)


@app.route("/")
def editor():
    return Response(EDITOR_HTML, mimetype="text/html")


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
    --text:#ddd; --text-dim:#777; --text-faint:#2a2a2a;
    --green:#39ff14; --red:#ff4444; --yellow:#ffcc00;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:var(--bg);color:var(--text);font-family:'Space Mono',monospace;display:flex;height:100vh;overflow:hidden;}
  button{font-family:inherit;}

  /* sidebar */
  .sidebar{width:206px;flex-shrink:0;background:#000;border-right:1px solid var(--border-accent);display:flex;flex-direction:column;}
  .logo{padding:.9rem 1rem;border-bottom:1px solid var(--border-accent);}
  .logo h1{font-family:'VT323',monospace;font-size:1.3rem;color:var(--purple);letter-spacing:2px;line-height:1;}
  .logo p{font-size:.48rem;color:var(--text-dim);letter-spacing:2px;margin-top:.2rem;}
  .nav-scroll{flex:1;overflow-y:auto;}
  .nav-group{padding:.4rem 0;border-bottom:1px solid #0d0d0d;}
  .nav-group-label{font-family:'Share Tech Mono',monospace;font-size:.44rem;letter-spacing:3px;color:#3a3a3a;text-transform:uppercase;padding:.2rem 1rem .35rem;}
  .nav-item{display:flex;align-items:center;gap:.5rem;padding:.5rem 1rem;cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:1px;text-transform:uppercase;color:var(--text-dim);border-left:2px solid transparent;transition:all .15s;user-select:none;}
  .nav-item:hover{color:var(--text);background:#0d0d0d;}
  .nav-item.active{color:var(--purple);border-left-color:var(--purple);background:#0a0018;}
  .nav-item.add{color:#3d2a55;}.nav-item.add:hover{color:var(--purple);}
  .nav-icon{font-size:.7rem;width:14px;text-align:center;}
  .badge{margin-left:auto;background:var(--purple-dark);color:#999;font-size:.44rem;padding:1px 5px;border-radius:2px;}
  .sidebar-bottom{padding:.7rem;border-top:1px solid var(--border-accent);display:flex;flex-direction:column;gap:.4rem;}
  .btn-save,.btn-publish{width:100%;padding:.55rem;border:none;cursor:pointer;font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:2px;text-transform:uppercase;transition:background .2s;}
  .btn-save{background:var(--purple);color:#fff;}.btn-save:hover{background:var(--purple-mid);}
  .btn-save.dirty{box-shadow:0 0 0 1px var(--yellow);}
  .btn-publish{background:#052a00;color:var(--green);border:1px solid #0b4a00;}.btn-publish:hover{background:#0a3d00;}
  .btn-save:disabled,.btn-publish:disabled{background:#222;color:#555;border-color:#222;cursor:not-allowed;}
  .status-line{font-size:.48rem;text-align:center;color:var(--text-dim);letter-spacing:1px;min-height:12px;font-family:'Share Tech Mono',monospace;}
  .status-line.ok{color:var(--green);}.status-line.err{color:var(--red);}.status-line.saving{color:var(--yellow);}

  /* main */
  .main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;}
  .topbar{background:#000;border-bottom:1px solid var(--border);padding:.55rem 1.1rem;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:1rem;}
  .topbar-left{display:flex;align-items:baseline;gap:.7rem;min-width:0;}
  .topbar-title{font-family:'VT323',monospace;font-size:1.2rem;color:#fff;letter-spacing:2px;white-space:nowrap;}
  .topbar-desc{font-size:.52rem;color:var(--text-dim);letter-spacing:1px;font-family:'Share Tech Mono',monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .btn-add{display:flex;align-items:center;gap:.35rem;padding:.38rem .8rem;background:var(--purple-dim);border:1px solid var(--purple-dark);color:var(--purple);font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:1px;text-transform:uppercase;cursor:pointer;transition:all .15s;white-space:nowrap;}
  .btn-add:hover{background:var(--purple-dark);color:#fff;}
  .btn-add.small{padding:.25rem .6rem;font-size:.5rem;}
  .btn-ghost{background:none;border:1px solid var(--border);color:var(--text-dim);font-family:'Share Tech Mono',monospace;font-size:.5rem;letter-spacing:1px;padding:.25rem .55rem;cursor:pointer;text-transform:uppercase;transition:all .15s;}
  .btn-ghost:hover{border-color:var(--purple);color:var(--purple);}
  .btn-ghost.danger:hover{border-color:var(--red);color:var(--red);}

  .scroll{flex:1;overflow-y:auto;padding:.9rem 1.1rem 3rem;}
  .panel{display:none;}.panel.active{display:block;}

  /* cards */
  .card-list{display:flex;flex-direction:column;gap:.35rem;margin-bottom:.4rem;}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:3px;overflow:hidden;transition:border-color .15s;}
  .card.drag-over,.bio-row.drag-over,.tile.drag-over{border-color:var(--purple)!important;}
  .card.dragging,.tile.dragging,.bio-row.dragging{opacity:.35;}
  .card.flash{animation:flash 1.2s ease-out;}
  @keyframes flash{0%{box-shadow:0 0 0 2px var(--green);}100%{box-shadow:0 0 0 0 transparent;}}
  .card-head{display:flex;align-items:center;gap:.55rem;padding:.55rem .7rem;cursor:pointer;transition:background .15s;user-select:none;}
  .card-head:hover{background:var(--surface2);}
  .drag-handle{color:#333;cursor:grab;font-size:.85rem;flex-shrink:0;padding:0 2px;transition:color .15s;}
  .card-head:hover .drag-handle,.bio-row:hover .drag-handle{color:#666;}
  .drag-handle:active{cursor:grabbing;}
  .dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
  .dot-live{background:var(--green);box-shadow:0 0 4px var(--green);}.dot-unlisted{background:var(--yellow);}.dot-placeholder{background:#555;}
  .dot-restricted{background:var(--red);}.dot-production{background:#ff8800;}.dot-scrapped{background:#333;}
  .card-title{font-family:'Share Tech Mono',monospace;font-size:.62rem;color:var(--purple);letter-spacing:1px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .card-sub{font-size:.48rem;color:var(--text-dim);letter-spacing:1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px;}
  .toggle{color:#444;font-size:.65rem;flex-shrink:0;transition:transform .15s;}
  .card.open .toggle{transform:rotate(90deg);}
  .btn-del{background:none;border:none;color:#3a1010;cursor:pointer;font-size:.8rem;flex-shrink:0;transition:color .15s;padding:0 2px;}
  .btn-del:hover{color:var(--red);}
  .card-body{display:none;padding:.7rem;border-top:1px solid var(--border);background:#080808;}
  .card.open .card-body{display:block;}

  .frow{display:grid;grid-template-columns:1fr 1fr;gap:.55rem;margin-bottom:.55rem;}
  .frow.three{grid-template-columns:1fr 1fr 1fr;}
  .f{display:flex;flex-direction:column;gap:.22rem;min-width:0;}
  .f label{font-family:'Share Tech Mono',monospace;font-size:.48rem;letter-spacing:2px;color:var(--text-dim);text-transform:uppercase;}
  .f input,.f textarea,.f select{background:#050505;border:1px solid var(--border);color:var(--text);font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:.38rem .45rem;outline:none;transition:border-color .15s;border-radius:2px;width:100%;}
  .f input:focus,.f textarea:focus,.f select:focus{border-color:var(--purple);}
  .f textarea{min-height:48px;resize:vertical;line-height:1.5;}
  .f select{cursor:pointer;}.f select option{background:#050505;}
  .inline{display:flex;gap:.3rem;}.inline input{flex:1;}
  .checkrow{display:flex;align-items:center;gap:.45rem;margin-bottom:.55rem;}
  .checkrow input[type=checkbox]{accent-color:var(--purple);width:13px;height:13px;cursor:pointer;flex-shrink:0;}
  .checkrow label{font-family:'Share Tech Mono',monospace;font-size:.52rem;color:var(--text-dim);letter-spacing:1px;cursor:pointer;}
  .ph-fields{border-left:2px solid var(--purple-dark);padding-left:.7rem;margin-top:.45rem;display:none;}
  .ph-fields.on{display:block;}
  .thumb-row{display:flex;gap:.5rem;align-items:flex-start;margin-bottom:.55rem;}
  .thumb-box{width:80px;height:45px;background:#111;border:1px solid var(--border);border-radius:2px;overflow:hidden;flex-shrink:0;}
  .thumb-box img{width:100%;height:100%;object-fit:cover;display:block;}
  .thumb-none{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-family:'Share Tech Mono',monospace;font-size:.4rem;color:#333;}

  /* section blocks inside a tab */
  .sec{border:1px solid var(--border-accent);border-radius:3px;padding:.8rem;margin-top:1rem;background:#070009;}
  .sec-head{display:flex;align-items:center;justify-content:space-between;gap:.6rem;margin:.9rem 0 .5rem;}
  .sec-head.first{margin-top:0;}
  .sec-label{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:3px;color:var(--purple);text-transform:uppercase;}
  .sec-tools{display:flex;gap:.3rem;}
  .add-sec{margin-top:1.1rem;width:100%;justify-content:center;padding:.65rem;border-style:dashed;}

  /* hero tiles */
  .dropzone{border:1px dashed var(--border-accent);border-radius:3px;padding:.9rem;text-align:center;font-family:'Share Tech Mono',monospace;font-size:.55rem;color:var(--text-dim);letter-spacing:1px;margin-bottom:.8rem;transition:all .15s;}
  .dropzone.over{border-color:var(--green);color:var(--green);background:#031200;}
  .tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(108px,1fr));gap:.5rem;margin-bottom:1rem;}
  .tile{position:relative;aspect-ratio:4/3;background:#111;border:1px solid var(--border);border-radius:2px;overflow:hidden;cursor:grab;}
  .tile img{width:100%;height:100%;object-fit:cover;display:block;pointer-events:none;}
  .tile img.bad{opacity:.15;}
  .tile-n{position:absolute;left:3px;top:3px;background:rgba(0,0,0,.75);color:#aaa;font-size:.45rem;padding:1px 4px;border-radius:2px;font-family:'Share Tech Mono',monospace;}
  .tile-x{position:absolute;right:3px;top:3px;background:rgba(0,0,0,.75);color:#a55;border:none;cursor:pointer;font-size:.6rem;width:16px;height:16px;border-radius:2px;display:none;}
  .tile:hover .tile-x{display:block;}.tile-x:hover{color:var(--red);}
  .tile-path{position:absolute;left:0;right:0;bottom:0;background:linear-gradient(transparent,rgba(0,0,0,.9));font-size:.42rem;color:#999;padding:8px 4px 2px;font-family:'Share Tech Mono',monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  .tile.lib{cursor:pointer;opacity:.75;}.tile.lib:hover{opacity:1;border-color:var(--green);}

  /* about */
  .bio-row{display:flex;gap:.5rem;align-items:flex-start;background:var(--surface);border:1px solid var(--border);border-radius:3px;padding:.5rem;margin-bottom:.35rem;}
  .bio-row textarea{flex:1;background:#050505;border:1px solid var(--border);color:var(--text);font-family:'Share Tech Mono',monospace;font-size:.62rem;padding:.4rem .5rem;outline:none;border-radius:2px;min-height:70px;resize:vertical;line-height:1.6;}
  .bio-row textarea:focus{border-color:var(--purple);}
  .hint{font-family:'Share Tech Mono',monospace;font-size:.5rem;color:var(--text-dim);letter-spacing:1px;line-height:1.7;margin-bottom:.7rem;}
  .fc{background:var(--surface);border:1px solid var(--border);border-radius:3px;padding:.9rem;margin-bottom:.7rem;}
  .fc-title{font-family:'Share Tech Mono',monospace;font-size:.52rem;letter-spacing:3px;color:var(--purple);text-transform:uppercase;margin-bottom:.7rem;padding-bottom:.35rem;border-bottom:1px solid var(--border-accent);}
  .fc .f{margin-bottom:.55rem;}.fc .f:last-child{margin-bottom:0;}

  /* preview */
  .preview{width:400px;flex-shrink:0;border-left:1px solid var(--border-accent);display:flex;flex-direction:column;background:#000;}
  .pbar{border-bottom:1px solid var(--border);padding:.5rem .7rem;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;gap:.4rem;flex-wrap:wrap;}
  .pbar-label{font-family:'Share Tech Mono',monospace;font-size:.52rem;color:var(--text-dim);letter-spacing:2px;}
  .pnav{display:flex;gap:.3rem;}
  .pnav-btn{font-family:'Share Tech Mono',monospace;font-size:.48rem;letter-spacing:1px;padding:.22rem .45rem;background:none;border:1px solid var(--border);color:var(--text-dim);cursor:pointer;text-transform:uppercase;transition:all .15s;}
  .pnav-btn:hover,.pnav-btn.active{border-color:var(--purple);color:var(--purple);background:var(--purple-dim);}
  .phint{font-family:'Share Tech Mono',monospace;font-size:.44rem;color:#2f6a24;letter-spacing:1px;padding:.3rem .7rem;border-bottom:1px solid var(--border);}
  .pframe-wrap{flex:1;overflow:hidden;position:relative;}
  .pframe{width:1280px;height:800px;border:none;transform-origin:top left;}
  .btn-refresh{position:absolute;bottom:.6rem;right:.6rem;font-family:'Share Tech Mono',monospace;font-size:.48rem;letter-spacing:1px;padding:.28rem .55rem;background:rgba(0,0,0,.85);border:1px solid var(--border-accent);color:var(--purple);cursor:pointer;text-transform:uppercase;transition:all .15s;}
  .btn-refresh:hover{background:var(--purple-dark);color:#fff;}

  .empty{padding:1.2rem;text-align:center;font-family:'Share Tech Mono',monospace;font-size:.55rem;color:#333;border:1px dashed var(--border);border-radius:3px;}

  /* toast + modal */
  .toast{position:fixed;left:50%;bottom:1.2rem;transform:translateX(-50%);background:#14001f;border:1px solid var(--purple);color:#ddd;font-family:'Share Tech Mono',monospace;font-size:.58rem;letter-spacing:1px;padding:.55rem .9rem;display:none;z-index:50;gap:.8rem;align-items:center;}
  .toast.on{display:flex;}
  .toast button{background:none;border:1px solid var(--purple);color:var(--purple);font-family:inherit;font-size:.55rem;padding:.15rem .5rem;cursor:pointer;letter-spacing:1px;}
  .modal{position:fixed;inset:0;background:rgba(0,0,0,.8);display:none;align-items:center;justify-content:center;z-index:60;}
  .modal.on{display:flex;}
  .modal-box{background:#050005;border:1px solid var(--purple);width:min(560px,90vw);padding:1rem 1.1rem;}
  .modal-box h3{font-family:'VT323',monospace;font-size:1.3rem;color:var(--purple);letter-spacing:2px;margin-bottom:.6rem;}
  .modal-box pre{font-family:'Share Tech Mono',monospace;font-size:.6rem;line-height:1.7;white-space:pre-wrap;color:#ccc;max-height:50vh;overflow:auto;margin-bottom:.8rem;}
  .modal-box pre .bad{color:var(--red);}.modal-box pre .good{color:var(--green);}

  ::-webkit-scrollbar{width:3px;height:3px;} ::-webkit-scrollbar-track{background:#000;} ::-webkit-scrollbar-thumb{background:var(--purple-dark);}
</style>
</head>
<body>

<div class="sidebar">
  <div class="logo"><h1>GP EDITOR</h1><p>SITE MANAGER v3.0</p></div>
  <div class="nav-scroll">
    <div class="nav-group">
      <p class="nav-group-label">Home</p>
      <div class="nav-item active" onclick="show('hero')" data-p="hero"><span class="nav-icon">⊞</span>Hero Images<span class="badge" id="b-hero">0</span></div>
      <div class="nav-item" onclick="show('herotext')" data-p="herotext"><span class="nav-icon">T</span>Hero Text</div>
    </div>
    <div class="nav-group">
      <p class="nav-group-label">Media Browser</p>
      <div id="nav-tabs"></div>
    </div>
    <div class="nav-group">
      <p class="nav-group-label">Site</p>
      <div class="nav-item" onclick="show('about')" data-p="about"><span class="nav-icon">▣</span>About</div>
      <div class="nav-item" onclick="show('contact')" data-p="contact"><span class="nav-icon">◆</span>Contact</div>
    </div>
  </div>
  <div class="sidebar-bottom">
    <button class="btn-save" id="btn-save" onclick="saveData()">[ SAVE ]</button>
    <button class="btn-publish" id="btn-publish" onclick="publish()">[ PUBLISH ▲ ]</button>
    <p class="status-line" id="status"></p>
  </div>
</div>

<div class="main">
  <div class="topbar">
    <div class="topbar-left">
      <span class="topbar-title" id="t-title">HERO IMAGES</span>
      <span class="topbar-desc" id="t-desc"></span>
    </div>
    <button class="btn-add" id="btn-add" onclick="addItem()">+ ADD</button>
  </div>
  <div class="scroll">
    <div class="panel active" id="panel-hero">
      <div class="dropzone" id="dropzone">DROP PHOTOS HERE · OR USE “+ UPLOAD PHOTOS” ABOVE · DRAG TILES TO REORDER · ✕ REMOVES FROM ROTATION (FILE STAYS IN img/)</div>
      <div class="tiles" id="tiles-hero"></div>
      <div class="sec-head"><span class="sec-label">In img/ but not in rotation — click to add</span></div>
      <div class="tiles" id="tiles-lib"></div>
    </div>

    <div class="panel" id="panel-herotext">
      <div class="fc">
        <p class="fc-title">Home Page Text</p>
        <div class="f"><label>Tag Line</label><input data-key="heroTag" type="text"></div>
        <div class="f"><label>Subtitle</label><input data-key="heroSubtitle" type="text"></div>
      </div>
    </div>

    <div class="panel" id="panel-tab"></div>

    <div class="panel" id="panel-about">
      <div class="sec-head first"><span class="sec-label">Bio paragraphs</span></div>
      <p class="hint">Wrap words in **double asterisks** to make them purple, e.g. **Catvision**. Drag ⠿ to reorder.</p>
      <div id="bio-list"></div>
      <div class="fc" style="margin-top:1rem;">
        <p class="fc-title">Skills</p>
        <div class="f"><label>Role</label><input data-key="skillRole" type="text"></div>
        <div class="f"><label>Affiliation</label><input data-key="skillAffil" type="text"></div>
        <div class="f"><label>Software</label><input data-key="skillTools" type="text"></div>
        <div class="f"><label>Live Production</label><input data-key="skillLive" type="text"></div>
        <div class="f"><label>Specialties</label><input data-key="skillSpec" type="text"></div>
      </div>
      <div class="fc">
        <p class="fc-title">Resume</p>
        <div class="f"><label>Resume filename (in site folder)</label>
          <div class="inline"><input data-key="resumeFile" type="text" placeholder="GrantHughesResume.pdf"><button class="btn-ghost" onclick="uploadResume()">↑ Upload PDF</button></div>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-contact">
      <div class="fc">
        <p class="fc-title">Links</p>
        <div class="f"><label>Email</label><input data-key="contactEmail" type="text"></div>
        <div class="f"><label>YouTube URL</label><input data-key="contactYoutube" type="text"></div>
        <div class="f"><label>Instagram URL</label><input data-key="contactInstagram" type="text"></div>
        <div class="f"><label>LinkedIn URL</label><input data-key="contactLinkedin" type="text"></div>
      </div>
      <div class="fc">
        <p class="fc-title">Copy</p>
        <div class="f"><label>Contact Blurb</label><textarea data-key="contactBlurb" rows="3"></textarea></div>
      </div>
    </div>
  </div>
</div>

<div class="preview" id="preview">
  <div class="pbar">
    <span class="pbar-label">// LIVE PREVIEW</span>
    <div class="pnav">
      <button class="pnav-btn active" onclick="pNav('home',this)">HOME</button>
      <button class="pnav-btn" onclick="pNav('about',this)">ABOUT</button>
      <button class="pnav-btn" onclick="pNav('projects',this)">PROJ</button>
      <button class="pnav-btn" onclick="pNav('contact',this)">CONT</button>
      <button class="pnav-btn" onclick="cycleSize()" title="Change preview width" id="btn-size">◧</button>
    </div>
  </div>
  <p class="phint">CLICK ANY GREEN-OUTLINED ITEM TO EDIT IT · PREVIEW SHOWS SAVED DATA</p>
  <div class="pframe-wrap" id="pwrap">
    <iframe class="pframe" id="pframe" src="/preview/index.html"></iframe>
    <button class="btn-refresh" onclick="refreshPreview()">↺ REFRESH</button>
  </div>
</div>

<div class="toast" id="toast"><span id="toast-msg"></span><button id="toast-undo" style="display:none">UNDO</button></div>
<div class="modal" id="modal"><div class="modal-box"><h3 id="modal-title">PUBLISH</h3><pre id="modal-log"></pre><button class="btn-add" onclick="closeModal()" id="modal-close">CLOSE</button></div></div>

<script>
const H = {'X-GP-Editor':'1'};
const ICON = {video:'▶', photo:'◻', broadcast:'◎'};
const FIELD_PANEL = k => k.startsWith('hero') ? 'herotext' : k.startsWith('contact') ? 'contact' : 'about';
let state = null, curPanel = 'hero', dirty = false, pPage = 'home';

/* ---------- helpers ---------- */
const esc = s => String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
const imgSrc = p => /^(https?:)?\/\//.test(p) ? p : '/preview/' + String(p || '').replace(/^\.\//,'');
const $ = id => document.getElementById(id);
const sub = (t, id) => t.subsections.find(s => s.id === id);
const tabById = id => state.tabs.find(t => t.id === id);
const curTab = () => tabById(curPanel.slice(4));
function listFor(tabId, subId) { const t = tabById(tabId); return subId ? sub(t, subId).files : t.files; }
function uid(prefix, taken) { let n = 1; while (taken.includes(prefix + n)) n++; return prefix + n; }
function arrMove(arr, from, to) { const [x] = arr.splice(from, 1); arr.splice(to, 0, x); }
const tabCount = t => t.files.length + t.subsections.reduce((n, s) => n + s.files.length, 0);

function setStatus(msg, cls) { const el = $('status'); el.textContent = msg; el.className = 'status-line ' + (cls || ''); }
function markDirty() { if (!dirty) { dirty = true; $('btn-save').classList.add('dirty'); $('btn-save').textContent = '[ SAVE • ]'; } }
function markClean() { dirty = false; $('btn-save').classList.remove('dirty'); $('btn-save').textContent = '[ SAVE ]'; }
window.addEventListener('beforeunload', e => { if (dirty) { e.preventDefault(); e.returnValue = ''; } });
document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveData(); } });

let toastTimer = null;
function toast(msg, undo) {
  $('toast-msg').textContent = msg;
  const u = $('toast-undo');
  u.style.display = undo ? '' : 'none';
  u.onclick = () => { undo(); $('toast').classList.remove('on'); };
  $('toast').classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').classList.remove('on'), undo ? 7000 : 2500);
}

async function api(url, body, isForm) {
  const opt = {method:'POST', headers:{...H}};
  if (isForm) opt.body = body; else { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  const r = await fetch(url, opt);
  return r.json();
}

/* ---------- load / save / publish ---------- */
async function loadData() {
  try {
    const r = await fetch('/api/data');
    state = await r.json();
    if (state.error) { setStatus('ERROR: ' + state.error, 'err'); return; }
    bindFields();
    show('hero');
    setStatus('LOADED', 'ok'); setTimeout(() => setStatus(''), 2000);
  } catch (e) { setStatus('LOAD FAILED', 'err'); }
}

async function saveData(quiet) {
  const btn = $('btn-save'); btn.disabled = true; setStatus('SAVING...', 'saving');
  try {
    const j = await api('/api/data', state);
    if (j.ok) { markClean(); setStatus('SAVED ✓', 'ok'); refreshPreview(); }
    else setStatus('ERROR: ' + j.error, 'err');
  } catch (e) { setStatus('SAVE FAILED', 'err'); }
  btn.disabled = false; setTimeout(() => setStatus(''), 3000);
}

function openModal(title, text) { $('modal-title').textContent = title; $('modal-log').innerHTML = text; $('modal').classList.add('on'); }
function closeModal() { $('modal').classList.remove('on'); }

async function publish() {
  if (!confirm('Save, rebuild index.html, then commit and push to GitHub Pages?')) return;
  const btn = $('btn-publish'); btn.disabled = true;
  openModal('PUBLISHING...', 'Working…');
  try {
    const j = await api('/api/publish', state);
    openModal(j.ok ? 'PUBLISHED' : 'PUBLISH PROBLEM',
      j.log.map(l => '<span class="' + (l.startsWith('✗') ? 'bad' : 'good') + '">' + esc(l) + '</span>').join('\n'));
    if (j.ok) { markClean(); refreshPreview(); }
  } catch (e) { openModal('PUBLISH FAILED', '<span class="bad">' + esc(e) + '</span>'); }
  btn.disabled = false;
}

/* ---------- uploads ---------- */
function pickFile(accept, multiple, cb) {
  const i = document.createElement('input'); i.type = 'file'; i.accept = accept; i.multiple = multiple;
  i.onchange = () => cb([...i.files]); i.click();
}
async function upload(files, dest) {
  if (!files.length) return [];
  const fd = new FormData(); fd.append('dest', dest);
  files.forEach(f => fd.append('files', f));
  setStatus('UPLOADING ' + files.length + '...', 'saving');
  try {
    const j = await api('/api/upload', fd, true);
    if (j.skipped && j.skipped.length) toast(j.skipped[0] + (j.skipped.length > 1 ? ' (+' + (j.skipped.length - 1) + ' more)' : ''));
    setStatus(j.paths.length ? 'UPLOADED ✓' : 'NOTHING UPLOADED', j.paths.length ? 'ok' : 'err');
    setTimeout(() => setStatus(''), 2500);
    return j.paths;
  } catch (e) { setStatus('UPLOAD FAILED', 'err'); return []; }
}

/* ---------- drag-sort ---------- */
let DRAG = null;
function sortable(item, handle, group, onMove) {
  handle.draggable = true;
  handle.addEventListener('dragstart', e => {
    DRAG = {group, from: +item.dataset.i};
    item.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', 'x');
    if (handle !== item) e.dataTransfer.setDragImage(item, 10, 10);
  });
  handle.addEventListener('dragend', () => { item.classList.remove('dragging'); DRAG = null; document.querySelectorAll('.drag-over').forEach(x => x.classList.remove('drag-over')); });
  item.addEventListener('dragover', e => { if (DRAG && DRAG.group === group) { e.preventDefault(); item.classList.add('drag-over'); } });
  item.addEventListener('dragleave', () => item.classList.remove('drag-over'));
  item.addEventListener('drop', e => {
    if (!DRAG || DRAG.group !== group) return;
    e.preventDefault(); e.stopPropagation(); item.classList.remove('drag-over');
    const to = +item.dataset.i; if (DRAG.from !== to) onMove(DRAG.from, to);
  });
}

/* ---------- panels ---------- */
function show(id) {
  if (id.startsWith('tab:') && !tabById(id.slice(4))) id = 'hero';
  curPanel = id;
  const base = id.startsWith('tab:') ? 'tab' : id;
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  $('panel-' + base).classList.add('active');
  document.querySelectorAll('.nav-item[data-p]').forEach(n => n.classList.toggle('active', n.dataset.p === id));

  let title, desc, add = null;
  if (base === 'hero') { title = 'HERO IMAGES'; desc = 'Photos that cycle through the CRT TV grid'; add = '+ UPLOAD PHOTOS'; renderHero(); }
  else if (base === 'herotext') { title = 'HERO TEXT'; desc = 'Text over the home page grid'; }
  else if (base === 'about') { title = 'ABOUT'; desc = 'Bio, skills and resume'; add = '+ ADD PARAGRAPH'; renderBio(); }
  else if (base === 'contact') { title = 'CONTACT'; desc = 'Links and copy'; }
  else { const t = curTab(); title = t.label; desc = '/archives/' + t.dir + ' · ' + tabCount(t) + ' entries'; add = '+ ADD ENTRY'; renderTab(); }
  $('t-title').textContent = title; $('t-desc').textContent = desc;
  const ab = $('btn-add'); ab.style.display = add ? 'flex' : 'none'; if (add) ab.textContent = add;
  renderSidebar();
  syncPreview();
}

function renderSidebar() {
  $('b-hero').textContent = state.heroImages.length;
  $('nav-tabs').innerHTML = state.tabs.map(t =>
    `<div class="nav-item ${curPanel === 'tab:' + t.id ? 'active' : ''}" onclick="show('tab:${t.id}')"><span class="nav-icon">${ICON[t.kind] || '▸'}</span>${esc(t.label)}<span class="badge">${tabCount(t)}</span></div>`
  ).join('') + `<div class="nav-item add" onclick="addTab()"><span class="nav-icon">+</span>Add tab</div>`;
}

function addItem() {
  if (curPanel === 'hero') return pickFile('image/*', true, async files => { addHeroPaths(await upload(files, 'img')); });
  if (curPanel === 'about') { state.aboutBio.push(''); markDirty(); renderBio(); const t = document.querySelectorAll('#bio-list textarea'); t[t.length - 1].focus(); return; }
  if (curPanel.startsWith('tab:')) addEntry(curPanel.slice(4), '');
}

/* ---------- fixed fields (data-key inputs) ---------- */
function bindFields() {
  document.querySelectorAll('[data-key]').forEach(el => {
    el.value = state[el.dataset.key] || '';
    el.oninput = () => { state[el.dataset.key] = el.value; markDirty(); };
  });
}
function focusKey(key) { const el = document.querySelector(`[data-key="${key}"]`); if (el) { el.focus(); el.select && el.select(); } }
function uploadResume() {
  pickFile('application/pdf', false, async files => {
    const p = await upload(files, 'root');
    if (p.length) { state.resumeFile = p[0].replace(/^\.\//, ''); bindFields(); markDirty(); }
  });
}

/* ---------- HERO IMAGES ---------- */
function addHeroPaths(paths) {
  paths.forEach(p => { if (!state.heroImages.includes(p)) state.heroImages.push(p); });
  if (paths.length) { markDirty(); renderHero(); renderSidebar(); }
}
function delHero(i) {
  const [p] = state.heroImages.splice(i, 1); markDirty(); renderHero(); renderSidebar();
  toast('Removed from rotation', () => { state.heroImages.splice(i, 0, p); markDirty(); renderHero(); renderSidebar(); });
}
async function renderHero() {
  const box = $('tiles-hero');
  box.innerHTML = state.heroImages.length ? '' : '<div class="empty" style="grid-column:1/-1">NO HERO IMAGES — UPLOAD SOME</div>';
  state.heroImages.forEach((p, i) => {
    const t = document.createElement('div'); t.className = 'tile'; t.dataset.i = i;
    t.innerHTML = `<img src="${esc(imgSrc(p))}" onerror="this.classList.add('bad')"><span class="tile-n">${i + 1}</span><button class="tile-x" onclick="delHero(${i})">✕</button><div class="tile-path">${esc(p.split('/').pop())}</div>`;
    sortable(t, t, 'hero', (a, b) => { arrMove(state.heroImages, a, b); markDirty(); renderHero(); });
    box.appendChild(t);
  });
  try {
    const all = await (await fetch('/api/images')).json();
    const unused = all.filter(p => !state.heroImages.includes(p));
    $('tiles-lib').innerHTML = unused.length ? '' : '<div class="empty" style="grid-column:1/-1">NOTHING ELSE IN img/</div>';
    unused.forEach(p => {
      const t = document.createElement('div'); t.className = 'tile lib';
      t.innerHTML = `<img src="${esc(imgSrc(p))}"><div class="tile-path">${esc(p.split('/').pop())}</div>`;
      t.onclick = () => addHeroPaths([p]);
      $('tiles-lib').appendChild(t);
    });
  } catch (e) {}
}
(function () {
  const dz = $('panel-hero');
  const hasFiles = e => e.dataTransfer && [...e.dataTransfer.types].includes('Files');
  dz.addEventListener('dragover', e => { if (hasFiles(e)) { e.preventDefault(); $('dropzone').classList.add('over'); } });
  dz.addEventListener('dragleave', e => { if (e.target === dz) $('dropzone').classList.remove('over'); });
  dz.addEventListener('drop', async e => {
    if (!hasFiles(e)) return;
    e.preventDefault(); $('dropzone').classList.remove('over');
    addHeroPaths(await upload([...e.dataTransfer.files], 'img'));
  });
})();

/* ---------- ABOUT BIO ---------- */
function renderBio() {
  const box = $('bio-list'); box.innerHTML = '';
  state.aboutBio.forEach((txt, i) => {
    const row = document.createElement('div'); row.className = 'bio-row'; row.dataset.i = i;
    row.innerHTML = `<span class="drag-handle">⠿</span><textarea data-bio="${i}">${esc(txt)}</textarea><button class="btn-del" onclick="delBio(${i})">✕</button>`;
    const ta = row.querySelector('textarea');
    ta.oninput = () => { state.aboutBio[i] = ta.value; markDirty(); };
    sortable(row, row.querySelector('.drag-handle'), 'bio', (a, b) => { arrMove(state.aboutBio, a, b); markDirty(); renderBio(); });
    box.appendChild(row);
  });
  if (!state.aboutBio.length) box.innerHTML = '<div class="empty">NO PARAGRAPHS YET.</div>';
}
function delBio(i) {
  const [t] = state.aboutBio.splice(i, 1); markDirty(); renderBio();
  toast('Paragraph deleted', () => { state.aboutBio.splice(i, 0, t); markDirty(); renderBio(); });
}

/* ---------- MEDIA TABS ---------- */
function addTab() {
  const id = uid('tab', state.tabs.map(t => t.id));
  state.tabs.push({id, label: 'NEW TAB', dir: 'new-tab', kind: 'video', files: [], subsections: []});
  markDirty(); show('tab:' + id);
  const el = document.querySelector('[data-k="tablabel"]'); if (el) { el.focus(); el.select(); }
}
function delTab() {
  const t = curTab();
  if (!confirm(`Delete the "${t.label}" tab and its ${tabCount(t)} entries?`)) return;
  state.tabs.splice(state.tabs.indexOf(t), 1); markDirty(); show('hero');
}
function moveTab(d) {
  const i = state.tabs.indexOf(curTab()), j = i + d;
  if (j < 0 || j >= state.tabs.length) return;
  arrMove(state.tabs, i, j); markDirty(); renderSidebar();
}
function tabFld(key, el) {
  const t = curTab();
  if (key === 'label') {
    if ((t.dir || '') === (slug(t.label) || t.id)) { t.dir = slug(el.value) || t.id; document.querySelector('[data-k="tabdir"]').value = t.dir; }
    $('t-title').textContent = el.value;
  }
  t[key] = el.value; markDirty(); renderSidebar();
  if (key === 'dir') $('t-desc').textContent = '/archives/' + t.dir + ' · ' + tabCount(t) + ' entries';
}
function addSub() {
  const t = curTab();
  const id = uid('sec', t.subsections.map(s => s.id));
  t.subsections.push({id, title: 'NEW SECTION', desc: '', files: []});
  markDirty(); renderTab();
  const el = document.querySelector(`[data-sec="${id}"] [data-k="subtitle"]`); if (el) { el.focus(); el.select(); el.scrollIntoView({block:'center'}); }
}
function subOf(el) { return sub(curTab(), el.closest('.sec').dataset.sec); }
function subFld(key, el) { subOf(el)[key] = el.value; markDirty(); }
function moveSub(el, d) {
  const t = curTab(), s = subOf(el), i = t.subsections.indexOf(s), j = i + d;
  if (j < 0 || j >= t.subsections.length) return;
  arrMove(t.subsections, i, j); markDirty(); renderTab();
}
function delSub(el) {
  const t = curTab(), s = subOf(el);
  if (!confirm(`Delete the "${s.title}" section and its ${s.files.length} entries?`)) return;
  t.subsections.splice(t.subsections.indexOf(s), 1); markDirty(); renderTab(); renderSidebar();
}

function renderTab() {
  const t = curTab(), p = $('panel-tab');
  p.innerHTML = `
    <div class="fc">
      <p class="fc-title">Tab settings</p>
      <div class="frow three">
        <div class="f"><label>Tab label</label><input data-k="tablabel" type="text" value="${esc(t.label)}" oninput="tabFld('label',this)"></div>
        <div class="f"><label>Directory name</label><input data-k="tabdir" type="text" value="${esc(t.dir)}" oninput="tabFld('dir',this)"></div>
        <div class="f"><label>Icon / style</label><select onchange="tabFld('kind',this)">${['video','photo','broadcast'].map(k => `<option value="${k}" ${t.kind === k ? 'selected' : ''}>${k}</option>`).join('')}</select></div>
      </div>
      <div class="sec-tools"><button class="btn-ghost" onclick="moveTab(-1)">◀ Move left</button><button class="btn-ghost" onclick="moveTab(1)">Move right ▶</button><button class="btn-ghost danger" onclick="delTab()">✕ Delete tab</button></div>
    </div>
    <div class="sec-head first"><span class="sec-label">Main entries</span><button class="btn-add small" onclick="addEntry('${t.id}','')">+ ENTRY</button></div>
    <div class="card-list" id="list-${t.id}-"></div>
    ${t.subsections.map(s => `
      <div class="sec" data-sec="${s.id}">
        <div class="sec-head first"><span class="sec-label">Section</span>
          <div class="sec-tools"><button class="btn-ghost" onclick="moveSub(this,-1)">▲</button><button class="btn-ghost" onclick="moveSub(this,1)">▼</button><button class="btn-ghost danger" onclick="delSub(this)">✕ Delete section</button></div></div>
        <div class="f" style="margin-bottom:.55rem"><label>Section title (last word shows in purple)</label><input data-k="subtitle" type="text" value="${esc(s.title)}" oninput="subFld('title',this)"></div>
        <div class="f" style="margin-bottom:.55rem"><label>Description</label><textarea oninput="subFld('desc',this)">${esc(s.desc)}</textarea></div>
        <div class="sec-head"><span class="sec-label">Entries</span><button class="btn-add small" onclick="addEntry('${t.id}','${s.id}')">+ ENTRY</button></div>
        <div class="card-list" id="list-${t.id}-${s.id}"></div>
      </div>`).join('')}
    <button class="btn-add add-sec" onclick="addSub()">+ ADD SECTION TO THIS TAB</button>`;
  renderList(t.id, '');
  t.subsections.forEach(s => renderList(t.id, s.id));
}

/* ---------- ENTRIES ---------- */
function dotClass(f) {
  if (!f.placeholder && f.link) return 'dot-live';
  const t = (f.placeholderTitle || '').toLowerCase();
  if (f.placeholder === true) {
    if (t.includes('scrapped')) return 'dot-scrapped';
    if (t.includes('production')) return 'dot-production';
    if (t.includes('restricted')) return 'dot-restricted';
    return 'dot-placeholder';
  }
  return 'dot-unlisted';
}

function renderList(tabId, subId) {
  const box = $(`list-${tabId}-${subId}`); if (!box) return;
  const files = listFor(tabId, subId);
  box.innerHTML = files.length ? '' : '<div class="empty">NO ENTRIES — USE “+ ENTRY”.</div>';
  files.forEach((f, i) => {
    const ph = f.placeholder === true;
    const card = document.createElement('div');
    card.className = 'card'; card.dataset.tab = tabId; card.dataset.sub = subId; card.dataset.i = i;
    card.innerHTML = `
      <div class="card-head" onclick="this.parentElement.classList.toggle('open')">
        <span class="drag-handle" onclick="event.stopPropagation()">⠿</span>
        <span class="dot ${dotClass(f)}"></span>
        <span class="card-title">${esc(f.title || 'UNTITLED')}</span>
        <span class="card-sub">${esc(f.description || '')}</span>
        <span class="toggle">›</span>
        <button class="btn-del" title="Delete entry" onclick="event.stopPropagation();delEntry(this)">✕</button>
      </div>
      <div class="card-body">
        <div class="frow">
          <div class="f"><label>Title</label><input data-k="title" type="text" value="${esc(f.title || '')}" oninput="fld(this,'title')"></div>
          <div class="f"><label>Description</label><input data-k="description" type="text" value="${esc(f.description || '')}" oninput="fld(this,'description')"></div>
        </div>
        <div class="frow">
          <div class="f"><label>Link URL (or ./file.pdf)</label>
            <div class="inline"><input data-k="link" type="text" value="${esc(f.link || '')}" oninput="fld(this,'link')"><button class="btn-ghost" title="Upload a PDF to link to" onclick="upLink(this)">↑ PDF</button></div></div>
          <div class="f"><label>YouTube link or ID (fills link + thumbnail)</label><input type="text" placeholder="paste a YouTube URL" oninput="applyYT(this)"></div>
        </div>
        <div class="thumb-row">
          <div class="thumb-box">${f.thumb ? `<img src="${esc(imgSrc(f.thumb))}" onerror="this.style.opacity='.1'">` : '<div class="thumb-none">NO THUMB</div>'}</div>
          <div class="f" style="flex:1;"><label>Thumbnail URL or ./img/ path</label>
            <div class="inline"><input data-k="thumb" type="text" value="${esc(f.thumb || '')}" oninput="fld(this,'thumb')"><button class="btn-ghost" onclick="upThumb(this)">↑ Image</button></div></div>
          <div class="f" style="width:110px;"><label>Tag (optional)</label><input data-k="tag" type="text" value="${esc(f.tag || '')}" placeholder="e.g. pitch" oninput="fld(this,'tag')"></div>
        </div>
        <div class="checkrow">
          <input type="checkbox" id="ph-${tabId}-${subId}-${i}" ${ph ? 'checked' : ''} onchange="chkPH(this)">
          <label for="ph-${tabId}-${subId}-${i}">Placeholder (no live link — shows an overlay when clicked)</label>
        </div>
        <div class="ph-fields ${ph ? 'on' : ''}">
          <div class="frow">
            <div class="f"><label>Overlay Title</label><input data-k="placeholderTitle" type="text" value="${esc(f.placeholderTitle || '')}" oninput="fld(this,'placeholderTitle')"></div>
            <div class="f"><label>Overlay Message</label><input data-k="placeholderMsg" type="text" value="${esc((f.placeholderMsg || '').replace(/\n/g, '\\n'))}" oninput="fldMsg(this)"></div>
          </div>
        </div>
      </div>`;
    sortable(card, card.querySelector('.drag-handle'), `list:${tabId}:${subId}`, (a, b) => { arrMove(files, a, b); markDirty(); renderList(tabId, subId); });
    box.appendChild(card);
  });
}

const cardOf = el => el.closest('.card');
const fileOf = el => { const c = cardOf(el); return listFor(c.dataset.tab, c.dataset.sub)[+c.dataset.i]; };
function syncHead(card, f) {
  card.querySelector('.card-title').textContent = f.title || 'UNTITLED';
  card.querySelector('.card-sub').textContent = f.description || '';
  card.querySelector('.dot').className = 'dot ' + dotClass(f);
}
function setThumbPreview(card, v) {
  card.querySelector('.thumb-box').innerHTML = v ? `<img src="${esc(imgSrc(v))}" onerror="this.style.opacity='.1'">` : '<div class="thumb-none">NO THUMB</div>';
}
function unPlaceholder(card, f) {          // entering a real link means it's no longer a placeholder
  if (f.link && f.placeholder) {
    f.placeholder = false;
    card.querySelector('input[type=checkbox]').checked = false;
    card.querySelector('.ph-fields').classList.remove('on');
  }
}
function fld(el, key) {
  const f = fileOf(el), card = cardOf(el);
  if (key === 'tag' && !el.value) delete f.tag; else f[key] = el.value;
  if (key === 'link') unPlaceholder(card, f);
  if (key === 'thumb') setThumbPreview(card, el.value);
  markDirty(); syncHead(card, f);
}
function fldMsg(el) { fileOf(el).placeholderMsg = el.value.replace(/\\n/g, '\n'); markDirty(); }
function chkPH(cb) {
  const f = fileOf(cb), card = cardOf(cb);
  f.placeholder = cb.checked;
  if (cb.checked && !f.placeholderTitle) {
    f.placeholderTitle = '[ COMING SOON ]'; f.placeholderMsg = 'CONTENT COMING SOON.';
    card.querySelector('[data-k=placeholderTitle]').value = f.placeholderTitle;
    card.querySelector('[data-k=placeholderMsg]').value = f.placeholderMsg;
  }
  card.querySelector('.ph-fields').classList.toggle('on', cb.checked);
  markDirty(); syncHead(card, f);
}
function applyYT(el) {
  const m = el.value.trim().match(/(?:youtu\.be\/|v=|embed\/|shorts\/)([\w-]{11})|^([\w-]{11})$/);
  const id = m && (m[1] || m[2]); if (!id) return;
  const f = fileOf(el), card = cardOf(el);
  f.link = 'https://youtu.be/' + id;
  f.thumb = `https://img.youtube.com/vi/${id}/maxresdefault.jpg`;
  card.querySelector('[data-k=link]').value = f.link;
  card.querySelector('[data-k=thumb]').value = f.thumb;
  setThumbPreview(card, f.thumb); unPlaceholder(card, f);
  markDirty(); syncHead(card, f);
}
function upThumb(btn) {
  pickFile('image/*', false, async files => {
    const p = await upload(files, 'img'); if (!p.length) return;
    const card = cardOf(btn), f = fileOf(btn);
    f.thumb = p[0]; card.querySelector('[data-k=thumb]').value = p[0]; setThumbPreview(card, p[0]); markDirty();
  });
}
function upLink(btn) {
  pickFile('application/pdf', false, async files => {
    const p = await upload(files, 'root'); if (!p.length) return;
    const card = cardOf(btn), f = fileOf(btn);
    f.link = p[0]; card.querySelector('[data-k=link]').value = p[0]; unPlaceholder(card, f); markDirty(); syncHead(card, f);
  });
}
function addEntry(tabId, subId) {
  listFor(tabId, subId).unshift({title: 'NEW ENTRY', description: '', thumb: '', link: '', placeholder: true, placeholderTitle: '[ COMING SOON ]', placeholderMsg: 'CONTENT COMING SOON.'});
  markDirty(); renderList(tabId, subId); renderSidebar();
  const card = document.querySelector(`#list-${tabId}-${subId} .card`);
  if (card) { card.classList.add('open'); card.scrollIntoView({block: 'center'}); const i = card.querySelector('[data-k=title]'); i.focus(); i.select(); }
}
function delEntry(btn) {
  const c = cardOf(btn), {tab, sub: s, i} = c.dataset, files = listFor(tab, s);
  const [f] = files.splice(+i, 1); markDirty(); renderList(tab, s); renderSidebar();
  toast(`Deleted “${f.title || 'entry'}”`, () => { files.splice(+i, 0, f); markDirty(); renderList(tab, s); renderSidebar(); });
}

/* ---------- PREVIEW ---------- */
const SIZES = [400, 620, 900]; let sizeI = 0;
function cycleSize() { sizeI = (sizeI + 1) % SIZES.length; $('preview').style.width = SIZES[sizeI] + 'px'; }
function fitPreview() {
  const w = $('pwrap'), f = $('pframe'), s = w.clientWidth / 1280;
  f.style.transform = `scale(${s})`; f.style.height = (w.clientHeight / s) + 'px';
}
new ResizeObserver(fitPreview).observe($('pwrap'));
$('pframe').addEventListener('load', () => { fitPreview(); syncPreview(); });

function previewTarget() {
  if (curPanel.startsWith('tab:')) return {page: 'projects', tab: curPanel.slice(4)};
  if (curPanel === 'about') return {page: 'about'};
  if (curPanel === 'contact') return {page: 'contact'};
  return {page: 'home'};
}
function syncPreview() {
  const m = previewTarget();
  document.querySelectorAll('.pnav-btn[onclick^="pNav"]').forEach(b => b.classList.toggle('active', b.getAttribute('onclick').includes(`'${m.page}'`)));
  try { $('pframe').contentWindow.postMessage({type: 'gp-show', ...m}, location.origin); } catch (e) {}
}
function pNav(page, btn) {
  try { $('pframe').contentWindow.postMessage({type: 'gp-show', page}, location.origin); } catch (e) {}
  document.querySelectorAll('.pnav-btn').forEach(b => b.classList.remove('active')); btn.classList.add('active');
}
function refreshPreview() { try { $('pframe').contentWindow.location.reload(); } catch (e) { $('pframe').src = '/preview/index.html'; } }

/* click in preview -> jump to the field */
window.addEventListener('message', e => {
  if (e.source !== $('pframe').contentWindow || !e.data || e.data.type !== 'gp-edit') return;
  const p = String(e.data.target).split(':');
  if (p[0] === 'hero') return show('hero');
  if (p[0] === 'field') { show(FIELD_PANEL(p[1])); return focusKey(p[1]); }
  if (p[0] === 'bio') { show('about'); const t = document.querySelector(`[data-bio="${p[1]}"]`); if (t) { t.scrollIntoView({block: 'center'}); t.focus(); } return; }
  if (p[0] === 'sub') {
    show('tab:' + p[1]);
    const el = document.querySelector(`[data-sec="${p[2]}"] [data-k="subtitle"]`); if (el) { el.scrollIntoView({block: 'center'}); el.focus(); el.select(); }
    return;
  }
  if (p[0] === 'file') {
    show('tab:' + p[1]);
    const card = document.querySelector(`.card[data-tab="${p[1]}"][data-sub="${p[2] === '-' ? '' : p[2]}"][data-i="${p[3]}"]`);
    if (card) { card.classList.add('open', 'flash'); card.scrollIntoView({block: 'center'}); setTimeout(() => card.classList.remove('flash'), 1300); }
  }
});

loadData();
</script>
</body>
</html>
"""

# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not INDEX.exists():
        print(f"ERROR: index.html not found at {INDEX}")
        print("Run this script from your WebPubPortfolio folder.")
        sys.exit(1)

    if not DATA_FILE.exists():
        write_json_atomic(DATA_FILE, load_data())
        print("  Created site-data.json from the data baked into index.html")
    else:
        # one-time upgrade of an older site-data.json to the tabs/sections format
        old = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if "tabs" not in old:
            BACKUP_FILE.write_text(DATA_FILE.read_text(encoding="utf-8"), encoding="utf-8")
            write_json_atomic(DATA_FILE, sitebuild.migrate(old))
            print("  Upgraded site-data.json to the new format (old copy: site-data.backup.json)")

    port = 5173
    print(f"\n  GP EDITOR v3.0 running at http://localhost:{port}")
    print(f"  Data file : {DATA_FILE}")
    print(f"  Photo resize on upload: {'on' if HAVE_PIL else 'off (pip install pillow to enable)'}")
    print("  Press Ctrl+C to stop\n")
    app.run(host="127.0.0.1", port=port, debug=False)
