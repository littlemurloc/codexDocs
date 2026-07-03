import math
import wave
from pathlib import Path

import numpy as np


SR = 44_100
DURATION = 20.0
BPM = 96
BEATS = int(DURATION / 60 * BPM)
ROOT = 55.0  # A1


def env_exp(t, decay):
    return np.exp(-t * decay)


def add(buf, start, sound):
    start_i = int(start * SR)
    end_i = min(len(buf), start_i + len(sound))
    if end_i > start_i:
        buf[start_i:end_i] += sound[: end_i - start_i]


def tone(freq, seconds, amp=1.0, harmonics=None, attack=0.01, release=0.08):
    n = max(1, int(seconds * SR))
    t = np.arange(n) / SR
    harmonics = harmonics or [(1, 1.0)]
    y = np.zeros(n, dtype=np.float64)
    for mul, gain in harmonics:
        y += gain * np.sin(2 * np.pi * freq * mul * t)
    y /= max(1e-6, sum(abs(g) for _, g in harmonics))
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] *= np.linspace(1, 0, r)
    return amp * y * env


def drum(seconds, base_freq, amp, decay, noise=0.0):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    sweep = base_freq * (1 + 2.5 * np.exp(-t * 25))
    phase = 2 * np.pi * np.cumsum(sweep) / SR
    y = np.sin(phase) * env_exp(t, decay)
    if noise:
        rng = np.random.default_rng(1307)
        y += noise * rng.normal(0, 1, n) * env_exp(t, decay * 1.3)
    return amp * y


def metallic(seconds, freqs, amp, decay):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for i, f in enumerate(freqs):
        y += np.sin(2 * np.pi * f * t + i * 0.71) * (0.7 / (i + 1))
    y *= env_exp(t, decay)
    rng = np.random.default_rng(190)
    y += 0.2 * rng.normal(0, 1, n) * env_exp(t, decay * 0.9)
    y /= max(1e-6, np.max(np.abs(y)))
    return amp * y


def pan(sound, pos):
    left = math.cos((pos + 1) * math.pi / 4)
    right = math.sin((pos + 1) * math.pi / 4)
    return np.column_stack((sound * left, sound * right))


def limiter(x):
    x = np.tanh(x * 1.25)
    peak = np.max(np.abs(x))
    if peak > 0:
        x = x / peak * 0.92
    return x


def main():
    length = int(DURATION * SR)
    mix = np.zeros((length, 2), dtype=np.float64)
    beat = 60.0 / BPM

    scale = [0, 3, 5, 7, 10]  # minor pentatonic
    bass_pattern = [0, 0, 7, 0, 10, 7, 5, 7]
    lead_pattern = [12, 10, 7, 10, 15, 12, 10, 7, 5, 7, 10, 12, 10, 7, 5, 3]

    for b in range(BEATS):
        t = b * beat

        if b % 4 in (0, 2):
            add(mix, t, pan(drum(0.55, 70, 0.78, 8.0, 0.05), 0.0))
        if b % 4 in (1, 3):
            add(mix, t, pan(drum(0.22, 170, 0.25, 18.0, 0.55), 0.0))

        if b % 2 == 0:
            add(mix, t + beat * 0.48, pan(metallic(0.35, [510, 760, 1180, 1520], 0.20, 7.5), 0.45))

        if b % 8 == 0:
            add(mix, t, pan(metallic(1.1, [140, 216, 320, 492], 0.42, 2.4), -0.2))

        degree = bass_pattern[b % len(bass_pattern)]
        f = ROOT * (2 ** (degree / 12))
        bass = tone(
            f,
            beat * 0.92,
            0.36,
            harmonics=[(1, 1), (2, 0.55), (3, 0.22)],
            attack=0.006,
            release=0.05,
        )
        add(mix, t, pan(bass, -0.05))

    for step in range(BEATS * 2):
        t = step * beat / 2
        deg = lead_pattern[step % len(lead_pattern)]
        f = ROOT * 4 * (2 ** (deg / 12))
        phrase_amp = 0.17 if step % 8 else 0.24
        lead = tone(
            f,
            beat * 0.42,
            phrase_amp,
            harmonics=[(1, 1.0), (2, 0.35), (3, 0.18), (5, 0.08)],
            attack=0.012,
            release=0.12,
        )
        add(mix, t, pan(lead, 0.22))

    for eighth in range(BEATS * 2):
        t = eighth * beat / 2
        hat = metallic(0.12, [3100, 4150, 5730, 6900], 0.055 if eighth % 2 else 0.08, 32.0)
        add(mix, t, pan(hat, 0.65))

    # Layer a sustained war-horn drone with the same phase at the loop boundary.
    t = np.arange(length) / SR
    drone = (
        np.sin(2 * np.pi * ROOT * t)
        + 0.45 * np.sin(2 * np.pi * ROOT * 1.5 * t)
        + 0.25 * np.sin(2 * np.pi * ROOT * 2 * t)
    )
    drone *= 0.06 * (0.65 + 0.35 * np.sin(2 * np.pi * t / 5) ** 2)
    mix += pan(drone, -0.35)

    # Tiny equal-power crossfade makes the final sample meet the first cleanly.
    fade = int(0.08 * SR)
    a = np.linspace(0, 1, fade)[:, None]
    mix[:fade] = mix[:fade] * a + mix[-fade:] * (1 - a)
    mix[-fade:] = mix[-fade:] * (1 - a) + mix[:fade] * a

    mix = limiter(mix)
    pcm = (mix * 32767).astype(np.int16)

    out_dir = Path("exports")
    out_dir.mkdir(exist_ok=True)
    wav_path = out_dir / "sanguo_battle_loop_20s.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())

    print(wav_path.resolve())


if __name__ == "__main__":
    main()
