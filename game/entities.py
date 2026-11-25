# -*- coding: utf-8 -*-
"""实体：单位、建筑、弹丸、特效。"""
import math
import random

from . import config as C
from . import data as D
from .nav import FlowField, astar, px_to_tile, tile_center, in_bounds, idx, nearest_free

TAU = math.pi * 2


def angle_to(dx, dy):
    return math.atan2(dy, dx)


def ang_lerp(a, b, t):
    d = (b - a + math.pi) % TAU - math.pi
    return a + d * t


class Entity:
    is_building = False
    is_air = False

    def __init__(self, eid, owner, d, x, y):
        self.id = eid
        self.owner = owner
        self.key = d.key
        self.d = d
        self.name = d.name
        self.max_hp = float(d.hp)
        self.hp = float(d.hp)
        self.armor = d.armor
        self.x = float(x)
        self.y = float(y)
        self.radius = d.radius * C.TILE
        self.sight = d.sight * C.TILE
        self.dead = False
        self.flash = 0.0
        self.kills = 0
        self.vet = 0
        self.last_hit_by = None
        self.sel = False
        self.hidden_by_fog = False

    @property
    def alive(self):
        return not self.dead and self.hp > 0

    def dist_to(self, other):
        return math.hypot(other.x - self.x, other.y - self.y)

    def edge_dist(self, other):
        return max(0.0, self.dist_to(other) - other.radius)

    def center(self):
        return self.x, self.y


class Unit(Entity):
    def __init__(self, eid, owner, d, x, y):
        super().__init__(eid, owner, d, x, y)
        self.is_air = d.is_air
        self.angle = random.uniform(0, TAU)
        self.turret = self.angle
        self.cooldown = 0.0
        self.order = None          # dict: {'type': ..., ...}
        self.dest = None
        self.flow = None
        self.path = []
        self.path_i = 0
        self.repath = 0.0
        self.target_id = None
        self.moving = False
        self.muzzle = 0.0
        self.bob = random.uniform(0, TAU)
        # 采矿
        self.h_state = "idle"
        self.ore_tile = None
        self.cargo = 0.0
        self.unload_t = 0.0
        self.harvest_fx = 0.0
        self.bad_ore = set()      # 寻路不可达的矿点，避免反复卡死
        self.stuck_t = 0.0        # 长时间无法移动的计时（自救用）
        # 心灵控制
        self.master = None
        self.mc_units = []
        self.orig_owner = None
        self.orig_color = None
        # 状态
        self.stun = 0.0
        self.berserk = 0.0
        self.slow = 0.0
        self.spawn_guard = 0.5
        self.suicide_armed = False

    @property
    def weapon(self):
        return D.WEAPONS.get(self.d.weapon) if self.d.weapon else None

    def max_slots(self):
        return self.d.mind_slots

    # ---------------- 指令 ----------------
    def order_move(self, world, x, y, attack_move=False):
        self.order = {"type": "attack_move" if attack_move else "move"}
        self.dest = (x, y)
        self.target_id = None
        self.path = []
        self.flow = world.flow_to_px(x, y)

    def order_attack(self, world, target):
        self.order = {"type": "attack"}
        self.target_id = target.id
        self.flow = None
        self.path = []

    def order_capture(self, world, building):
        self.order = {"type": "capture"}
        self.target_id = building.id
        self.flow = world.flow_to_px(building.x, building.y)
        self.path = []

    def order_harvest(self, world, tx=None, ty=None):
        if not self.d.is_harvester:
            return
        self.order = {"type": "harvest"}
        self.h_state = "seek"
        self.ore_tile = None
        self.flow = None
        self.path = []
        self.target_id = None

    def order_stop(self):
        self.order = None
        self.dest = None
        self.flow = None
        self.path = []
        self.target_id = None
        self.moving = False

    # ---------------- 每帧 ----------------
    def update(self, world, dt):
        if self.dead:
            return
        self.flash = max(0.0, self.flash - dt * 5)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.muzzle = max(0.0, self.muzzle - dt * 6)
        self.spawn_guard = max(0.0, self.spawn_guard - dt)
        if self.stun > 0:
            self.stun -= dt
            self.moving = False
            return
        if self.slow > 0:
            self.slow -= dt
        if self.berserk > 0:
            self.berserk -= dt
            self._update_berserk(world, dt)
            return
        if self.d.is_harvester:
            self._update_harvester(world, dt)
            return
        self._update_combat_unit(world, dt)

    # ---------- 普通战斗单位 ----------
    def _update_combat_unit(self, world, dt):
        order = self.order
        target = world.get(self.target_id)
        if target is not None and target.dead:
            target = None
        if target is None and self.target_id is not None:
            self.target_id = None

        if order is None:
            # 待机自动索敌（不追击，只在射程内开火）
            t = world.acquire_target(self, self.sight, prefer_units=True)
            if t is not None and self.weapon is not None and self.in_range(t):
                self.target_id = t.id
                self._try_fire(world, t, dt)
            self.moving = False
            self._idle_bob(dt)
            return

        typ = order["type"]
        if typ == "move":
            if self.dest is None:
                self.order = None
                return
            self._follow(world, dt)
            if self._arrived():
                self.order = None
                self.flow = None
                self.dest = None
            return

        if typ == "attack_move":
            # 途中索敌
            enemy = world.acquire_target(self, self.sight, prefer_units=True)
            if enemy is not None:
                if self.weapon is None:
                    pass
                elif self.in_range(enemy):
                    self.target_id = enemy.id
                    self._try_fire(world, enemy, dt)
                    self.moving = False
                    return
                else:
                    self.target_id = enemy.id
                    self._chase(world, enemy, dt)
                    return
            if self.dest is None:
                self.order = None
                return
            self._follow(world, dt)
            if self._arrived():
                self.order = None
                self.flow = None
                self.dest = None
            return

        if typ == "attack":
            if target is None:
                self.order = None
                self.moving = False
                return
            if self.weapon is None:
                self.order = None
                return
            if self.in_range(target):
                self.moving = False
                self._try_fire(world, target, dt)
            else:
                self._chase(world, target, dt)
            return

        if typ == "capture":
            if target is None or target.dead:
                self.order = None
                return
            if self.dist_to(target) < target.radius + self.radius + 12:
                world.engineer_capture(self, target)
                return
            self._chase(world, target, dt)
            return

    def _update_berserk(self, world, dt):
        t = world.get(self.target_id)
        if t is None or t.dead or world.get(t.id) is None:
            t = world.nearest_entity_any(self.x, self.y, 6 * C.TILE)
            self.target_id = t.id if t else None
        if t is None:
            self.moving = False
            return
        if self.in_range(t):
            self.moving = False
            self._try_fire(world, t, dt)
        else:
            self._chase(world, t, dt)

    # ---------- 移动 ----------
    def _arrived(self):
        if self.dest is None:
            return True
        return math.hypot(self.dest[0] - self.x, self.dest[1] - self.y) < 10

    def _follow(self, world, dt):
        if self.dest is None:
            return
        if self._arrived():
            return
        tx, ty = self.dest
        if self.flow is not None:
            cx, cy = px_to_tile(self.x, self.y)
            nxt = self.flow.step_from(cx, cy, world.blocked)
            if nxt is not None:
                tx, ty = tile_center(*nxt)
        self._step(world, tx, ty, dt)

    def _chase(self, world, target, dt):
        if self.is_air:
            self._step(world, target.x, target.y, dt, ignore_terrain=True)
            return
        d = self.dist_to(target)
        self.repath -= dt
        if self.flow is None or self.repath <= 0:
            self.repath = 0.45
            self.flow = world.flow_to_px(target.x, target.y)
        cx, cy = px_to_tile(self.x, self.y)
        nxt = self.flow.step_from(cx, cy, world.blocked) if self.flow else None
        if nxt is not None and math.hypot(target.x - self.x, target.y - self.y) > 2.2 * C.TILE:
            self._step(world, *tile_center(*nxt), dt)
        else:
            self._step(world, target.x, target.y, dt)

    def _step(self, world, tx, ty, dt, ignore_terrain=False):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 0.01:
            self.moving = False
            return
        speed = self.d.speed * C.TILE
        if self.slow > 0:
            speed *= 0.55
        step = speed * dt
        if step > dist:
            step = dist
        ux, uy = dx / dist, dy / dist
        # 单位间分离
        sx, sy = world.separation(self)
        ux += sx * 0.55
        uy += sy * 0.55
        n = math.hypot(ux, uy) or 1.0
        ux, uy = ux / n, uy / n
        nx = self.x + ux * step
        ny = self.y + uy * step
        if not ignore_terrain:
            if world.point_blocked(nx, self.y, self.radius * 0.6):
                nx = self.x
            if world.point_blocked(self.x, ny, self.radius * 0.6):
                ny = self.y
        self.x = max(8.0, min(nx, C.WORLD_W - 8))
        self.y = max(8.0, min(ny, C.WORLD_H - 8))
        self.angle = ang_lerp(self.angle, math.atan2(uy, ux), min(1.0, dt * 8))
        self.moving = True
        self._idle_bob(dt)

    def _idle_bob(self, dt):
        if self.moving:
            self.bob += dt * self.d.speed * 5.0
        else:
            self.bob += dt * 1.5

    # ---------- 攻击 ----------
    def in_range(self, target):
        w = self.weapon
        if w is None:
            return False
        if target.is_air and not w.can_air:
            return False
        if (not target.is_air) and not w.can_ground:
            return False
        return self.edge_dist(target) <= w.range * C.TILE

    def _try_fire(self, world, target, dt):
        w = self.weapon
        if w is None or self.cooldown > 0 or not self.alive:
            return
        if target is None or target.dead:
            return
        if target.is_air and not w.can_air:
            return
        if (not target.is_air) and not w.can_ground:
            return
        if self.edge_dist(target) > w.range * C.TILE:
            return
        want = angle_to(target.x - self.x, target.y - self.y)
        self.turret = ang_lerp(self.turret, want, min(1.0, dt * 10))
        diff = abs(((want - self.turret + math.pi) % TAU) - math.pi)
        if diff > 0.45 and not self.is_air:
            return
        if self.d.suicide:
            world.detonate_unit(self, target)
            return
        self.cooldown = w.rof
        self.muzzle = 1.0
        if self.d.mind_slots and w.effect == "mc":
            if world.try_mind_control(self, target):
                world.spawn_effect("mind", target.x, target.y, 0.7, color=w.color)
                return
        world.fire_weapon(self, target, w)

    # ---------- 采矿车 ----------
    def _update_harvester(self, world, dt):
        self.harvest_fx = max(0.0, self.harvest_fx - dt)
        if self.order is not None and self.order.get("type") in ("move", "attack_move"):
            self._follow(world, dt)
            if self._arrived():
                self.order = None
                self.dest = None
                self.flow = None
                self.h_state = "seek"
                self.path = []
            return
        if self.h_state == "seek":
            if self.cargo >= C.REFINERY_STORAGE - 0.01:
                self.h_state = "return"
                return
            if not self.moving:
                self.stuck_t += dt
                if self.stuck_t > 12.0:
                    # 自救：被建筑围死或矿点不可达时，回到精炼厂卸货点重新出发
                    ref = world.nearest_refinery(self.owner, self.x, self.y)
                    if ref is not None:
                        dx, dy = ref.dock_point()
                        self.x, self.y = world.free_spot(dx, dy, self.radius + 4)
                    self.bad_ore.clear()
                    self.ore_tile = None
                    self.path = []
                    self.stuck_t = 0.0
            else:
                self.stuck_t = 0.0
            if self.ore_tile is None or world.ore_amount(*self.ore_tile) <= 0:
                self.ore_tile = world.nearest_ore(self.x, self.y, self.bad_ore)
                if self.ore_tile is None:
                    self.moving = False
                    if self.cargo > 0:
                        self.h_state = "return"
                    return
                self.path = []
                self.repath = 0
            tx, ty = tile_center(*self.ore_tile)
            if math.hypot(tx - self.x, ty - self.y) < C.TILE * 0.6:
                self.h_state = "harvest"
                self.moving = False
                return
            if not self._move_path(world, tx, ty, dt):
                # 该矿点不可达（隔着水域/建筑），拉黑后换下一个
                self.bad_ore.add(self.ore_tile)
                self.ore_tile = None
                self.path = []
                if len(self.bad_ore) > 400:
                    self.bad_ore.clear()
        elif self.h_state == "harvest":
            amount = world.harvest_tile(self.ore_tile, C.HARVEST_RATE * dt,
                                        C.REFINERY_STORAGE - self.cargo)
            if amount > 0:
                self.cargo += amount
                self.harvest_fx = 0.25
                self.moving = False
            if self.cargo >= C.REFINERY_STORAGE - 0.01:
                self.h_state = "return"
                self.path = []
            elif world.ore_amount(*self.ore_tile) <= 0:
                self.ore_tile = None
                self.h_state = "seek"
        elif self.h_state == "return":
            ref = world.nearest_refinery(self.owner, self.x, self.y)
            if ref is None:
                self.moving = False
                return
            dock = ref.dock_point()
            if math.hypot(dock[0] - self.x, dock[1] - self.y) < C.TILE * 0.9:
                self.h_state = "unload"
                self.unload_t = 1.4
                self.moving = False
                return
            self._move_path(world, dock[0], dock[1], dt)
        elif self.h_state == "unload":
            self.moving = False
            self.unload_t -= dt
            if self.unload_t <= 0:
                if self.cargo > 0 and self.owner is not None:
                    self.owner.earn(self.cargo, source="harvest")
                self.cargo = 0.0
                self.h_state = "seek"
                self.ore_tile = None
                self.path = []
        else:
            self.moving = False

    def _move_path(self, world, tx, ty, dt):
        """沿 A* 路径移动；无可行路径时返回 False。"""
        self.repath -= dt
        if not self.path or self.repath <= 0:
            self.repath = 1.2
            start = px_to_tile(self.x, self.y)
            goal = px_to_tile(tx, ty)
            if world.point_blocked(*tile_center(*goal), 2):
                g2 = nearest_free(world.blocked, *goal)
                goal = g2 or goal
            p = astar(world.blocked, start, goal)
            if not p:
                self.path = []
                self._step(world, tx, ty, dt)
                return False
            self.path = [tile_center(*p[i]) for i in range(len(p))]
            self.path_i = 1 if len(self.path) > 1 else 0
        if not self.path:
            self._step(world, tx, ty, dt)
            return True
        while self.path_i < len(self.path) and math.hypot(
                self.path[self.path_i][0] - self.x, self.path[self.path_i][1] - self.y) < C.TILE * 0.5:
            self.path_i += 1
        if self.path_i >= len(self.path):
            self.path = []
            self._step(world, tx, ty, dt)
            return True
        self._step(world, *self.path[self.path_i], dt)
        return True


class Building(Entity):
    is_building = True
    is_air = False

    def __init__(self, eid, owner, d, tx, ty):
        self.tx = tx
        self.ty = ty
        self.w = d.w
        self.h = d.h
        x = (tx + d.w / 2.0) * C.TILE
        y = (ty + d.h / 2.0) * C.TILE
        super().__init__(eid, owner, d, x, y)
        self.radius = max(d.w, d.h) * C.TILE * 0.45
        self.built = True
        self.construct_t = C.CONSTRUCTION_ANIM
        if self.construct_t > 0:
            self.hp = max(1.0, self.max_hp * 0.15)
        self.cooldown = 0.0
        self.muzzle = 0.0
        self.rally = None
        self.repair = False
        self.super_key = d.superweapon
        self.spawn_base = 0.0
        self.sel = False

    @property
    def weapon(self):
        return D.WEAPONS.get(self.d.weapon) if self.d.weapon else None

    def dock_point(self):
        return (self.x, (self.ty + self.h) * C.TILE + C.TILE * 0.9)

    def update(self, world, dt):
        if self.dead:
            return
        self.flash = max(0.0, self.flash - dt * 5)
        self.muzzle = max(0.0, self.muzzle - dt * 6)
        if self.construct_t > 0:
            self.construct_t -= dt
            frac = 1.0 - max(0.0, self.construct_t) / C.CONSTRUCTION_ANIM
            self.hp = min(self.max_hp, self.max_hp * (0.15 + 0.85 * frac))
            if self.construct_t <= 0:
                self.construct_t = 0.0
                self.hp = self.max_hp
                self.built = True
                world.on_building_complete(self)
            return
        w = self.weapon
        if w is None:
            return
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.cooldown > 0:
            return
        t = world.acquire_target(self, w.range * C.TILE, prefer_units=True)
        if t is None:
            return
        self.cooldown = w.rof * (1.5 if self.owner.power_low else 1.0)
        self.muzzle = 1.0
        world.fire_weapon(self, t, w)


class Projectile:
    def __init__(self, owner, weapon, x, y, target=None, target_pos=None):
        self.owner = owner            # 发射者实体
        self.attacker_ref = owner
        self.w = weapon
        self.x = x
        self.y = y
        self.target_id = target.id if target else None
        self.tx, self.ty = target_pos if target_pos else (x, y)
        if target is not None:
            self.tx, self.ty = target.x, target.y
        self.speed = weapon.speed * C.TILE
        self.kind = weapon.projectile
        self.dead = False
        self.ttl = 6.0
        self.angle = math.atan2(self.ty - y, self.tx - x)
        self.arc_h = 0.0
        self.start = (x, y)

    def update(self, world, dt):
        if self.dead:
            return
        self.ttl -= dt
        target = world.get(self.target_id) if self.target_id else None
        if target is not None and not target.dead:
            self.tx, self.ty = target.x, target.y
        dx, dy = self.tx - self.x, self.ty - self.y
        dist = math.hypot(dx, dy)
        if self.ttl <= 0:
            self.dead = True
            return
        step = self.speed * dt
        if self.kind == "bomb":
            step = max(step, 60)
        if dist <= step or dist < 6:
            self.dead = True
            world.projectile_hit(self)
            return
        self.angle = math.atan2(dy, dx)
        self.x += dx / dist * step
        self.y += dy / dist * step


class Effect:
    def __init__(self, kind, x, y, dur, radius=0.0, color=(255, 200, 120), text="", data=None):
        self.kind = kind
        self.x = x
        self.y = y
        self.dur = dur
        self.t = 0.0
        self.radius = radius
        self.color = color
        self.text = text
        self.data = data or {}
        self.dead = False

    def update(self, dt):
        self.t += dt
        if self.t >= self.dur:
            self.dead = True
