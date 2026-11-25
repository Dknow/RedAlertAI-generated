# -*- coding: utf-8 -*-
"""世界：地图生成、实体管理、战斗结算、采集、迷雾、胜负。"""
import math
import random

from . import config as C
from . import data as D
from .entities import Unit, Building, Projectile, Effect
from .nav import (FlowField, astar, in_bounds, idx, nearest_free, px_to_tile, tile_center,
                  W, H, N)
from .player import Player

TILE = C.TILE


class World:
    def __init__(self, seed=20261125):
        self.seed = seed
        self.rng = random.Random(seed)
        self.time = 0.0
        self.entities = {}
        self.next_id = 1
        self.projectiles = []
        self.effects = []
        self.strikes = []
        self.players = []
        self.audio = None
        self.cam = (0, 0)
        self.messages = []
        self.game_over = None
        self.game_over_time = 0.0
        self.nav_version = 0
        self._flow_cache = {}
        self._flow_budget = 6
        self.terrain = bytearray(N)
        self.ore = [0.0] * N
        self.blocked = bytearray(N)
        self.visible = bytearray(N)
        self.explored = bytearray(N)
        self.fog_timer = 0.0
        self.selected = []
        self._hash = {}
        self.generate_map()

    # ================= 地图 =================
    def generate_map(self):
        rng = self.rng
        self.terrain = bytearray([C.T_GRASS]) * N
        # 草地纹理：泥土斑块
        for _ in range(70):
            cx, cy = rng.randrange(W), rng.randrange(H)
            r = rng.randint(2, 6)
            for y in range(max(0, cy - r), min(H, cy + r + 1)):
                for x in range(max(0, cx - r), min(W, cx + r + 1)):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                        self.terrain[idx(x, y)] = C.T_DIRT
        self.spawns = [(12, 70), (70, 12)]
        # 用直线走廊保证连通
        self._clear_corridor(self.spawns[0], self.spawns[1], 7)
        # 湖泊
        for _ in range(4):
            for _try in range(30):
                cx, cy = rng.randrange(8, W - 8), rng.randrange(8, H - 8)
                if self._dist_to_line((cx, cy), self.spawns[0], self.spawns[1]) < 10:
                    continue
                if self._near_spawn(cx, cy, 14):
                    continue
                r = rng.randint(3, 6)
                self._blob(cx, cy, r, C.T_WATER)
                break
        # 岩地
        for _ in range(26):
            for _try in range(20):
                cx, cy = rng.randrange(3, W - 3), rng.randrange(3, H - 3)
                if self._dist_to_line((cx, cy), self.spawns[0], self.spawns[1]) < 7:
                    continue
                if self._near_spawn(cx, cy, 13):
                    continue
                r = rng.randint(1, 3)
                self._blob(cx, cy, r, C.T_ROCK)
                break
        # 出生区整平
        for sx, sy in self.spawns:
            for y in range(max(0, sy - 12), min(H, sy + 12)):
                for x in range(max(0, sx - 12), min(W, sx + 12)):
                    if (x - sx) ** 2 + (y - sy) ** 2 <= 144:
                        if self.terrain[idx(x, y)] in (C.T_WATER, C.T_ROCK):
                            self.terrain[idx(x, y)] = C.T_GRASS
        # 矿脉
        ore_spots = [
            (self.spawns[0][0] + 13, self.spawns[0][1] - 7),
            (self.spawns[0][0] + 5, self.spawns[0][1] - 15),
            (self.spawns[1][0] - 13, self.spawns[1][1] + 7),
            (self.spawns[1][0] - 5, self.spawns[1][1] + 15),
            (W // 2, H // 2),
            (W // 2 - 14, H // 2 + 16),
            (W // 2 + 16, H // 2 - 16),
        ]
        for ox, oy in ore_spots:
            self._ore_blob(ox, oy, rng.randint(3, 5))
        # 统计阻挡
        self.blocked = bytearray(N)
        for i in range(N):
            if self.terrain[i] in C.BLOCKING:
                self.blocked[i] = 1
        self._ensure_connectivity()

    def _clear_corridor(self, a, b, radius):
        ax, ay = a
        bx, by = b
        steps = int(max(abs(bx - ax), abs(by - ay)) * 1.5) + 1
        for i in range(steps + 1):
            t = i / steps
            cx = ax + (bx - ax) * t
            cy = ay + (by - ay) * t
            for y in range(int(cy - radius), int(cy + radius) + 1):
                for x in range(int(cx - radius), int(cx + radius) + 1):
                    if in_bounds(x, y):
                        self.terrain[idx(x, y)] = C.T_GRASS

    def _dist_to_line(self, p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    def _near_spawn(self, x, y, r):
        return any((x - sx) ** 2 + (y - sy) ** 2 < r * r for sx, sy in self.spawns)

    def _blob(self, cx, cy, r, t):
        for y in range(max(0, cy - r), min(H, cy + r + 1)):
            for x in range(max(0, cx - r), min(W, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + self.rng.randint(0, 2):
                    self.terrain[idx(x, y)] = t

    def _ore_blob(self, cx, cy, r):
        for y in range(max(0, cy - r), min(H, cy + r + 1)):
            for x in range(max(0, cx - r), min(W, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    i = idx(x, y)
                    if self.terrain[i] not in (C.T_WATER, C.T_ROCK):
                        self.ore[i] = float(C.ORE_TILE_VALUE)

    def _ensure_connectivity(self):
        a = self.spawns[0]
        b = self.spawns[1]
        if not astar(self.blocked, a, b, 20000):
            # 兜底：直线开道
            self._clear_corridor(a, b, 4)
            for i in range(N):
                self.blocked[i] = 1 if self.terrain[i] in C.BLOCKING else 0

    # ================= 开局 =================
    def setup_match(self, players):
        self.players = players
        for i, p in enumerate(players):
            sx, sy = self.spawns[i % len(self.spawns)]
            self._build_start_base(p, sx, sy, i)
        self.update_power()
        self.update_fog(force=True)
        self.add_msg("战斗开始！采集矿石、建立军队、摧毁敌方全部建筑。", C.C_ACCENT)

    def _build_start_base(self, p, sx, sy, index):
        pre = p.faction[0]
        layout = [
            (f"{pre}_cy", sx - 1, sy - 1),
            (f"{pre}_power", sx - 4, sy - 3),
            (f"{pre}_refinery", sx + 2, sy - 1),
            (f"{pre}_factory", sx - 2, sy + 3),
            (f"{pre}_barracks", sx + 3, sy + 3),
        ]
        for key, tx, ty in layout:
            self.place_building(p, key, tx, ty, force=True, free=True)
        ref = None
        for e in self.entities.values():
            if e.is_building and e.owner is p and e.key.endswith("_refinery"):
                ref = e
                break
        if ref:
            dx, dy = ref.dock_point()
            h = self.spawn_unit(p, f"{pre}_harvester", dx, dy + TILE * 0.4)
            if h:
                h.h_state = "seek"
        tank = {"allied": "a_grizzly", "soviet": "s_rhino", "yuri": "y_lasher"}[p.faction]
        inf = {"allied": "a_rifle", "soviet": "s_conscript", "yuri": "y_initiate"}[p.faction]
        for i in range(2):
            self.spawn_unit(p, tank if i == 0 else inf, (sx + 1.5) * TILE + i * 30, (sy + 5.2) * TILE)
        self.spawn_unit(p, inf, (sx + 3.2) * TILE, (sy + 5.0) * TILE)

    # ================= 基础查询 =================
    def get(self, eid):
        if eid is None:
            return None
        return self.entities.get(eid)

    def add_msg(self, text, color=None):
        self.messages.append({"t": self.time, "text": text, "color": color or C.C_TEXT})
        if len(self.messages) > 40:
            self.messages.pop(0)

    def sfx(self, name, x=None, y=None, vol=1.0):
        if self.audio is None:
            return
        try:
            self.audio.play(name, x, y, self.cam, vol)
        except Exception:
            pass

    # ================= 地形 =================
    def point_blocked(self, px, py, pad=0.0):
        if px < 0 or py < 0 or px >= C.WORLD_W or py >= C.WORLD_H:
            return True
        checks = [(px, py)]
        if pad > 0:
            checks += [(px - pad, py), (px + pad, py), (px, py - pad), (px, py + pad)]
        for x, y in checks:
            tx, ty = px_to_tile(x, y)
            if not in_bounds(tx, ty) or self.blocked[idx(tx, ty)]:
                return True
        return False

    def tile_free(self, tx, ty):
        return in_bounds(tx, ty) and not self.blocked[idx(tx, ty)]

    def ore_amount(self, tx, ty):
        if not in_bounds(tx, ty):
            return 0.0
        return self.ore[idx(tx, ty)]

    def harvest_tile(self, tile, amount, space):
        if tile is None:
            return 0.0
        tx, ty = tile
        if not in_bounds(tx, ty):
            return 0.0
        i = idx(tx, ty)
        take = min(amount, self.ore[i], space)
        self.ore[i] -= take
        if self.ore[i] < 1.0:
            self.ore[i] = 0.0
        return take

    def nearest_ore(self, px, py, avoid=None):
        best = None
        bd = 1e18
        for i in range(N):
            if self.ore[i] <= 0:
                continue
            x, y = i % W, i // W
            if avoid and (x, y) in avoid:
                continue
            d = (x * TILE - px) ** 2 + (y * TILE - py) ** 2
            if d < bd:
                bd = d
                best = (x, y)
        return best

    def nearest_refinery(self, player, px, py):
        best = None
        bd = 1e18
        for e in self.entities.values():
            if e.dead or not e.is_building or e.owner is not player:
                continue
            if not e.key.endswith("_refinery") or e.construct_t > 0:
                continue
            d = (e.x - px) ** 2 + (e.y - py) ** 2
            if d < bd:
                bd = d
                best = e
        return best

    # ================= 寻路 =================
    def flow_to_tile(self, tx, ty):
        if not in_bounds(tx, ty):
            return None
        if self.blocked[idx(tx, ty)]:
            f = nearest_free(self.blocked, tx, ty, 8)
            if f is None:
                return None
            tx, ty = f
        k = (tx, ty)
        ent = self._flow_cache.get(k)
        if ent and ent[0] == self.nav_version and self.time - ent[1] < 2.0:
            return ent[2]
        if self._flow_budget <= 0:
            return None
        self._flow_budget -= 1
        ff = FlowField(self.blocked, [(tx, ty)])
        self._flow_cache[k] = (self.nav_version, self.time, ff)
        if len(self._flow_cache) > 64:
            old = sorted(self._flow_cache.items(), key=lambda kv: kv[1][1])[:16]
            for kk, _ in old:
                self._flow_cache.pop(kk, None)
        return ff

    def flow_to_px(self, px, py):
        tx, ty = px_to_tile(px, py)
        return self.flow_to_tile(tx, ty)

    def separation(self, u):
        sx = sy = 0.0
        tx, ty = px_to_tile(u.x, u.y)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for other in self._hash.get((tx + dx, ty + dy), ()):
                    if other is u or other.dead or other.is_building:
                        continue
                    if other.is_air != u.is_air:
                        continue
                    ddx = u.x - other.x
                    ddy = u.y - other.y
                    d2 = ddx * ddx + ddy * ddy
                    minr = (u.radius + other.radius) * 1.05
                    if d2 < minr * minr and d2 > 0.01:
                        d = math.sqrt(d2)
                        k = (minr - d) / minr
                        sx += ddx / d * k
                        sy += ddy / d * k
        n = math.hypot(sx, sy)
        if n > 1.0:
            sx, sy = sx / n, sy / n
        return sx, sy

    def rebuild_hash(self):
        self._hash = {}
        for e in self.entities.values():
            if e.dead:
                continue
            tx, ty = px_to_tile(e.x, e.y)
            self._hash.setdefault((tx, ty), []).append(e)

    # ================= 目标 =================
    def _weapon_ok(self, weapon, target):
        if weapon is None:
            return False
        if target.is_air and not weapon.can_air:
            return False
        if (not target.is_air) and not weapon.can_ground:
            return False
        return True

    def acquire_target(self, unit, max_dist, prefer_units=True):
        w = unit.weapon
        if w is None:
            return None
        best = None
        bd = 1e18
        best_b = None
        bdb = 1e18
        tx, ty = px_to_tile(unit.x, unit.y)
        rad = int(max_dist / TILE) + 1
        seen = set()
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                for e in self._hash.get((tx + dx, ty + dy), ()):
                    if e.id in seen:
                        continue
                    seen.add(e.id)
                    if e is unit or e.dead or e.owner is unit.owner:
                        continue
                    if not self._weapon_ok(w, e):
                        continue
                    d = unit.edge_dist(e)
                    if d > max_dist:
                        continue
                    if e.is_building:
                        if d < bdb:
                            bdb = d
                            best_b = e
                    else:
                        if d < bd:
                            bd = d
                            best = e
        if prefer_units and best is not None:
            return best
        return best if best is not None else best_b

    def nearest_entity_any(self, px, py, radius):
        best = None
        bd = radius * radius
        for e in self.entities.values():
            if e.dead:
                continue
            d = (e.x - px) ** 2 + (e.y - py) ** 2
            if d < bd:
                bd = d
                best = e
        return best

    # ================= 单位/建筑生成 =================
    def free_spot(self, px, py, radius=14.0, tries=64):
        if not self.point_blocked(px, py, radius * 0.6):
            occupied = False
            for e in self.entities.values():
                if e.dead or e.is_building:
                    continue
                if (e.x - px) ** 2 + (e.y - py) ** 2 < (radius * 1.6) ** 2:
                    occupied = True
                    break
            if not occupied:
                return px, py
        for i in range(1, tries + 1):
            ang = i * 2.39996
            r = i * 4.0
            nx = px + math.cos(ang) * r
            ny = py + math.sin(ang) * r
            if nx < 16 or ny < 16 or nx > C.WORLD_W - 16 or ny > C.WORLD_H - 16:
                continue
            if self.point_blocked(nx, ny, radius * 0.5):
                continue
            ok = True
            for e in self.entities.values():
                if e.dead or e.is_building:
                    continue
                if (e.x - nx) ** 2 + (e.y - ny) ** 2 < (radius * 1.5) ** 2:
                    ok = False
                    break
            if ok:
                return nx, ny
        return px, py

    def spawn_unit(self, player, key, x=None, y=None):
        d = D.UNITS[key]
        if x is None or y is None:
            prod = player.producer(self, d.tab)
            if prod is not None:
                x, y = prod.x, (prod.ty + prod.h) * TILE + TILE * 0.7
                rx, ry = prod.rally if prod.rally else (x, y + TILE * 1.4)
            else:
                cy = None
                for e in self.entities.values():
                    if not e.dead and e.is_building and e.owner is player and e.key.endswith("_cy"):
                        cy = e
                        break
                x, y = (cy.x, cy.y + TILE * 2) if cy else (C.WORLD_W / 2, C.WORLD_H / 2)
                rx, ry = x, y
        else:
            rx, ry = x, y
        x, y = self.free_spot(x, y, d.radius * TILE + 6)
        u = Unit(self.next_id, player, d, x, y)
        self.next_id += 1
        self.entities[u.id] = u
        self.spawn_effect("spawn", x, y, 0.5, color=player.color)
        # 出厂后前往集结点
        if math.hypot(rx - x, ry - y) > TILE * 0.8:
            u.order_move(self, rx, ry)
        return u

    def can_place(self, player, key, tx, ty):
        d = D.BUILDINGS[key]
        for y in range(ty, ty + d.h):
            for x in range(tx, tx + d.w):
                if not in_bounds(x, y) or self.blocked[idx(x, y)]:
                    return False, "地形不可建造"
        # 必须靠近己方建筑
        cx = (tx + d.w / 2) * TILE
        cy = (ty + d.h / 2) * TILE
        near = False
        for e in self.entities.values():
            if e.dead or not e.is_building or e.owner is not player:
                continue
            if math.hypot(e.x - cx, e.y - cy) < 9 * TILE:
                near = True
                break
        if not near:
            return False, "必须建在基地附近"
        return True, ""

    def find_build_spot(self, player, key, ox, oy, max_r=18):
        """从（ox,oy）向外螺旋寻找合法建造点，返回左上角格坐标。"""
        d = D.BUILDINGS[key]
        for r in range(1, max_r + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    tx = ox + dx
                    ty = oy + dy
                    if tx < 0 or ty < 0 or tx + d.w > W or ty + d.h > H:
                        continue
                    ok, _ = self.can_place(player, key, tx, ty)
                    if ok:
                        return tx, ty
        return None

    def place_building(self, player, key, tx, ty, force=False, free=False):
        d = D.BUILDINGS[key]
        if not force:
            ok, _ = self.can_place(player, key, tx, ty)
            if not ok:
                return None
        b = Building(self.next_id, player, d, tx, ty)
        self.next_id += 1
        self.entities[b.id] = b
        for y in range(ty, ty + d.h):
            for x in range(tx, tx + d.w):
                if in_bounds(x, y):
                    self.blocked[idx(x, y)] = 1
        self.nav_version += 1
        b.construct_t = 0.0 if free else C.CONSTRUCTION_ANIM
        if free:
            b.hp = b.max_hp
        # 把站在建筑里的单位挤出去
        for e in list(self.entities.values()):
            if e.dead or e.is_building:
                continue
            if tx * TILE <= e.x <= (tx + d.w) * TILE and ty * TILE <= e.y <= (ty + d.h) * TILE:
                nx, ny = self.free_spot(e.x, e.y, 20)
                e.x, e.y = nx, ny
        self.spawn_effect("build", b.x, b.y, 0.8, color=player.color)
        self.update_power()
        return b

    def on_building_complete(self, b):
        p = b.owner
        self.sfx("build")
        self.add_msg(f"{p.name}：{b.name} 建造完成", p.color)
        if b.key.endswith("_refinery"):
            pre = p.faction[0]
            dx, dy = b.dock_point()
            h = self.spawn_unit(p, f"{pre}_harvester", dx, dy + TILE * 0.5)
            if h:
                h.h_state = "seek"
        if b.super_key:
            p.sw[b.super_key] = {"t": 0.0, "ready": False}

    def sell_building(self, b):
        if not b.is_building or b.dead:
            return
        refund = int(b.d.cost * C.SELL_REFUND * (max(0.2, b.hp / b.max_hp)))
        b.owner.credits += refund
        self.add_msg(f"出售 {b.name}，回收 ${refund}", C.C_OK)
        self.kill_entity(b, None, silent=True)
        self.sfx("sell")

    def update_power(self):
        for p in self.players:
            prod = 0
            used = 0
            for e in self.entities.values():
                if e.dead or not e.is_building or e.owner is not p:
                    continue
                if e.construct_t > 0:
                    continue
                if e.d.power >= 0:
                    prod += e.d.power
                else:
                    used += -e.d.power
            p.power_produced = prod
            p.power_used = used
            p.power_low = used > prod

    # ================= 战斗 =================
    def fire_weapon(self, attacker, target, w):
        ax, ay = attacker.x, attacker.y
        if w.projectile in ("beam", "tesla", "magnetic"):
            if w.effect == "mc":
                if not self.try_mind_control(attacker, target):
                    return
            else:
                self.apply_damage(target, w.damage, w.warhead, attacker, w)
                if w.splash > 0:
                    self.apply_splash(target.x, target.y, w.splash * TILE, w.damage * 0.5,
                                      w.warhead, attacker, w, exclude=target)
            self.spawn_effect(w.projectile, ax, ay, 0.22, color=w.color,
                              data={"x2": target.x, "y2": target.y, "w": w})
        else:
            for i in range(max(1, w.burst)):
                p = Projectile(attacker, w, ax, ay, target)
                if w.burst > 1:
                    p.x += self.rng.uniform(-6, 6)
                    p.y += self.rng.uniform(-6, 6)
                    p.ttl += i * 0.08
                self.projectiles.append(p)
        self.sfx(self._weapon_sound(w), ax, ay)

    def _weapon_sound(self, w):
        if w.projectile in ("beam", "laser"):
            return "laser"
        if w.projectile == "tesla":
            return "tesla"
        if w.warhead == "sa":
            return "rifle"
        if w.projectile == "rocket":
            return "rocket"
        if w.projectile == "bomb":
            return "bomb"
        if w.projectile == "psychic":
            return "mind"
        if w.warhead == "ap":
            return "cannon"
        return "cannon"

    def projectile_hit(self, p):
        w = p.w
        target = self.get(p.target_id)
        ox, oy = p.x, p.y
        if target is not None and not target.dead:
            ox, oy = target.x, target.y
            if w.effect == "mc":
                if self.try_mind_control(p.attacker_ref, target):
                    self.spawn_effect("mind", ox, oy, 0.6, color=w.color)
                return
            self.apply_damage(target, w.damage, w.warhead, p.attacker_ref, w)
        if w.splash > 0:
            self.apply_splash(ox, oy, w.splash * TILE, w.damage * 0.7, w.warhead,
                              p.attacker_ref, w, exclude=target)
        self.spawn_effect("explosion" if w.splash > 0.5 else "impact", ox, oy,
                          0.35, radius=w.splash * TILE, color=w.color)
        self.sfx("explosion" if w.splash > 0.8 else "impact", ox, oy, 0.7)

    def apply_damage(self, target, amount, warhead, attacker=None, w=None):
        if target is None or target.dead:
            return
        mult = D.WARHEADS[warhead].get(target.armor, 0.0)
        if mult <= 0:
            return
        dmg = amount * mult
        if attacker is not None and getattr(attacker, "vet", 0):
            dmg *= C.VET_DAMAGE[min(2, attacker.vet)]
        target.hp -= dmg
        target.flash = 1.0
        if attacker is not None:
            target.last_hit_by = attacker if getattr(attacker, "is_building", False) is False else attacker
        if target.hp <= 0:
            self.kill_entity(target, attacker)

    def apply_splash(self, x, y, radius, amount, warhead, attacker, w=None, exclude=None):
        if radius <= 0:
            return
        for e in list(self.entities.values()):
            if e.dead or e is exclude:
                continue
            d = math.hypot(e.x - x, e.y - y) - e.radius * 0.5
            if d > radius:
                continue
            fall = 1.0 - max(0.0, d) / radius
            fall = C.SPLASH_FALLOFF + (1.0 - C.SPLASH_FALLOFF) * fall
            if attacker is not None and e.owner is attacker.owner and e is not attacker:
                fall *= C.FRIENDLY_FIRE
            self.apply_damage(e, amount * fall, warhead, attacker, w)

    def detonate_unit(self, unit, target):
        w = unit.weapon
        if w is None:
            return
        self.apply_splash(unit.x, unit.y, max(w.splash, 1.0) * TILE, w.damage, w.warhead, unit, w)
        self.spawn_effect("explosion", unit.x, unit.y, 0.6, radius=w.splash * TILE)
        self.sfx("explosion", unit.x, unit.y)
        if unit.d.berserk_on_death:
            self.apply_berserk(unit.x, unit.y, 3.5 * TILE, 8.0)
        unit.dead = True
        if unit.owner:
            unit.owner.stats["lost"] += 1

    def apply_berserk(self, x, y, radius, dur):
        for e in self.entities.values():
            if e.dead or e.is_building or e.owner is None:
                continue
            if math.hypot(e.x - x, e.y - y) <= radius:
                e.berserk = max(e.berserk, dur)
                e.order = None
                e.target_id = None
                self.spawn_effect("chaos", e.x, e.y, 0.8, color=(200, 120, 255))

    def try_mind_control(self, source, target):
        if source is None or target is None or target.dead or target.is_building:
            return False
        if target.owner is source.owner:
            return False
        if getattr(target, "master", None) is not None:
            return False
        if len(getattr(source, "mc_units", [])) >= source.d.mind_slots:
            return False
        if source.mc_units is None:
            return False
        target.orig_owner = target.owner
        target.master = source
        source.mc_units.append(target)
        target.owner = source.owner
        target.order = None
        target.target_id = None
        target.sel = False
        self.add_msg(f"{source.name} 控制了 {target.name}", (200, 150, 255))
        return True

    def release_mc(self, unit):
        if unit.master is not None:
            if unit in unit.master.mc_units:
                unit.master.mc_units.remove(unit)
            unit.master = None
        if unit.orig_owner is not None:
            unit.owner = unit.orig_owner
            unit.orig_owner = None
            self.spawn_effect("mind", unit.x, unit.y, 0.4, color=(180, 140, 255))

    def engineer_capture(self, engineer, building):
        if engineer.dead or building.dead or building.owner is engineer.owner:
            return
        old = building.owner
        building.owner = engineer.owner
        building.hp = building.max_hp
        building.repair = False
        building.sel = False
        self.spawn_effect("capture", building.x, building.y, 1.0, color=engineer.owner.color)
        self.sfx("capture", building.x, building.y)
        self.add_msg(f"工程师占领了 {building.name}", engineer.owner.color)
        self.kill_entity(engineer, None, silent=True)
        if old is not None:
            old.stats["lost"] += 0
        self.update_power()

    def kill_entity(self, e, attacker=None, silent=False):
        if e.dead:
            return
        e.dead = True
        if not silent:
            is_b = e.is_building
            self.spawn_effect("explosion", e.x, e.y, 0.9 if is_b else 0.5,
                              radius=(e.radius * 1.8 if is_b else e.radius * 2.2))
            self.sfx("big_explosion" if is_b else "explosion", e.x, e.y)
            if is_b:
                self.add_msg(f"{e.name} 被摧毁！", C.C_BAD)
            if attacker is not None and getattr(attacker, "owner", None) is not None \
                    and attacker.owner is not e.owner:
                attacker.kills += 1
                attacker.owner.stats["kills"] += 1
                if attacker.vet < 2:
                    need = (3, 8)[attacker.vet]
                    if attacker.kills >= need:
                        attacker.vet += 1
                        attacker.max_hp *= C.VET_HP[attacker.vet] / C.VET_HP[attacker.vet - 1]
                        attacker.hp = min(attacker.max_hp, attacker.hp + attacker.max_hp * 0.2)
                        self.spawn_effect("rankup", attacker.x, attacker.y, 0.8,
                                          color=(255, 215, 90))
        if e.owner is not None:
            e.owner.stats["lost"] += 1
        if e.is_building:
            d = e.d
            for y in range(e.ty, e.ty + d.h):
                for x in range(e.tx, e.tx + d.w):
                    if in_bounds(x, y):
                        self.blocked[idx(x, y)] = 0
            self.nav_version += 1
            if e.super_key and e.owner is not None:
                e.owner.sw.pop(e.super_key, None)
            self.spawn_effect("rubble", e.x, e.y, 6.0, radius=e.radius)
        else:
            if e.master is not None:
                self.release_mc(e)
            for m in list(e.mc_units):
                if not m.dead:
                    self.release_mc(m)
            if e.d.berserk_on_death and not silent:
                self.apply_berserk(e.x, e.y, 3.5 * TILE, 8.0)
        self.update_power()

    def repair_buildings(self, dt):
        for e in self.entities.values():
            if e.dead or not e.is_building or e.construct_t > 0 or not e.repair:
                continue
            if e.hp >= e.max_hp:
                e.repair = False
                continue
            heal = e.max_hp * 0.035 * dt
            cost = heal * 0.55
            p = e.owner
            if p.credits < cost:
                continue
            p.credits -= cost
            e.hp = min(e.max_hp, e.hp + heal)
            if self.rng.random() < dt * 3:
                self.spawn_effect("spark", e.x + self.rng.uniform(-e.radius, e.radius),
                                  e.y + self.rng.uniform(-e.radius, e.radius), 0.3)

    # ================= 超武 =================
    def fire_superweapon(self, player, key, x, y):
        if not player.superweapon_consume(key):
            return False
        sw = D.SUPERWEAPONS[key]
        if sw["kind"] == "strike":
            if sw["duration"] <= 0.3:
                # 瞬时打击（核弹）：一次结算全部伤害
                self.apply_splash(x, y, sw["radius"] * TILE, sw["damage"], "explosive", None)
                self.spawn_effect("big_explosion", x, y, 1.4,
                                  radius=sw["radius"] * TILE, color=sw["color"])
            else:
                self.strikes.append({
                    "x": x, "y": y, "r": sw["radius"] * TILE,
                    "dps": sw["damage"] / sw["duration"],
                    "t": 0.0, "dur": sw["duration"], "tick": 0.0,
                    "owner": player, "color": sw["color"], "key": key,
                })
            self.spawn_effect("super_incoming", x, y, 1.0, radius=sw["radius"] * TILE,
                              color=sw["color"])
            self.add_msg(f"{player.name} 发动了 {sw['name']}！", player.color)
            self.sfx("nuke", x, y)
        else:
            n = 0
            for e in list(self.entities.values()):
                if e.dead or e.is_building or e.owner is player:
                    continue
                if math.hypot(e.x - x, e.y - y) <= sw["radius"] * TILE:
                    if self.try_mind_control_force(player, e):
                        n += 1
                        if n >= sw["mc"]:
                            break
            self.spawn_effect("dominate", x, y, 1.6, radius=sw["radius"] * TILE,
                              color=sw["color"])
            self.add_msg(f"{player.name} 发动了 {sw['name']}，控制了 {n} 个单位！", player.color)
            self.sfx("mind", x, y)
        return True

    def try_mind_control_force(self, player, target):
        target.orig_owner = target.owner
        target.owner = player
        target.master = None
        target.order = None
        target.target_id = None
        target.sel = False
        self.spawn_effect("mind", target.x, target.y, 0.6, color=(220, 160, 255))
        return True

    def update_strikes(self, dt):
        for s in self.strikes:
            s["t"] += dt
            s["tick"] -= dt
            if s["tick"] <= 0:
                s["tick"] = 0.22
                dmg = s["dps"] * 0.22
                for e in list(self.entities.values()):
                    if e.dead:
                        continue
                    d = math.hypot(e.x - s["x"], e.y - s["y"])
                    if d <= s["r"]:
                        fall = 1.0 - 0.55 * (d / s["r"])
                        self.apply_damage(e, dmg * fall, "explosive", None)
                for _ in range(3):
                    a = self.rng.uniform(0, math.tau)
                    rr = self.rng.uniform(0, s["r"])
                    self.spawn_effect("lightning", s["x"] + math.cos(a) * rr,
                                      s["y"] + math.sin(a) * rr, 0.25, color=s["color"])
                self.sfx("thunder", s["x"], s["y"], 0.8)
        self.strikes = [s for s in self.strikes if s["t"] < s["dur"]]

    # ================= 特效 =================
    def spawn_effect(self, kind, x, y, dur, radius=0.0, color=(255, 200, 120), text="", data=None):
        self.effects.append(Effect(kind, x, y, dur, radius, color, text, data))
        if len(self.effects) > 500:
            self.effects = self.effects[-400:]

    # ================= 迷雾 =================
    def update_fog(self, force=False):
        if not force and self.fog_timer > 0:
            return
        self.fog_timer = C.FOG_UPDATE_INTERVAL
        human = self.players[0] if self.players else None
        vis = bytearray(N)
        if human is not None:
            for e in self.entities.values():
                if e.dead or e.owner is not human:
                    continue
                r = e.sight
                rt = r / TILE
                ctx, cty = px_to_tile(e.x, e.y)
                ir = int(rt) + 1
                for ty in range(cty - ir, cty + ir + 1):
                    if ty < 0 or ty >= H:
                        continue
                    for tx in range(ctx - ir, ctx + ir + 1):
                        if tx < 0 or tx >= W:
                            continue
                        if (tx - ctx) ** 2 + (ty - cty) ** 2 <= rt * rt:
                            vis[idx(tx, ty)] = 1
        for i in range(N):
            if vis[i]:
                self.explored[i] = 1
        self.visible = vis

    def tile_visible(self, tx, ty):
        if not in_bounds(tx, ty):
            return False
        return bool(self.visible[idx(tx, ty)])

    def tile_explored(self, tx, ty):
        if not in_bounds(tx, ty):
            return False
        return bool(self.explored[idx(tx, ty)])

    def entity_visible(self, e):
        if e.owner is self.players[0]:
            return True
        tx, ty = px_to_tile(e.x, e.y)
        return self.tile_visible(tx, ty)

    # ================= 主循环 =================
    def update(self, dt):
        dt = min(dt, 0.1)
        self.time += dt
        self._flow_budget = 4
        self.fog_timer -= dt
        self.rebuild_hash()
        if self.game_over is not None:
            for e in list(self.effects):
                e.update(dt)
            self.effects = [e for e in self.effects if not e.dead]
            return
        self.update_power()
        for p in self.players:
            p.tick(self, dt)
            if p.ai is not None:
                p.ai.update(dt)
        self.repair_buildings(dt)
        for e in list(self.entities.values()):
            if not e.dead:
                e.update(self, dt)
        for p in self.projectiles:
            p.update(self, dt)
        self.projectiles = [p for p in self.projectiles if not p.dead]
        self.update_strikes(dt)
        for e in self.effects:
            e.update(dt)
        self.effects = [e for e in self.effects if not e.dead]
        self._cleanup()
        self.update_fog()
        self.check_victory()

    def _cleanup(self):
        dead = [k for k, e in self.entities.items() if e.dead]
        for k in dead:
            self.entities.pop(k, None)
        if dead:
            for s in self.selected:
                pass
            self.selected = [e for e in self.selected if not e.dead]

    def check_victory(self):
        if self.game_over is not None or self.time < 5.0:
            return
        if not self.players:
            return
        human = self.players[0]
        enemies = [p for p in self.players[1:] if not p.defeated]
        human_b = human.buildings(self, include_unbuilt=True)
        if not human_b:
            self.game_over = "lose"
            self.game_over_time = self.time
            self.add_msg("基地已被摧毁…… 战斗失败。", C.C_BAD)
            return
        if not enemies:
            self.game_over = "win"
            self.game_over_time = self.time
            self.add_msg("敌军已被彻底消灭，胜利！", C.C_OK)
            return
        alive_enemies = 0
        for p in enemies:
            bs = p.buildings(self, include_unbuilt=True)
            if bs:
                alive_enemies += 1
            else:
                p.defeated = True
        if alive_enemies == 0:
            self.game_over = "win"
            self.game_over_time = self.time
            self.add_msg("敌军已被彻底消灭，胜利！", C.C_OK)
