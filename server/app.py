"""Music Agent - FastAPI backend server.

Flow (v3):
1. /api/lyrics        — Generate lyrics, return voice options
2. /api/vocal         — Generate vocal TTS FIRST (user picks voice)
3. /api/plan          — Design tracks based on vocal timeline
4. /api/notes         — Generate instrument notes (parallel, aligned to vocal)
5. /api/render/{id}   — Render instruments + mix with vocal
"""

import os, json, uuid, time, asyncio, traceback, re
import logging

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_debug.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Optional, Dict, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import numpy as np
import soundfile as sf

from config import get_config, set_config, PRESETS
from llm_client import (
    generate_lyrics, generate_track_plan, generate_track_notes,
    synthesize_voice, synthesize_voice_segments, clone_voice,
    TTS_STYLE_PROMPTS, VOICE_CATALOG, AVAILABLE_INSTRUMENTS, STYLE_KNOWLEDGE
)
from skill_loader import get_skill_by_type, list_skill_summaries
import importlib.util
spec = importlib.util.spec_from_file_location("music_search_skill", str((Path(__file__).resolve().parent.parent / "skills" / "music-search" / "skill.py")))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_offline_refs = mod._offline

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio_out"
UPLOAD_DIR = BASE_DIR / "uploads"
FRONTEND_DIR = BASE_DIR.parent / "dist"
SAMPLE_RATE = 44100

app = FastAPI(title="Music Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _rj(p):
    with open(p, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def _wj(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# ---------- Request models ----------
class ConfigUpdate(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    provider_format: Optional[str] = None
    model: Optional[str] = None
    tts_model: Optional[str] = None
    default_voice: Optional[str] = None

class LyricsRequest(BaseModel):
    prompt: str
    style: Optional[str] = None

class VocalRequest(BaseModel):
    job_id: str
    lyrics: str
    voice: str = "冰糖"

class PlanRequest(BaseModel):
    job_id: str
    lyrics: str
    style: Optional[str] = None
    tracks: list = []
    bpm: Optional[int] = None
    time_signature: Optional[str] = None
    key: Optional[str] = None

class NotesRequest(BaseModel):
    job_id: str
    lyrics: str
    style: Optional[str] = None

class SynthRequest(BaseModel):
    text: str
    voice: str = "mimo_default"
    style: str = ""

class SearchRequest(BaseModel):
    query: str


# ---------- Skill helpers ----------
def _render_instruments(arr, out):
    s = get_skill_by_type("audio.render")
    if not s:
        raise RuntimeError("audio.render skill not found")
    return s.module.render_arrangement(arr, out)

def _get_inst_names():
    s = get_skill_by_type("audio.render")
    return s.module.get_instrument_names() if s else AVAILABLE_INSTRUMENTS

async def _search(q):
    s = get_skill_by_type("web.search")
    if not s:
        raise RuntimeError("web.search skill not found")
    return await s.module.search_music_info(q)

async def _refs(prompt, style="", key="C"):
    s = get_skill_by_type("web.search")
    if not s:
        return {"results": [], "count": 0, "source": "offline"}
    return await s.module.gather_references_for_prompt(prompt, style, key)


# ────────────────────────────────────────────
#  Vocal generation with gap-aware timing
# ────────────────────────────────────────────

def _split_lyrics_with_gaps(lyrics: str, gap_spaces: int = 8) -> str:
    """Insert spaces between lyric phrases for TTS breathing gaps.
    
    TTS will naturally pause on spaces. We add multiple spaces between
    phrases (after punctuation) to create measurable silence gaps.
    """
    # Split at natural phrase boundaries
    phrases = re.split(r'([。！？；\n])', lyrics)
    result = []
    gap = " " * gap_spaces
    for i, p in enumerate(phrases):
        p = p.strip()
        if not p:
            continue
        result.append(p)
        # Add gap after punctuation or between phrases
        if i < len(phrases) - 1:
            result.append(gap)
    return " ".join(result)


async def _generate_vocal_track(lyrics: str, voice: str, job_dir: Path) -> dict:
    """Generate vocal track via TTS. Returns timing metadata.
    
    Strategy: insert spaces between phrases so TTS produces natural pauses.
    The resulting audio has both singing and silence segments.
    We return the audio file path and approximate timing info.
    """
    # Add gaps between phrases
    tts_text = _split_lyrics_with_gaps(lyrics, gap_spaces=10)
    logger.info(f"[Vocal] Generating vocal: voice={voice}, text_len={len(tts_text)}")

    # Determine singing style
    if voice in ("白桦", "Milo", "Dean"):
        tts_style = "用深情款款的男歌手方式演唱，匀速稳定"
    else:
        tts_style = "用甜美动人的女歌手方式演唱，匀速稳定"

    try:
        # Split into segments <= 1024 chars
        segments = []
        text = tts_text.strip()
        while text:
            if len(text) <= 1024:
                segments.append(text)
                break
            best = 1024
            for sep in ["。", "！", "？", "；", "\n", "，", ".", "!", "?", "、", " "]:
                p = text.rfind(sep, 0, 1024)
                if p > 256:
                    best = p + 1
                    break
            segments.append(text[:best])
            text = text[best:].lstrip()

        all_audio = []
        for i, seg in enumerate(segments):
            if not seg.strip():
                continue
            logger.info(f"[Vocal] Segment {i+1}/{len(segments)}: {len(seg)} chars")
            audio_bytes = await synthesize_voice(seg, voice, tts_style)
            all_audio.append(audio_bytes)
            logger.info(f"[Vocal] Segment {i+1}: {len(audio_bytes)} bytes")

        if not all_audio:
            raise ValueError("No audio generated")

        # Concatenate all segments (raw bytes = WAV)
        combined = b"".join(all_audio)
        
        # Read the concatenated audio
        import tempfile, io
        tmp = io.BytesIO(combined)
        data, sr = sf.read(tmp, dtype='float64')
        if data.ndim == 2:
            data = data.mean(axis=1)
        
        # Add intro silence (8s) and outro silence (6s)
        intro_silence = int(8.0 * sr)
        outro_silence = int(6.0 * sr)
        data = np.concatenate([
            np.zeros(intro_silence, dtype=np.float64),
            data,
            np.zeros(outro_silence, dtype=np.float64),
        ])
        
        # Save the padded vocal
        vocal_path = job_dir / "vocal_raw.wav"
        sf.write(str(vocal_path), data, sr)
        duration_sec = len(data) / sr
        logger.info(f"[Vocal] Padded: intro=8s + singing + outro=6s = {duration_sec:.1f}s")
        logger.info(f"[Vocal] Done: {duration_sec:.1f}s, {len(data)} samples")

        return {
            "path": str(vocal_path),
            "duration_sec": duration_sec,
            "samples": len(data),
            "sample_rate": sr,
            "voice": voice,
        }
    except Exception as e:
        logger.error(f"[Vocal] Failed: {e}")
        logger.error(traceback.format_exc())
        raise


# ────────────────────────────────────────────
#  Master mix & multitrack
# ────────────────────────────────────────────

def _master_mix(track_paths: Dict[str, str], arrangement: dict, job_dir: Path):
    """Mix all rendered tracks into master_mix.wav and multitrack.wav."""
    ordered_ids = []
    track_audio = {}
    max_len = 0

    for tid, fpath in track_paths.items():
        if fpath and os.path.exists(fpath):
            try:
                data, sr = sf.read(fpath, dtype='float64')
                if data.ndim == 2:
                    data = data.mean(axis=1)
                # Resample to SAMPLE_RATE if needed (e.g. TTS returns 24000Hz)
                if sr != SAMPLE_RATE and len(data) > 0:
                    new_len = int(len(data) * SAMPLE_RATE / sr)
                    if new_len > 1:
                        x_old = np.linspace(0, 1, len(data))
                        x_new = np.linspace(0, 1, new_len)
                        data = np.interp(x_new, x_old, data)
                        logger.info(f"[Mix] Resampled {tid}: {sr}Hz -> {SAMPLE_RATE}Hz")
                track_audio[tid] = data
                ordered_ids.append(tid)
                if len(data) > max_len:
                    max_len = len(data)
                logger.info(f"[Mix] {tid}: {len(data)} samples ({len(data)/SAMPLE_RATE:.1f}s)")
            except Exception as e:
                logger.error(f"[Mix] Failed to read {tid}: {e}")

    if not track_audio:
        logger.warning("[Mix] No audio tracks to mix")
        return

    # Master stereo mix with per-track gain staging
    # Vocal gets -3dB reduction to sit in the mix without dominating
    mix = np.zeros(max_len, dtype=np.float64)
    for tid in ordered_ids:
        audio = track_audio[tid]
        if len(audio) < max_len:
            audio = np.pad(audio, (0, max_len - len(audio)))
        # Per-track gain: vocal reduced to sit in mix
        gain = 0.6 if "vocal" in tid.lower() else 1.0
        mix += audio * gain

    # Normalize (no tanh — just clean peak normalize)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix = mix / peak * 0.92
    sf.write(str(job_dir / "master_mix.wav"), mix, SAMPLE_RATE)
    logger.info(f"[Mix] Master: {len(mix)/SAMPLE_RATE:.1f}s")

    # Multi-track WAV (N channels)
    channels = []
    for tid in ordered_ids:
        audio = track_audio[tid].copy()
        if len(audio) < max_len:
            audio = np.pad(audio, (0, max_len - len(audio)))
        pk = np.max(np.abs(audio))
        if pk > 0:
            audio = audio / pk * 0.9
        channels.append(audio)

    multi = np.column_stack(channels)
    sf.write(str(job_dir / "multitrack.wav"), multi, SAMPLE_RATE, subtype='PCM_16')
    logger.info(f"[Mix] Multitrack: {len(ordered_ids)} channels, {len(multi)/SAMPLE_RATE:.1f}s")


# ────────────────────────────────────────────
#  Render: instruments + vocal merge
# ────────────────────────────────────────────

async def _render_all(arrangement: dict, job_dir: Path) -> Dict[str, str]:
    """Render instrument tracks via skill. Vocal is already pre-rendered."""
    tracks = arrangement.get("tracks", [])
    track_paths = {}

    vocal_tracks = [t for t in tracks if t.get("role") == "vocal"]
    inst_tracks = [t for t in tracks if t.get("role") != "vocal"]

    # Check for pre-rendered vocal
    vocal_path = job_dir / "vocal_raw.wav"
    for t in vocal_tracks:
        if vocal_path.exists():
            # Rename to proper track file
            tid = t["id"]
            name = t.get("name", tid).replace(" ", "_").replace("/", "_")
            dest = job_dir / f"{tid}_{name}.wav"
            import shutil
            shutil.copy2(str(vocal_path), str(dest))
            track_paths[tid] = str(dest)
            logger.info(f"[Render] Vocal {tid} from pre-rendered: {dest}")

    # Render instruments via skill
    if inst_tracks:
        inst_arr = {**arrangement, "tracks": inst_tracks}
        try:
            loop = asyncio.get_event_loop()
            inst_result = await loop.run_in_executor(None, _render_instruments, inst_arr, str(job_dir))
            track_paths.update(inst_result)
            logger.info(f"[Render] Instruments: {list(inst_result.keys())}")
        except Exception as e:
            logger.error(f"[Render] Instruments failed: {e}")
            logger.error(traceback.format_exc())

    return track_paths


# ────────────────────────────────────────────
#  API Routes
# ────────────────────────────────────────────

@app.get("/api/config")
async def get_current_config():
    cfg = get_config()
    return {
        "base_url": cfg.base_url,
        "api_key": cfg.api_key[:8] + "***" if cfg.api_key else "",
        "provider_format": cfg.provider_format,
        "model": cfg.model,
        "tts_model": cfg.tts_model,
        "default_voice": cfg.default_voice,
        "presets": PRESETS,
    }

@app.post("/api/config")
async def update_config(req: ConfigUpdate):
    return set_config(**{k: v for k, v in req.model_dump().items() if v is not None})

@app.post("/api/lyrics")
async def create_lyrics(req: LyricsRequest):
    """Step 1: Generate lyrics."""
    jid = str(uuid.uuid4())[:8]
    jd = AUDIO_DIR / jid
    os.makedirs(jd, exist_ok=True)
    try:
        refs = await _refs(req.prompt, req.style or "")
        lyrics = await generate_lyrics(req.prompt)
    except Exception as e:
        raise HTTPException(502, f"Lyrics generation failed: {e}")
    _wj(jd / "lyrics.json", lyrics)
    return {"job_id": jid, "lyrics": lyrics, "references": refs}

@app.post("/api/vocal")
async def create_vocal(req: VocalRequest):
    """Step 2: Generate vocal TTS (user picks voice after seeing lyrics)."""
    jd = AUDIO_DIR / req.job_id
    os.makedirs(jd, exist_ok=True)
    try:
        vocal_info = await _generate_vocal_track(req.lyrics, req.voice, jd)
    except Exception as e:
        raise HTTPException(502, f"Vocal generation failed: {e}")
    _wj(jd / "vocal_info.json", vocal_info)
    return {"job_id": req.job_id, "vocal": vocal_info}

@app.post("/api/plan")
async def create_plan(req: PlanRequest):
    """Step 3: Design track structure based on vocal timeline."""
    jd = AUDIO_DIR / req.job_id
    os.makedirs(jd, exist_ok=True)

    # Load vocal info if available
    vocal_info = {}
    vip = jd / "vocal_info.json"
    if vip.exists():
        vocal_info = _rj(vip)

    try:
        local_refs = _offline_refs(req.lyrics[:200], req.style or "")
        try:
            refs = await _refs(req.lyrics[:200], req.style or "")
        except Exception:
            refs = local_refs
        plan = await generate_track_plan(
            req.lyrics, req.tracks, req.style or "", refs,
            req.bpm, req.time_signature, req.key,
            vocal_duration=vocal_info.get("duration_sec"),
        )
    except Exception as e:
        raise HTTPException(502, f"Plan generation failed: {e}")

    _wj(jd / "plan.json", plan)
    return {"job_id": req.job_id, "arrangement": plan, "references": refs}

@app.post("/api/notes")
async def create_notes(req: NotesRequest):
    """Step 4: Generate note sequences for all instrument tracks."""
    jd = AUDIO_DIR / req.job_id
    if not (jd / "plan.json").exists():
        raise HTTPException(404, "Plan not found.")
    plan = _rj(jd / "plan.json")
    try:
        full = await generate_track_notes(req.lyrics, plan, req.style or "")
    except Exception as e:
        raise HTTPException(502, f"Notes generation failed: {e}")
    _wj(jd / "arrangement.json", full)
    return {"job_id": req.job_id, "arrangement": full}

@app.post("/api/render/{job_id}")
async def render_tracks(job_id: str):
    """Step 5: Render instruments + mix with pre-rendered vocal."""
    jd = AUDIO_DIR / job_id
    if not (jd / "arrangement.json").exists():
        raise HTTPException(404, "Arrangement not found.")
    arr = _rj(jd / "arrangement.json")
    try:
        tp = await _render_all(arr, jd)
    except Exception as e:
        raise HTTPException(500, f"Render failed: {e}")

    _master_mix(tp, arr, jd)

    ti = []
    for t in arr.get("tracks", []):
        tid = t["id"]
        fp = tp.get(tid)
        if fp and os.path.exists(fp):
            ti.append({
                "id": tid,
                "name": t.get("name", tid),
                "role": t.get("role"),
                "instrument": t.get("instrument", ""),
                "voice": t.get("voice", ""),
                "channel": t.get("channel", 0),
                "part": t.get("part", ""),
                "volume": t.get("volume", 0.8),
                "note_count": t.get("note_count"),
                "audio_url": f"/api/audio/{job_id}/{os.path.basename(fp)}"
            })

    master_fp = jd / "master_mix.wav"
    multi_fp = jd / "multitrack.wav"
    return {
        "job_id": job_id,
        "tracks": ti,
        "master_url": f"/api/audio/{job_id}/master_mix.wav" if master_fp.exists() else None,
        "multitrack_url": f"/api/audio/{job_id}/multitrack.wav" if multi_fp.exists() else None,
        "arrangement": arr
    }

@app.get("/api/voices")
async def list_voices():
    return {"voices": [{"id": k, "label": v[0], "description": v[1]} for k, v in VOICE_CATALOG.items()]}

@app.get("/api/instruments")
async def list_instruments():
    return {"instruments": _get_inst_names()}

@app.get("/api/styles")
async def list_styles():
    return {"styles": {k: {"label": k, **v} for k, v in STYLE_KNOWLEDGE.items()}}

@app.get("/api/arrangement/{job_id}")
async def get_arrangement(job_id: str):
    p = AUDIO_DIR / job_id / "arrangement.json"
    if not p.exists():
        raise HTTPException(404, "Not found")
    return _rj(p)

@app.get("/api/audio/{job_id}/{filename}")
async def serve_audio(job_id: str, filename: str):
    fp = AUDIO_DIR / job_id / filename
    if not fp.exists():
        raise HTTPException(404, "Audio file not found")
    return FileResponse(str(fp), media_type="audio/wav")

@app.post("/api/synth")
async def voice_synthesis(req: SynthRequest):
    jid = str(uuid.uuid4())[:8]
    try:
        ab = await synthesize_voice(req.text, req.voice, req.style)
    except Exception as e:
        raise HTTPException(502, f"TTS failed: {e}")
    od = AUDIO_DIR / "voice"
    os.makedirs(od, exist_ok=True)
    fp = od / f"{jid}.wav"
    with open(fp, "wb") as f:
        f.write(ab)
    return {"job_id": jid, "audio_url": f"/api/audio/voice/{jid}.wav"}

@app.post("/api/clone")
async def voice_clone(text: str = Form(...), file: UploadFile = File(...)):
    ab = await file.read()
    jid = str(uuid.uuid4())[:8]
    try:
        rb = await clone_voice(ab, text, file.filename or "sample.wav")
    except Exception as e:
        raise HTTPException(502, f"Clone failed: {e}")
    od = AUDIO_DIR / "clone"
    os.makedirs(od, exist_ok=True)
    fp = od / f"{jid}.wav"
    with open(fp, "wb") as f:
        f.write(rb)
    return {"job_id": jid, "audio_url": f"/api/audio/clone/{jid}.wav"}

@app.post("/api/search")
async def search_music(req: SearchRequest):
    try:
        return await _search(req.query)
    except Exception as e:
        raise HTTPException(502, f"Search failed: {e}")

@app.get("/api/skills")
async def list_skills():
    return {"skills": list_skill_summaries(), "instruments": _get_inst_names()}

@app.post("/api/arrange")
async def compat_arrange(req: PlanRequest):
    return await create_plan(req)

@app.post("/api/render")
async def compat_render(body: dict):
    job_id = body.get("job_id")
    if not job_id:
        raise HTTPException(400, "job_id is required")
    return await render_tracks(job_id)

@app.get("/api/presets")
async def compat_presets():
    return {"presets": PRESETS}

@app.get("/api/health")
async def health():
    return {"status": "ok", "time": time.time()}

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")



