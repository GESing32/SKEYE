from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask
from pathlib import Path
import numpy as np, cv2, io, base64, re, csv, tempfile, zipfile, os
from typing import List
import httpx

AUTONOMOUS_BASE = os.getenv("AUTONOMOUS_BASE", "http://localhost:9001")  # set to her server URL/port

app = FastAPI(title="NDVI Web API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Serve ./web at /web (keeps API paths clean)
WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR, html=True), name="web")

def _imread_gray_from_bytes(b: bytes) -> np.ndarray:
    arr = np.frombuffer(b, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None: raise ValueError("Invalid image bytes")
    return img

def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    if nir.shape != red.shape:
        red = cv2.resize(red, (nir.shape[1], nir.shape[0]), interpolation=cv2.INTER_AREA)
    nirf = nir.astype(np.float32); redf = red.astype(np.float32)
    ndvi = (nirf - redf) / (nirf + redf + 1e-6)
    return np.clip(ndvi, -1.0, 1.0)

def ndvi_to_png_bytes(ndvi: np.ndarray, color=True) -> bytes:
    ndvi_u8 = ((ndvi + 1.0) * 127.5).astype(np.uint8)
    if color:
        cmap = getattr(cv2, "COLORMAP_TURBO", cv2.COLORMAP_JET)
        vis = cv2.applyColorMap(ndvi_u8, cmap)
        _, buf = cv2.imencode(".png", vis)
    else:
        _, buf = cv2.imencode(".png", ndvi_u8)
    return buf.tobytes()

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/ndvi/single")
async def ndvi_single(nir: UploadFile = File(...), red: UploadFile = File(...), color: int = Form(1)):
    try:
        nir_im = _imread_gray_from_bytes(await nir.read())
        red_im = _imread_gray_from_bytes(await red.read())
        ndvi = compute_ndvi(nir_im, red_im)
        stats = {
            "min": float(np.min(ndvi)),
            "max": float(np.max(ndvi)),
            "mean": float(np.mean(ndvi)),
            "shape": [int(ndvi.shape[0]), int(ndvi.shape[1])],
        }
        png = ndvi_to_png_bytes(ndvi, color=bool(color))
        b64 = base64.b64encode(png).decode("ascii")
        return {"status": "ok", "stats": stats, "ndvi_png_b64": f"data:image/png;base64,{b64}"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

_pair_re = re.compile(r"^(?P<stem>.+?)[-_\.](?P<band>nir|red)$", re.IGNORECASE)
def _key_and_band(filename: str):
    name = os.path.splitext(os.path.basename(filename))[0]
    m = _pair_re.match(name)
    if not m: return None, None
    return m.group("stem").lower(), m.group("band").lower()

@app.post("/api/ndvi/batch")
async def ndvi_batch(files: List[UploadFile] = File(...), color: int = Form(1)):
    """
    Upload a folder using <input webkitdirectory>. Filenames must end with:
      *_nir.*  and  *_red.*   (same stem pairs, e.g., plot1_nir.png & plot1_red.png)
    Returns a ZIP: {<stem>_ndvi.png, ndvi_stats.csv}
    """
    buckets = {}
    for f in files:
        key, band = _key_and_band(f.filename or "")
        if not key or band not in ("nir","red"):
            continue
        buckets.setdefault(key, {})[band] = await f.read()

    if not buckets:
        return JSONResponse(status_code=400, content={"error":"No valid *_nir / *_red pairs found."})

    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip"); tmp_zip.close()
    rows = [("key","width","height","min","max","mean")]
    try:
        with zipfile.ZipFile(tmp_zip.name, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for key, bands in buckets.items():
                if "nir" not in bands or "red" not in bands: 
                    continue
                nir_im = _imread_gray_from_bytes(bands["nir"])
                red_im = _imread_gray_from_bytes(bands["red"])
                ndvi = compute_ndvi(nir_im, red_im)
                h, w = ndvi.shape
                rows.append((key, w, h, float(np.min(ndvi)), float(np.max(ndvi)), float(np.mean(ndvi))))
                zf.writestr(f"{key}_ndvi.png", ndvi_to_png_bytes(ndvi, color=bool(color)))
            # CSV
            with io.StringIO() as sio:
                csv.writer(sio).writerows(rows)
                zf.writestr("ndvi_stats.csv", sio.getvalue())

        def _cleanup(p=tmp_zip.name):
            try: os.remove(p)
            except: pass

        return FileResponse(tmp_zip.name, media_type="application/zip",
                            filename="ndvi_results.zip", background=BackgroundTask(_cleanup))
    except Exception as e:
        try: os.remove(tmp_zip.name)
        except: pass
        return JSONResponse(status_code=500, content={"error": str(e)})

# -------- proxy (pass-through to auto's backend) --------
async def _proxy_json(method: str, path: str, payload=None):
    url = AUTONOMOUS_BASE.rstrip("/") + path
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request(method, url, json=payload)
    # Prefer JSON if provided, otherwise return text
    ctype = r.headers.get("content-type", "")
    if "application/json" in ctype:
        return JSONResponse(status_code=r.status_code, content=r.json())
    return JSONResponse(status_code=r.status_code, content={"text": r.text})

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(str(WEB_DIR / "index.html"))