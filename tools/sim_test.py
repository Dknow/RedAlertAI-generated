# -*- coding: utf-8 -*-
"""无头逻辑回归测试：模拟对局、检验经济/战斗/AI/胜负，不依赖显示器。"""
import math
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game import config as C          # noqa: E402
from game import data as D            # noqa: E402
from game.ai import AIController      # noqa: E402
from game.player import Player        # noqa: E402
from game.world import World          # noqa: E402


def run_match(human_fac, ai_fac, diff="hard", seconds=180, seed=1234):
    w = World(seed)
    p0 = Player(0, human_fac, "H")
    p1 = Player(1, ai_fac, "AI", is_ai=True,
                income_mult=C.DIFFICULTIES[diff]["income"],
                speed_mult=C.DIFFICULTIES[diff]["speed"])
    w.setup_match([p0, p1])
    p1.ai = AIController(w, p1, diff)
    # 人类侧也交给 AI，验证双方都能正常运转
    p0.ai = AIController(w, p0, "normal")
    t0 = time.time()
    dt = 1.0 / 30.0
    for _ in range(int(seconds / dt)):
        w.update(dt)
    dur = time.time() - t0
    for e in w.entities.values():
        assert not (math.isnan(e.x) or math.isnan(e.y)), f"NaN 坐标 {e.key}"
        assert not (e.hp > e.max_hp + 0.01), f"血量溢出 {e.key}"
    print(f"[{human_fac} vs {ai_fac}/{diff}] {seconds}s 模拟耗时 {dur:.2f}s  "
          f"单位={len([e for e in w.entities.values() if not e.is_building])} "
          f"建筑={len([e for e in w.entities.values() if e.is_building])} "
          f"AI资金={int(p1.credits)} 收入={int(p1.stats['earned'])} "
          f"H收入={int(p0.stats['earned'])} 击杀={p1.stats['kills']} 胜负={w.game_over}")
    assert p0.stats["earned"] > 0, "人类采矿没有收入"
    assert p1.stats["earned"] > 0, "AI 采矿没有收入"
    return w


def test_combat():
    w = World(777)
    p0 = Player(0, "allied", "H")
    p1 = Player(1, "soviet", "AI")
    w.setup_match([p0, p1])
    a = w.spawn_unit(p0, "a_grizzly", 40 * C.TILE, 40 * C.TILE)
    b = w.spawn_unit(p1, "s_conscript", 41 * C.TILE, 40 * C.TILE)
    hp0 = b.hp
    a.order_attack(w, b)
    for _ in range(120):
        w.update(1 / 30)
    print(f"[combat] 步兵血量 {hp0:.0f} -> {b.hp:.1f} dead={b.dead}")
    assert b.dead or b.hp < hp0, "坦克未能命中步兵"


def test_superweapon():
    w = World(888)
    p0 = Player(0, "soviet", "H")
    p1 = Player(1, "allied", "AI")
    w.setup_match([p0, p1])
    for k in list(p0.sw):
        pass
    # 手动造核弹井
    b = w.place_building(p0, "s_super", 12, 60, force=True, free=True)
    p0.sw["nuke"] = {"t": C.SUPERWEAPON_CHARGE, "ready": True}
    target = w.spawn_unit(p1, "a_rifle", 30 * C.TILE, 40 * C.TILE)
    w.fire_superweapon(p0, "nuke", target.x, target.y)
    for _ in range(30):
        w.update(1 / 30)
    print(f"[super] 目标 dead={target.dead}")
    assert target.dead, "核弹未能击杀目标"


def test_data_sanity():
    for k, d in D.UNITS.items():
        assert d.faction in C.FACTION_INFO, k
        assert d.cost > 0 and d.hp > 0 and d.speed > 0, k
        if d.weapon:
            assert d.weapon in D.WEAPONS, (k, d.weapon)
            for p in d.prereq:
                assert p in D.BUILDINGS, (k, p)
        assert D.get_def(k) is d
    for k, b in D.BUILDINGS.items():
        assert b.faction in C.FACTION_INFO, k
        if b.weapon:
            assert b.weapon in D.WEAPONS, (k, b.weapon)
        for p in b.prereq:
            assert p in D.BUILDINGS, (k, p)
        if b.superweapon:
            assert b.superweapon in D.SUPERWEAPONS
    for fac, tabs in D.FACTION_BUILD_ORDER.items():
        for tab, keys in tabs.items():
            for kk in keys:
                assert kk in D.UNITS or kk in D.BUILDINGS, (fac, tab, kk)
    print(f"[data] 单位 {len(D.UNITS)} 建筑 {len(D.BUILDINGS)} 武器 {len(D.WEAPONS)} 校验通过")


if __name__ == "__main__":
    test_data_sanity()
    test_combat()
    test_superweapon()
    run_match("allied", "soviet", "hard", 150)
    run_match("soviet", "yuri", "normal", 150)
    run_match("yuri", "allied", "easy", 150)
    print("ALL TESTS PASSED")
