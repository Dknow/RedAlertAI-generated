# -*- coding: utf-8 -*-
"""字体与文本工具（中文优先）。"""
import pygame

_cache = {}


def font(size, bold=False):
    key = (size, bold)
    f = _cache.get(key)
    if f is not None:
        return f
    path = None
    try:
        path = pygame.font.match_font("microsoftyahei,msyh,simhei,dengxian,simsun", bold=bold)
    except Exception:
        path = None
    if path:
        f = pygame.font.Font(path, size)
    else:
        f = pygame.font.SysFont(None, size, bold=bold)
    _cache[key] = f
    return f


def text(surf, s, pos, size=16, color=(228, 232, 236), bold=False, align="left", shadow=True):
    f = font(size, bold)
    img = f.render(str(s), True, color)
    x, y = pos
    if align == "center":
        x -= img.get_width() // 2
    elif align == "right":
        x -= img.get_width()
    if shadow:
        sh = f.render(str(s), True, (0, 0, 0))
        sh.set_alpha(150)
        surf.blit(sh, (x + 1, y + 2))
    surf.blit(img, (x, y))
    return img.get_width()


def wrap(s, size, width, bold=False):
    f = font(size, bold)
    lines = []
    cur = ""
    for ch in str(s):
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        test = cur + ch
        if f.size(test)[0] > width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines
