# -*- coding: utf-8 -*-
"""单位、建筑、武器、伤害表等全部静态数据（三大阵营）。

数值参考《红色警戒2：尤里的复仇》公开资料（rules.ini 量级与装甲/弹头克制关系），
并按本作 1:1 复刻的实时比例做了换算与微调。
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple

from . import config as C

ARMOR_TYPES = ("none", "flak", "plate", "light", "medium", "heavy", "wood", "steel", "concrete")

ARMOR_NAMES = {
    "none": "无甲", "flak": "防弹衣", "plate": "金属护甲", "light": "轻甲",
    "medium": "中甲", "heavy": "重甲", "wood": "木质结构", "steel": "钢结构", "concrete": "混凝土",
}

# 弹头对各装甲的伤害倍率（0~2.0）
WARHEADS = {
    "sa":       dict(none=1.00, flak=0.55, plate=0.45, light=0.25, medium=0.18, heavy=0.10, wood=0.45, steel=0.30, concrete=0.05),
    "ap":       dict(none=0.12, flak=0.08, plate=0.08, light=0.75, medium=1.00, heavy=1.00, wood=0.65, steel=0.90, concrete=0.55),
    "he":       dict(none=0.60, flak=0.35, plate=0.35, light=0.70, medium=0.65, heavy=0.55, wood=1.00, steel=0.85, concrete=0.85),
    "rocket":   dict(none=0.35, flak=0.25, plate=0.30, light=1.00, medium=0.95, heavy=0.85, wood=0.75, steel=0.70, concrete=0.50),
    "flak":     dict(none=0.85, flak=0.50, plate=0.45, light=0.35, medium=0.30, heavy=0.25, wood=0.35, steel=0.25, concrete=0.10),
    "tesla":    dict(none=1.00, flak=0.80, plate=0.80, light=0.55, medium=0.50, heavy=0.45, wood=0.60, steel=0.50, concrete=0.35),
    "prism":    dict(none=0.60, flak=0.50, plate=0.50, light=1.00, medium=0.95, heavy=0.85, wood=0.80, steel=0.90, concrete=0.70),
    "laser":    dict(none=0.55, flak=0.45, plate=0.45, light=1.00, medium=0.95, heavy=0.85, wood=0.75, steel=0.85, concrete=0.65),
    "psychic":  dict(none=1.00, flak=1.00, plate=1.00, light=0.85, medium=0.80, heavy=0.75, wood=0.40, steel=0.35, concrete=0.30),
    "magnetic": dict(none=0.00, flak=0.00, plate=0.00, light=1.00, medium=1.00, heavy=1.00, wood=0.30, steel=0.25, concrete=0.10),
    "explosive": dict(none=0.90, flak=0.70, plate=0.70, light=0.90, medium=0.90, heavy=0.85, wood=1.00, steel=0.95, concrete=0.95),
}

WARHEAD_NAMES = {
    "sa": "轻武器", "ap": "穿甲弹", "he": "高爆", "rocket": "火箭", "flak": "防空弹",
    "tesla": "磁暴", "prism": "光棱", "laser": "镭射", "psychic": "心灵", "magnetic": "磁力",
    "explosive": "爆破",
}


@dataclass(frozen=True)
class Weapon:
    key: str
    name: str
    damage: float
    rof: float              # 射击间隔（秒）
    range: float            # 射程（格）
    warhead: str
    projectile: str = "bullet"   # bullet/shell/rocket/beam/tesla/psychic/bomb/magnetic
    splash: float = 0.0     # 溅射半径（格）
    can_air: bool = False
    can_ground: bool = True
    burst: int = 1
    min_range: float = 0.0
    speed: float = 30.0     # 弹速（格/秒），光束类忽略
    color: Tuple[int, int, int] = (255, 230, 150)
    mc: int = 0             # 心灵控制数量（武器）
    effect: Optional[str] = None


WEAPONS = {
    "rifle":        Weapon("rifle", "突击步枪", 20, 0.55, 5.0, "sa", "bullet", 0, False, True, 1, 0, 40, (255, 235, 170)),
    "rocket_launcher": Weapon("rocket_launcher", "火箭筒", 45, 2.0, 6.2, "rocket", "rocket", 0.55, True, True, 1, 0, 7.0, (255, 190, 120)),
    "conscript_rifle": Weapon("conscript_rifle", "冲锋枪", 15, 0.5, 4.8, "sa", "bullet", 0, False, True, 1, 0, 40, (255, 225, 160)),
    "flak_gun":     Weapon("flak_gun", "防空机枪", 26, 0.85, 5.6, "flak", "bullet", 0.55, True, True, 3, 0, 45, (255, 210, 110)),
    "tesla_zap":    Weapon("tesla_zap", "磁暴电击", 58, 1.8, 4.6, "tesla", "tesla", 0.35, False, True, 1, 0, 0, (150, 200, 255)),
    "grizzly_gun":  Weapon("grizzly_gun", "105mm 主炮", 45, 0.9, 5.2, "ap", "shell", 0.15, False, True, 1, 0, 22, (255, 205, 130)),
    "ifv_gun":      Weapon("ifv_gun", "速射机关炮", 30, 0.5, 5.0, "ap", "bullet", 0.1, True, True, 2, 0, 40, (255, 240, 180)),
    "prism_beam":   Weapon("prism_beam", "光棱射线", 95, 2.6, 9.5, "prism", "beam", 0.6, False, True, 1, 0, 0, (150, 220, 255)),
    "heli_rockets": Weapon("heli_rockets", "火箭巢", 42, 2.2, 6.0, "rocket", "rocket", 0.55, True, True, 2, 0, 9.0, (255, 180, 110)),
    "rhino_gun":    Weapon("rhino_gun", "125mm 主炮", 90, 1.1, 5.5, "ap", "shell", 0.2, False, True, 1, 0, 20, (255, 200, 120)),
    "apoc_gun":     Weapon("apoc_gun", "双联 125mm", 100, 2.0, 6.5, "ap", "shell", 0.35, False, True, 2, 0, 20, (255, 190, 110)),
    "v3_rocket":    Weapon("v3_rocket", "V3 火箭", 200, 6.0, 13.5, "he", "rocket", 1.7, False, True, 1, 2.5, 6.5, (255, 160, 90)),
    "drone_boom":   Weapon("drone_boom", "自爆冲击", 200, 2.0, 1.4, "explosive", "beam", 1.0, False, True, 1, 0, 0, (255, 220, 120)),
    "kirov_bomb":   Weapon("kirov_bomb", "重型航空炸弹", 260, 5.0, 3.6, "he", "bomb", 1.9, False, True, 1, 0, 0, (255, 180, 100)),
    "initiate_bolt": Weapon("initiate_bolt", "心灵冲击", 26, 0.7, 5.0, "psychic", "psychic", 0, False, True, 1, 0, 18, (196, 150, 255)),
    "brute_claw":   Weapon("brute_claw", "蛮力撕扯", 65, 1.2, 1.3, "sa", "beam", 0, False, True, 1, 0, 0, (255, 160, 160)),
    "lasher_gun":   Weapon("lasher_gun", "镭射炮", 65, 1.0, 5.2, "laser", "beam", 0.25, False, True, 1, 0, 0, (255, 110, 220)),
    "magnet_beam":  Weapon("magnet_beam", "磁力光束", 55, 1.6, 7.0, "magnetic", "magnetic", 0.2, False, True, 1, 0, 0, (180, 150, 255)),
    "disc_laser":   Weapon("disc_laser", "飞碟镭射", 35, 0.55, 5.2, "laser", "beam", 0.1, False, True, 1, 0, 0, (255, 120, 230)),
    "mc_beam":      Weapon("mc_beam", "心灵控制", 0, 4.0, 6.2, "psychic", "psychic", 0, False, True, 1, 0, 0, (200, 140, 255), 1, "mc"),
    "mc_prime":     Weapon("mc_prime", "精神支配", 0, 5.0, 7.0, "psychic", "psychic", 0, False, True, 1, 0, 0, (210, 150, 255), 2, "mc"),
    "pillbox_gun":  Weapon("pillbox_gun", "机枪", 26, 0.45, 5.6, "sa", "bullet", 0, False, True, 2, 0, 45, (255, 235, 170)),
    "prism_tower":  Weapon("prism_tower", "光棱塔射线", 75, 2.2, 8.0, "prism", "beam", 0.5, False, True, 1, 0, 0, (140, 220, 255)),
    "sentry_gun":   Weapon("sentry_gun", "哨戒机炮", 24, 0.6, 5.6, "ap", "bullet", 0.1, False, True, 2, 0, 40, (255, 225, 160)),
    "flak_cannon":  Weapon("flak_cannon", "防空炮", 42, 1.1, 5.8, "flak", "bullet", 0.7, True, True, 3, 0, 40, (255, 205, 120)),
    "psychic_tower": Weapon("psychic_tower", "心灵波", 38, 1.2, 6.2, "psychic", "psychic", 0.2, False, True, 1, 0, 18, (200, 150, 255)),
    "gatling":      Weapon("gatling", "加特林机炮", 20, 0.28, 5.5, "sa", "bullet", 0, True, True, 1, 0, 50, (255, 240, 180)),
}


@dataclass(frozen=True)
class UnitDef:
    key: str
    name: str
    faction: str
    tab: str                    # infantry / vehicle / air
    cost: int
    hp: int
    armor: str
    speed: float                # 格/秒
    sight: float                # 格
    weapon: Optional[str]
    prereq: Tuple[str, ...] = ()
    tier: int = 1
    radius: float = 0.32        # 格
    desc: str = ""
    is_air: bool = False
    is_harvester: bool = False
    capture: bool = False
    suicide: bool = False
    berserk_on_death: bool = False
    mind_slots: int = 0
    build_time: float = 0.0

    def __post_init__(self):
        if self.build_time <= 0:
            object.__setattr__(self, "build_time", max(3.0, self.cost * C.BUILD_TIME_PER_CREDIT))


@dataclass(frozen=True)
class BuildingDef:
    key: str
    name: str
    faction: str
    tab: str                    # structure / defense / special
    cost: int
    hp: int
    armor: str
    w: int
    h: int
    power: int
    sight: float
    weapon: Optional[str] = None
    produces: Optional[str] = None
    prereq: Tuple[str, ...] = ()
    tier: int = 1
    superweapon: Optional[str] = None
    desc: str = ""
    build_time: float = 0.0
    starts_built: bool = False

    def __post_init__(self):
        if self.build_time <= 0:
            object.__setattr__(self, "build_time", max(5.0, self.cost * C.BUILDING_TIME_PER_CREDIT))

    @property
    def radius(self) -> float:
        """建筑占地的等效半径（格），由占地尺寸推导。"""
        return max(self.w, self.h) * 0.45


def _u(key, name, faction, tab, cost, hp, armor, speed, sight, weapon, prereq=(), tier=1,
       radius=0.32, desc="", **kw):
    return UnitDef(key, name, faction, tab, cost, hp, armor, speed, sight, weapon,
                   tuple(prereq), tier, radius, desc, **kw)


def _b(key, name, faction, tab, cost, hp, armor, w, h, power, sight, weapon=None,
       produces=None, prereq=(), tier=1, superweapon=None, desc=""):
    return BuildingDef(key, name, faction, tab, cost, hp, armor, w, h, power, sight,
                       weapon, produces, tuple(prereq), tier, superweapon, desc)


# ---------------------------------------------------------------- 盟军
UNITS = {}
BUILDINGS = {}


def _add(d):
    if isinstance(d, UnitDef):
        UNITS[d.key] = d
    else:
        BUILDINGS[d.key] = d


# ===== 盟军 =====
for d in [
    _u("a_rifle", "步枪兵", "allied", "infantry", 200, 125, "none", 1.6, 5.0, "rifle",
       desc="盟军基础步兵，价廉物美的反步兵火力。"),
    _u("a_rocket", "火箭兵", "allied", "infantry", 300, 110, "none", 1.5, 6.0, "rocket_launcher",
       desc="携带火箭筒，可同时攻击地面与空中目标。"),
    _u("a_engineer", "工程师", "allied", "infantry", 500, 90, "none", 1.7, 5.0, None,
       desc="可以占领敌方或中立建筑，占领后建筑满血归你所有。", capture=True, radius=0.28),
    _u("a_grizzly", "灰熊坦克", "allied", "vehicle", 700, 300, "light", 2.6, 6.0, "grizzly_gun",
       desc="盟军主战坦克，机动性优秀，适合快速穿插。", radius=0.48),
    _u("a_ifv", "多功能步兵车", "allied", "vehicle", 600, 220, "light", 3.0, 7.0, "ifv_gun",
       desc="高机动速射载具，可对空，适合骚扰与防空。", radius=0.44),
    _u("a_prism", "光棱坦克", "allied", "vehicle", 1200, 180, "light", 2.0, 7.0, "prism_beam",
       ("a_radar",), 2, 0.46, "超远程光棱射线，脆皮但输出极高，需要前排保护。"),
    _u("a_heli", "夜鹰直升机", "allied", "air", 1000, 260, "light", 5.0, 8.0, "heli_rockets",
       ("a_radar",), 2, 0.5, "空中火箭平台，无视地形，只能被防空火力命中。", is_air=True),
    _u("a_harvester", "采矿车", "allied", "vehicle", 1400, 1000, "heavy", 1.8, 5.0, None,
       ("a_refinery",), 1, 0.5, "自动往返矿区与精炼厂采集矿石。", is_harvester=True),
]:
    _add(d)

for d in [
    _b("a_cy", "建造厂", "allied", "structure", 3000, 1500, "steel", 3, 3, 0, 7.0,
       desc="基地核心，提供建筑建造与科技基础。被摧毁后可以重建。"),
    _b("a_power", "电厂", "allied", "structure", 800, 750, "wood", 2, 2, 100, 6.0,
       desc="提供 100 点电力。电力不足会拖慢生产与防御武器射速。"),
    _b("a_refinery", "矿石精炼厂", "allied", "structure", 2000, 1000, "steel", 3, 2, -35, 6.0,
       desc="处理矿石换取资金，建成时附赠一辆采矿车。"),
    _b("a_barracks", "兵营", "allied", "structure", 500, 800, "wood", 2, 2, -15, 6.0, produces="infantry",
       desc="训练盟军步兵。"),
    _b("a_factory", "战车工厂", "allied", "structure", 2000, 1000, "steel", 3, 3, -35, 6.0, produces="vehicle",
       desc="生产盟军载具与采矿车。"),
    _b("a_radar", "雷达站", "allied", "structure", 1000, 800, "wood", 2, 2, -25, 9.0, tier=2,
       desc="解锁二级科技：光棱坦克、夜鹰直升机、天气控制器。"),
    _b("a_pillbox", "机枪碉堡", "allied", "defense", 600, 700, "steel", 1, 1, -10, 6.0, weapon="pillbox_gun",
       desc="廉价的对地防御，克制步兵。"),
    _b("a_prismtower", "光棱塔", "allied", "defense", 1200, 800, "steel", 1, 1, -30, 7.0, weapon="prism_tower",
       prereq=("a_radar",), desc="高伤害对地防御塔，射程远。"),
    _b("a_super", "天气控制器", "allied", "special", 5000, 1000, "concrete", 2, 2, -80, 6.0,
       prereq=("a_radar",), tier=3, superweapon="storm",
       desc="超级武器：闪电风暴，对目标区域持续降下雷暴。"),
]:
    _add(d)

# ===== 苏军 =====
for d in [
    _u("s_conscript", "动员兵", "soviet", "infantry", 200, 100, "none", 1.6, 5.0, "conscript_rifle",
       desc="苏军基础步兵，便宜、量大、管饱。"),
    _u("s_flak", "防空步兵", "soviet", "infantry", 300, 100, "flak", 1.5, 6.0, "flak_gun",
       desc="高射机枪，对空火力凶猛，对步兵也有溅射。"),
    _u("s_tesla", "磁暴步兵", "soviet", "infantry", 500, 125, "plate", 1.4, 5.0, "tesla_zap",
       desc="近距离磁暴电击，对步兵与轻型目标伤害极高。"),
    _u("s_rhino", "犀牛坦克", "soviet", "vehicle", 900, 400, "heavy", 2.3, 6.0, "rhino_gun",
       desc="苏军主战坦克，高血量高单发，正面硬刚之王。", radius=0.5),
    _u("s_apoc", "天启坦克", "soviet", "vehicle", 1750, 800, "heavy", 1.9, 6.0, "apoc_gun",
       ("s_radar",), 2, 0.6, "双联重炮的陆战堡垒，几乎无法被正面击穿。"),
    _u("s_v3", "V3火箭发射车", "soviet", "vehicle", 1000, 200, "light", 1.7, 7.0, "v3_rocket",
       ("s_radar",), 2, 0.48, "超远程攻城火箭，需要前排与视野保护。"),
    _u("s_drone", "恐怖机器人", "soviet", "vehicle", 600, 150, "light", 4.2, 5.0, "drone_boom",
       desc="高速自爆单位，冲进敌阵后引爆造成范围伤害。", suicide=True, radius=0.3),
    _u("s_kirov", "基洛夫飞艇", "soviet", "air", 2000, 1000, "heavy", 1.1, 8.0, "kirov_bomb",
       ("s_radar",), 2, 0.78, "缓慢但恐怖的空中堡垒，投下重型炸弹。", is_air=True),
    _u("s_harvester", "采矿车", "soviet", "vehicle", 1400, 1000, "heavy", 1.8, 5.0, None,
       ("s_refinery",), 1, 0.5, "自动往返矿区与精炼厂采集矿石。", is_harvester=True),
]:
    _add(d)

for d in [
    _b("s_cy", "建造厂", "soviet", "structure", 3000, 1500, "steel", 3, 3, 0, 7.0,
       desc="基地核心，提供建筑建造与科技基础。被摧毁后可以重建。"),
    _b("s_power", "电厂", "soviet", "structure", 800, 750, "wood", 2, 2, 100, 6.0,
       desc="提供 100 点电力。"),
    _b("s_refinery", "矿石精炼厂", "soviet", "structure", 2000, 1000, "steel", 3, 2, -35, 6.0,
       desc="处理矿石换取资金，建成时附赠一辆采矿车。"),
    _b("s_barracks", "兵营", "soviet", "structure", 500, 800, "wood", 2, 2, -15, 6.0, produces="infantry",
       desc="训练苏军步兵。"),
    _b("s_factory", "战车工厂", "soviet", "structure", 2000, 1000, "steel", 3, 3, -35, 6.0, produces="vehicle",
       desc="生产苏军载具与采矿车。"),
    _b("s_radar", "雷达站", "soviet", "structure", 1000, 800, "wood", 2, 2, -25, 9.0, tier=2,
       desc="解锁二级科技：天启坦克、V3、基洛夫、核弹发射井。"),
    _b("s_sentry", "哨戒炮", "soviet", "defense", 600, 700, "steel", 1, 1, -10, 6.0, weapon="sentry_gun",
       desc="廉价对地防御，射速快。"),
    _b("s_flakcannon", "防空炮", "soviet", "defense", 1000, 800, "steel", 1, 1, -25, 7.0, weapon="flak_cannon",
       desc="强力防空炮，同时兼顾对地溅射。"),
    _b("s_super", "核弹发射井", "soviet", "special", 5000, 1000, "concrete", 2, 2, -80, 6.0,
       prereq=("s_radar",), tier=3, superweapon="nuke",
       desc="超级武器：战术核弹，单次毁灭性范围伤害。"),
]:
    _add(d)

# ===== 尤里 =====
for d in [
    _u("y_initiate", "尤里新兵", "yuri", "infantry", 200, 100, "none", 1.6, 5.0, "initiate_bolt",
       desc="发射心灵冲击波的基础步兵，对步兵有奇效。"),
    _u("y_brute", "狂兽人", "yuri", "infantry", 400, 260, "plate", 1.9, 5.0, "brute_claw",
       desc="近战肉盾，血量高，能冲到敌人脸上撕碎步兵。", radius=0.34),
    _u("y_lasher", "镭射坦克", "yuri", "vehicle", 700, 300, "medium", 2.6, 6.0, "lasher_gun",
       desc="尤里主战坦克，镭射炮对载具与建筑都很稳定。", radius=0.48),
    _u("y_magnet", "磁电坦克", "yuri", "vehicle", 1000, 280, "light", 2.2, 7.0, "magnet_beam",
       ("y_radar",), 2, 0.48, "磁力光束专克载具，对步兵无效。"),
    _u("y_chaos", "神经突击车", "yuri", "vehicle", 800, 220, "light", 3.2, 6.0, None,
       ("y_radar",), 2, 0.42, "自爆后释放神经毒气，让周围敌军陷入混乱互相攻击。",
       berserk_on_death=True),
    _u("y_mc", "心灵控制车", "yuri", "vehicle", 1200, 260, "light", 2.4, 7.0, "mc_beam",
       ("y_radar",), 2, 0.46, "心灵控制一台敌方载具或步兵，控制者阵亡则目标解放。", mind_slots=1),
    _u("y_disc", "镭射飞碟", "yuri", "air", 1200, 300, "light", 4.5, 8.0, "disc_laser",
       ("y_radar",), 2, 0.5, "高速悬浮飞碟，持续镭射输出，可被防空击落。", is_air=True),
    _u("y_prime", "尤里复制人", "yuri", "infantry", 1500, 220, "none", 2.0, 7.0, "mc_prime",
       ("y_radar",), 2, 0.3, "强大的心灵控制者，可同时控制 2 个敌方单位。", mind_slots=2),
    _u("y_harvester", "采矿车", "yuri", "vehicle", 1400, 1000, "heavy", 1.8, 5.0, None,
       ("y_refinery",), 1, 0.5, "自动往返矿区与精炼厂采集矿石。", is_harvester=True),
]:
    _add(d)

for d in [
    _b("y_cy", "建造厂", "yuri", "structure", 3000, 1500, "steel", 3, 3, 0, 7.0,
       desc="基地核心，提供建筑建造与科技基础。被摧毁后可以重建。"),
    _b("y_power", "生化电厂", "yuri", "structure", 800, 750, "wood", 2, 2, 100, 6.0,
       desc="提供 100 点电力。"),
    _b("y_refinery", "矿石精炼厂", "yuri", "structure", 2000, 1000, "steel", 3, 2, -35, 6.0,
       desc="处理矿石换取资金，建成时附赠一辆采矿车。"),
    _b("y_barracks", "兵营", "yuri", "structure", 500, 800, "wood", 2, 2, -15, 6.0, produces="infantry",
       desc="训练尤里步兵。"),
    _b("y_factory", "战车工厂", "yuri", "structure", 2000, 1000, "steel", 3, 3, -35, 6.0, produces="vehicle",
       desc="生产尤里载具与采矿车。"),
    _b("y_radar", "心灵雷达", "yuri", "structure", 1000, 800, "wood", 2, 2, -25, 9.0, tier=2,
       desc="解锁二级科技：磁电坦克、心灵控制车、飞碟、心灵控制器。"),
    _b("y_psychtower", "心灵塔", "yuri", "defense", 800, 700, "steel", 1, 1, -15, 6.0, weapon="psychic_tower",
       desc="心灵波防御塔，对步兵伤害极高。"),
    _b("y_gatling", "加特林炮", "yuri", "defense", 1000, 800, "steel", 1, 1, -25, 7.0, weapon="gatling",
       desc="高射速防空/对地两用防御。"),
    _b("y_super", "心灵控制器", "yuri", "special", 5000, 1000, "concrete", 2, 2, -80, 6.0,
       prereq=("y_radar",), tier=3, superweapon="dominator",
       desc="超级武器：心灵支配，永久控制区域内最多 12 个敌方单位。"),
]:
    _add(d)


SUPERWEAPONS = {
    "storm": {
        "name": "闪电风暴", "kind": "strike", "radius": 5.0, "damage": 900.0, "duration": 5.0,
        "color": (150, 210, 255), "desc": "在目标区域持续 5 秒降下雷暴，对范围内所有单位与建筑造成伤害。",
    },
    "nuke": {
        "name": "战术核弹", "kind": "strike", "radius": 4.6, "damage": 1600.0, "duration": 0.1,
        "color": (255, 180, 90), "desc": "单次巨大范围爆炸，可瞬间抹平整片敌军。",
    },
    "dominator": {
        "name": "心灵支配", "kind": "dominate", "radius": 6.0, "mc": 12,
        "color": (200, 140, 255), "desc": "永久心灵控制区域内最多 12 个敌方单位。",
    },
}

# 建筑可生产类别 -> 需要该建筑
PRODUCER_OF = {"infantry": "barracks", "vehicle": "factory"}

TAB_NAMES = {
    "structure": "建筑", "defense": "防御", "special": "超武",
    "infantry": "步兵", "vehicle": "载具", "air": "空军",
}

FACTION_BUILD_ORDER = {
    "allied": {
        "structure": ["a_power", "a_refinery", "a_barracks", "a_factory", "a_radar"],
        "defense": ["a_pillbox", "a_prismtower"],
        "special": ["a_super"],
        "infantry": ["a_rifle", "a_rocket", "a_engineer"],
        "vehicle": ["a_grizzly", "a_ifv", "a_prism", "a_harvester"],
        "air": ["a_heli"],
    },
    "soviet": {
        "structure": ["s_power", "s_refinery", "s_barracks", "s_factory", "s_radar"],
        "defense": ["s_sentry", "s_flakcannon"],
        "special": ["s_super"],
        "infantry": ["s_conscript", "s_flak", "s_tesla"],
        "vehicle": ["s_rhino", "s_apoc", "s_v3", "s_drone", "s_harvester"],
        "air": ["s_kirov"],
    },
    "yuri": {
        "structure": ["y_power", "y_refinery", "y_barracks", "y_factory", "y_radar"],
        "defense": ["y_psychtower", "y_gatling"],
        "special": ["y_super"],
        "infantry": ["y_initiate", "y_brute", "y_prime"],
        "vehicle": ["y_lasher", "y_magnet", "y_chaos", "y_mc", "y_harvester"],
        "air": ["y_disc"],
    },
}


def get_def(key):
    return UNITS.get(key) or BUILDINGS[key]


def unit_icon_color(key):
    if key in UNITS:
        return C.FACTION_INFO[UNITS[key].faction]["color"]
    return (160, 160, 160)
