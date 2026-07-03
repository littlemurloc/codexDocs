import math
import wave
from pathlib import Path

import numpy as np


SR = 48_000
DURATION = 20.0
N = int(SR * DURATION)
BPM = 84
BEAT = 60 / BPM
ROOT = 73.416  # D2


def add(buf, start, snd, gain=1.0):
    i = int(round(start * SR)) % len(buf)
    snd = snd * gain
    end = i + len(snd)
    if end <= len(buf):
        buf[i:end] += snd
    else:
        k = len(buf) - i
        buf[i:] += snd[:k]
        buf[: end - len(buf)] += snd[k:]


def lp(x, cutoff):
    rc = 1 / (2 * math.pi * cutoff)
    dt = 1 / SR
    a = dt / (rc + dt)
    y = np.empty_like(x)
    s = 0.0
    for i, v in enumerate(x):
        s += a * (v - s)
        y[i] = s
    return y


def hp(x, cutoff):
    return x - lp(x, cutoff)


def env(n, a=0.01, d=0.1, s=0.65, r=0.12):
    e = np.ones(n) * s
    ai = min(n, max(1, int(a * SR)))
    di = min(max(0, n - ai), max(1, int(d * SR)))
    ri = min(n, max(1, int(r * SR)))
    e[:ai] = np.linspace(0, 1, ai)
    if di:
        e[ai : ai + di] = np.linspace(1, s, di)
    e[-ri:] *= np.linspace(1, 0, ri)
    return e


def pan(x, p):
    l = math.cos((p + 1) * math.pi / 4)
    r = math.sin((p + 1) * math.pi / 4)
    return np.column_stack((x * l, x * r))


def note(semi, octave=1):
    return ROOT * octave * (2 ** (semi / 12))


def string_spiccato(freq, sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    phase = 2 * np.pi * freq * t
    y = np.zeros(n)
    for h in range(1, 18):
        y += np.sin(phase * h + 0.03 * h) / (h ** 0.82)
    y /= max(1e-6, np.max(np.abs(y)))
    y = hp(lp(y, 3600), 120)
    y *= env(n, 0.006, 0.035, 0.22, 0.07)
    return y * gain


def string_tremolo(freq, sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.4 * t)
    phase = 2 * np.pi * np.cumsum(freq * vib) / SR
    y = np.zeros(n)
    for h in range(1, 24):
        y += np.sin(phase * h) / (h ** 0.9)
    trem = 0.55 + 0.45 * (np.sin(2 * np.pi * 8 * t) > 0).astype(float)
    y = np.tanh(y * 1.2)
    y = hp(lp(y, 2800), 90)
    y *= trem * env(n, 0.18, 0.25, 0.78, 0.45)
    return y * gain


def brass_stab(freq, sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    bend = 1 + 0.018 * np.exp(-t * 10)
    phase = 2 * np.pi * np.cumsum(freq * bend) / SR
    y = (
        np.sin(phase)
        + 0.8 * np.sin(2 * phase + 0.2)
        + 0.42 * np.sin(3 * phase)
        + 0.24 * np.sin(5 * phase)
    )
    y = np.tanh(y * 1.8)
    y = hp(lp(y, 2500), 80)
    y *= env(n, 0.025, 0.12, 0.55, 0.28)
    return y * gain


def low_drum(sec, freq=64, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 2.3 * np.exp(-t * 26))
    phase = 2 * np.pi * np.cumsum(f) / SR
    rng = np.random.default_rng(912)
    body = np.sin(phase) * np.exp(-t * 4.5)
    skin = lp(rng.normal(0, 1, n), 900) * np.exp(-t * 20)
    thwack = hp(rng.normal(0, 1, n), 1800) * np.exp(-t * 80)
    y = body + 0.32 * skin + 0.16 * thwack
    y /= max(1e-6, np.max(np.abs(y)))
    return y * gain


def war_snare(sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(210)
    y = hp(rng.normal(0, 1, n), 900) * np.exp(-t * 18)
    y += 0.25 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 12)
    y /= max(1e-6, np.max(np.abs(y)))
    return y * gain


def metal_hit(sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(77)
    y = np.zeros(n)
    for f in (410, 590, 910, 1370, 2210, 3180):
        y += np.sin(2 * np.pi * f * t + f * 0.01) / math.sqrt(f / 410)
    y += 0.25 * hp(rng.normal(0, 1, n), 2500)
    y *= np.exp(-t * 3.4)
    y /= max(1e-6, np.max(np.abs(y)))
    return y * gain


def short_reverb(x):
    y = x.copy()
    for sec, g in ((0.041, 0.14), (0.073, 0.11), (0.127, 0.075), (0.191, 0.052)):
        y += np.roll(x, int(sec * SR), axis=0) * g
    for sec, g in ((0.293, 0.035), (0.421, 0.024)):
        y += np.roll(x, int(sec * SR), axis=0) * g
    return y


def master(x):
    x[:, 0] = hp(lp(x[:, 0], 14500), 30)
    x[:, 1] = hp(lp(x[:, 1], 14500), 30)
    # Keep it dark and weighty like a battle cue, not bright trailer music.
    x[:, 0] = lp(x[:, 0], 9200)
    x[:, 1] = lp(x[:, 1], 9200)
    x = np.tanh(x * 1.55)
    x /= max(1e-6, np.max(np.abs(x)))
    return x * 0.94


def main():
    mix = np.zeros((N, 2), dtype=np.float64)

    # 20 seconds at 84 BPM = 28 beats: seven bars of 4/4.
    bass_cells = [0, 0, -2, 0, -5, -5, -2, 0, 3, 3, 0, -2, -5, -2]
    for b in range(28):
        t = b * BEAT
        semi = bass_cells[b % len(bass_cells)]
        add(mix, t, pan(string_spiccato(note(semi, 0.5), BEAT * 0.42, 0.18), -0.22))
        add(mix, t + BEAT * 0.5, pan(string_spiccato(note(semi + 12, 0.5), BEAT * 0.28, 0.075), 0.18))

    pad_plan = [
        (0, [0, 7, 12]),
        (4, [-2, 5, 10]),
        (8, [-5, 2, 7]),
        (12, [0, 3, 10]),
        (16, [3, 10, 15]),
        (20, [-5, 2, 7]),
        (24, [-2, 5, 10]),
    ]
    for beat, chord in pad_plan:
        for i, semi in enumerate(chord):
            add(mix, beat * BEAT, pan(string_tremolo(note(semi, 1), 4 * BEAT, 0.075), -0.55 + i * 0.55))

    # Low brass answers: short, grim, and usable under gameplay.
    for b, semi in ((0, 0), (3, -2), (8, -5), (11, 0), (16, 3), (20, -5), (24, -2), (26, 0)):
        add(mix, b * BEAT, pan(brass_stab(note(semi, 1), BEAT * 1.45, 0.20), -0.08))
        add(mix, b * BEAT + 0.028, pan(brass_stab(note(semi + 7, 1), BEAT * 1.2, 0.10), 0.25))

    # Restrained ethnic/war motif: no showy melody, just a signal-like phrase.
    motif = [12, 10, 7, 10, 5, 7, 3, 0]
    for i, semi in enumerate(motif):
        t = (8 + i * 0.5) * BEAT
        add(mix, t, pan(brass_stab(note(semi, 2), BEAT * 0.55, 0.075), 0.38))
    for i, semi in enumerate([7, 5, 3, 5, 0, -2, 0]):
        t = (20 + i * 0.5) * BEAT
        add(mix, t, pan(brass_stab(note(semi, 2), BEAT * 0.5, 0.065), 0.35))

    # Percussion is the cue's engine: asymmetric but loopable.
    for b in range(28):
        t = b * BEAT
        if b % 4 in (0, 2):
            add(mix, t, pan(low_drum(0.92, 62, 0.55), -0.12))
        if b % 4 == 3:
            add(mix, t + BEAT * 0.64, pan(low_drum(0.42, 92, 0.28), 0.18))
        if b % 2 == 1:
            add(mix, t, pan(war_snare(0.30, 0.16), 0.12))
        if b in (0, 8, 16, 24):
            add(mix, t, pan(metal_hit(1.4, 0.17), -0.32))

    for b in (6, 7, 14, 15, 22, 23, 26, 27):
        for k in range(3):
            add(mix, (b + 0.2 + k * 0.18) * BEAT, pan(war_snare(0.18, 0.10), -0.18 + k * 0.18))

    # Dark battlefield bed, phase aligned over 20 seconds.
    t = np.arange(N) / SR
    bed = (
        0.035 * np.sin(2 * np.pi * 36 * t)
        + 0.022 * np.sin(2 * np.pi * 55 * t)
        + 0.014 * np.sin(2 * np.pi * 73.416 * t)
    )
    bed *= 0.75 + 0.25 * np.sin(2 * np.pi * t / 10) ** 2
    mix += pan(bed, 0.0)

    mix = short_reverb(mix)
    mix = master(mix)

    # Sample-accurate edge blend for clean looping.
    f = int(0.035 * SR)
    a = np.sin(np.linspace(0, math.pi / 2, f))[:, None] ** 2
    head_next = np.vstack((mix[1:f], mix[:1]))
    mix[-f:] = mix[-f:] * (1 - a) + head_next * a
    mix /= max(1e-6, np.max(np.abs(mix)))
    mix *= 0.94

    out = Path("exports")
    out.mkdir(exist_ok=True)
    wav_path = out / "sanguo_battle_loop_20s_yishan_style.wav"
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(wav_path.resolve())


if __name__ == "__main__":
    main()
