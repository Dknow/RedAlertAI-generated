# -*- coding: utf-8 -*-
"""玩家：资金、生产队列、建筑放置、超级武器状态。"""
from . import config as C
from . import data as D


class Player:
    def __init__(self, pid, faction, name, is_ai=False, income_mult=1.0, speed_mult=1.0):
        self.pid = pid
        self.faction = faction
        self.name = name
        self.is_ai = is_ai
        self.color = C.FACTION_INFO[faction]["color"]
        self.income_mult = income_mult
        self.speed_mult = speed_mult
        self.credits = float(C.START_CREDITS)
        self.queues = {"structure": [], "infantry": [], "vehicle": []}
        self.pending_placement = []
        self.sw = {}
        self.power_produced = 0.0
        self.power_used = 0.0
        self.power_low = False
        self.stats = {"earned": 0, "spent": 0, "kills": 0, "lost": 0, "built": 0}
        self.ai = None
        self.defeated = False

    # ---------------- 经济 ----------------
    def earn(self, amount, source="harvest"):
        amount *= self.income_mult
        self.credits = min(self.credits + amount, 999999)
        self.stats["earned"] += amount

    def spend(self, amount):
        if self.credits + 1e-6 < amount:
            return False
        self.credits -= amount
        self.stats["spent"] += amount
        return True

    def refund(self, amount):
        self.credits += amount
        self.stats["spent"] = max(0, self.stats["spent"] - amount)

    # ---------------- 查询 ----------------
    def buildings(self, world, include_unbuilt=False):
        out = []
        for e in world.entities.values():
            if e.dead or not e.is_building or e.owner is not self:
                continue
            if not include_unbuilt and e.construct_t > 0:
                continue
            out.append(e)
        return out

    def units(self, world, include_harvester=True):
        out = []
        for e in world.entities.values():
            if e.dead or e.is_building or e.owner is not self:
                continue
            if not include_harvester and e.d.is_harvester:
                continue
            out.append(e)
        return out

    def has_building(self, world, key):
        for e in world.entities.values():
            if e.dead or not e.is_building or e.owner is not self:
                continue
            if e.key == key:
                return True
        return False

    def count_building(self, world, key):
        n = 0
        for e in world.entities.values():
            if e.dead or not e.is_building or e.owner is not self:
                continue
            if e.key == key:
                n += 1
        return n

    def radar_built(self, world):
        return self.has_building(world, f"{self.faction[0]}_{'radar'}")

    def has_cy(self, world):
        return self.has_building(world, f"{self.faction[0]}_cy")

    def producer(self, world, tab):
        want = "barracks" if tab == "infantry" else "factory"
        for e in world.entities.values():
            if e.dead or not e.is_building or e.owner is not self:
                continue
            if e.key == f"{self.faction[0]}_{want}" and e.construct_t <= 0:
                return e
        return None

    def buildable(self, world, key):
        d = D.get_def(key)
        if d.faction != self.faction:
            return False, "阵营不符"
        if key.endswith("_cy") and self.has_cy(world):
            return False, "已有建造厂"
        if isinstance(d, D.BuildingDef):
            if d.superweapon and self.has_building(world, key):
                return False, "已建造超级武器"
            if key.endswith("_cy"):
                if self.has_cy(world):
                    return False, "已有建造厂"
            elif not self.has_cy(world):
                return False, "需要建造厂"
        else:
            if self.producer(world, d.tab) is None:
                need = "兵营" if d.tab == "infantry" else "战车工厂"
                return False, f"需要{need}"
        for p in d.prereq:
            if not self.has_building(world, p):
                return False, f"需要{D.BUILDINGS[p].name}"
        if d.tier >= 2 and not key.endswith("_radar") and not self.radar_built(world):
            return False, "需要雷达站"
        return True, ""

    def queue_len(self, cat):
        return len(self.queues[cat])

    # ---------------- 生产 ----------------
    def enqueue(self, world, key):
        d = D.get_def(key)
        ok, reason = self.buildable(world, key)
        if not ok:
            return False, reason
        cat = "structure" if isinstance(d, D.BuildingDef) else (
            "infantry" if d.tab == "infantry" else "vehicle")
        if len(self.queues[cat]) >= 7:
            return False, "生产队列已满"
        if not self.spend(d.cost):
            return False, "资金不足"
        self.queues[cat].append({
            "key": key, "remaining": d.build_time, "total": d.build_time,
            "cost": d.cost, "kind": "building" if isinstance(d, D.BuildingDef) else "unit",
        })
        return True, ""

    def cancel(self, cat, index):
        q = self.queues[cat]
        if 0 <= index < len(q):
            item = q.pop(index)
            self.refund(item["cost"])
            return True
        return False

    def cancel_key(self, world, key):
        for cat in ("structure", "infantry", "vehicle"):
            for i, it in enumerate(self.queues[cat]):
                if it["key"] == key:
                    self.cancel(cat, i)
                    return True
        return False

    def cancel_placement(self):
        if self.pending_placement:
            key = self.pending_placement.pop(0)
            self.refund(D.BUILDINGS[key].cost)
            return key
        return None

    def tick(self, world, dt):
        for cat in ("structure", "infantry", "vehicle"):
            q = self.queues[cat]
            if not q:
                continue
            if cat == "structure" and self.pending_placement:
                continue
            item = q[0]
            rate = 0.6 if self.power_low else 1.0
            item["remaining"] -= dt * rate * self.speed_mult
            if item["remaining"] <= 0:
                q.pop(0)
                if item["kind"] == "building":
                    self.pending_placement.append(item["key"])
                else:
                    world.spawn_unit(self, item["key"])
                    self.stats["built"] += 1

        # 超级武器充能
        present = set()
        for b in self.buildings(world):
            if b.super_key:
                present.add(b.super_key)
        for k in list(self.sw.keys()):
            if k not in present:
                del self.sw[k]
        for k in present:
            st = self.sw.setdefault(k, {"t": 0.0, "ready": False})
            if not st["ready"]:
                st["t"] += dt * (0.55 if self.power_low else 1.0)
                if st["t"] >= C.SUPERWEAPON_CHARGE:
                    st["t"] = C.SUPERWEAPON_CHARGE
                    st["ready"] = True

    def superweapon_ready(self, key):
        st = self.sw.get(key)
        return bool(st and st["ready"])

    def superweapon_consume(self, key):
        st = self.sw.get(key)
        if st and st["ready"]:
            st["ready"] = False
            st["t"] = 0.0
            return True
        return False

    def power_ratio(self):
        if self.power_used <= 0:
            return 1.0
        return min(1.0, self.power_produced / max(1.0, self.power_used))
