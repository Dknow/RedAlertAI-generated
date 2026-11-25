# -*- coding: utf-8 -*-
"""网格寻路：流场（群体移动）+ A*（矿车等单点路径）。"""
from collections import deque
import heapq

from .config import MAP_W, MAP_H, TILE

W, H = MAP_W, MAP_H
N = W * H
NEIGHBORS = ((-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1))


def idx(tx, ty):
    return ty * W + tx


def in_bounds(tx, ty):
    return 0 <= tx < W and 0 <= ty < H


class FlowField:
    """从目标格出发的 BFS 距离场，值越小越接近目标。"""

    def __init__(self, blocked, goal_tiles):
        self.dist = [-1] * N
        q = deque()
        for tx, ty in goal_tiles:
            if in_bounds(tx, ty) and not blocked[idx(tx, ty)]:
                self.dist[idx(tx, ty)] = 0
                q.append((tx, ty))
        self.goal = goal_tiles[0] if goal_tiles else (0, 0)
        while q:
            tx, ty = q.popleft()
            d = self.dist[idx(tx, ty)] + 1
            for dx, dy in NEIGHBORS:
                nx, ny = tx + dx, ty + dy
                if not in_bounds(nx, ny):
                    continue
                ni = idx(nx, ny)
                if blocked[ni] or self.dist[ni] != -1:
                    continue
                if dx and dy:
                    # 禁止斜穿墙角
                    if blocked[idx(tx + dx, ty)] or blocked[idx(tx, ty + dy)]:
                        continue
                self.dist[ni] = d
                q.append((nx, ny))

    def step_from(self, tx, ty, blocked):
        """返回朝目标前进的下一格（无路可走返回 None）。"""
        if not in_bounds(tx, ty):
            return None
        cur = self.dist[idx(tx, ty)]
        if cur < 0:
            return None
        best = None
        bestd = cur
        for dx, dy in NEIGHBORS:
            nx, ny = tx + dx, ty + dy
            if not in_bounds(nx, ny):
                continue
            ni = idx(nx, ny)
            d = self.dist[ni]
            if d < 0 or d >= bestd:
                continue
            if dx and dy and (blocked[idx(tx + dx, ty)] or blocked[idx(tx, ty + dy)]):
                continue
            bestd = d
            best = (nx, ny)
        return best


def astar(blocked, start, goal, max_expand=6000):
    """A* 返回格坐标路径（含起点终点），失败返回 []。"""
    if not in_bounds(*start) or not in_bounds(*goal):
        return []
    if blocked[idx(*goal)]:
        goal = nearest_free(blocked, *goal)
        if goal is None:
            return []
    if start == goal:
        return [start]
    sx, sy = start
    gx, gy = goal
    open_heap = [(0, 0.0, start)]
    came = {}
    gscore = {start: 0.0}
    expanded = 0
    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            return path
        expanded += 1
        if expanded > max_expand:
            return []
        cx, cy = cur
        for dx, dy in NEIGHBORS:
            nx, ny = cx + dx, cy + dy
            if not in_bounds(nx, ny):
                continue
            ni = idx(nx, ny)
            if blocked[ni]:
                continue
            if dx and dy and (blocked[idx(cx + dx, cy)] or blocked[idx(cx, cy + dy)]):
                continue
            step = 1.4142 if (dx and dy) else 1.0
            ng = g + step
            nxt = (nx, ny)
            if ng < gscore.get(nxt, 1e18):
                gscore[nxt] = ng
                came[nxt] = cur
                h = max(abs(nx - gx), abs(ny - gy)) + 0.4142 * min(abs(nx - gx), abs(ny - gy))
                heapq.heappush(open_heap, (ng + h, ng, nxt))
    return []


def nearest_free(blocked, tx, ty, max_r=10):
    if in_bounds(tx, ty) and not blocked[idx(tx, ty)]:
        return (tx, ty)
    for r in range(1, max_r + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                nx, ny = tx + dx, ty + dy
                if in_bounds(nx, ny) and not blocked[idx(nx, ny)]:
                    return (nx, ny)
    return None


def px_to_tile(px, py):
    return int(px // TILE), int(py // TILE)


def tile_center(tx, ty):
    return (tx + 0.5) * TILE, (ty + 0.5) * TILE


def clamp_camera(cx, cy, view_w, view_h, world_w, world_h):
    maxx = max(0, world_w - view_w)
    maxy = max(0, world_h - view_h)
    return max(0, min(cx, maxx)), max(0, min(cy, maxy))
