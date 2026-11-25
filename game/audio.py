# -*- coding: utf-8 -*-
"""程序化音效合成（numpy -> pygame.mixer），无需外部音频文件。"""
import math

import numpy as np
import pygame

SR = 22050


def _t(dur):
    return np.arange(int(SR * dur), dtype=np.float32) / SR


def _env(n, attack=0.004, power=3.0):
    t = np.linspace(0, 1, n, dtype=np.float32)
    a = max(1, int(n * attack / 0.1)) if attack > 0 else 1
    e = np.ones(n, dtype=np.float32)
    e[:a] = np.linspace(0, 1, a, dtype=np.float32)
    e[a:] = (1 - t[a:]) ** power
    return e


def _noise(n, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1, 1, n).astype(np.float32)


def _lowpass(x, k=0.12):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += (x[i] - acc) * k
        y[i] = acc
    return y


def _sine(freq, dur, vol=0.6, sweep=None):
    t = _t(dur)
    if sweep is None:
        phase = 2 * math.pi * freq * t
    else:
        f = np.linspace(freq, sweep, len(t))
        phase = 2 * math.pi * np.cumsum(f) / SR
    return (np.sin(phase) * vol).astype(np.float32)


def _mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n, dtype=np.float32)
    for p in parts:
        out[:len(p)] += p
    return out


def _norm(x, peak=0.85):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * peak).astype(np.float32)


def _to_sound(x):
    x = np.clip(x, -1, 1)
    arr = (x * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.ascontiguousarray(arr))


class Audio:
    def __init__(self):
        self.ok = False
        self.sounds = {}
        self.volume = 0.55
        self.muted = False
        try:
            try:
                pygame.mixer.quit()
            except Exception:
                pass
            pygame.mixer.pre_init(SR, -16, 1, 512)
            pygame.mixer.init(SR, -16, 1, 512)
            pygame.mixer.set_num_channels(32)
            self.ok = True
        except Exception:
            self.ok = False
            return
        try:
            self._build()
        except Exception:
            self.ok = False

    def _build(self):
        S = self.sounds
        n = len(_noise(int(SR * 0.1)))
        S["rifle"] = _to_sound(_norm(_mix(
            _noise(n, 1) * _env(n, 0.002, 5) * 0.7,
            _sine(220, 0.09, 0.5, 90) * _env(int(SR * 0.09), 0.001, 5)), 0.55))

        n = int(SR * 0.35)
        S["cannon"] = _to_sound(_norm(_mix(
            _noise(n, 2) * _env(n, 0.001, 4) * 0.6,
            _sine(150, 0.35, 0.9, 45) * _env(n, 0.001, 3)), 0.8))

        n = int(SR * 0.42)
        rk = _noise(n, 3) * np.linspace(0.2, 1.0, n, dtype=np.float32) * _env(n, 0.02, 2)
        S["rocket"] = _to_sound(_norm(_mix(rk * 0.8, _sine(400, 0.4, 0.25, 900)), 0.5))

        n = int(SR * 0.75)
        S["explosion"] = _to_sound(_norm(_mix(
            _lowpass(_noise(n, 4), 0.25) * _env(n, 0.002, 3) * 2.2,
            _sine(90, 0.6, 0.7, 35) * _env(n, 0.002, 3)), 0.9))

        n = int(SR * 1.3)
        S["big_explosion"] = _to_sound(_norm(_mix(
            _lowpass(_noise(n, 5), 0.10) * _env(n, 0.002, 2.5) * 2.6,
            _sine(62, 1.2, 0.9, 24) * _env(n, 0.002, 2.2)), 1.0))

        n = int(SR * 0.2)
        S["laser"] = _to_sound(_norm(_mix(
            _sine(1500, 0.18, 0.5, 220) * _env(n, 0.002, 3),
            _noise(n, 6) * 0.12 * _env(n, 0.01, 5)), 0.6))

        n = int(SR * 0.28)
        buzz = np.sign(_sine(95, 0.28, 0.5)) * 0.35
        S["tesla"] = _to_sound(_norm(_mix(
            buzz * _env(n, 0.003, 2),
            _noise(n, 7) * 0.5 * _env(n, 0.005, 3),
            _sine(1200, 0.25, 0.2, 300) * _env(n, 0.02, 4)), 0.65))

        n = int(SR * 0.08)
        S["impact"] = _to_sound(_norm(_mix(
            _noise(n, 8) * _env(n, 0.001, 6),
            _sine(320, 0.07, 0.4, 120)), 0.45))

        n = int(SR * 0.6)
        S["build"] = _to_sound(_norm(_mix(
            _sine(523, 0.22, 0.4) * _env(int(SR * 0.22), 0.01, 2),
            np.concatenate([np.zeros(int(SR * 0.16), np.float32),
                            _sine(784, 0.4, 0.4) * _env(int(SR * 0.4), 0.01, 2)]), 16), 0.55))

        n = int(SR * 0.07)
        S["select"] = _to_sound(_norm(_sine(900, 0.07, 0.35) * _env(n, 0.003, 4), 0.4))

        n = int(SR * 0.05)
        S["click"] = _to_sound(_norm(_noise(n, 9) * _env(n, 0.001, 6) * 0.6, 0.35))

        n = int(SR * 0.18)
        S["error"] = _to_sound(_norm(_mix(
            _sine(160, 0.18, 0.5) * _env(n, 0.005, 2),
            _sine(120, 0.18, 0.4) * _env(n, 0.005, 2)), 0.5))

        S["capture"] = _to_sound(_norm(_mix(
            _sine(440, 0.12, 0.4) * _env(int(SR * 0.12), 0.01, 2),
            np.concatenate([np.zeros(int(SR * 0.1), np.float32),
                            _sine(660, 0.3, 0.45) * _env(int(SR * 0.3), 0.01, 2)]), 21), 0.5))

        n = int(SR * 0.7)
        S["mind"] = _to_sound(_norm(_mix(
            _sine(280, 0.7, 0.4, 520) * _env(n, 0.1, 1.5),
            _sine(285, 0.7, 0.3, 540) * _env(n, 0.1, 1.5),
            _noise(n, 10) * 0.08), 0.55))

        n = int(SR * 1.8)
        S["nuke"] = _to_sound(_norm(_mix(
            _lowpass(_noise(n, 11), 0.06) * _env(n, 0.001, 1.8) * 3.0,
            _sine(45, 1.8, 0.9, 20) * _env(n, 0.001, 1.6)), 1.0))

        n = int(SR * 0.9)
        S["thunder"] = _to_sound(_norm(_mix(
            _lowpass(_noise(n, 12), 0.18) * _env(n, 0.01, 1.6) * 1.8,
            _sine(70, 0.9, 0.4, 40) * _env(n, 0.01, 1.6)), 0.85))

        n = int(SR * 0.4)
        S["sell"] = _to_sound(_norm(_mix(
            _sine(1046, 0.09, 0.35) * _env(int(SR * 0.09), 0.002, 3),
            np.concatenate([np.zeros(int(SR * 0.07), np.float32),
                            _sine(1568, 0.3, 0.35) * _env(int(SR * 0.3), 0.002, 3)]), 22), 0.45))

        n = int(SR * 0.22)
        S["spawn"] = _to_sound(_norm(_mix(
            _noise(n, 13) * _env(n, 0.05, 2) * 0.8,
            _sine(300, 0.2, 0.3, 700)), 0.4))

        n = int(SR * 0.3)
        S["ready"] = _to_sound(_norm(_mix(
            _sine(880, 0.12, 0.35) * _env(int(SR * 0.12), 0.005, 2),
            np.concatenate([np.zeros(int(SR * 0.1), np.float32),
                            _sine(1320, 0.2, 0.3) * _env(int(SR * 0.2), 0.005, 2)]), 23), 0.45))

        n = int(SR * 0.7)
        S["bomb"] = _to_sound(_norm(_mix(
            _sine(900, 0.55, 0.3, 180) * _env(int(SR * 0.55), 0.05, 2),
            np.concatenate([np.zeros(int(SR * 0.55), np.float32),
                            _noise(int(SR * 0.15), 14) * 0.7 * _env(int(SR * 0.15), 0.001, 4)]), 15), 0.7))

    def play(self, name, x=None, y=None, cam=(0, 0), vol=1.0):
        if not self.ok or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        v = max(0.0, min(1.0, vol * self.volume))
        if x is not None and y is not None:
            cx, cy = cam[0] + 500, cam[1] + 380
            d = math.hypot(x - cx, y - cy)
            if d > 1500:
                return
            v *= max(0.08, 1.0 - d / 1500)
        try:
            ch = snd.play()
            if ch is not None:
                ch.set_volume(v)
        except Exception:
            pass

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted
