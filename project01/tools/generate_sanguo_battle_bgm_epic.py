import math
import wave
from pathlib import Path

import numpy as np


SR = 48_000
DURATION = 20.0
BPM = 96
ROOT = 73.416  # D2
N = int(SR * DURATION)


def midi(root, semis):
    return root * (2 ** (semis / 12))


def add(buf, start, sound, gain=1.0):
    i = int(round(start * SR)) % len(buf)
    sound = sound * gain
    end = i + len(sound)
    if end <= len(buf):
        buf[i:end] += sound
    else:
        k = len(buf) - i
        buf[i:] += sound[:k]
        buf[: end - len(buf)] += sound[k:]


def adsr(n, a=0.02, d=0.08, s=0.7, r=0.12):
    env = np.ones(n) * s
    ai = max(1, int(a * SR))
    di = max(1, int(d * SR))
    ri = max(1, int(r * SR))
    env[:ai] = np.linspace(0, 1, ai)
    env[ai : ai + di] = np.linspace(1, s, min(di, max(0, n - ai)))
    env[-ri:] *= np.linspace(1, 0, ri)
    return env


def onepole_lowpass(x, cutoff):
    rc = 1.0 / (2 * math.pi * cutoff)
    dt = 1.0 / SR
    a = dt / (rc + dt)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def onepole_highpass(x, cutoff):
    return x - onepole_lowpass(x, cutoff)


def stereo(mono, pan=0.0):
    l = math.cos((pan + 1) * math.pi / 4)
    r = math.sin((pan + 1) * math.pi / 4)
    return np.column_stack((mono * l, mono * r))


def detuned_saw(freq, sec, harmonics=18, detune=0.004, gain=1.0, cutoff=2600, vib=0.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for d in (-detune, 0, detune):
        phase = 2 * np.pi * freq * (1 + d) * t + vib * np.sin(2 * np.pi * 5.1 * t)
        for h in range(1, harmonics + 1):
            y += np.sin(phase * h) / h
    y /= max(1e-6, np.max(np.abs(y)))
    y = onepole_lowpass(y, cutoff)
    return y * gain


def brass(freq, sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    bend = 1 + 0.012 * np.exp(-t * 7)
    phase = 2 * np.pi * np.cumsum(freq * bend) / SR
    y = (
        1.0 * np.sin(phase)
        + 0.72 * np.sin(2 * phase + 0.18)
        + 0.46 * np.sin(3 * phase)
        + 0.22 * np.sin(5 * phase)
        + 0.10 * np.sin(7 * phase)
    )
    y /= np.max(np.abs(y))
    y = np.tanh(y * 1.8)
    y = onepole_lowpass(y, 3100)
    y *= adsr(n, 0.09, 0.18, 0.82, 0.35)
    return y * gain


def bowed_lead(freqs, sec, gain=1.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    points = np.linspace(0, n - 1, len(freqs))
    freq = np.interp(np.arange(n), points, freqs)
    vib = 1 + 0.008 * np.sin(2 * np.pi * 5.7 * t)
    phase = 2 * np.pi * np.cumsum(freq * vib) / SR
    y = np.sin(phase) + 0.38 * np.sin(2 * phase + 0.5) + 0.14 * np.sin(3 * phase)
    y += 0.028 * np.sign(np.sin(phase * 2.01))
    y = onepole_lowpass(y, 4200)
    y /= np.max(np.abs(y))
    y *= adsr(n, 0.045, 0.12, 0.86, 0.22)
    return y * gain


def taiko(sec, freq=86, gain=1.0, click=0.18):
    n = int(sec * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 1.8 * np.exp(-t * 22))
    phase = 2 * np.pi * np.cumsum(f) / SR
    rng = np.random.default_rng(401)
    body = np.sin(phase) * np.exp(-t * 4.8)
    skin = onepole_lowpass(rng.normal(0, 1, n), 1200) * np.exp(-t * 22)
    transient = rng.normal(0, 1, n) * np.exp(-t * 95)
    y = body + 0.42 * skin + click * transient
    y /= np.max(np.abs(y))
    return y * gain


def cymbal(sec, gain=1.0, decay=5.0):
    n = int(sec * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(931)
    y = rng.normal(0, 1, n)
    y = onepole_highpass(y, 4200)
    ring = np.zeros(n)
    for f in (5100, 6230, 7350, 9100, 11400):
        ring += np.sin(2 * np.pi * f * t + f * 0.001)
    y = 0.68 * y + 0.32 * ring
    y *= np.exp(-t * decay)
    y /= max(1e-6, np.max(np.abs(y)))
    return y * gain


def circular_space(x):
    y = x.copy()
    delays = [(0.087, 0.19, -0.35), (0.143, 0.14, 0.42), (0.229, 0.10, -0.1), (0.371, 0.075, 0.28)]
    for sec, g, pan_shift in delays:
        d = int(sec * SR)
        wet = np.roll(x, d, axis=0) * g
        wet[:, 0] *= 1 - pan_shift * 0.18
        wet[:, 1] *= 1 + pan_shift * 0.18
        y += wet

    # A short diffuse tail made circular so the loop boundary remains continuous.
    tail = np.zeros_like(x)
    for d_sec, g in ((0.031, 0.11), (0.047, 0.09), (0.071, 0.075), (0.109, 0.055)):
        d = int(d_sec * SR)
        tail += np.roll(y, d, axis=0) * g
    return y + tail


def soft_master(x):
    x = onepole_highpass(x, 32)
    x[:, 0] = onepole_lowpass(x[:, 0], 15_000)
    x[:, 1] = onepole_lowpass(x[:, 1], 15_000)
    x = np.tanh(x * 1.35)
    peak = np.max(np.abs(x))
    return x / peak * 0.94


def main():
    beat = 60 / BPM
    mix = np.zeros((N, 2), dtype=np.float64)

    # D minor colored with pentatonic/Chinese-war-drama intervals, kept original.
    chords = [
        [0, 7, 12, 15],
        [-2, 5, 10, 14],
        [-5, 2, 7, 10],
        [-7, 0, 5, 9],
        [0, 7, 12, 17],
        [3, 10, 15, 19],
        [-5, 2, 7, 12],
        [-2, 5, 10, 14],
    ]

    for bar in range(8):
        t = bar * 4 * beat
        chord = chords[bar]
        for i, semi in enumerate(chord):
            note = detuned_saw(midi(ROOT, semi), 4 * beat, harmonics=22, detune=0.0035, gain=0.07, cutoff=1800, vib=0.06)
            add(mix, t, stereo(note * adsr(len(note), 0.18, 0.35, 0.82, 0.5), pan=-0.55 + i * 0.34))

        low = detuned_saw(midi(ROOT / 2, chord[0]), 4 * beat, harmonics=12, detune=0.002, gain=0.11, cutoff=650)
        add(mix, t, stereo(low * adsr(len(low), 0.08, 0.24, 0.9, 0.3), pan=0.0))

    ost = [0, 0, 7, 0, 10, 7, 5, 7, 0, 7, 12, 10, 7, 5, 3, 5]
    for step in range(64):
        t = step * beat / 2
        semi = ost[step % len(ost)]
        pulse = detuned_saw(midi(ROOT, semi), beat * 0.42, harmonics=14, detune=0.002, gain=0.075, cutoff=1350)
        pulse *= adsr(len(pulse), 0.008, 0.04, 0.45, 0.09)
        add(mix, t, stereo(pulse, pan=-0.22 if step % 2 else 0.18))

    horn_line = [0, 7, 10, 7, 12, 10, 7, 5]
    for i, semi in enumerate(horn_line):
        t = i * 2 * beat
        h = brass(midi(ROOT * 2, semi), 1.85 * beat, gain=0.20 if i in (0, 4) else 0.15)
        add(mix, t, stereo(h, pan=-0.18))
        add(mix, t + 0.018, stereo(brass(midi(ROOT * 2, semi + 7), 1.72 * beat, gain=0.11), pan=0.28))

    lead_notes = [12, 15, 17, 19, 17, 15, 12, 10, 12, 10, 7, 5, 7, 10, 12, 15]
    for phrase in range(2):
        start = (phrase * 8 + 1.0) * beat
        for i in range(0, len(lead_notes), 2):
            freqs = [midi(ROOT * 4, lead_notes[i]), midi(ROOT * 4, lead_notes[(i + 1) % len(lead_notes)])]
            lead = bowed_lead(freqs, beat * 0.92, gain=0.105)
            add(mix, start + i * beat / 2, stereo(lead, pan=0.34))

    for b in range(32):
        t = b * beat
        if b % 4 in (0, 2):
            add(mix, t, stereo(taiko(0.95, 72, gain=0.48), pan=-0.12))
            add(mix, t + 0.035, stereo(taiko(0.78, 98, gain=0.28), pan=0.22))
        if b % 4 in (1, 3):
            add(mix, t, stereo(taiko(0.48, 145, gain=0.24, click=0.38), pan=0.12))
        if b % 8 == 7:
            for k in range(4):
                add(mix, t + k * beat / 4, stereo(taiko(0.25, 118 + k * 18, gain=0.16), pan=-0.3 + k * 0.2))

    for i in range(16):
        add(mix, i * beat * 2, stereo(cymbal(0.55, gain=0.045, decay=8.5), pan=0.52))
    for i in (0, 8, 16, 24):
        add(mix, i * beat, stereo(cymbal(2.6, gain=0.16, decay=2.1), pan=-0.38))

    # Sub battlefield rumble, phase-aligned to the 20 s loop.
    t = np.arange(N) / SR
    rumble = 0.04 * np.sin(2 * np.pi * 36 * t) * (0.72 + 0.28 * np.sin(2 * np.pi * t / 10) ** 2)
    mix += stereo(rumble, pan=0.0)

    mix = circular_space(mix)

    # Boundary polish: the final samples fade into the first samples so looping players
    # do not click when they jump back to time zero.
    f = int(0.06 * SR)
    a = np.sin(np.linspace(0, math.pi / 2, f))[:, None] ** 2
    tail = mix[-f:].copy()
    head_next = np.vstack((mix[1:f], mix[:1]))
    mix[-f:] = tail * (1 - a) + head_next * a

    mix = soft_master(mix)
    f = int(0.025 * SR)
    a = np.sin(np.linspace(0, math.pi / 2, f))[:, None] ** 2
    head_next = np.vstack((mix[1:f], mix[:1]))
    mix[-f:] = mix[-f:] * (1 - a) + head_next * a
    mix = mix / max(1e-6, np.max(np.abs(mix))) * 0.94
    pcm = (mix * 32767).astype(np.int16)

    out_dir = Path("exports")
    out_dir.mkdir(exist_ok=True)
    wav = out_dir / "sanguo_battle_loop_20s_epic.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(wav.resolve())


if __name__ == "__main__":
    main()
