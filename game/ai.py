# -*- coding: utf-8 -*-
"""遭遇战 AI：经济、造兵、防守、进攻与超级武器。"""
import math
import random

from . import config as C
from . import data as D


class AIController:
    def __init__(self, world, player, difficulty_key):
        self.world = world
        self.p = player
        self.diff = C.DIFFICULTIES.get(difficulty_key, C.DIFFICULTIES["normal"])
        self.timer = 4.0
        self.attack_cd = random.uniform(45, 70)
        self.rng = random.Random(world.seed + 77)
        self.wave_active = False
        self.wave_point = None

    # ---------------- 工具 ----------------
    def base_building(self, suffix):
        pre = self.p.faction[0]
        for e in self.world.entities.values():
            if not e.dead and e.is_building and e.owner is self.p and e.key == f"{pre}_{suffix}":
                return e
        return None

    def count(self, suffix):
        pre = self.p.faction[0]
        n = 0
        for e in self.world.entities.values():
            if not e.dead and e.is_building and e.owner is self.p and e.key == f"{pre}_{suffix}":
                n += 1
        return n

    def try_build(self, key):
        p = self.p
        d = D.get_def(key)
        if p.credits < d.cost or key in p.pending_placement:
            return False
        cat = ("structure" if isinstance(d, D.BuildingDef)
               else "infantry" if d.tab == "infantry" else "vehicle")
        if len(p.queues[cat]) >= (2 if cat == "structure" else 6):
            return False
        if any(it["key"] == key for it in p.queues[cat]):
            return False
        ok, _ = p.buildable(self.world, key)
        if not ok:
            return False
        return p.enqueue(self.world, key)[0]

    # ---------------- 主逻辑 ----------------
    def update(self, dt):
        self.attack_cd -= dt
        self.timer -= dt
        if self.timer > 0:
            return
        self.timer = max(0.35, 1.2 / self.diff["speed"])
        p = self.p
        w = self.world
        if p.defeated:
            return

        # 放置待建建筑（不阻塞后续决策）
        if p.pending_placement:
            self._place()

        pre = p.faction[0]
        cy = self.base_building("cy")
        if cy is None:
            if p.credits >= 3000:
                self.try_build(f"{pre}_cy")
            return

        # 电力：缺电或余量不足就补电厂，但不再卡死其它决策
        headroom = p.power_produced - p.power_used
        if p.power_low or (headroom < 60 and p.credits > 2500):
            self.try_build(f"{pre}_power")

        # 经济与科技建筑
        if self.count("refinery") == 0:
            self.try_build(f"{pre}_refinery")
        elif self.count("refinery") < 2 and p.credits > 4000:
            self.try_build(f"{pre}_refinery")
        if self.count("barracks") == 0:
            self.try_build(f"{pre}_barracks")
        if self.count("factory") == 0:
            self.try_build(f"{pre}_factory")

        harvesters = sum(1 for u in p.units(w) if u.d.is_harvester)
        target_h = 2 + self.count("refinery")
        need_harv = harvesters < target_h
        need_ref = self.count("refinery") == 0
        if need_harv and p.credits >= 1600:
            self.try_build(f"{pre}_harvester")
        elif harvesters == 0 and self.count("refinery") > 0 and p.credits >= 2000:
            # 矿车全灭又买不起时，补精炼厂顺带白嫖一辆矿车
            self.try_build(f"{pre}_refinery")

        if self.count("radar") == 0 and p.credits >= 1200:
            self.try_build(f"{pre}_radar")
        # 防御
        defenses = self.count("pillbox") + self.count("sentry") + self.count("psychtower") \
            + self.count("prismtower") + self.count("flakcannon") + self.count("gatling")
        if defenses < 2 + (1 if self.diff["name"] == "困难" else 0) and p.credits >= 900:
            key = D.FACTION_BUILD_ORDER[p.faction]["defense"][0 if defenses % 2 == 0 else 1]
            self.try_build(key)
        # 超级武器
        if self.count("radar") > 0:
            sup = {"allied": "a_super", "soviet": "s_super", "yuri": "y_super"}[p.faction]
            if self.count(sup.split("_")[1]) == 0 and p.credits > 5500:
                self.try_build(sup)

        # 部队
        army = [u for u in p.units(w, include_harvester=False)]
        if (need_harv or need_ref) and p.credits < 1600:
            pass                 # 先攒钱补经济，避免断档后无力回天
        elif len(army) < 80 and p.credits > 500:
            self._build_army(army)
        # 进攻
        self._attack(army, cy)
        self._use_superweapon()

    def _build_army(self, army):
        p = self.p
        pre = p.faction
        options = []
        for k in D.FACTION_BUILD_ORDER[pre]["vehicle"]:
            if "harvester" in k:
                continue
            ok, _ = p.buildable(self.world, k)
            if ok:
                cost = D.UNITS[k].cost
                weight = max(1, int(1200 / max(300, cost)))
                options += [k] * weight
        if p.credits < 900:
            for k in D.FACTION_BUILD_ORDER[pre]["infantry"]:
                ok, _ = p.buildable(self.world, k)
                if ok:
                    options.append(k)
        if not options:
            return
        key = self.rng.choice(options)
        d = D.UNITS[key]
        cat = "infantry" if d.tab == "infantry" else "vehicle"
        if len(p.queues[cat]) >= 3:
            return
        if p.credits >= d.cost:
            p.enqueue(self.world, key)

    def _place(self):
        p = self.p
        key = p.pending_placement[0]
        d = D.BUILDINGS[key]
        w = self.world
        cy = self.base_building("cy")
        if cy is not None:
            ox, oy = int(cy.tx), int(cy.ty)
        else:
            own = p.buildings(w)
            if own:
                ox, oy = int(own[0].tx), int(own[0].ty)
            else:
                ox, oy = C.MAP_W // 2, C.MAP_H // 2
        # 防御朝敌方方向推一点
        if d.tab == "defense":
            enemy = self._enemy_base()
            if enemy:
                bx, by = (cy.x, cy.y) if cy else (ox * C.TILE, oy * C.TILE)
                vx, vy = enemy[0] - bx, enemy[1] - by
                n = math.hypot(vx, vy) or 1
                ox = int(ox + vx / n * 3)
                oy = int(oy + vy / n * 3)
        spot = w.find_build_spot(p, key, ox, oy, 22)
        if spot:
            w.place_building(p, key, spot[0], spot[1])
            p.pending_placement.pop(0)
        else:
            # 找不到位置就取消并全额退款，避免占着资金卡生产
            p.pending_placement.pop(0)
            p.refund(d.cost)

    def _enemy_base(self):
        best = None
        bd = 1e18
        me = None
        for e in self.world.entities.values():
            if e.is_building and e.owner is not self.p and not e.dead:
                if best is None:
                    best = e
                d = 0
                if me is None:
                    cy = self.base_building("cy")
                    me = (cy.x, cy.y) if cy else (e.x, e.y)
                d = (e.x - me[0]) ** 2 + (e.y - me[1]) ** 2
                if d < bd:
                    bd = d
                    best = e
        return (best.x, best.y) if best else None

    def _attack(self, army, cy):
        p = self.p
        w = self.world
        if not army:
            return
        base = (cy.x, cy.y) if cy else (army[0].x, army[0].y)
        # 防守：基地附近有敌人
        threat = None
        for e in w.entities.values():
            if e.dead or e.is_building or e.owner is p:
                continue
            if math.hypot(e.x - base[0], e.y - base[1]) < 9 * C.TILE:
                threat = e
                break
        if threat is not None:
            for u in army:
                if u.target_id is None:
                    u.order_attack(w, threat)
            return
        # 集结进攻（留 2 个单位守家，避免全军出击被偷家）
        if self.attack_cd <= 0 and len(army) >= self.diff["threshold"] + 2:
            target = self._enemy_base()
            if target:
                ordered = sorted(army, key=lambda u: (u.x - base[0]) ** 2 + (u.y - base[1]) ** 2)
                for u in ordered[2:]:
                    u.order_move(w, target[0], target[1], attack_move=True)
                self.attack_cd = self.diff["aggression"]
                self.wave_active = True
                self.wave_point = target
                w.add_msg(f"{p.name} 的部队发起了进攻！", p.color)
            else:
                self.attack_cd = 20.0

    def _use_superweapon(self):
        p = self.p
        w = self.world
        for k, st in list(p.sw.items()):
            if not st.get("ready"):
                continue
            sw = D.SUPERWEAPONS[k]
            enemies = [e for e in w.entities.values()
                       if not e.dead and e.owner is not p and not e.is_building]
            center = None
            if enemies:
                best = None
                bestn = -1
                for cand in enemies[:30]:
                    n = sum(1 for e in enemies
                            if math.hypot(e.x - cand.x, e.y - cand.y) <= sw["radius"] * C.TILE)
                    if n > bestn:
                        bestn = n
                        best = cand
                if bestn >= 2:
                    center = (best.x, best.y)
            if center is None:
                eb = self._enemy_base()
                if eb:
                    center = eb
            if center:
                w.fire_superweapon(p, k, center[0], center[1])
