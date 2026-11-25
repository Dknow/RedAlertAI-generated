# -*- coding: utf-8 -*-
"""全部美术资源程序化生成与绘制（无外部图片）。"""
import math
import random

import pygame

from . import config as C
from . import data as D
from .nav import px_to_tile

T = C.TILE
BUCKETS = 32


# ---------------------------------------------------------------- 颜色工具
def shade(c, k):
    return (max(0, min(255, int(c[0] * k))),
            max(0, min(255, int(c[1] * k))),
            max(0, min(255, int(c[2] * k))))


def mix(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


class Renderer:
    def __init__(self, world):
        self.world = world
        self.terrain = self._make_terrain()
        self.ore_last = [0.0] * (C.MAP_W * C.MAP_H)
        self.unit_cache = {}
        self.bld_cache = {}
        self.minimap_base = self._make_minimap()
        self.fog_surf = pygame.Surface((C.VIEW_W, C.VIEW_H), pygame.SRCALPHA)
        self.ghost_cache = {}

    # ================= 地形 =================
    def _make_terrain(self):
        w = self.world
        surf = pygame.Surface((C.WORLD_W, C.WORLD_H))
        surf.fill((58, 84, 48))
        rng = random.Random(7)
        for ty in range(C.MAP_H):
            for tx in range(C.MAP_W):
                i = ty * C.MAP_W + tx
                t = w.terrain[i]
                px, py = tx * T, ty * T
                if t == C.T_GRASS:
                    base = (54 + rng.randint(-6, 6), 84 + rng.randint(-7, 7), 46 + rng.randint(-5, 5))
                    surf.fill(base, (px, py, T, T))
                    for _ in range(3):
                        gx = px + rng.randint(1, T - 2)
                        gy = py + rng.randint(1, T - 2)
                        surf.set_at((gx, gy), shade(base, 0.82))
                        if rng.random() < 0.5:
                            surf.set_at((min(gx + 1, px + T - 1), gy), shade(base, 1.15))
                elif t == C.T_DIRT:
                    base = (86 + rng.randint(-6, 6), 68 + rng.randint(-5, 5), 44 + rng.randint(-4, 4))
                    surf.fill(base, (px, py, T, T))
                    for _ in range(4):
                        surf.set_at((px + rng.randint(0, T - 1), py + rng.randint(0, T - 1)),
                                    shade(base, 0.85))
                elif t == C.T_WATER:
                    base = (26, 52, 78)
                    surf.fill(base, (px, py, T, T))
                    for k in range(3):
                        yy = py + 6 + k * 9 + rng.randint(-2, 2)
                        pygame.draw.line(surf, (44, 82, 108), (px + 3, yy), (px + T - 4, yy), 1)
                elif t == C.T_ROCK:
                    base = (74, 72, 68)
                    surf.fill(base, (px, py, T, T))
                    pygame.draw.polygon(surf, (92, 89, 82),
                                        [(px + 4, py + T - 4), (px + 11, py + 5),
                                         (px + 24, py + 9), (px + 28, py + T - 4)])
                    pygame.draw.line(surf, (52, 50, 48), (px + 11, py + 5), (px + 24, py + 9), 2)
                elif t == C.T_ROAD:
                    surf.fill((70, 70, 68), (px, py, T, T))
                    if tx % 2 == 0:
                        surf.fill((96, 96, 90), (px + 13, py + 6, 6, 18))
        # 地图边缘暗化
        pygame.draw.rect(surf, (18, 22, 20), (0, 0, C.WORLD_W, 6))
        pygame.draw.rect(surf, (18, 22, 20), (0, C.WORLD_H - 6, C.WORLD_W, 6))
        pygame.draw.rect(surf, (18, 22, 20), (0, 0, 6, C.WORLD_H))
        pygame.draw.rect(surf, (18, 22, 20), (C.WORLD_W - 6, 0, 6, C.WORLD_H))
        return surf

    def _make_minimap(self):
        return pygame.transform.smoothscale(self.terrain, (208, 208))

    def _draw_ore_tile(self, tx, ty, amount):
        surf = self.terrain
        px, py = tx * T, ty * T
        # 重绘底图
        t = self.world.terrain[ty * C.MAP_W + tx]
        if t == C.T_GRASS:
            surf.fill((56, 84, 48), (px, py, T, T))
        elif t == C.T_DIRT:
            surf.fill((86, 68, 44), (px, py, T, T))
        else:
            surf.fill((60, 70, 50), (px, py, T, T))
        frac = amount / max(1.0, C.ORE_TILE_VALUE)
        n = 2 if frac < 0.35 else (3 if frac < 0.75 else 5)
        rng = random.Random(tx * 131 + ty * 17)
        for i in range(n):
            ox = px + 6 + rng.randint(0, T - 14)
            oy = py + 6 + rng.randint(0, T - 14)
            s = rng.randint(3, 6)
            pygame.draw.polygon(surf, (214, 176, 48),
                                [(ox, oy - s), (ox + s, oy), (ox, oy + s), (ox - s, oy)])
            pygame.draw.polygon(surf, (255, 226, 120),
                                [(ox, oy - s), (ox + s, oy), (ox, oy)])
            pygame.draw.line(surf, (150, 118, 30), (ox - s, oy), (ox, oy + s), 1)

    def sync_ore(self):
        w = self.world
        for i in range(C.MAP_W * C.MAP_H):
            if abs(w.ore[i] - self.ore_last[i]) > 1.0:
                self.ore_last[i] = w.ore[i]
                self._draw_ore_tile(i % C.MAP_W, i // C.MAP_W, w.ore[i])

    # ================= 单位贴图 =================
    def _unit_sprites(self, key, fac, bucket):
        ck = (key, fac, bucket)
        hit = self.unit_cache.get(ck)
        if hit:
            return hit
        info = C.FACTION_INFO[fac]
        col, light, dark = info["color"], info["light"], info["dark"]
        deg = bucket * (360 / BUCKETS)
        d = D.UNITS[key]
        body, turret, barrel = self._draw_unit_raw(key, d, col, light, dark)
        if deg:
            body = pygame.transform.rotozoom(body, -deg, 1.0)
            if turret is not None:
                turret = pygame.transform.rotozoom(turret, -deg, 1.0)
        self.unit_cache[ck] = (body, turret, barrel)
        return self.unit_cache[ck]

    def _draw_unit_raw(self, key, d, col, light, dark):
        S = 88
        body = pygame.Surface((S, S), pygame.SRCALPHA)
        cx = cy = S // 2
        turret = None
        barrel = 12
        kind = d.tab
        is_harv = d.is_harvester
        if kind == "infantry":
            # 阴影
            pygame.draw.ellipse(body, (0, 0, 0, 70), (cx - 11, cy + 5, 22, 10))
            if key == "y_brute":
                pygame.draw.circle(body, (118, 88, 74), (cx, cy), 12)
                pygame.draw.circle(body, col, (cx, cy), 9)
                pygame.draw.circle(body, (206, 176, 148), (cx + 7, cy), 5)
            else:
                pygame.draw.circle(body, dark, (cx, cy), 9)
                pygame.draw.circle(body, col, (cx, cy), 7)
                pygame.draw.circle(body, (222, 196, 164), (cx + 4, cy), 4)
                pygame.draw.rect(body, (210, 190, 150), (cx + 6, cy - 4, 5, 8), border_radius=2)
            pygame.draw.line(body, (32, 32, 36), (cx + 6, cy - 7), (cx + 16, cy - 7), 3)
            barrel = 15
        elif key == "s_kirov":
            body = pygame.Surface((150, 150), pygame.SRCALPHA)
            cx = cy = 75
            pygame.draw.ellipse(body, (0, 0, 0, 60), (cx - 44, cy + 40, 88, 22))
            pygame.draw.ellipse(body, shade(col, 0.9), (cx - 44, cy - 26, 88, 54))
            pygame.draw.ellipse(body, light, (cx - 34, cy - 20, 66, 30))
            pygame.draw.rect(body, dark, (cx - 16, cy + 18, 32, 18), border_radius=5)
            pygame.draw.line(body, (60, 60, 66), (cx - 10, cy + 36), (cx - 10, cy + 46), 3)
            pygame.draw.line(body, (60, 60, 66), (cx + 10, cy + 36), (cx + 10, cy + 46), 3)
            pygame.draw.circle(body, (255, 80, 70), (cx + 30, cy - 6), 4)
            pygame.draw.circle(body, (255, 230, 140), (cx - 30, cy - 6), 4)
            barrel = 0
        elif key == "y_disc":
            pygame.draw.ellipse(body, (0, 0, 0, 60), (cx - 22, cy + 16, 44, 14))
            pygame.draw.circle(body, dark, (cx, cy), 22)
            pygame.draw.circle(body, col, (cx, cy), 18)
            pygame.draw.circle(body, light, (cx, cy), 11)
            pygame.draw.circle(body, (240, 210, 255), (cx, cy), 5)
            for a in range(0, 360, 45):
                r = math.radians(a)
                pygame.draw.line(body, shade(col, 1.25),
                                 (cx + math.cos(r) * 14, cy + math.sin(r) * 14),
                                 (cx + math.cos(r) * 20, cy + math.sin(r) * 20), 2)
            barrel = 0
        elif key == "a_heli":
            pygame.draw.ellipse(body, (0, 0, 0, 60), (cx - 26, cy + 14, 52, 16))
            pygame.draw.ellipse(body, dark, (cx - 24, cy - 11, 48, 22))
            pygame.draw.ellipse(body, col, (cx - 20, cy - 8, 36, 16))
            pygame.draw.circle(body, light, (cx + 14, cy - 6), 6)
            pygame.draw.line(body, (30, 34, 40), (cx - 6, cy - 18), (cx + 6, cy - 18), 2)
            pygame.draw.line(body, (30, 34, 40), (cx - 6, cy - 18), (cx - 16, cy - 26), 2)
            pygame.draw.line(body, (30, 34, 40), (cx - 6, cy - 18), (cx + 8, cy - 30), 2)
            pygame.draw.line(body, (30, 34, 40), (cx - 6, cy - 18), (cx - 20, cy - 12), 2)
            pygame.draw.line(body, (30, 34, 40), (cx - 6, cy - 18), (cx + 12, cy - 8), 2)
            pygame.draw.rect(body, (52, 56, 62), (cx - 26, cy - 4, 10, 8), border_radius=2)
            barrel = 12
        elif is_harv:
            pygame.draw.ellipse(body, (0, 0, 0, 60), (cx - 24, cy + 14, 48, 14))
            pygame.draw.rect(body, (52, 50, 46), (cx - 26, cy - 20, 52, 40), border_radius=5)
            pygame.draw.rect(body, (84, 80, 72), (cx - 22, cy - 16, 44, 32), border_radius=4)
            pygame.draw.rect(body, (196, 158, 44), (cx - 12, cy - 12, 26, 24), border_radius=3)
            pygame.draw.rect(body, dark, (cx - 26, cy - 22, 10, 44), border_radius=3)
            pygame.draw.rect(body, dark, (cx + 16, cy - 22, 10, 44), border_radius=3)
            pygame.draw.polygon(body, (150, 150, 156),
                                [(cx + 24, cy - 10), (cx + 34, cy - 4), (cx + 34, cy + 8), (cx + 24, cy + 12)])
            barrel = 0
        elif key == "s_drone":
            pygame.draw.circle(body, (0, 0, 0, 60), (cx, cy + 8), 12)
            pygame.draw.circle(body, dark, (cx, cy), 13)
            pygame.draw.circle(body, col, (cx, cy), 9)
            for a in range(0, 360, 60):
                r = math.radians(a)
                pygame.draw.line(body, (60, 40, 40),
                                 (cx + math.cos(r) * 9, cy + math.sin(r) * 9),
                                 (cx + math.cos(r) * 16, cy + math.sin(r) * 16), 2)
            pygame.draw.circle(body, (255, 120, 60), (cx, cy), 3)
            barrel = 0
        elif key == "y_chaos":
            pygame.draw.rect(body, (0, 0, 0, 60), (cx - 22, cy + 8, 44, 12), border_radius=4)
            pygame.draw.rect(body, dark, (cx - 20, cy - 12, 40, 24), border_radius=5)
            pygame.draw.rect(body, col, (cx - 16, cy - 8, 32, 16), border_radius=4)
            pygame.draw.circle(body, (210, 130, 255), (cx, cy - 12), 6)
            pygame.draw.rect(body, (54, 52, 50), (cx - 24, cy - 14, 6, 28), border_radius=2)
            pygame.draw.rect(body, (54, 52, 50), (cx + 18, cy - 14, 6, 28), border_radius=2)
            barrel = 0
        else:
            # 通用坦克
            heavy = key in ("s_apoc", "s_rhino")
            bw = 30 if not heavy else 34
            bh = 21 if not heavy else 24
            pygame.draw.ellipse(body, (0, 0, 0, 65), (cx - bw, cy + bh - 9, bw * 2, 16))
            pygame.draw.rect(body, (44, 46, 44), (cx - bw - 3, cy - bh - 2, 9, bh * 2 + 4), border_radius=3)
            pygame.draw.rect(body, (44, 46, 44), (cx + bw - 6, cy - bh - 2, 9, bh * 2 + 4), border_radius=3)
            pygame.draw.rect(body, shade(col, 0.75), (cx - bw, cy - bh, bw * 2, bh * 2), border_radius=5)
            pygame.draw.rect(body, col, (cx - bw + 3, cy - bh + 3, bw * 2 - 6, bh * 2 - 6), border_radius=4)
            pygame.draw.line(body, light, (cx - bw + 6, cy - bh + 5), (cx + bw - 8, cy - bh + 5), 2)
            if key == "s_v3":
                pygame.draw.rect(body, (70, 74, 66), (cx - 16, cy - 14, 30, 28), border_radius=3)
            # 炮塔
            turret = pygame.Surface((72, 72), pygame.SRCALPHA)
            tc = 36
            if key == "a_prism":
                pygame.draw.circle(turret, dark, (tc, tc), 10)
                pygame.draw.polygon(turret, (140, 210, 255),
                                    [(tc + 2, tc - 9), (tc + 12, tc), (tc + 2, tc + 9), (tc - 5, tc)])
                pygame.draw.polygon(turret, (230, 250, 255),
                                    [(tc + 2, tc - 9), (tc + 12, tc), (tc + 2, tc)])
                barrel = 18
            elif key == "s_v3":
                pygame.draw.rect(turret, shade(col, 0.8), (tc - 8, tc - 10, 20, 20), border_radius=3)
                pygame.draw.rect(turret, (96, 100, 92), (tc - 2, tc - 6, 26, 12), border_radius=2)
                pygame.draw.polygon(turret, (230, 80, 60), [(tc + 22, tc - 5), (tc + 28, tc), (tc + 22, tc + 5)])
                barrel = 24
            elif key == "s_apoc":
                pygame.draw.circle(turret, shade(col, 0.72), (tc, tc), 13)
                pygame.draw.circle(turret, col, (tc, tc), 10)
                pygame.draw.rect(turret, (52, 54, 52), (tc + 4, tc - 8, 26, 5), border_radius=2)
                pygame.draw.rect(turret, (52, 54, 52), (tc + 4, tc + 3, 26, 5), border_radius=2)
                barrel = 26
            elif key == "y_magnet":
                pygame.draw.circle(turret, shade(col, 0.7), (tc, tc), 11)
                pygame.draw.circle(turret, (170, 140, 255), (tc, tc), 7)
                pygame.draw.line(turret, (220, 200, 255), (tc, tc - 7), (tc, tc + 7), 2)
                pygame.draw.arc(turret, (220, 200, 255), (tc - 14, tc - 9, 28, 18), 0.3, 2.8, 3)
                barrel = 16
            else:
                pygame.draw.circle(turret, shade(col, 0.72), (tc, tc), 11)
                pygame.draw.circle(turret, col, (tc, tc), 8)
                pygame.draw.rect(turret, (40, 42, 44), (tc + 2, tc - 3, 20, 6), border_radius=2)
                if key == "a_ifv":
                    pygame.draw.rect(turret, (40, 42, 44), (tc + 2, tc - 7, 16, 3), border_radius=1)
                barrel = 22
        return body, turret, barrel

    def unit_sprite_bucket(self, angle):
        b = int(((angle / (2 * math.pi)) * BUCKETS) % BUCKETS)
        return b

    def draw_unit(self, screen, u, cam):
        body, turret, barrel = self._unit_sprites(u.key, u.owner.faction if u.owner else "allied",
                                                 self.unit_sprite_bucket(u.angle))
        sx = u.x - cam[0]
        sy = u.y - cam[1]
        if sx < -100 or sy < -100 or sx > C.VIEW_W + 100 or sy > C.VIEW_H + 100:
            return
        if u.is_air:
            pygame.draw.ellipse(screen, (0, 0, 0), (sx - 20, sy + 22, 40, 10))
            bob = math.sin(u.bob * 2) * 2
            sy += bob - 12
        rect = body.get_rect(center=(sx, sy))
        screen.blit(body, rect)
        if turret is not None:
            tb, _, _ = self._unit_sprites(u.key, u.owner.faction if u.owner else "allied",
                                         self.unit_sprite_bucket(u.turret))
            if tb is not None:
                screen.blit(tb, tb.get_rect(center=(sx, sy)))
        if u.muzzle > 0.2 and barrel > 0:
            mx = sx + math.cos(u.turret) * barrel
            my = sy + math.sin(u.turret) * barrel
            r = 4 + 5 * u.muzzle
            pygame.draw.circle(screen, (255, 232, 150), (int(mx), int(my)), int(r))
            pygame.draw.circle(screen, (255, 170, 70), (int(mx), int(my)), int(r * 0.55))
        if u.flash > 0:
            pygame.draw.circle(screen, (255, 80, 60, 120), (int(sx), int(sy)), int(u.radius + 3), 2)

    # ================= 建筑贴图 =================
    def building_sprite(self, b):
        fac = b.owner.faction if b.owner else "allied"
        ck = (b.key, fac)
        s = self.bld_cache.get(ck)
        if s is None:
            s = self._draw_building(b.key, D.BUILDINGS[b.key], fac)
            self.bld_cache[ck] = s
        return s

    def _draw_building(self, key, d, fac):
        info = C.FACTION_INFO[fac]
        col, light, dark = info["color"], info["light"], info["dark"]
        w, h = d.w * T, d.h * T
        extra = 22
        surf = pygame.Surface((w + 12, h + extra + 8), pygame.SRCALPHA)
        ox, oy = 6, extra
        # 阴影
        pygame.draw.ellipse(surf, (0, 0, 0, 70), (ox - 2, oy + h - 10, w + 4, 16))
        wall = shade((132, 136, 140), 1.0)
        roof = (168, 172, 176)
        body_col = mix(wall, col, 0.18)
        # 立体底座
        pygame.draw.rect(surf, (54, 58, 60), (ox, oy, w, h), border_radius=4)
        pygame.draw.rect(surf, body_col, (ox + 2, oy + 2, w - 4, h - 4), border_radius=3)
        # 顶面
        pygame.draw.rect(surf, roof, (ox + 2, oy - 10, w - 4, 16), border_radius=3)
        pygame.draw.rect(surf, shade(roof, 0.78), (ox + 2, oy - 10, w - 4, 5), border_radius=2)
        # 阵营条纹
        pygame.draw.rect(surf, col, (ox + 2, oy + h - 14, w - 4, 5))
        # 类型细节
        kind = key.split("_", 1)[1] if "_" in key else key
        cx = ox + w // 2
        if kind == "cy":
            pygame.draw.rect(surf, (86, 90, 94), (cx - 14, oy - 26, 28, 18), border_radius=2)
            pygame.draw.line(surf, (60, 64, 68), (cx, oy - 26), (cx - 18, oy - 40), 4)
            pygame.draw.line(surf, (60, 64, 68), (cx - 18, oy - 40), (cx - 34, oy - 40), 3)
            pygame.draw.rect(surf, (200, 170, 60), (cx + 8, oy + 8, 16, 10), border_radius=2)
        elif kind == "power":
            for i in range(2):
                px = ox + 10 + i * (w // 2)
                pygame.draw.rect(surf, (120, 126, 124), (px, oy - 18, 18, 24), border_radius=3)
                pygame.draw.ellipse(surf, (170, 176, 172), (px, oy - 22, 18, 10))
            pygame.draw.line(surf, (230, 220, 120), (ox + 6, oy + 10), (ox + 18, oy + 18), 2)
        elif kind == "refinery":
            for i in range(2):
                sx = ox + 12 + i * 34
                pygame.draw.rect(surf, (150, 152, 148), (sx, oy - 24, 22, 30), border_radius=6)
                pygame.draw.ellipse(surf, (190, 192, 188), (sx, oy - 28, 22, 12))
                pygame.draw.rect(surf, (212, 174, 60), (sx + 5, oy - 4, 12, 6))
            pygame.draw.line(surf, (96, 100, 100), (ox + 24, oy + h - 20), (ox + w - 8, oy + h - 20), 4)
            pygame.draw.rect(surf, (70, 74, 74), (ox + w - 28, oy + h - 30, 20, 16), border_radius=2)
        elif kind == "barracks":
            pygame.draw.rect(surf, shade(body_col, 0.8), (ox + 8, oy + 6, w - 16, 10))
            pygame.draw.rect(surf, (70, 52, 40), (cx - 8, oy + h - 30, 16, 20), border_radius=2)
            for i in range(3):
                pygame.draw.rect(surf, light, (ox + 8 + i * 14, oy - 6, 8, 4))
        elif kind == "factory":
            pygame.draw.rect(surf, (78, 82, 84), (ox + 10, oy + 8, w - 20, h - 28), border_radius=3)
            for i in range(3):
                pygame.draw.line(surf, (110, 114, 116), (ox + 10, oy + 16 + i * 10), (ox + w - 10, oy + 16 + i * 10), 2)
            pygame.draw.rect(surf, (46, 50, 52), (cx - 18, oy + h - 32, 36, 22), border_radius=2)
            pygame.draw.rect(surf, (120, 120, 120), (ox + 8, oy - 16, 12, 18), border_radius=2)
            pygame.draw.rect(surf, (120, 120, 120), (ox + w - 20, oy - 16, 12, 18), border_radius=2)
        elif kind == "radar":
            cx2 = ox + w // 2
            pygame.draw.line(surf, (70, 74, 74), (cx2, oy + 6), (cx2, oy - 26), 4)
            pygame.draw.ellipse(surf, (200, 204, 200), (cx2 - 20, oy - 36, 40, 14))
            pygame.draw.ellipse(surf, (150, 154, 150), (cx2 - 20, oy - 36, 40, 14), 2)
            pygame.draw.circle(surf, (230, 90, 70), (cx2, oy - 30), 3)
        elif kind in ("pillbox", "sentry", "psychtower", "prismtower", "flakcannon", "gatling"):
            pygame.draw.circle(surf, (100, 104, 104), (cx, oy + h // 2), min(w, h) // 3)
            pygame.draw.circle(surf, shade(col, 0.85), (cx, oy + h // 2), min(w, h) // 5)
            if kind == "prismtower":
                pygame.draw.polygon(surf, (150, 220, 255),
                                    [(cx, oy - 34), (cx + 12, oy + 6), (cx, oy + 16), (cx - 12, oy + 6)])
            elif kind == "flakcannon":
                pygame.draw.rect(surf, (60, 62, 64), (cx - 4, oy - 26, 8, 28), border_radius=2)
                pygame.draw.rect(surf, (60, 62, 64), (cx + 4, oy - 22, 6, 24), border_radius=2)
            elif kind == "gatling":
                pygame.draw.circle(surf, (60, 62, 64), (cx, oy + 2), 9)
                for a in range(0, 360, 60):
                    r = math.radians(a)
                    pygame.draw.line(surf, (130, 134, 136),
                                     (cx + math.cos(r) * 4, oy + 2 + math.sin(r) * 4),
                                     (cx + math.cos(r) * 10, oy + 2 + math.sin(r) * 10), 2)
            elif kind == "psychtower":
                pygame.draw.circle(surf, (200, 150, 255), (cx, oy + 2), 8)
                pygame.draw.circle(surf, (80, 60, 110), (cx, oy + 2), 8, 2)
            else:
                pygame.draw.rect(surf, (60, 62, 64), (cx, oy + 2, 16, 5), border_radius=2)
        elif kind == "super":
            if key.startswith("a_"):
                pygame.draw.rect(surf, (110, 116, 120), (cx - 26, oy - 30, 52, 26), border_radius=4)
                pygame.draw.ellipse(surf, (180, 220, 255), (cx - 18, oy - 24, 36, 12))
                pygame.draw.line(surf, (90, 96, 100), (cx - 6, oy + 4), (cx - 6, oy - 12), 3)
                pygame.draw.line(surf, (90, 96, 100), (cx + 6, oy + 4), (cx + 6, oy - 12), 3)
            elif key.startswith("s_"):
                pygame.draw.circle(surf, (90, 94, 90), (cx, oy + h // 2), min(w, h) // 3)
                pygame.draw.circle(surf, (60, 64, 60), (cx, oy + h // 2), min(w, h) // 4)
                for a in range(0, 360, 90):
                    r = math.radians(a)
                    pygame.draw.line(surf, (150, 120, 40), (cx, oy + h // 2),
                                     (cx + math.cos(r) * 9, oy + h // 2 + math.sin(r) * 9), 2)
            else:
                pygame.draw.circle(surf, (120, 80, 160), (cx, oy + 6), 16)
                pygame.draw.polygon(surf, (210, 160, 255),
                                    [(cx, oy - 32), (cx + 12, oy + 6), (cx, oy + 18), (cx - 12, oy + 6)])
        pygame.draw.rect(surf, (32, 36, 38), (ox, oy, w, h), 2, border_radius=4)
        return surf

    def draw_building(self, screen, b, cam):
        s = self.building_sprite(b)
        sx = b.tx * T - cam[0] - 6
        sy = b.ty * T - cam[1] - 22
        if sx < -s.get_width() or sy < -s.get_height() or sx > C.VIEW_W or sy > C.VIEW_H:
            return
        if b.construct_t > 0:
            s = s.copy()
            s.set_alpha(150)
        screen.blit(s, (sx, sy))
        if b.construct_t > 0:
            r = pygame.Rect(sx + 6, sy + 22, b.d.w * T, b.d.h * T)
            pygame.draw.rect(screen, (90, 200, 240), r, 1)
            for i in range(4):
                yy = r.y + int(r.h * (i / 4 + b.construct_t / C.CONSTRUCTION_ANIM * 0.1))
                pygame.draw.line(screen, (120, 220, 255), (r.x, min(yy, r.bottom)), (r.right, min(yy, r.bottom)), 1)
        if b.flash > 0:
            pygame.draw.rect(screen, (255, 80, 60), (sx + 6, sy + 22, b.d.w * T, b.d.h * T), 2)

    # ================= 主绘制 =================
    def draw(self, screen, cam, hover=None, sel_b=None, placing=None, place_ok=True,
             attack_cursor=False, super_target=None, show_rally=False):
        w = self.world
        screen.blit(self.terrain, (0, 0), (cam[0], cam[1], C.VIEW_W, C.VIEW_H))
        self.sync_ore()
        for e in w.entities.values():
            if e.dead or not e.is_building:
                continue
            if not w.tile_explored(*px_to_tile(e.x, e.y)):
                continue
            self.draw_building(screen, e, cam)
        # 地面特效（残骸）
        for fx in w.effects:
            if fx.kind == "rubble":
                sx, sy = fx.x - cam[0], fx.y - cam[1]
                a = max(0, min(1, 1 - fx.t / fx.dur))
                r = int(fx.radius * (0.8 + 0.2 * min(1, fx.t)))
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(s, (30, 28, 26, int(150 * a)), (0, 0, r * 2, r * 2))
                screen.blit(s, (sx - r, sy - r * 0.6))
        # 单位
        units = [e for e in w.entities.values()
                 if not e.dead and not e.is_building and w.entity_visible(e)]
        units.sort(key=lambda e: e.y)
        for u in units:
            self.draw_unit(screen, u, cam)
        # 弹丸
        for p in w.projectiles:
            sx, sy = p.x - cam[0], p.y - cam[1]
            if sx < -20 or sy < -20 or sx > C.VIEW_W + 20 or sy > C.VIEW_H + 20:
                continue
            if p.kind == "bullet":
                pygame.draw.line(screen, (255, 245, 190), (sx, sy),
                                 (sx - math.cos(p.angle) * 7, sy - math.sin(p.angle) * 7), 2)
            elif p.kind == "shell":
                pygame.draw.circle(screen, (255, 210, 120), (int(sx), int(sy)), 3)
                pygame.draw.line(screen, (255, 170, 80), (sx, sy),
                                 (sx - math.cos(p.angle) * 12, sy - math.sin(p.angle) * 12), 2)
            elif p.kind == "rocket":
                pygame.draw.circle(screen, (255, 170, 80), (int(sx), int(sy)), 3)
                for i in range(3):
                    tx = sx - math.cos(p.angle) * (6 + i * 5)
                    ty = sy - math.sin(p.angle) * (6 + i * 5)
                    pygame.draw.circle(screen, (180, 170, 160), (int(tx), int(ty)), 2)
            elif p.kind == "bomb":
                pygame.draw.ellipse(screen, (40, 40, 44), (sx - 4, sy - 8, 8, 14))
                pygame.draw.circle(screen, (0, 0, 0), (int(sx + 12), int(sy + 4)), 3)
            elif p.kind == "psychic":
                pygame.draw.circle(screen, (210, 160, 255), (int(sx), int(sy)), 4)
                pygame.draw.circle(screen, (255, 240, 255), (int(sx), int(sy)), 2)
        # 空中特效
        for fx in w.effects:
            if fx.kind != "rubble":
                self._draw_effect(screen, fx, cam)
        # 迷雾
        self._draw_fog(screen, cam)
        # 选择圈 / 血条（迷雾之后，保证自己的单位清晰）
        for u in units:
            self._unit_overlay(screen, u, cam)
        for e in w.entities.values():
            if e.dead or not e.is_building:
                continue
            if not w.tile_explored(*px_to_tile(e.x, e.y)):
                continue
            self._building_overlay(screen, e, cam)
        if hover is not None and not hover.dead:
            sx, sy = hover.x - cam[0], hover.y - cam[1]
            pygame.draw.circle(screen, (255, 120, 90), (int(sx), int(sy)), int(hover.radius + 6), 1)
            if hover.is_building:
                r = pygame.Rect(hover.tx * T - cam[0], hover.ty * T - cam[1], hover.d.w * T, hover.d.h * T)
                pygame.draw.rect(screen, (255, 120, 90), r, 1)
        if show_rally and sel_b is not None and sel_b.rally:
            sx, sy = sel_b.rally[0] - cam[0], sel_b.rally[1] - cam[1]
            pygame.draw.line(screen, (120, 220, 120), (sel_b.x - cam[0], sel_b.y - cam[1]), (sx, sy), 1)
            pygame.draw.circle(screen, (120, 220, 120), (int(sx), int(sy)), 4, 1)
        if placing is not None:
            d = D.BUILDINGS[placing]
            mx, my = pygame.mouse.get_pos()
            tx = int((mx + cam[0]) // T) - d.w // 2
            ty = int((my + cam[1]) // T) - d.h // 2
            s = self._ghost(placing)
            gx = tx * T - cam[0] - 6
            gy = ty * T - cam[1] - 22
            s2 = s.copy()
            s2.set_alpha(160 if place_ok else 90)
            screen.blit(s2, (gx, gy))
            col = (90, 240, 120) if place_ok else (240, 80, 70)
            pygame.draw.rect(screen, col, (tx * T - cam[0], ty * T - cam[1], d.w * T, d.h * T), 2)
            for y in range(ty, ty + d.h):
                for x in range(tx, tx + d.w):
                    pygame.draw.rect(screen, col, (x * T - cam[0], y * T - cam[1], T, T), 1)
        if super_target is not None:
            mx, my = pygame.mouse.get_pos()
            wx, wy = mx + cam[0], my + cam[1]
            r = int(D.SUPERWEAPONS[super_target]["radius"] * T)
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 120, 80, 40), (r, r), r)
            pygame.draw.circle(s, (255, 140, 90, 200), (r, r), r, 2)
            screen.blit(s, (mx - r, my - r))

    def _ghost(self, key):
        s = self.ghost_cache.get(key)
        if s is None:
            d = D.BUILDINGS[key]
            fac = "allied"
            for p in self.world.players:
                if p.faction + "_cy" == key or p.faction + "_power" == key:
                    pass
            fac = self.world.players[0].faction if self.world.players else "allied"
            if d.faction:
                fac = d.faction
            s = self._draw_building(key, d, fac)
            self.ghost_cache[key] = s
        return s

    def _draw_fog(self, screen, cam):
        w = self.world
        fs = self.fog_surf
        fs.fill((0, 0, 0, 0))
        tx0 = max(0, int(cam[0] // T))
        ty0 = max(0, int(cam[1] // T))
        tx1 = min(C.MAP_W, int((cam[0] + C.VIEW_W) // T) + 2)
        ty1 = min(C.MAP_H, int((cam[1] + C.VIEW_H) // T) + 2)
        for ty in range(ty0, ty1):
            run_start = -1
            run_alpha = 0
            for tx in range(tx0, tx1 + 1):
                if tx < tx1:
                    i = ty * C.MAP_W + tx
                    if not w.explored[i]:
                        a = 255
                    elif not w.visible[i]:
                        a = C.EXPLORED_ALPHA
                    else:
                        a = 0
                else:
                    a = -1
                if a != run_alpha:
                    if run_alpha > 0 and run_start >= 0:
                        x0 = run_start * T - cam[0]
                        y0 = ty * T - cam[1]
                        fs.fill((0, 0, 0, run_alpha), (x0, y0, (tx - run_start) * T + 1, T + 1))
                    run_start = tx
                    run_alpha = a
        screen.blit(fs, (0, 0))

    def _unit_overlay(self, screen, u, cam):
        sx, sy = u.x - cam[0], u.y - cam[1]
        if u.sel:
            pygame.draw.ellipse(screen, (120, 240, 120),
                                (sx - u.radius - 5, sy - u.radius * 0.55, (u.radius + 5) * 2,
                                 u.radius * 1.5), 2)
        elif u.owner is not None and u.owner.pid == 0:
            pass
        if u.hp < u.max_hp - 0.5 or u.sel:
            self._hp_bar(screen, sx, sy - u.radius - 12, u.radius * 2, u.hp / u.max_hp,
                         u.owner.color if u.owner else (200, 200, 200))
        if u.vet > 0:
            for i in range(u.vet):
                pygame.draw.polygon(screen, (255, 216, 90),
                                    [(sx - 5 + i * 7, sy - u.radius - 17),
                                     (sx - 1 + i * 7, sy - u.radius - 24),
                                     (sx + 3 + i * 7, sy - u.radius - 17)])
        if u.berserk > 0:
            pygame.draw.circle(screen, (210, 120, 255), (int(sx), int(sy)), int(u.radius + 8), 1)
        if u.master is not None:
            pygame.draw.circle(screen, (200, 140, 255), (int(sx), int(sy) - int(u.radius) - 6), 3)

    def _building_overlay(self, screen, b, cam):
        sx = b.tx * T - cam[0]
        sy = b.ty * T - cam[1]
        wpx = b.d.w * T
        hpx = b.d.h * T
        if b.sel:
            L = 12
            for (x, y, dx, dy) in ((sx, sy, 1, 1), (sx + wpx, sy, -1, 1),
                                   (sx, sy + hpx, 1, -1), (sx + wpx, sy + hpx, -1, -1)):
                pygame.draw.line(screen, (120, 240, 120), (x, y), (x + dx * L, y), 2)
                pygame.draw.line(screen, (120, 240, 120), (x, y), (x, y + dy * L), 2)
        if b.hp < b.max_hp - 0.5 or b.sel:
            self._hp_bar(screen, sx + wpx / 2, sy - 8, wpx * 0.8, b.hp / b.max_hp,
                         b.owner.color if b.owner else (200, 200, 200))
        if b.repair:
            pygame.draw.circle(screen, (110, 220, 160), (int(sx + wpx / 2), int(sy - 18)), 4, 1)
        if b.construct_t > 0:
            pass

    def _hp_bar(self, screen, cx, y, wpx, frac, color):
        wpx = max(20, int(wpx))
        x = int(cx - wpx / 2)
        y = int(y)
        pygame.draw.rect(screen, (18, 18, 18), (x - 1, y - 1, wpx + 2, 6))
        f = max(0.0, min(1.0, frac))
        c = (90, 210, 110) if f > 0.55 else ((230, 190, 70) if f > 0.28 else (220, 70, 60))
        pygame.draw.rect(screen, c, (x, y, int(wpx * f), 4))

    def _draw_effect(self, screen, fx, cam):
        sx, sy = fx.x - cam[0], fx.y - cam[1]
        p = max(0.0, min(1.0, fx.t / fx.dur))
        if fx.kind == "explosion":
            r = int((fx.radius if fx.radius > 0 else 26) * (0.35 + 0.85 * p))
            a = int(230 * (1 - p))
            s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 150, 60, max(0, a // 3)), (r + 2, r + 2), r)
            pygame.draw.circle(s, (255, 220, 130, max(0, a)), (r + 2, r + 2), int(r * 0.55))
            screen.blit(s, (sx - r, sy - r))
        elif fx.kind == "impact":
            r = int(10 * (1 - p)) + 2
            pygame.draw.circle(screen, (255, 230, 170), (int(sx), int(sy)), r)
        elif fx.kind in ("beam", "laser", "magnetic", "psychic"):
            x2 = fx.data.get("x2", fx.x) - cam[0]
            y2 = fx.data.get("y2", fx.y) - cam[1]
            col = fx.color
            wdt = 5 if fx.kind == "beam" else 3
            k = max(0.0, 1.0 - p)
            outer = mix((24, 26, 30), col, k)
            mid = mix((52, 56, 62), col, min(1.0, k * 1.4))
            pygame.draw.line(screen, outer, (sx, sy), (x2, y2), wdt + 4)
            pygame.draw.line(screen, mid, (sx, sy), (x2, y2), wdt + 1)
            core = mix((120, 120, 120), (255, 255, 255), k)
            pygame.draw.line(screen, core, (sx, sy), (x2, y2), max(1, wdt - 2))
        elif fx.kind == "tesla":
            x2 = fx.data.get("x2", fx.x)
            y2 = fx.data.get("y2", fx.y)
            self._jagged(screen, sx, sy, x2 - cam[0], y2 - cam[1], (150, 210, 255), 3)
        elif fx.kind == "lightning":
            top = sy - 300
            self._jagged(screen, sx, top, sx, sy, fx.color, 3)
            pygame.draw.circle(screen, (230, 240, 255), (int(sx), int(sy)), 8)
        elif fx.kind == "ring":
            r = int(fx.radius * (0.3 + p))
            s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*fx.color, int(200 * (1 - p))), (r + 2, r + 2), r, 2)
            screen.blit(s, (sx - r, sy - r))
        elif fx.kind in ("spawn", "capture", "mind", "chaos", "rankup"):
            r = int(20 + 34 * p)
            col = fx.color
            s = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, int(220 * (1 - p))), (r + 2, r + 2), r, 2)
            pygame.draw.circle(s, (*col, int(120 * (1 - p))), (r + 2, r + 2), int(r * 0.6), 1)
            screen.blit(s, (sx - r, sy - r))
        elif fx.kind == "super_incoming":
            r = int(fx.radius)
            t = fx.t
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 120, 60, 26), (r, r), r)
            for i in range(4):
                rr = int(r * ((t * 0.8 + i * 0.25) % 1.0))
                if rr > 4:
                    pygame.draw.circle(s, (*fx.color, 120), (r, r), rr, 2)
            screen.blit(s, (sx - r, sy - r))
        elif fx.kind == "dominate":
            r = int(fx.radius * min(1.0, p * 2))
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*fx.color, int(90 * (1 - p))), (r, r), r)
            pygame.draw.circle(s, (*fx.color, int(220 * (1 - p))), (r, r), r, 3)
            screen.blit(s, (sx - r, sy - r))
        elif fx.kind == "spark":
            pygame.draw.line(screen, (255, 230, 150), (sx - 4, sy), (sx + 4, sy), 1)
            pygame.draw.line(screen, (255, 230, 150), (sx, sy - 3), (sx, sy + 3), 1)

    def _jagged(self, screen, x1, y1, x2, y2, color, width):
        n = 9
        pts = [(x1, y1)]
        for i in range(1, n):
            t = i / n
            px = x1 + (x2 - x1) * t + random.uniform(-9, 9)
            py = y1 + (y2 - y1) * t + random.uniform(-9, 9)
            pts.append((px, py))
        pts.append((x2, y2))
        pygame.draw.lines(screen, color, False, pts, width)
        pygame.draw.lines(screen, (255, 255, 255), False, pts, 1)
