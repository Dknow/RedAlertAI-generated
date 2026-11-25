# -*- coding: utf-8 -*-
"""无头渲染冒烟：菜单/设置/对局场景逐帧 update+draw，捕获画面层崩溃。"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

from game import config as C          # noqa: E402
from game.app import Game             # noqa: E402
from game.ui import TAB_ORDER         # noqa: E402

g = Game()
for _ in range(5):
    g.scene.update(1 / 60)
    g.scene.draw(g.screen)
print("[smoke] menu ok")

g.go("setup")
for _ in range(5):
    g.scene.update(1 / 60)
    g.scene.draw(g.screen)
print("[smoke] setup ok")

g.settings = {"faction": "allied", "difficulty": "hard", "seed": 4242}
g.go("game")
sc = g.scene
t0 = time.time()
for i in range(1800):          # 30 秒游戏时间
    sc.update(1 / 60)
    sc.draw(g.screen)
print(f"[smoke] game 30s ok, {time.time() - t0:.2f}s, entities={len(sc.world.entities)}")

# 选中己方全部单位+建筑，覆盖信息面板/血条/修理出售按钮
mine = [e for e in sc.world.entities.values() if e.owner is sc.player and not e.dead]
sc.selected = mine[:11]
sc.ui.selected = mine[0] if mine else None
sc.draw(g.screen)

# 逐一切换侧栏标签，覆盖所有建造按钮/图标
for tab, _name in TAB_ORDER:
    sc.ui.tab = tab
    sc.draw(g.screen)
print("[smoke] tabs ok")

# 超武瞄准与建筑放置虚影
sc.ui.tab = "special"
sc.super_target = "storm"
sc.draw(g.screen)
sc.super_target = None
sc.placing = True
sc.player.pending_placement = ["a_barracks"]
sc.draw(g.screen)
sc.placing = False
sc.player.pending_placement = []

# 暂停/结算覆盖层
sc.paused = True
sc.draw(g.screen)
sc.paused = False
sc.world.game_over = "win"
sc.draw(g.screen)
print("[smoke] overlays ok")
pygame.quit()
print("RENDER SMOKE PASSED")
