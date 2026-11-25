# -*- coding: utf-8 -*-
"""从 RA2 Explorer 在线派生图集切出本项目使用的精灵图。

数据来源：https://hansimov.github.io/ra2-explorer/ （代码 MIT，游戏素材版权归 EA）
本脚本只做一次性抓取与切图，运行产物写入 game/assets/sprites/。
"""
import json
import os
import urllib.request

from PIL import Image

BASE = "https://cdn.jsdelivr.net/npm/ra2-explorer-pages-core@0.16.0/data"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "game", "assets", "sprites")
CACHE_DIR = os.path.join(ROOT, "build", "ra2-atlas-cache")

# 本项目 key -> (RA2 实体 id, 图集分类)
SPRITES = {
    # 盟军
    "a_rifle": ("E1", "infantry"),
    "a_rocket": ("GGI", "infantry"),
    "a_engineer": ("ENGINEER", "infantry"),
    "a_grizzly": ("MTNK", "vehicle"),
    "a_ifv": ("FV", "vehicle"),
    "a_prism": ("SREF", "vehicle"),
    "a_heli": ("SHAD", "vehicle"),
    "a_harvester": ("CMIN", "vehicle"),
    "a_cy": ("GACNST", "building"),
    "a_power": ("GAPOWR", "building"),
    "a_refinery": ("GAREFN", "building"),
    "a_barracks": ("GAPILE", "building"),
    "a_factory": ("GAWEAP", "building"),
    "a_radar": ("GAAIRC", "building"),
    "a_pillbox": ("GAPILL", "building"),
    "a_prismtower": ("ATESLA", "building"),
    "a_super": ("GAWEAT", "building"),
    # 苏军
    "s_conscript": ("E2", "infantry"),
    "s_flak": ("FLAKT", "infantry"),
    "s_tesla": ("SHK", "infantry"),
    "s_rhino": ("HTNK", "vehicle"),
    "s_apoc": ("APOC", "vehicle"),
    "s_v3": ("V3", "vehicle"),
    "s_drone": ("DRON", "vehicle"),
    "s_kirov": ("ZEP", "vehicle"),
    "s_harvester": ("HARV", "vehicle"),
    "s_cy": ("NACNST", "building"),
    "s_power": ("NAPOWR", "building"),
    "s_refinery": ("NAREFN", "building"),
    "s_barracks": ("NAHAND", "building"),
    "s_factory": ("NAWEAP", "building"),
    "s_radar": ("NARADR", "building"),
    "s_sentry": ("NALASR", "building"),
    "s_flakcannon": ("NAFLAK", "building"),
    "s_super": ("NAMISL", "building"),
    # 尤里
    "y_initiate": ("INIT", "infantry"),
    "y_brute": ("BRUTE", "infantry"),
    "y_prime": ("YURI", "infantry"),
    "y_lasher": ("LTNK", "vehicle"),
    "y_magnet": ("TELE", "vehicle"),
    "y_chaos": ("CAOS", "vehicle"),
    "y_mc": ("MIND", "vehicle"),
    "y_disc": ("DISK", "vehicle"),
    "y_harvester": ("SMIN", "vehicle"),
    "y_cy": ("YACNST", "building"),
    "y_power": ("YAPOWR", "building"),
    "y_refinery": ("YAREFN", "building"),
    "y_barracks": ("YABRCK", "building"),
    "y_factory": ("YAWEAP", "building"),
    "y_radar": ("YACOMD", "building"),
    "y_psychtower": ("YAPSYT", "building"),
    "y_gatling": ("YAGGUN", "building"),
    "y_super": ("YAPPET", "building"),
}


def fetch(url, path):
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path)
    return path


def fade_foundation(img):
    """淡化贴图底部的浅色雪地地基，让建筑在草地上不显得突兀。

    只降低底部 30% 区域内浅色低饱和像素的不透明度，不改动颜色与形状，
    避免误删建筑本体的白色墙面。
    """
    img = img.copy()
    px = img.load()
    w, h = img.size
    for y in range(int(h * 0.70), h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and min(r, g, b) >= 205 and max(r, g, b) - min(r, g, b) <= 34:
                px[x, y] = (r, g, b, 130)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    catalog_path = fetch(f"{BASE}/catalog/entities.zh-CN.json",
                         os.path.join(CACHE_DIR, "entities.zh-CN.json"))
    with open(catalog_path, encoding="utf-8") as f:
        catalog = {it["id"]: it for it in json.load(f)["items"]}

    # 每种分类的图集需要几个朝向文件
    kinds = {kind for _, kind in SPRITES.values()}
    max_facing = {}
    for eid, kind in SPRITES.values():
        item = catalog.get(eid)
        if not item:
            raise SystemExit(f"缺少实体：{eid}")
        atlas = item["thumbnail_atlas"]
        max_facing[kind] = max(max_facing.get(kind, 1), atlas["facing_count"])

    atlases = {}
    for kind in kinds:
        atlases[kind] = []
        for facing in range(max_facing[kind]):
            url = f"{BASE}/previews/entity-atlases/{kind}/{facing}-r10.webp"
            path = fetch(url, os.path.join(CACHE_DIR, f"{kind}-{facing}.webp"))
            atlases[kind].append(Image.open(path).convert("RGBA"))

    meta = {}
    for key, (eid, kind) in sorted(SPRITES.items()):
        item = catalog[eid]
        ta = item["thumbnail_atlas"]
        cols, cw, ch = ta["columns"], ta["cell_width"], ta["cell_height"]
        row, col = divmod(ta["index"], cols)
        bounds_list = ta["content_bounds"] or [None]
        saved = []
        for facing in range(ta["facing_count"]):
            bounds = bounds_list[min(facing, len(bounds_list) - 1)]
            if not bounds:
                raise SystemExit(f"{key} 第 {facing} 朝向缺少裁剪框")
            cell = atlases[kind][facing].crop(
                (col * cw, row * ch, col * cw + cw, row * ch + ch))
            img = cell.crop((bounds["x"], bounds["y"],
                             bounds["x"] + bounds["width"],
                             bounds["y"] + bounds["height"]))
            name = key if facing == 0 else f"{key}_f{facing}"
            if kind == "building":
                img = fade_foundation(img)
            img.save(os.path.join(OUT_DIR, f"{name}.png"))
            saved.append(img.size)
        meta[key] = {"entity": eid, "kind": kind, "facings": ta["facing_count"],
                     "frames": saved}
        print(f"{key:16s} <- {eid:10s} facings={ta['facing_count']} size={saved[0]}")

    with open(os.path.join(OUT_DIR, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"\n共导出 {len(meta)} 个精灵到 {OUT_DIR}")


if __name__ == "__main__":
    main()
