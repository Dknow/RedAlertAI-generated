# -*- coding: utf-8 -*-
"""侧边栏 UI：小地图、电力、资金、建造按钮、队列、信息面板、提示。"""
import math

import pygame

from . import config as C
from . import data as D
from . import fonts as F
from .nav import px_to_tile

SB_X = C.VIEW_W
PAD = 12
MM = pygame.Rect(SB_X + 14, 12, 208, 208)

TAB_ORDER = [
    ("structure", "建筑"), ("defense", "防御"), ("infantry", "步兵"),
    ("vehicle", "载具"), ("air", "空军"), ("special", "超武"),
]


class UI:
    def __init__(self, world, renderer, audio):
        self.world = world
        self.renderer = renderer
        self.audio = audio
        self.tab = "structure"
        self.tab_rects = []
        self.btn_rects = []
        self.queue_rects = []
        self.info_btns = []
        self.hover_btn = None
        self.selected = None

    # ---------------- 图标 ----------------
    def icon(self, key, size=40):
        ck = (key, size)
        cached = getattr(self, "_icons", None)
        if cached is None:
            self._icons = {}
            cached = self._icons
        s = cached.get(ck)
        if s is not None:
            return s
        fac = D.get_def(key).faction
        if key in D.UNITS:
            body, _, _ = self.renderer._unit_sprites(key, fac, 0)
            src = body
        else:
            src = self.renderer._draw_building(key, D.BUILDINGS[key], fac)
        w, h = src.get_size()
        k = min(size / max(1, w), size / max(1, h))
        nw, nh = max(1, int(w * k)), max(1, int(h * k))
        out = pygame.Surface((size, size), pygame.SRCALPHA)
        sc = pygame.transform.smoothscale(src, (nw, nh))
        out.blit(sc, ((size - nw) // 2, (size - nh) // 2))
        cached[ck] = out
        return out

    # ---------------- 点击 ----------------
    def handle_click(self, pos, button, game):
        for r, act in self.info_btns:
            if r.collidepoint(pos):
                self._info_action(act, game)
                return True
        if not (pos[0] >= SB_X):
            return False
        if MM.collidepoint(pos):
            wx = (pos[0] - MM.x) / MM.w * C.WORLD_W
            wy = (pos[1] - MM.y) / MM.h * C.WORLD_H
            game.center_camera(wx, wy)
            return True
        for r, key in self.tab_rects:
            if r.collidepoint(pos):
                if self.tab != key:
                    self.tab = key
                    self.audio.play("click")
                return True
        for r, key in self.btn_rects:
            if r.collidepoint(pos):
                if button == 3:
                    if game.players[0].cancel_key(self.world, key):
                        self.audio.play("click")
                    else:
                        self.audio.play("error")
                else:
                    self.activate(key, game)
                return True
        for r, cat, idx in self.queue_rects:
            if r.collidepoint(pos):
                if game.players[0].cancel(cat, idx):
                    self.audio.play("click")
                return True
        return True

    def _info_action(self, act, game):
        sel = game.selected
        if not sel:
            return
        e = sel[0]
        if act == "sell" and e.is_building and e.owner is game.players[0]:
            self.world.sell_building(e)
            game.selected = [x for x in game.selected if not x.dead]
            self.audio.play("sell")
        elif act == "repair" and e.is_building and e.owner is game.players[0]:
            e.repair = not e.repair
            self.audio.play("click")
            if e.repair:
                self.world.add_msg(f"开始修理 {e.name}", C.C_OK)

    def activate(self, key, game):
        p = game.players[0]
        d = D.get_def(key)
        if isinstance(d, D.BuildingDef) and d.superweapon:
            st = p.sw.get(d.superweapon)
            if p.has_building(self.world, key):
                if st and st["ready"]:
                    game.super_target = d.superweapon
                    self.world.add_msg(f"选择 {D.SUPERWEAPONS[d.superweapon]['name']} 的目标位置", d_color(d))
                else:
                    self.audio.play("error")
                    self.world.add_msg("超级武器仍在充能中", C.C_BAD)
                return
        ok, reason = p.enqueue(self.world, key)
        if ok:
            self.audio.play("click")
            if isinstance(d, D.BuildingDef):
                pass
        else:
            self.audio.play("error")
            self.world.add_msg(reason, C.C_BAD)

    # ---------------- 绘制 ----------------
    def draw(self, screen, game):
        self._draw_sidebar(screen, game)
        self._draw_messages(screen)
        self._draw_superbar(screen, game)
        self._draw_info(screen, game)
        self._draw_tooltip(screen, game)

    def _draw_sidebar(self, screen, game):
        p = game.players[0]
        pygame.draw.rect(screen, C.C_SIDEBAR, (SB_X, 0, C.SIDEBAR_W, C.SCREEN_H))
        pygame.draw.rect(screen, (54, 62, 72), (SB_X, 0, 2, C.SCREEN_H))
        pygame.draw.line(screen, (60, 70, 82), (SB_X + 12, 226), (SB_X + 224, 226))
        # 小地图
        screen.blit(self.renderer.minimap_base, MM.topleft)
        self._draw_minimap_entities(screen)
        pygame.draw.rect(screen, (78, 90, 104), MM, 1)
        cam = game.cam
        sc = MM.w / C.WORLD_W
        cr = pygame.Rect(MM.x + cam[0] * sc, MM.y + cam[1] * sc,
                         C.VIEW_W * sc, C.VIEW_H * sc)
        pygame.draw.rect(screen, (230, 240, 230), cr, 1)
        # 电力
        pygame.draw.rect(screen, (16, 20, 24), (SB_X + 14, 234, 208, 14))
        prod, used = p.power_produced, p.power_used
        ratio = min(1.0, prod / used) if used > 0 else 1.0
        col = (220, 70, 60) if p.power_low else (80, 200, 120)
        pygame.draw.rect(screen, col, (SB_X + 14, 234, int(208 * ratio), 14))
        pygame.draw.rect(screen, (70, 80, 92), (SB_X + 14, 234, 208, 14), 1)
        F.text(screen, f"电力  {int(prod)}/{int(used)}", (SB_X + 118, 235), 12,
               (240, 240, 240), align="center")
        # 资金
        F.text(screen, "资金", (SB_X + 16, 256), 13, C.C_TEXT_DIM)
        F.text(screen, f"$ {int(p.credits):,}", (SB_X + 222, 252), 22, C.C_ACCENT, bold=True, align="right")
        # 标签
        self.tab_rects = []
        idx = 0
        for row in range(2):
            for col in range(3):
                if idx >= len(TAB_ORDER):
                    break
                key, name = TAB_ORDER[idx]
                r = pygame.Rect(SB_X + 14 + col * 74, 282 + row * 30, 70, 26)
                active = self.tab == key
                pygame.draw.rect(screen, (46, 58, 70) if active else (30, 37, 44), r, border_radius=3)
                pygame.draw.rect(screen, C.C_ACCENT if active else (56, 66, 78), r, 1, border_radius=3)
                F.text(screen, name, (r.centerx, r.y + 6), 13,
                       (255, 236, 200) if active else C.C_TEXT_DIM, align="center")
                self.tab_rects.append((r, key))
                idx += 1
        # 建造按钮
        self.btn_rects = []
        keys = D.FACTION_BUILD_ORDER[p.faction].get(self.tab, [])
        for i, key in enumerate(keys[:6]):
            col = i % 2
            row = i // 2
            r = pygame.Rect(SB_X + 14 + col * 110, 346 + row * 70, 104, 64)
            self._draw_build_button(screen, r, key, p)
            self.btn_rects.append((r, key))
        # 队列
        self._draw_queue(screen, p)
        F.text(screen, "空格：回到基地   ESC：菜单   M：静音", (SB_X + 122, 730), 11,
               (110, 120, 132), align="center")

    def _draw_build_button(self, screen, r, key, p):
        d = D.get_def(key)
        ok, reason = p.buildable(self.world, key)
        hover = r.collidepoint(pygame.mouse.get_pos())
        base = (42, 50, 60) if ok else (30, 34, 40)
        if hover:
            base = (56, 66, 78) if ok else (38, 42, 48)
        pygame.draw.rect(screen, base, r, border_radius=4)
        pygame.draw.rect(screen, (76, 88, 102) if ok else (48, 54, 62), r, 1, border_radius=4)
        screen.blit(self.icon(key, 40), (r.x + 5, r.y + 5))
        name_col = C.C_TEXT if ok else (120, 126, 134)
        F.text(screen, d.name, (r.x + 49, r.y + 6), 12, name_col)
        F.text(screen, f"${d.cost}", (r.x + 49, r.y + 23), 13,
               C.C_ACCENT if ok else (120, 106, 70))
        q = None
        cat = "structure" if isinstance(d, D.BuildingDef) else (
            "infantry" if d.tab == "infantry" else "vehicle")
        for it in p.queues[cat]:
            if it["key"] == key:
                q = it
                break
        if q is not None:
            frac = 1.0 - max(0.0, q["remaining"]) / q["total"]
            is_active = p.queues[cat] and p.queues[cat][0] is q
            pygame.draw.rect(screen, (16, 18, 20), (r.x + 5, r.y + r.h - 9, r.w - 10, 4))
            pygame.draw.rect(screen, (110, 210, 120), (r.x + 5, r.y + r.h - 9, int((r.w - 10) * frac), 4))
            if is_active:
                pygame.draw.rect(screen, (150, 240, 160), r, 1, border_radius=4)
            n = sum(1 for it in p.queues[cat] if it["key"] == key)
            if n > 1:
                F.text(screen, f"x{n}", (r.right - 6, r.y + 5), 12, (220, 240, 220), align="right")
        if isinstance(d, D.BuildingDef) and d.superweapon and p.has_building(self.world, key):
            st = p.sw.get(d.superweapon)
            if st and st["ready"]:
                wv = int(3 + 3 * abs(math.sin(pygame.time.get_ticks() / 260)))
                pygame.draw.rect(screen, (240, 200, 90), r.inflate(wv * 2, wv * 2), 2, border_radius=6)
                F.text(screen, "就绪", (r.x + 6, r.y + r.h - 18), 11, (255, 230, 140))
        if not ok:
            dim = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            dim.fill((8, 10, 12, 110))
            screen.blit(dim, r.topleft)

    def _draw_queue(self, screen, p):
        F.text(screen, "生产队列", (SB_X + 16, 556), 13, C.C_TEXT_DIM)
        self.queue_rects = []
        y = 578
        for cat, label in (("structure", "建筑"), ("infantry", "步兵"), ("vehicle", "载具")):
            F.text(screen, label, (SB_X + 16, y + 3), 11, (130, 140, 152))
            x = SB_X + 56
            for i, it in enumerate(p.queues[cat][:7]):
                r = pygame.Rect(x, y, 24, 24)
                pygame.draw.rect(screen, (24, 28, 34), r, border_radius=3)
                screen.blit(self.icon(it["key"], 20), (x + 2, y + 2))
                frac = 1.0 - max(0.0, it["remaining"]) / it["total"]
                if i == 0:
                    pygame.draw.rect(screen, (120, 220, 140), (x, y + 22, int(24 * frac), 2))
                self.queue_rects.append((r, cat, i))
                x += 28
            y += 30

    def _draw_minimap_entities(self, screen):
        sc = MM.w / C.WORLD_W
        w = self.world
        for i in range(0, C.MAP_W * C.MAP_H):
            if w.ore[i] > 0 and w.explored[i]:
                x, y = i % C.MAP_W, i // C.MAP_W
                screen.set_at((MM.x + int(x * sc), MM.y + int(y * sc)), (214, 176, 48))
        for e in w.entities.values():
            if e.dead:
                continue
            if e.owner is not w.players[0] and not w.entity_visible(e):
                continue
            x = MM.x + int(e.x / C.WORLD_W * MM.w)
            y = MM.y + int(e.y / C.WORLD_H * MM.h)
            col = e.owner.color if e.owner else (200, 200, 200)
            if e.is_building:
                r = 2 if e.d.w <= 2 else 3
                pygame.draw.rect(screen, col, (x - r, y - r, r * 2, r * 2))
            else:
                screen.set_at((x, y), col)
                if e.sel:
                    pygame.draw.circle(screen, (255, 255, 255), (x, y), 2, 1)

    # ---------------- 消息 / 超武 / 信息 ----------------
    def _draw_messages(self, screen):
        w = self.world
        y = 10
        for m in w.messages[-6:]:
            age = w.time - m["t"]
            a = 255 if age < 6 else max(0, int(255 * (1 - (age - 6) / 2)))
            if a <= 0:
                continue
            col = (min(255, m["color"][0] + 20), min(255, m["color"][1] + 20),
                   min(255, m["color"][2] + 20))
            img = F.font(13).render(m["text"], True, col)
            img.set_alpha(a)
            bg = pygame.Surface((img.get_width() + 12, img.get_height() + 4), pygame.SRCALPHA)
            bg.fill((8, 10, 12, min(150, a)))
            screen.blit(bg, (10, y))
            screen.blit(img, (16, y + 2))
            y += img.get_height() + 7

    def _draw_superbar(self, screen, game):
        p = game.players[0]
        items = list(p.sw.items())
        if not items:
            return
        x = C.VIEW_W // 2 - 100
        for k, st in items:
            sw = D.SUPERWEAPONS[k]
            r = pygame.Rect(x, 10, 200, 40)
            pygame.draw.rect(screen, (14, 18, 22), r, border_radius=4)
            pygame.draw.rect(screen, (70, 80, 92), r, 1, border_radius=4)
            pygame.draw.circle(screen, sw["color"], (r.x + 18, r.y + 20), 9, 2)
            F.text(screen, sw["name"], (r.x + 34, r.y + 6), 12, (220, 226, 232))
            if st["ready"]:
                blink = int(180 + 70 * math.sin(pygame.time.get_ticks() / 200))
                F.text(screen, "就绪 · 点击超武按钮", (r.x + 34, r.y + 23), 11, (blink, 230, 150))
            else:
                rem = max(0, int(C.SUPERWEAPON_CHARGE - st["t"]))
                mm, ss = rem // 60, rem % 60
                F.text(screen, f"充能 {mm:02d}:{ss:02d}", (r.x + 34, r.y + 23), 11, (150, 160, 172))
                frac = st["t"] / C.SUPERWEAPON_CHARGE
                pygame.draw.rect(screen, (18, 22, 28), (r.x + 34, r.y + 35, 154, 3))
                pygame.draw.rect(screen, sw["color"], (r.x + 34, r.y + 35, int(154 * frac), 3))
            x += 210

    def _draw_info(self, screen, game):
        sel = [e for e in game.selected if not e.dead]
        self.selected = sel[0] if sel else None
        self.info_btns = []
        if not sel:
            return
        r = pygame.Rect(12, C.SCREEN_H - 132, 336, 118)
        bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        bg.fill((14, 18, 22, 215))
        screen.blit(bg, r.topleft)
        pygame.draw.rect(screen, (70, 82, 96), r, 1, border_radius=4)
        e = sel[0]
        screen.blit(self.icon(e.key, 56), (r.x + 8, r.y + 8))
        F.text(screen, e.name, (r.x + 72, r.y + 8), 15, C.C_TEXT, bold=True)
        if len(sel) > 1:
            F.text(screen, f"已选择 {len(sel)} 个单位", (r.right - 8, r.y + 10), 11,
                   C.C_TEXT_DIM, align="right")
        F.text(screen, f"{D.ARMOR_NAMES.get(e.armor, e.armor)}", (r.x + 72, r.y + 30), 11,
               C.C_TEXT_DIM)
        # 血条
        hb = pygame.Rect(r.x + 72, r.y + 46, r.w - 90, 8)
        pygame.draw.rect(screen, (20, 22, 26), hb)
        fr = max(0.0, e.hp / e.max_hp)
        col = (90, 210, 110) if fr > 0.5 else ((230, 190, 70) if fr > 0.25 else (220, 70, 60))
        pygame.draw.rect(screen, col, (hb.x, hb.y, int(hb.w * fr), hb.h))
        F.text(screen, f"{int(e.hp)}/{int(e.max_hp)}", (hb.right - 2, r.y + 42), 11,
               (230, 230, 230), align="right")
        w = e.weapon if hasattr(e, "weapon") else None
        if w is not None:
            F.text(screen, f"{w.name}  伤害 {int(w.damage)}  射程 {w.range:.1f}格  "
                           f"{D.WARHEAD_NAMES.get(w.warhead, w.warhead)}",
                   (r.x + 72, r.y + 58), 11, (180, 190, 200))
        elif not e.is_building and e.d.is_harvester:
            F.text(screen, f"矿石 {int(e.cargo)}/{C.REFINERY_STORAGE}", (r.x + 72, r.y + 58), 11, (220, 190, 90))
        desc = e.d.desc
        for i, line in enumerate(F.wrap(desc, 11, r.w - 88)[:2]):
            F.text(screen, line, (r.x + 72, r.y + 74 + i * 14), 11, (150, 160, 170))
        if e.is_building and e.owner is game.players[0]:
            rb = pygame.Rect(r.right - 88, r.bottom - 24, 38, 18)
            rs = pygame.Rect(r.right - 46, r.bottom - 24, 38, 18)
            pygame.draw.rect(screen, (56, 42, 46) if e.repair else (40, 48, 58), rb, border_radius=3)
            pygame.draw.rect(screen, (70, 82, 96), rb, 1, border_radius=3)
            F.text(screen, "修理", (rb.x + 1, rb.y + 2), 11, (220, 230, 240))
            pygame.draw.rect(screen, (58, 38, 38), rs, border_radius=3)
            pygame.draw.rect(screen, (96, 70, 70), rs, 1, border_radius=3)
            F.text(screen, "出售", (rs.x + 1, rs.y + 2), 11, (240, 200, 200))
            self.info_btns = [(rb, "repair"), (rs, "sell")]

    def _draw_tooltip(self, screen, game):
        mx, my = pygame.mouse.get_pos()
        key = None
        if mx >= SB_X:
            for r, k in self.btn_rects:
                if r.collidepoint(mx, my):
                    key = k
                    break
        if key is None:
            return
        p = game.players[0]
        d = D.get_def(key)
        lines = [f"{d.name}    ${d.cost}"]
        if isinstance(d, D.UnitDef):
            lines.append(f"生命 {d.hp}   装甲 {D.ARMOR_NAMES.get(d.armor, d.armor)}   速度 {d.speed:.1f}")
            if d.weapon:
                w = D.WEAPONS[d.weapon]
                lines.append(f"武器 {w.name}：伤害 {int(w.damage)} / 射程 {w.range:.1f}格 / "
                             f"{D.WARHEAD_NAMES.get(w.warhead, w.warhead)}")
        else:
            lines.append(f"生命 {d.hp}   电力 {'+' if d.power >= 0 else ''}{d.power}   占地 {d.w}x{d.h}")
        lines += F.wrap(d.desc, 12, 260)
        ok, reason = p.buildable(self.world, key)
        if not ok:
            lines.append("✖ " + reason)
        wmax = max(F.font(12).size(s)[0] for s in lines) + 20
        h = 10 + len(lines) * 17
        x = min(mx + 16, C.VIEW_W - wmax - 8)
        y = min(my + 10, C.SCREEN_H - h - 8)
        bg = pygame.Surface((wmax, h), pygame.SRCALPHA)
        bg.fill((12, 15, 19, 238))
        screen.blit(bg, (x, y))
        pygame.draw.rect(screen, (86, 98, 112), (x, y, wmax, h), 1, border_radius=3)
        yy = y + 6
        for i, line in enumerate(lines):
            col = (232, 236, 240) if i == 0 else ((219, 120, 110) if line.startswith("✖") else (170, 180, 190))
            F.text(screen, line, (x + 10, yy), 12, col, bold=(i == 0))
            yy += 17


def d_color(d):
    return C.FACTION_INFO[d.faction]["color"]
