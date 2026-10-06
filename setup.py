import os, subprocess, sys

def write(path, content):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

write('requirements.txt', 'fastapi==0.109.0\nuvicorn[standard]==0.27.0\nhttpx==0.26.0\npydantic==2.5.3\n')
write('.gitignore', '__pycache__/\n*.py[cod]\n.env\n.venv/\n*.log\n.DS_Store\n')
write('README.md', '# Username Sniper Pro\n\nPremium username checker.\n\n## Run\n\n```bash\npython -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload\n```\n\nOpen http://localhost:8000\n')

# main.py
write('main.py', '''from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx, time, asyncio
from pathlib import Path

app = FastAPI(title="Username Sniper Pro")
BASE_DIR = Path(__file__).resolve().parent
stats = {"checks": 0, "available": 0, "taken": 0, "errors": 0, "started_at": time.time(), "last_result": None}

class CheckRequest(BaseModel):
    platform: str
    username: str

class BulkCheckRequest(BaseModel):
    platform: str
    words: list
    mix_numbers: bool = False

def record(r):
    stats["checks"] += 1
    if r.get("error"): stats["errors"] += 1
    elif r.get("available"): stats["available"] += 1
    else: stats["taken"] += 1
    stats["last_result"] = r

async def check_mc(u):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get(f"https://api.mojang.com/users/profiles/minecraft/{u}", headers={"User-Agent":"sniper/1.0"})
            if r.status_code == 429: return {"platform":"minecraft","username":u,"available":False,"error":"rate_limited"}
            return {"platform":"minecraft","username":u,"available":r.status_code in [204,404]}
    except Exception as e: return {"platform":"minecraft","username":u,"available":False,"error":str(e)}

async def check_rb(u):
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post("https://users.roblox.com/v1/usernames/validate", json={"username":u}, headers={"Content-Type":"application/json"})
            if r.status_code == 429: return {"platform":"roblox","username":u,"available":False,"error":"rate_limited"}
            if r.status_code != 200: return {"platform":"roblox","username":u,"available":False,"error":"unexpected"}
            return {"platform":"roblox","username":u,"available":bool(r.json().get("valid"))}
    except Exception as e: return {"platform":"roblox","username":u,"available":False,"error":str(e)}

async def check_ig(u):
    return {"platform":"instagram","username":u,"available":False,"status":"manual_review","note":"Requires approved API"}

@app.get("/api/stats")
async def get_stats(): return {**stats, "uptime_seconds": int(time.time()-stats["started_at"])}

@app.post("/api/check")
async def check(req: CheckRequest):
    p, u = req.platform.lower().strip(), req.username.strip()
    if not u: raise HTTPException(400, "Username required")
    ch = {"minecraft":check_mc,"roblox":check_rb,"instagram":check_ig}.get(p)
    if not ch: raise HTTPException(400, "Unsupported platform")
    r = await ch(u); record(r); return r

@app.post("/api/bulk-check")
async def bulk_check(req: BulkCheckRequest):
    results = []
    ch = {"minecraft":check_mc,"roblox":check_rb,"instagram":check_ig}.get(req.platform.lower())
    if not ch: return {"results":[],"total":0}
    for w in req.words:
        u = f"{w}{__import__('random').randint(0,9999)}" if req.mix_numbers else w
        r = await ch(u); record(r); results.append(r); await asyncio.sleep(0.1)
    return {"results":results,"total":len(results)}

@app.get("/")
async def home(): return FileResponse(BASE_DIR / "ui" / "index.html")

app.mount("/static", StaticFiles(directory=str(BASE_DIR/"ui")), name="static")
''')

print('✅ All backend files created!')
print('⚠️  Now add ui/index.html, ui/css/style.css, and ui/js/app.js via GitHub upload.')
print('Then run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload')