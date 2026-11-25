# -*- coding: utf-8 -*-
"""全局常量与平衡性参数。"""

APP_NAME = "红色警戒：心灵风暴"
APP_SUBTITLE = "RA2 玩法致敬复刻版"
VERSION = "1.0.0"

SCREEN_W = 1280
SCREEN_H = 768
SIDEBAR_W = 244
VIEW_W = SCREEN_W - SIDEBAR_W
VIEW_H = SCREEN_H
FPS = 60

TILE = 32
MAP_W = 84
MAP_H = 84
WORLD_W = MAP_W * TILE
WORLD_H = MAP_H * TILE

# 地形
T_GRASS, T_DIRT, T_WATER, T_ROCK, T_ROAD = 0, 1, 2, 3, 4
BLOCKING = {T_WATER, T_ROCK}
TERRAIN_NAMES = {T_GRASS: "草地", T_DIRT: "泥土", T_WATER: "水域", T_ROCK: "岩地", T_ROAD: "道路"}

# 颜色
C_BG = (10, 12, 14)
C_SIDEBAR = (22, 26, 31)
C_SIDEBAR_DARK = (15, 18, 22)
C_PANEL = (30, 36, 43)
C_PANEL_LIGHT = (42, 50, 59)
C_TEXT = (220, 226, 232)
C_TEXT_DIM = (140, 150, 160)
C_ACCENT = (226, 168, 33)
C_OK = (86, 196, 120)
C_BAD = (219, 83, 74)
C_SELECT = (120, 240, 120)

FACTION_INFO = {
    "allied": {
        "name": "盟军",
        "color": (58, 118, 214),
        "light": (120, 176, 244),
        "dark": (32, 62, 118),
        "desc": "高科技与精准打击。光棱科技、天气控制器、多功能载具。",
    },
    "soviet": {
        "name": "苏军",
        "color": (196, 58, 48),
        "light": (238, 132, 116),
        "dark": (104, 30, 24),
        "desc": "重装甲与暴力火力。天启坦克、磁暴科技、核弹。",
    },
    "yuri": {
        "name": "尤里",
        "color": (139, 76, 199),
        "light": (192, 150, 236),
        "dark": (74, 38, 108),
        "desc": "心灵控制与生化科技。心灵控制、镭射坦克、精神支配。",
    },
}

PLAYER_COLORS = [
    (58, 118, 214),
    (196, 58, 48),
    (139, 76, 199),
    (52, 168, 120),
]

# 经济
START_CREDITS = 10000
REFINERY_STORAGE = 500          # 矿车一次满载可卸载的资金
HARVEST_RATE = 180.0            # 每秒开采资金
ORE_TILE_VALUE = 650            # 每格矿脉总量（资金）
ORE_REGROW = 0.0                # 矿脉再生速度（每格每秒）

# 建造
BUILD_TIME_PER_CREDIT = 0.013   # 单位：造价 * 系数 = 秒
BUILDING_TIME_PER_CREDIT = 0.0135
CONSTRUCTION_ANIM = 1.4         # 落地后的施工动画时长
SELL_REFUND = 0.5
REPAIR_COST_RATE = 0.35         # 修复费用 = 缺失血量比例 * 造价 * 系数

# 战斗
VET_DAMAGE = (1.0, 1.2, 1.45)   # 0/1/2 级伤害倍率
VET_HP = (1.0, 1.15, 1.3)
SPLASH_FALLOFF = 0.35
FRIENDLY_FIRE = 0.35            # 溅射对友军伤害比例
SUPERWEAPON_CHARGE = 180.0      # 超武充能秒数（建造完成后）

# 迷雾
FOG_UPDATE_INTERVAL = 0.22
EXPLORED_ALPHA = 118

# 难度
DIFFICULTIES = {
    "easy": {"name": "简单", "income": 0.75, "speed": 0.85, "threshold": 4, "aggression": 55.0},
    "normal": {"name": "普通", "income": 1.0, "speed": 1.0, "threshold": 6, "aggression": 40.0},
    "hard": {"name": "困难", "income": 1.35, "speed": 1.25, "threshold": 8, "aggression": 30.0},
}
