# -*- coding: utf-8 -*-
"""游戏主程序：菜单、遭遇战设置、对局场景与输入。"""
import math
import random
import sys
import time

import pygame

from . import config as C
from . import data as D
from . import fonts as F
from .ai import AIController
from .audio import Audio
from .nav import clamp_camera, px_to_tile, tile_center
from .player import Player
from .render import Renderer
from .ui import UI, SB_X
from .world import World

T = C.TILE


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption(f"{C.APP_NAME}  v{C.VERSION}")
        self.clock = pygame.time.Clock()
        self.running = True
        self.audio = Audio()
        self.settings = {"faction": "allied", "difficulty": "normal", "seed": random.randint(10000, 99999)}
        self.state = "menu"
        self.scene = MenuScene(self)
        self.fps_show = False

    def go(self, state):
        self.state = state
        if state == "menu":
            self.scene = MenuScene(self)
        elif state == "setup":
            self.scene = SetupScene(self)
        elif state == "game":
            self.scene = GameScene(self, self.settings)

    def run(self):
        while self.running:
            dt = min(0.05, self.clock.tick(C.FPS) / 1000.0)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scene.event(e)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            pygame.display.flip()
        pygame.quit()


# ---------------------------------------------------------------- 主菜单
class MenuScene:
    def __init__(self, game):
        self.g = game
        self.t = 0.0
        self.show_help = False
        self.buttons = []
        self.bg = self._bg()

    def _bg(self):
        s = pygame.Surface((C.SCREEN_W, C.SCREEN_H))
        for y in range(C.SCREEN_H):
            k = y / C.SCREEN_H
            col = (int(8 + 26 * (1 - k)), int(10 + 16 * (1 - k)), int(16 + 20 * (1 - k)))
            pygame.draw.line(s, col, (0, y), (C.SCREEN_W, y))
        return s

    def event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.show_help:
                    self.show_help = False
                else:
                    self.g.running = False
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.show_help:
                    self.show_help = False
                else:
                    self.g.go("setup")
                    self.g.audio.play("click")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, act in self.buttons:
                if r.collidepoint(e.pos):
                    self.g.audio.play("click")
                    if act == "start":
                        self.g.go("setup")
                    elif act == "help":
                        self.show_help = not self.show_help
                    elif act == "quit":
                        self.g.running = False
                    return

    def update(self, dt):
        self.t += dt

    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        # 动态网格
        off = (self.t * 22) % 60
        for x in range(-60, C.SCREEN_W + 60, 60):
            pygame.draw.line(screen, (18, 24, 30), (x + off, 0), (x + off, C.SCREEN_H))
        for y in range(-60, C.SCREEN_H + 60, 60):
            pygame.draw.line(screen, (18, 24, 30), (0, y + off), (C.SCREEN_W, y + off))
        # 红色风暴光晕
        for i in range(5):
            r = 220 + i * 70 + math.sin(self.t * 0.7 + i) * 14
            s = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
            pygame.draw.circle(s, (120, 26, 20, 12), (int(r), int(r)), int(r))
            screen.blit(s, (C.SCREEN_W // 2 - r, 216 - r))
        F.text(screen, "红 色 警 戒", (C.SCREEN_W // 2, 118), 78, (226, 64, 48), bold=True, align="center")
        F.text(screen, "心 灵 风 暴", (C.SCREEN_W // 2, 208), 46, (240, 208, 150), bold=True, align="center")
        F.text(screen, "RA2 玩法致敬复刻 · 原创程序化美术与音效 · 三大阵营即时战略", (C.SCREEN_W // 2, 274),
               16, (168, 180, 192), align="center")
        F.text(screen, f"v{C.VERSION}   创意复刻，非官方作品，不含任何原作素材", (C.SCREEN_W // 2, 300),
               12, (110, 120, 132), align="center")

        self.buttons = []
        items = [("开始遭遇战", "start"), ("操作说明", "help"), ("退出游戏", "quit")]
        for i, (label, act) in enumerate(items):
            r = pygame.Rect(C.SCREEN_W // 2 - 130, 376 + i * 66, 260, 50)
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (44, 34, 32) if hov else (26, 28, 32), r, border_radius=4)
            pygame.draw.rect(screen, (196, 72, 56) if hov else (88, 76, 70), r, 2, border_radius=4)
            F.text(screen, label, (r.centerx, r.y + 12), 20,
                   (255, 236, 210) if hov else (208, 214, 220), align="center")
            self.buttons.append((r, act))
        F.text(screen, "提示：先采矿、再造兵，A 键攻击移动，Ctrl+数字编队", (C.SCREEN_W // 2, 586), 13,
               (120, 132, 144), align="center")
        if self.show_help:
            self._draw_help(screen)

    def _draw_help(self, screen):
        r = pygame.Rect(180, 90, 920, 600)
        s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        s.fill((10, 13, 17, 248))
        screen.blit(s, r.topleft)
        pygame.draw.rect(screen, (150, 110, 80), r, 2, border_radius=4)
        F.text(screen, "操作说明", (r.centerx, r.y + 18), 24, C.C_ACCENT, bold=True, align="center")
        lines = [
            "鼠标左键：选择单位 / 框选部队；点击侧栏建造按钮下单",
            "鼠标右键：移动、攻击、占领、采矿；点击建造按钮可取消生产",
            "WASD / 方向键 / 鼠标贴边：移动镜头        空格：回到基地或选中部队",
            "A + 左键：攻击移动（沿途自动交战）        S：停止",
            "Ctrl + 1~9：编队        1~9：调出编队        H：跳到建造厂",
            "Delete：出售选中的己方建筑        R：切换修理        ESC：取消 / 暂停菜单",
            "M：静音        F11：全屏切换",
            "",
            "基地：建造厂提供建造能力；电厂供电，电力不足会拖慢生产与射速。",
            "经济：精炼厂处理矿石换资金，采矿车会自动往返；矿脉会被采空，注意扩张。",
            "科技：雷达站解锁二级单位与超级武器；超级武器建成后需要 5 分钟充能。",
            "克制：轻武器打步兵、穿甲弹打载具、高爆拆建筑；对空需要防空单位。",
            "胜利条件：摧毁敌方全部建筑；己方建筑全灭则失败。",
        ]
        y = r.y + 64
        for line in lines:
            F.text(screen, line, (r.x + 36, y), 14, (206, 214, 222) if line else (120, 130, 140))
            y += 30
        F.text(screen, "点击任意处 / ESC 关闭", (r.centerx, r.bottom - 34), 13, (150, 160, 172), align="center")


# ---------------------------------------------------------------- 遭遇战设置
class SetupScene:
    def __init__(self, game):
        self.g = game
        self.t = 0.0
        self.cards = []
        self.diff_rects = []
        self.start_rect = None
        self.back_rect = None
        self.seed_rect = None
        self.bg = MenuScene._bg(None)

    def event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.g.go("menu")
            elif e.key == pygame.K_RETURN:
                self.g.go("game")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, fac in self.cards:
                if r.collidepoint(e.pos):
                    self.g.settings["faction"] = fac
                    self.g.audio.play("click")
            for r, key in self.diff_rects:
                if r.collidepoint(e.pos):
                    self.g.settings["difficulty"] = key
                    self.g.audio.play("click")
            if self.seed_rect and self.seed_rect.collidepoint(e.pos):
                self.g.settings["seed"] = random.randint(10000, 99999)
                self.g.audio.play("click")
            if self.start_rect and self.start_rect.collidepoint(e.pos):
                self.g.audio.play("click")
                self.g.go("game")
            if self.back_rect and self.back_rect.collidepoint(e.pos):
                self.g.go("menu")

    def update(self, dt):
        self.t += dt

    def draw(self, screen):
        screen.blit(self.bg, (0, 0))
        F.text(screen, "遭遇战设置", (C.SCREEN_W // 2, 34), 32, (236, 220, 190), bold=True, align="center")
        F.text(screen, "选择阵营", (C.SCREEN_W // 2, 92), 16, (160, 172, 184), align="center")
        self.cards = []
        for i, fac in enumerate(("allied", "soviet", "yuri")):
            info = C.FACTION_INFO[fac]
            r = pygame.Rect(150 + i * 340, 124, 300, 264)
            sel = self.g.settings["faction"] == fac
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (20, 24, 30) if not sel else (30, 34, 42), r, border_radius=6)
            pygame.draw.rect(screen, info["color"] if sel else ((70, 80, 92) if not hov else (110, 122, 136)),
                             r, 3 if sel else 1, border_radius=6)
            pygame.draw.circle(screen, info["color"], (r.centerx, r.y + 52), 26)
            pygame.draw.circle(screen, info["light"], (r.centerx, r.y + 52), 18, 2)
            F.text(screen, info["name"], (r.centerx, r.y + 88), 26, (240, 244, 248), bold=True, align="center")
            for j, line in enumerate(F.wrap(info["desc"], 13, r.w - 40)):
                F.text(screen, line, (r.centerx, r.y + 132 + j * 22), 13, (150, 160, 172), align="center")
            if sel:
                F.text(screen, "✔ 已选择", (r.centerx, r.bottom - 30), 14, (140, 230, 160), align="center")
            self.cards.append((r, fac))

        F.text(screen, "AI 难度", (C.SCREEN_W // 2, 412), 16, (160, 172, 184), align="center")
        self.diff_rects = []
        for i, key in enumerate(("easy", "normal", "hard")):
            d = C.DIFFICULTIES[key]
            r = pygame.Rect(C.SCREEN_W // 2 - 240 + i * 165, 442, 150, 44)
            sel = self.g.settings["difficulty"] == key
            hov = r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(screen, (34, 44, 40) if sel else ((36, 40, 46) if hov else (26, 30, 36)),
                             r, border_radius=4)
            pygame.draw.rect(screen, (120, 210, 150) if sel else (66, 76, 88), r, 2 if sel else 1,
                             border_radius=4)
            F.text(screen, d["name"], (r.centerx, r.y + 12), 17,
                   (200, 240, 210) if sel else (206, 214, 222), align="center")
            self.diff_rects.append((r, key))

        self.seed_rect = pygame.Rect(C.SCREEN_W // 2 - 150, 508, 300, 40)
        hov = self.seed_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (36, 40, 48) if hov else (28, 32, 38), self.seed_rect, border_radius=4)
        pygame.draw.rect(screen, (76, 88, 102), self.seed_rect, 1, border_radius=4)
        F.text(screen, f"地图种子 {self.g.settings['seed']}   （点击换一张）",
               (self.seed_rect.centerx, self.seed_rect.y + 11), 14, (190, 200, 210), align="center")

        self.start_rect = pygame.Rect(C.SCREEN_W // 2 - 170, 580, 340, 58)
        hov = self.start_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (52, 38, 34) if hov else (30, 26, 26), self.start_rect, border_radius=5)
        pygame.draw.rect(screen, (230, 96, 70) if hov else (150, 80, 66), self.start_rect, 2, border_radius=5)
        F.text(screen, "开 始 战 斗", (self.start_rect.centerx, self.start_rect.y + 14), 24,
               (255, 238, 214), bold=True, align="center")
        self.back_rect = pygame.Rect(28, 668, 120, 40)
        F.text(screen, "← 返回主菜单 (ESC)", (self.back_rect.x, self.back_rect.y + 10), 14, (150, 160, 172))
        F.text(screen, "初始资金 $10,000 · 1v1 遭遇战 · 摧毁敌方全部建筑", (C.SCREEN_W // 2, 700), 13,
               (120, 132, 144), align="center")


# ---------------------------------------------------------------- 对局
class GameScene:
    def __init__(self, game, settings):
        self.g = game
        self.settings = dict(settings)
        self.audio = game.audio
        seed = settings.get("seed", 12345)
        self.world = World(seed)
        self.world.audio = self.audio
        human_fac = settings["faction"]
        others = [f for f in ("allied", "soviet", "yuri") if f != human_fac]
        ai_fac = random.choice(others)
        diff_key = settings.get("difficulty", "normal")
        diff = C.DIFFICULTIES[diff_key]
        p0 = Player(0, human_fac, "指挥官", is_ai=False)
        p1 = Player(1, ai_fac, f"敌军·{C.FACTION_INFO[ai_fac]['name']}", is_ai=True,
                    income_mult=diff["income"], speed_mult=diff["speed"])
        self.world.setup_match([p0, p1])
        p1.ai = AIController(self.world, p1, diff_key)
        self.player = p0
        self.enemy = p1
        self.difficulty = diff
        self.renderer = Renderer(self.world)
        self.ui = UI(self.world, self.renderer, self.audio)
        self.cam = [0, 0]
        self.selected = []
        self.drag_start = None
        self.drag_now = None
        self.panning = False
        self.pan_last = (0, 0)
        self.placing = False
        self.super_target = None
        self.attack_mode = False
        self.paused = False
        self.groups = {}
        self.last_click = (0.0, None)
        self.sel_time = 0.0
        self.hover = None
        self.time = 0.0
        cy = self._find_building(p0, "_cy")
        if cy:
            self.center_camera(cy.x, cy.y)
        self.world.cam = tuple(self.cam)
        self.world.add_msg(f"对手：{C.FACTION_INFO[ai_fac]['name']} · 难度 {diff['name']}", (200, 200, 210))

    # ---------------- 工具 ----------------
    @property
    def players(self):
        """UI 统一从这里取玩家列表。"""
        return self.world.players

    def _find_building(self, p, suffix):
        for e in self.world.entities.values():
            if not e.dead and e.is_building and e.owner is p and e.key.endswith(suffix):
                return e
        return None

    def center_camera(self, wx, wy):
        self.cam[0], self.cam[1] = clamp_camera(wx - C.VIEW_W / 2, wy - C.VIEW_H / 2,
                                                C.VIEW_W, C.VIEW_H, C.WORLD_W, C.WORLD_H)
        self.world.cam = tuple(self.cam)

    def mouse_world(self):
        mx, my = pygame.mouse.get_pos()
        return mx + self.cam[0], my + self.cam[1]

    def in_view(self, pos):
        return pos[0] < SB_X and 0 <= pos[1] < C.VIEW_H

    def entity_at(self, wx, wy, include_buildings=True):
        best = None
        bd = 1e9
        for e in self.world.entities.values():
            if e.dead:
                continue
            if e.is_building and not include_buildings:
                continue
            if e.owner is not self.player and not self.world.entity_visible(e):
                continue
            if e.is_building:
                if (e.tx * T <= wx <= (e.tx + e.d.w) * T and
                        e.ty * T <= wy <= (e.ty + e.d.h) * T):
                    return e
            else:
                d = math.hypot(e.x - wx, e.y - wy)
                if d < e.radius + 8 and d < bd:
                    bd = d
                    best = e
        return best

    # ---------------- 输入 ----------------
    def event(self, e):
        if e.type == pygame.KEYDOWN:
            self._key(e)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_down(e)
        elif e.type == pygame.MOUSEWHEEL:
            pass
        elif e.type == pygame.MOUSEBUTTONUP:
            self._mouse_up(e)

    def _key(self, e):
        k = e.key
        mods = pygame.key.get_mods()
        if self.world.game_over is not None:
            if k == pygame.K_r:
                self.g.go("game")
            elif k in (pygame.K_ESCAPE, pygame.K_q):
                self.g.go("menu")
            return
        if k == pygame.K_ESCAPE:
            if self.super_target:
                self.super_target = None
            elif self.placing or self.player.pending_placement:
                self.placing = False
                key = self.player.cancel_placement()
                if key:
                    self.world.add_msg(f"取消建造 {D.BUILDINGS[key].name}，已退款", C.C_TEXT_DIM)
            elif self.attack_mode:
                self.attack_mode = False
            elif self.paused:
                self.paused = False
            elif self.selected:
                self.selected = []
            else:
                self.paused = True
            return
        if self.paused:
            if k in (pygame.K_p, pygame.K_ESCAPE):
                self.paused = False
            elif k == pygame.K_r:
                self.g.go("game")
            elif k == pygame.K_q:
                self.g.go("menu")
            return
        if k == pygame.K_a:
            self.attack_mode = True
            self.super_target = None
            self.placing = False
            self.audio.play("select")
        elif k == pygame.K_s:
            for u in self._sel_units():
                u.order_stop()
        elif k == pygame.K_h:
            b = self._find_building(self.player, "_cy")
            if b:
                self.center_camera(b.x, b.y)
        elif k == pygame.K_SPACE:
            if self.selected:
                xs = [x.x for x in self.selected]
                ys = [x.y for x in self.selected]
                self.center_camera(sum(xs) / len(xs), sum(ys) / len(ys))
            else:
                b = self._find_building(self.player, "_cy")
                if b:
                    self.center_camera(b.x, b.y)
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                   pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9):
            n = k - pygame.K_0
            if mods & pygame.KMOD_CTRL:
                self.groups[n] = [x.id for x in self.selected if not x.is_building]
                self.world.add_msg(f"编队 {n} 已设定（{len(self.groups[n])} 个单位）", (180, 210, 180))
            elif n in self.groups:
                ids = self.groups[n]
                self.selected = [e for e in (self.world.get(i) for i in ids)
                                 if e is not None and not e.dead and e.owner is self.player]
                for x in self.selected:
                    x.sel = True
                self.audio.play("select")
        elif k == pygame.K_DELETE:
            for e in list(self.selected):
                if e.is_building and e.owner is self.player:
                    self.world.sell_building(e)
            self.selected = [e for e in self.selected if not e.dead]
        elif k == pygame.K_r:
            for e in self.selected:
                if e.is_building and e.owner is self.player:
                    e.repair = not e.repair
        elif k == pygame.K_TAB:
            tabs = ["structure", "defense", "infantry", "vehicle", "air", "special"]
            i = (tabs.index(self.ui.tab) + 1) % len(tabs)
            self.ui.tab = tabs[i]
        elif k == pygame.K_m:
            self.world.add_msg("静音" if self.audio.toggle_mute() else "开启声音", C.C_TEXT_DIM)
        elif k == pygame.K_F11:
            pygame.display.toggle_fullscreen()
        elif k == pygame.K_F3:
            self.g.fps_show = not self.g.fps_show

    def _mouse_down(self, e):
        if self.world.game_over is not None or self.paused:
            return
        if self.ui.handle_click(e.pos, e.button, self):
            return
        if e.button == 2:
            self.panning = True
            self.pan_last = e.pos
            return
        if not self.in_view(e.pos):
            return
        wx, wy = e.pos[0] + self.cam[0], e.pos[1] + self.cam[1]
        if e.button == 1:
            if self.super_target:
                sw = self.super_target
                if self.world.fire_superweapon(self.player, sw, wx, wy):
                    self.super_target = None
                return
            if self.player.pending_placement:
                self._try_place(wx, wy)
                return
            if self.attack_mode:
                self._issue_move(wx, wy, attack_move=True)
                self.attack_mode = False
                return
            self.drag_start = e.pos
            self.drag_now = e.pos
        elif e.button == 3:
            if self.super_target:
                self.super_target = None
                return
            if self.placing or self.player.pending_placement:
                key = self.player.cancel_placement()
                self.placing = False
                if key:
                    self.world.add_msg(f"取消建造 {D.BUILDINGS[key].name}，已退款", C.C_TEXT_DIM)
                return
            if self.attack_mode:
                self.attack_mode = False
                return
            self._issue_order(wx, wy)

    def _mouse_up(self, e):
        if e.button == 2:
            self.panning = False
            return
        if e.button != 1 or self.drag_start is None:
            return
        start = self.drag_start
        end = e.pos
        self.drag_start = None
        self.drag_now = None
        if not self.in_view(end):
            return
        dist = math.hypot(end[0] - start[0], end[1] - start[1])
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        if dist < 7:
            wx, wy = end[0] + self.cam[0], end[1] + self.cam[1]
            ent = self.entity_at(wx, wy)
            if ent is None:
                if not shift:
                    self.selected = []
                return
            now = time.time()
            if (now - self.last_click[0] < 0.36 and self.last_click[1] == ent.key
                    and not ent.is_building):
                sx, sy = start[0] + self.cam[0], start[1] + self.cam[1]
                for u in self.world.entities.values():
                    if (not u.dead and not u.is_building and u.owner is self.player and u.key == ent.key
                            and u.x - self.cam[0] < C.VIEW_W and u.y - self.cam[1] < C.VIEW_H):
                        u.sel = True
                        if u not in self.selected:
                            self.selected.append(u)
                self.last_click = (0.0, None)
            else:
                if not shift:
                    for s in self.selected:
                        s.sel = False
                    self.selected = []
                if ent not in self.selected:
                    ent.sel = True
                    self.selected.append(ent)
                self.last_click = (now, ent.key)
                self.audio.play("select")
        else:
            x0 = min(start[0], end[0]) + self.cam[0]
            x1 = max(start[0], end[0]) + self.cam[0]
            y0 = min(start[1], end[1]) + self.cam[1]
            y1 = max(start[1], end[1]) + self.cam[1]
            if not shift:
                for s in self.selected:
                    s.sel = False
                self.selected = []
            units = []
            for u in self.world.entities.values():
                if u.dead or u.is_building or u.owner is not self.player:
                    continue
                if x0 <= u.x <= x1 and y0 <= u.y <= y1:
                    units.append(u)
            if not units:
                for b in self.world.entities.values():
                    if b.dead or not b.is_building or b.owner is not self.player:
                        continue
                    if x0 <= b.x <= x1 and y0 <= b.y <= y1:
                        units.append(b)
            for u in units:
                if u not in self.selected:
                    u.sel = True
                    self.selected.append(u)
            if units:
                self.audio.play("select")

    # ---------------- 指令 ----------------
    def _sel_units(self):
        return [e for e in self.selected if not e.is_building and not e.dead]

    def _issue_move(self, wx, wy, attack_move=False):
        units = self._sel_units()
        if not units:
            return
        n = len(units)
        cols = max(1, int(math.sqrt(n)))
        for i, u in enumerate(units):
            if n == 1:
                tx, ty = wx, wy
            else:
                col = i % cols
                row = i // cols
                tx = wx + (col - (cols - 1) / 2) * 34
                ty = wy + (row - (cols - 1) / 2) * 34
            u.order_move(self.world, tx, ty, attack_move=attack_move)
        self.audio.play("select")

    def _issue_order(self, wx, wy):
        units = self._sel_units()
        buildings = [e for e in self.selected if e.is_building and e.owner is self.player]
        target = self.entity_at(wx, wy)
        # 建筑集结点
        if not units and buildings:
            for b in buildings:
                b.rally = (wx, wy)
                self.world.add_msg(f"{b.name} 集结点已设置", (150, 200, 150))
                self.world.spawn_effect("ring", wx, wy, 0.6, color=(120, 220, 120))
            return
        if not units:
            return
        if target is not None and target.owner is not self.player:
            if target.is_building:
                engineers = [u for u in units if u.d.capture]
                if engineers:
                    for u in engineers:
                        u.order_capture(self.world, target)
                    self.audio.play("select")
                    return
            for u in units:
                if u.d.capture and target.is_building:
                    u.order_capture(self.world, target)
                else:
                    u.order_attack(self.world, target)
            self.audio.play("select")
            return
        if target is not None and target.owner is self.player and target.is_building:
            if any(u.d.is_harvester for u in units):
                self._harvest_order(units, target)
                return
            for b in buildings:
                b.rally = (wx, wy)
            return
        # 矿脉 / 采集
        tx, ty = px_to_tile(wx, wy)
        harv = [u for u in units if u.d.is_harvester]
        if harv and self.world.ore_amount(tx, ty) > 0:
            self._harvest_order(harv)
            return
        self._issue_move(wx, wy, attack_move=False)

    def _harvest_order(self, units, refinery=None):
        for u in units:
            if not u.d.is_harvester:
                continue
            if u.cargo >= C.REFINERY_STORAGE - 1:
                u.h_state = "return"
                u.path = []
            else:
                u.order_harvest(self.world)
                u.h_state = "seek"
        self.audio.play("select")

    def _try_place(self, wx, wy):
        if not self.player.pending_placement:
            return
        key = self.player.pending_placement[0]
        d = D.BUILDINGS[key]
        tx = int(wx // T) - d.w // 2
        ty = int(wy // T) - d.h // 2
        ok, reason = self.world.can_place(self.player, key, tx, ty)
        if not ok:
            self.world.add_msg(reason, C.C_BAD)
            self.audio.play("error")
            return
        self.world.place_building(self.player, key, tx, ty)
        self.player.pending_placement.pop(0)
        self.audio.play("build")
        self.placing = bool(self.player.pending_placement)

    # ---------------- 更新 ----------------
    def update(self, dt):
        self.time += dt
        self.ui.selected = self.selected[0] if self.selected else None
        if not self.paused:
            self.world.update(dt)
            keys = pygame.key.get_pressed()
            sp = 760 * dt
            mx, my = pygame.mouse.get_pos()
            edge = 8
            dx = dy = 0
            if self.in_view((mx, my)):
                if mx < edge:
                    dx -= sp
                if mx > SB_X - edge:
                    dx += sp
                if my < edge:
                    dy -= sp
                if my > C.VIEW_H - edge:
                    dy += sp
            if keys[pygame.K_LEFT]:
                dx -= sp
            if keys[pygame.K_RIGHT]:
                dx += sp
            if keys[pygame.K_UP]:
                dy -= sp
            if keys[pygame.K_DOWN]:
                dy += sp
            if dx or dy:
                self.cam[0] += dx
                self.cam[1] += dy
            if self.panning:
                lx, ly = self.pan_last
                self.cam[0] -= mx - lx
                self.cam[1] -= my - ly
                self.pan_last = (mx, my)
            self.cam[0], self.cam[1] = clamp_camera(self.cam[0], self.cam[1],
                                                    C.VIEW_W, C.VIEW_H, C.WORLD_W, C.WORLD_H)
            self.world.cam = tuple(self.cam)
            if pygame.mouse.get_pressed()[1] and not self.panning:
                self.panning = True
                self.pan_last = (mx, my)
            # 自动进入放置模式
            if self.player.pending_placement and not self.super_target:
                self.placing = True
            elif not self.player.pending_placement:
                self.placing = False
            # 清理选中
            alive = []
            for e in self.selected:
                if not e.dead and e.owner is self.player:
                    alive.append(e)
                else:
                    e.sel = False
            self.selected = alive
            self.hover = None
            if self.in_view((mx, my)):
                self.hover = self.entity_at(mx + self.cam[0], my + self.cam[1])
            if self.drag_start is not None:
                self.drag_now = (mx, my)

    # ---------------- 绘制 ----------------
    def draw(self, screen):
        place_ok = True
        if self.placing and self.player.pending_placement:
            key = self.player.pending_placement[0]
            d = D.BUILDINGS[key]
            mx, my = pygame.mouse.get_pos()
            tx = int((mx + self.cam[0]) // T) - d.w // 2
            ty = int((my + self.cam[1]) // T) - d.h // 2
            place_ok = self.world.can_place(self.player, key, tx, ty)[0]
        sel_b = self.selected[0] if self.selected and self.selected[0].is_building else None
        self.renderer.draw(screen, self.cam, hover=self.hover, sel_b=sel_b,
                           placing=self.player.pending_placement[0] if self.placing and self.player.pending_placement else None,
                           place_ok=place_ok, attack_cursor=self.attack_mode,
                           super_target=self.super_target, show_rally=True)
        # 框选
        if self.drag_start is not None and self.drag_now is not None:
            x0, y0 = self.drag_start
            x1, y1 = self.drag_now
            if abs(x1 - x0) > 4 or abs(y1 - y0) > 4:
                r = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
                s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                s.fill((90, 230, 120, 26))
                screen.blit(s, r.topleft)
                pygame.draw.rect(screen, (110, 240, 130), r, 1)
        # 光标模式指示
        if self.attack_mode or self.super_target:
            mx, my = pygame.mouse.get_pos()
            col = (255, 110, 90) if self.attack_mode else D.SUPERWEAPONS[self.super_target]["color"]
            pygame.draw.circle(screen, col, (mx, my), 11, 2)
            pygame.draw.line(screen, col, (mx - 15, my), (mx - 6, my), 2)
            pygame.draw.line(screen, col, (mx + 6, my), (mx + 15, my), 2)
            pygame.draw.line(screen, col, (mx, my - 15), (mx, my - 6), 2)
            pygame.draw.line(screen, col, (mx, my + 6), (mx, my + 15), 2)
        # 对局信息
        F.text(screen, f"敌军：{C.FACTION_INFO[self.enemy.faction]['name']}（{self.difficulty['name']}）",
               (SB_X - 12, C.VIEW_H - 22), 12, (180, 150, 150), align="right")
        F.text(screen, f"时间 {int(self.world.time // 60):02d}:{int(self.world.time % 60):02d}",
               (12, C.SCREEN_H - 158), 12, (170, 180, 190))
        if self.world.game_over is None and self.player.pending_placement:
            key = self.player.pending_placement[0]
            F.text(screen, f"放置建筑：{D.BUILDINGS[key].name}  （左键确认 / 右键取消）",
                   (C.VIEW_W // 2, C.VIEW_H - 26), 14, (150, 230, 160), align="center")
        self.ui.draw(screen, self)
        if self.paused:
            self._overlay_pause(screen)
        if self.world.game_over is not None:
            self._overlay_result(screen)
        if self.g.fps_show:
            F.text(screen, f"FPS {int(self.g.clock.get_fps())}", (8, 8), 11, (150, 160, 170))

    def _dim(self, screen, alpha=190):
        s = pygame.Surface((C.SCREEN_W, C.SCREEN_H), pygame.SRCALPHA)
        s.fill((6, 8, 10, alpha))
        screen.blit(s, (0, 0))

    def _overlay_pause(self, screen):
        self._dim(screen, 170)
        F.text(screen, "暂 停", (C.SCREEN_W // 2, 220), 46, (236, 226, 206), bold=True, align="center")
        lines = ["ESC / P：继续游戏", "R：重新开始本局", "Q：返回主菜单", "M：静音开关"]
        for i, line in enumerate(lines):
            F.text(screen, line, (C.SCREEN_W // 2, 306 + i * 40), 18, (190, 200, 210), align="center")
        F.text(screen, "提示：电力不足会拖慢生产；记得补第二辆采矿车。", (C.SCREEN_W // 2, 500), 14,
               (140, 150, 160), align="center")

    def _overlay_result(self, screen):
        win = self.world.game_over == "win"
        self._dim(screen, 180)
        col = (120, 230, 140) if win else (230, 100, 90)
        F.text(screen, "胜 利" if win else "失 败", (C.SCREEN_W // 2, 200), 62, col, bold=True, align="center")
        F.text(screen, "敌军基地已被彻底摧毁" if win else "我方基地已被摧毁",
               (C.SCREEN_W // 2, 286), 20, (220, 226, 232), align="center")
        t = int(self.world.time)
        st = self.player.stats
        lines = [
            f"对局时长：{t // 60:02d}:{t % 60:02d}",
            f"累计收入：${int(st['earned']):,}    支出：${int(st['spent']):,}",
            f"击杀：{st['kills']}    损失：{st['lost']}    建造：{st['built']}",
        ]
        for i, line in enumerate(lines):
            F.text(screen, line, (C.SCREEN_W // 2, 340 + i * 32), 16, (190, 200, 210), align="center")
        F.text(screen, "R：再来一局        ESC：返回主菜单", (C.SCREEN_W // 2, 480), 18,
               (240, 220, 180), align="center")
