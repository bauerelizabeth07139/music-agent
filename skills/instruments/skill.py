"""Instrument synthesis skill — v3.2

Key changes from v3.1:
1. Envelope: 0.5s sustain plateau before exponential decay starts
2. Violin vs Cello clearly differentiated:
   - Violin: 10 harmonics, even+odd, fast vibrato 6Hz, bright
   - Cello: 6 harmonics, mostly odd, slow vibrato 4.5Hz, warm body resonance
   - Flute: nearly pure sine, very weak overtones, breath noise dominant
3. Piano uses hammer-hit impulse + fast decay (completely different from bowed strings)
"""

import numpy as np
import soundfile as sf
import os
from typing import Dict, List, Any

SAMPLE_RATE = 44100

NOTE_FREQS: Dict[str, float] = {}
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
for octave in range(0, 9):
    for i, name in enumerate(NOTE_NAMES):
        midi = octave * 12 + i + 12
        freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        NOTE_FREQS[f"{name}{octave}"] = freq
        if name == "C#": NOTE_FREQS[f"Db{octave}"] = freq
        elif name == "D#": NOTE_FREQS[f"Eb{octave}"] = freq
        elif name == "F#": NOTE_FREQS[f"Gb{octave}"] = freq
        elif name == "G#": NOTE_FREQS[f"Ab{octave}"] = freq
        elif name == "A#": NOTE_FREQS[f"Bb{octave}"] = freq

def note_to_freq(note: str) -> float:
    return NOTE_FREQS.get(note, 440.0)

def _amp(velocity: int) -> float:
    return max(0.05, min(1.0, velocity / 127.0))


# ── Envelope: sustain for hold_time, THEN exponential decay ──

def _hold_decay_envelope(t: np.ndarray, duration: float,
                         attack: float = 0.02, hold_time: float = 0.25,
                         decay_rate: float = 5.0) -> np.ndarray:
    """Envelope: attack -> full sustain for hold_time -> e^(-rate*(t-hold)/dur).

    hold_time: seconds of full-amplitude sustain before decay starts
    decay_rate: how fast it dies after hold_time
    
    For a 2s note with hold=0.5, rate=5:
      0.0-0.02s: attack ramp
      0.02-0.5s: full amplitude (sustain plateau)
      0.5-2.0s:  e^(-5*(t-0.5)/1.5) decaying to ~1.5% at note end
    """
    n = len(t)
    env = np.ones(n, dtype=np.float64)

    # Attack phase
    attack_end = int(attack * SAMPLE_RATE)
    if attack_end > 0 and attack_end < n:
        env[:attack_end] = np.linspace(0, 1, attack_end)

    # Decay phase: starts after hold_time
    hold_samples = int(hold_time * SAMPLE_RATE)
    decay_duration = max(duration - hold_time, 0.01)
    for i in range(hold_samples, n):
        dt = (i / SAMPLE_RATE) - hold_time
        env[i] = np.exp(-decay_rate * dt / decay_duration)

    # Ensure attack phase is also <= 1
    env[:attack_end] *= 1.0  # already ramped

    return env


# ── Bowed string harmonics ──

def _bowed_harmonics(freq: float, duration: float, sr: int,
                     n_harmonics: int = 8, odd_weight: float = 0.7,
                     brightness: float = 1.0,
                     vibrato_rate: float = 5.5, vibrato_depth: float = 0.006,
                     vibrato_onset: float = 0.15) -> np.ndarray:
    """Bowed string harmonic generator.

    odd_weight: 0-1, how much to emphasize odd harmonics (1=only odd, 0=equal).
                Cello uses high odd_weight (hollow/warm).
                Violin uses low odd_weight (bright/full).
    """
    n = int(duration * sr)
    t = np.arange(n, dtype=np.float64) / sr

    # Vibrato LFO with delayed onset
    vib = np.zeros(n)
    vs = int(vibrato_onset * sr)
    if vs < n:
        vr = min(int(0.1 * sr), n - vs)
        vib[vs:vs+vr] = np.linspace(0, 1, vr)
        vib[vs+vr:] = 1.0
    vib *= vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t)

    lf = max(np.log(freq), 1.0)
    sig = np.zeros(n, dtype=np.float64)
    for k in range(1, n_harmonics + 1):
        # Base amplitude: 1/k rolloff
        amp = brightness / k
        # Odd/even weighting
        if k % 2 == 0:
            amp *= (1.0 - odd_weight)  # suppress even if odd_weight is high
        # High-frequency rolloff (string stiffness)
        amp /= (1.0 + k * 2.0 / lf)
        freq_k = freq * k
        if freq_k > sr / 2.2:
            break
        sig += amp * np.sin(2 * np.pi * freq_k * (t + vib * t))

    return sig


# ──────────────────────────────────────────────
#  Karplus-Strong
# ──────────────────────────────────────────────

def _karplus_strong(freq, duration, sr, damping=0.996):
    n = int(duration * sr)
    period = max(2, int(sr / freq))
    buf = np.random.randn(period) * np.linspace(1.0, 0.3, period)
    out = np.empty(n, dtype=np.float64)
    for i in range(n):
        idx = i % period
        buf[idx] = damping * 0.5 * (buf[idx] + buf[(idx - 1) % period])
        out[i] = buf[idx]
    t = np.arange(n, dtype=np.float64) / sr
    out *= _hold_decay_envelope(t, duration, attack=0.002, hold_time=0.0, decay_rate=5.0)
    return out


# ──────────────────────────────────────────────
#  Instruments
# ──────────────────────────────────────────────

def synth_piano(freq, duration, velocity, sr=SAMPLE_RATE):
    """Piano: hammer impulse + many harmonics + fast decay (no hold plateau)."""
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)
    lf = max(np.log(freq), 1.0)
    sig = np.zeros(n)
    # Rich harmonics: piano has strong upper partials
    for k in range(1, 12):
        amp = 1.0 / (k ** 0.8)  # slower rolloff than strings
        amp /= (1.0 + k * 1.5 / lf)
        sig += amp * np.sin(2 * np.pi * freq * k * t)
    # Hammer attack: sharp transient
    hammer = np.exp(-t * 80) * 0.5 + 1.0
    # Fast decay: no hold, immediate e^(-5t/dur)
    env = _hold_decay_envelope(t, duration, attack=0.001, hold_time=0.0, decay_rate=5.0)
    return a * sig * hammer * env


def synth_guitar(freq, duration, velocity, sr=SAMPLE_RATE):
    a = _amp(velocity)
    raw = _karplus_strong(freq, duration, sr, damping=0.997)
    d1 = max(1, int(sr / (freq * 2.01)))
    d2 = max(1, int(sr / (freq * 0.99)))
    body = np.zeros_like(raw)
    if d1 < len(raw): body[d1:] += raw[:-d1] * 0.12
    if d2 < len(raw): body[d2:] += raw[:-d2] * 0.08
    out = raw + body
    peak = np.max(np.abs(out))
    if peak > 0: out /= peak
    return a * out


def synth_bass(freq, duration, velocity, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)
    sig = np.sin(2*np.pi*freq*t) + 0.3*np.sin(2*np.pi*freq*0.5*t) + 0.15*np.sin(2*np.pi*freq*2*t)
    return a * sig * _hold_decay_envelope(t, duration, attack=0.01, hold_time=0.1, decay_rate=4.0)


def synth_drums(freq, duration, velocity, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)
    if freq < 70:
        fs = freq*3*np.exp(-8.0*t/max(duration,0.01))
        body = np.sin(2*np.pi*np.cumsum(fs)/sr)*0.8
        noise = np.random.randn(n)*0.3*np.exp(-20.0*t/max(duration,0.01))
        return a*(body+noise)*_hold_decay_envelope(t, duration, attack=0.001, hold_time=0.0, decay_rate=10.0)
    elif freq < 80:
        fs = freq*2*np.exp(-10.0*t/max(duration,0.01))
        body = np.sin(2*np.pi*np.cumsum(fs)/sr)*0.5
        noise = np.random.randn(n)*0.5*np.exp(-12.0*t/max(duration,0.01))
        return a*(body+noise)*_hold_decay_envelope(t, duration, attack=0.001, hold_time=0.0, decay_rate=10.0)
    elif freq < 100:
        return a*np.random.randn(n)*0.6*_hold_decay_envelope(t, duration, attack=0.001, hold_time=0.0, decay_rate=15.0)
    elif freq < 130:
        return a*np.random.randn(n)*0.7*_hold_decay_envelope(t, duration, attack=0.001, hold_time=0.0, decay_rate=4.0)
    else:
        return a*np.random.randn(n)*0.5*_hold_decay_envelope(t, duration, attack=0.001, hold_time=0.0, decay_rate=12.0)


def synth_violin(freq, duration, velocity, sr=SAMPLE_RATE):
    """Violin — bright, full, fast vibrato.

    - 10 harmonics, equal odd/even weighting (bright)
    - Fast vibrato 6Hz, starts at 0.12s
    - Hold 0.5s sustain, then decay rate=6
    - Bow noise layer
    """
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)

    sig = _bowed_harmonics(freq, duration, sr,
                           n_harmonics=10, odd_weight=0.2,   # mostly even+odd = bright
                           brightness=1.3,
                           vibrato_rate=6.0, vibrato_depth=0.007,
                           vibrato_onset=0.12)

    env = _hold_decay_envelope(t, duration, attack=0.05, hold_time=0.15, decay_rate=8.0)
    sig *= env

    # Bow noise (scraping)
    bow = np.random.randn(n) * 0.006
    bow = np.diff(bow, prepend=0.0)
    sig += bow * env

    peak = np.max(np.abs(sig))
    if peak > 0: sig /= peak
    return a * sig


def synth_cello(freq, duration, velocity, sr=SAMPLE_RATE):
    """Cello — warm, hollow, slow vibrato, strong body resonance.

    - 6 harmonics, heavy odd weighting (hollow/warm character)
    - Slow vibrato 4.5Hz, starts at 0.2s
    - Hold 0.5s, then decay rate=5
    - Body comb filter at ~180Hz and ~280Hz
    - More bow noise (heavier bow pressure)
    """
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)

    sig = _bowed_harmonics(freq, duration, sr,
                           n_harmonics=6, odd_weight=0.75,    # mostly odd = hollow/warm
                           brightness=0.9,
                           vibrato_rate=4.5, vibrato_depth=0.010,
                           vibrato_onset=0.20)

    env = _hold_decay_envelope(t, duration, attack=0.07, hold_time=0.15, decay_rate=7.0)
    sig *= env

    # Heavier bow noise
    bow = np.random.randn(n) * 0.010
    bow = np.diff(bow, prepend=0.0)
    sig += bow * env

    # Body resonance: two comb filters simulating cello body cavity
    body = np.zeros(n)
    d1 = max(1, int(sr / 180))   # main body resonance ~180Hz
    d2 = max(1, int(sr / 280))   # secondary ~280Hz
    if d1 < n: body[d1:] += sig[:-d1] * 0.10
    if d2 < n: body[d2:] += sig[:-d2] * 0.06
    sig = sig * 0.84 + body * 0.16

    peak = np.max(np.abs(sig))
    if peak > 0: sig /= peak
    return a * sig


def synth_flute(freq, duration, velocity, sr=SAMPLE_RATE):
    """Flute — nearly pure sine, breathy, gentle vibrato.

    - Only fundamental + very weak 2nd harmonic (flute is almost pure sine)
    - Breath noise is the main texture
    - Gentle vibrato 4.8Hz
    - Hold 0.3s, then gentle decay
    """
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)

    # Vibrato
    vib = np.zeros(n)
    vs = int(0.25 * sr)
    if vs < n:
        vr = min(int(0.15 * sr), n - vs)
        vib[vs:vs+vr] = np.linspace(0, 1, vr)
        vib[vs+vr:] = 1.0
    vib = 1.0 + 0.003 * vib * np.sin(2 * np.pi * 4.8 * t)

    # Almost pure sine — flute's defining characteristic
    sig = np.sin(2 * np.pi * freq * vib * t) * 1.0
    sig += np.sin(2 * np.pi * freq * 2 * vib * t) * 0.04  # very faint 2nd

    # Breath noise: the main texture of a flute
    breath = np.random.randn(n) * 0.035
    # Bandpass around the playing frequency
    ks = max(3, int(sr / freq * 1.5))
    breath = np.convolve(breath, np.ones(ks)/ks, mode='same')[:n]
    # Breath follows note shape
    breath *= (0.2 + 0.8 * np.minimum(t / 0.05, 1.0))

    sig = sig * 0.7 + breath * 0.3

    env = _hold_decay_envelope(t, duration, attack=0.04, hold_time=0.15, decay_rate=7.0)
    sig *= env

    peak = np.max(np.abs(sig))
    if peak > 0: sig /= peak
    return a * sig


def synth_trumpet(freq, duration, velocity, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)
    vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.0 * t)
    sig = (np.sin(2*np.pi*freq*vib*t)*0.55 +
           np.sin(2*np.pi*freq*2*vib*t)*0.25 +
           np.sin(2*np.pi*freq*3*vib*t)*0.12 +
           np.sin(2*np.pi*freq*4*vib*t)*0.06)
    env = _hold_decay_envelope(t, duration, attack=0.03, hold_time=0.3, decay_rate=7.0)
    return a * sig * env


def synth_synth_pad(freq, duration, velocity, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)
    d = 0.003
    sig = (np.sin(2*np.pi*freq*(1+d)*t)*0.4 +
           np.sin(2*np.pi*freq*(1-d)*t)*0.4 +
           np.sin(2*np.pi*freq*2*t)*0.15)
    env = _hold_decay_envelope(t, duration, attack=1.5, hold_time=2.0, decay_rate=3.0)
    return a * sig * env


def synth_synth_lead(freq, duration, velocity, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.arange(n, dtype=np.float64) / sr
    a = _amp(velocity)
    sig = (np.sin(2*np.pi*freq*t)*0.5 +
           np.sin(2*np.pi*freq*2*t)*0.3 +
           np.sin(2*np.pi*freq*3*t)*0.2 +
           np.sign(np.sin(2*np.pi*freq*t))*0.15)
    env = _hold_decay_envelope(t, duration, attack=0.01, hold_time=0.2, decay_rate=7.0)
    return a * sig * env


def synth_hulusi(freq, duration, velocity, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    a = _amp(velocity)
    vib = 1.0 + 0.02 * np.sin(2 * np.pi * 5.0 * t)
    sig = (np.sin(2*np.pi*freq*vib*t)*1.0 +
           np.sin(2*np.pi*freq*2*vib*t)*0.25 +
           np.sin(2*np.pi*freq*3*vib*t)*0.08)
    breath = np.random.randn(n) * 0.04
    breath = np.convolve(breath, np.ones(20)/20, mode='same')
    sig += breath * 0.3
    swell = 0.8 + 0.2 * np.sin(np.pi * t / max(duration, 0.01))
    env = _hold_decay_envelope(t, duration, attack=0.12, hold_time=0.3, decay_rate=5.0)
    return a * sig * env * swell


# ── Synth map ──
SYNTH_MAP = {
    "piano": synth_piano, "guitar": synth_guitar, "bass": synth_bass,
    "drums": synth_drums, "violin": synth_violin, "cello": synth_cello,
    "flute": synth_flute, "trumpet": synth_trumpet,
    "synth_pad": synth_synth_pad, "synth_lead": synth_synth_lead,
    "hulusi": synth_hulusi,
}


def get_instrument_names() -> List[str]:
    return list(SYNTH_MAP.keys())


def render_track(track: Dict[str, Any], bpm: float, sr: int = SAMPLE_RATE) -> np.ndarray:
    instrument = track.get("instrument", "piano")
    synth_fn = SYNTH_MAP.get(instrument, synth_piano)
    notes = track.get("notes", [])
    volume = track.get("volume", 0.8)
    if not notes:
        return np.zeros(sr * 2, dtype=np.float64)

    beats_total = 0.0
    for note in notes:
        end = note["start"] + note["duration"]
        if end > beats_total: beats_total = end
    beats_total += 1.0
    total_samp = int(beats_total * 60.0 / bpm * sr)
    mix = np.zeros(total_samp, dtype=np.float64)

    for note in notes:
        freq = note_to_freq(note["pitch"])
        dur_sec = note["duration"] * 60.0 / bpm
        start_sec = note["start"] * 60.0 / bpm
        vel = note.get("velocity", 80)
        sig = synth_fn(freq, dur_sec, vel, sr)
        s0 = int(start_sec * sr)
        s1 = s0 + len(sig)
        if s0 >= total_samp: continue
        if s1 > total_samp:
            sig = sig[:total_samp - s0]
            s1 = total_samp
        mix[s0:s1] += sig

    peak = np.max(np.abs(mix))
    if peak > 0: mix = mix / peak * 0.9 * volume
    return mix


def render_arrangement(arrangement: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    bpm = arrangement.get("bpm", 120)
    tracks = arrangement.get("tracks", [])
    os.makedirs(output_dir, exist_ok=True)
    result_paths: Dict[str, str] = {}
    for track in tracks:
        tid = track["id"]
        tname = track.get("name", tid)
        role = track.get("role", "instrument")
        if role == "vocal":
            result_paths[tid] = None
            continue
        notes = track.get("notes", [])
        audio = render_track(track, bpm) if notes else np.zeros(SAMPLE_RATE * 2, dtype=np.float64)
        fname = f"{tid}_{tname.replace(' ', '_').replace('/', '_')}.wav"
        fpath = os.path.join(output_dir, fname)
        sf.write(fpath, audio, SAMPLE_RATE)
        result_paths[tid] = fpath
    return result_paths


