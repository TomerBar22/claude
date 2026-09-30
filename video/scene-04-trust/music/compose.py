"""Original background track for the 14s vertical ad (royalty-free: synthesized here).

96 BPM, so one bar = 2.5s and every cut in vertical.html lands on a downbeat:
  bar 0   0.0-2.5   intro      pad + piano-ish arpeggio, no drums
  bar 1-3 2.5-10    photos     drums, bass and plucks come in
  bar 4   10.0-12.5 offer      riser into an impact at 10.0, full groove
  bar 5   12.5-14   ending     G for a beat, final D rings out

Usage: python3 compose.py  ->  music/track.wav (44.1kHz stereo, pre-master)
Needs numpy. render.mjs masters and muxes it into the MP4.
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM            # 0.625s
BAR = 4 * BEAT             # 2.5s
LENGTH = 14.0
N = int(SR * LENGTH)
rng = np.random.default_rng(7)

def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)

# D major: D - A - Bm - G, then D for the offer, G -> D to close (at 13.125s).
CHORDS = [
    [62, 66, 69],   # D
    [61, 64, 69],   # A (voice-led)
    [62, 66, 71],   # Bm
    [62, 67, 71],   # G
    [62, 66, 69],   # D   (offer)
    [62, 67, 71],   # G -> resolves to D at 13.0s
]
ROOTS = [38, 45, 47, 43, 38, 43]

L = np.zeros(N)
R = np.zeros(N)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(pan, 0))
    R[i:i + len(sig)] += sig * gain * (1 + min(pan, 0))

def t_(dur):
    return np.arange(int(dur * SR)) / SR

def env_adsr(n, a, d, s, r, sr=SR):
    a, d, r = (min(int(x * sr), n) for x in (a, d, r))
    d = min(d, n - a)
    e = np.full(n, s, dtype=float)
    e[:a] = np.linspace(0, 1, a, endpoint=False)
    e[a:a + d] = np.linspace(1, s, d, endpoint=False)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e

def soft_saw(f, t, harmonics=7):
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harmonics + 1))

def lowpass(x, alpha):
    """One-pole low-pass; alpha in (0,1], smaller = darker."""
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += alpha * (v - acc)
        y[i] = acc
    return y

# ---------- pad (whole piece) ----------
def pad(chord, dur):
    t = t_(dur)
    out_l = np.zeros_like(t)
    out_r = np.zeros_like(t)
    for m in chord + [chord[0] - 12]:
        f = hz(m)
        out_l += soft_saw(f * 0.998, t, 5)
        out_r += soft_saw(f * 1.002, t, 5)
    e = env_adsr(len(t), 0.35, 0.3, 0.8, 0.35)
    return out_l * e, out_r * e

for bar, chord in enumerate(CHORDS):
    start = bar * BAR
    dur = min(BAR + 0.35, LENGTH - start)
    if bar == 5:
        # G for one beat, then the final D rings out to the end
        pl, pr = pad(chord, BEAT + 0.3)
        add(pl, start, 0.035, -0.3); add(pr, start, 0.035, 0.3)
        tail = LENGTH - (start + BEAT)
        pl, pr = pad(CHORDS[0], tail)
        add(pl, start + BEAT, 0.04, -0.3); add(pr, start + BEAT, 0.04, 0.3)
        continue
    pl, pr = pad(chord, dur)
    add(pl, start, 0.035, -0.3)
    add(pr, start, 0.035, 0.3)

# ---------- pluck arpeggio (8th notes) ----------
def pluck(f, dur=0.6):
    # Karplus-Strong
    n = int(dur * SR)
    period = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, period)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.5 * (buf[i % period] + buf[(i + 1) % period]) * 0.996
    return lowpass(out, 0.5)

PATTERN = [0, 1, 2, 3, 2, 1, 2, 3]  # indices into chord+octave
for bar, chord in enumerate(CHORDS[:5]):
    tones = [m + 12 for m in chord] + [chord[0] + 24]
    for step, idx in enumerate(PATTERN):
        when = bar * BAR + step * BEAT / 2
        gain = 0.10 if bar == 0 else 0.085
        add(pluck(hz(tones[idx])), when, gain, pan=0.35 if step % 2 else -0.35)

# ---------- drums (bars 1-4, plus a last hit) ----------
def kick():
    t = t_(0.35)
    f = 45 + 75 * np.exp(-t * 28)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 9)

def clap():
    t = t_(0.25)
    n = rng.uniform(-1, 1, len(t))
    n = np.diff(n, prepend=0)          # crude high-pass
    e = np.exp(-t * 22)
    e[: int(0.012 * SR)] *= 0.6
    return n * e

def shaker():
    t = t_(0.06)
    n = np.diff(np.diff(rng.uniform(-1, 1, len(t)), prepend=0), prepend=0)
    return n * np.exp(-t * 70)

for bar in range(1, 5):
    for beat in range(4):
        when = bar * BAR + beat * BEAT
        add(kick(), when, 0.38)
        if beat in (1, 3):
            add(clap(), when, 0.16, 0.1)
        for sub in (0.5, 0.75) if bar < 4 else (0.25, 0.5, 0.75):
            add(shaker(), when + sub * BEAT, 0.05, -0.4 + 0.8 * (sub == 0.75))
add(kick(), 5 * BAR, 0.38)
add(kick(), 5 * BAR + BEAT, 0.34)

# ---------- bass (bars 1-5) ----------
def bass(f, dur):
    t = t_(dur)
    s = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)
    return s * env_adsr(len(t), 0.01, 0.12, 0.65, 0.08)

for bar in range(1, 6):
    root = ROOTS[bar]
    for beat in range(4):
        r = root
        if bar == 5 and beat >= 1:
            r = ROOTS[0]
        add(bass(hz(r), BEAT * 0.9), bar * BAR + beat * BEAT, 0.16)

# ---------- riser into the offer, impact on 10.0 ----------
rise_start, rise_end = 4 * BAR - 1.25, 4 * BAR
t = t_(rise_end - rise_start)
x = t / t[-1]
noise = rng.uniform(-1, 1, len(t))
bright = noise - lowpass(noise, 0.3)   # airy band
sweep = np.sin(2 * np.pi * np.cumsum(300 + 1500 * x ** 2) / SR)
add((bright * 0.6 + sweep * 0.25) * x ** 2.2, rise_start, 0.18)

t = t_(1.6)
boom = np.sin(2 * np.pi * np.cumsum(35 + 60 * np.exp(-t * 12)) / SR) * np.exp(-t * 3.5)
def crash():
    return np.diff(rng.uniform(-1, 1, len(t)), prepend=0) * np.exp(-t * 3)

add(boom, 4 * BAR, 0.5)
add(crash(), 4 * BAR, 0.10, -0.6)   # two noise bursts, one per side, for width
add(crash(), 4 * BAR, 0.10, 0.6)

# ---------- pumping (side-chain feel) on pad/plucks under the kick ----------
pump = np.ones(N)
for bar in range(1, 5):
    for beat in range(4):
        i = int((bar * BAR + beat * BEAT) * SR)
        k = int(0.22 * SR)
        seg = 1 - 0.35 * np.exp(-np.arange(k) / (0.06 * SR))
        pump[i:i + k] = np.minimum(pump[i:i + k], seg[: max(0, min(k, N - i))])
L *= pump
R *= pump

# ---------- fades + write ----------
fade_in = int(0.03 * SR)
fade_out = int(0.9 * SR)
for ch in (L, R):
    ch[:fade_in] *= np.linspace(0, 1, fade_in)
    ch[-fade_out:] *= np.linspace(1, 0, fade_out) ** 1.5

mix = np.stack([L, R], axis=1)
mix /= np.max(np.abs(mix)) / 0.9
pcm = (mix * 32767).astype(np.int16)

out = Path(__file__).with_name("track.wav")
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", out)
