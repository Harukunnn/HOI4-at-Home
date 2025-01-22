# Engineering/pathfinding.py

import math
import collections
from .consts import NX, NY, T_MOUNTAIN, TILE_SIZE

def in_bounds(tx, ty):
    """
    Vérifie si (tx, ty) est dans la grille [0..NX-1, 0..NY-1].
    """
    return (0 <= tx < NX and 0 <= ty < NY)

def distance(x1, y1, x2, y2):
    """
    Distance euclidienne entre (x1, y1) et (x2, y2).
    """
    return math.hypot(x2 - x1, y2 - y1)

def build_blocked_map(grid, other_units, mountain_margin_px=16, unit_margin_px=16):
    """
    Construit une map 'blocked[y][x]' tenant compte d'une marge autour des montagnes
    et d'une marge autour des autres unités.

    - mountain_margin_px : rayon en pixels à bloquer autour des montagnes.
    - unit_margin_px : rayon en pixels à bloquer autour des unités.
    - Ne requiert aucune modification dans les autres scripts.
    """
    ny = len(grid)
    nx = len(grid[0])
    blocked = [[False]*nx for _ in range(ny)]

    tile_margin_mtn = int(math.ceil(mountain_margin_px / TILE_SIZE))
    for ty in range(ny):
        for tx in range(nx):
            if grid[ty][tx] == T_MOUNTAIN:
                for dy in range(-tile_margin_mtn, tile_margin_mtn+1):
                    for dx in range(-tile_margin_mtn, tile_margin_mtn+1):
                        xx = tx+dx
                        yy = ty+dy
                        if in_bounds(xx, yy):
                            blocked[yy][xx] = True

    tile_margin_unit = int(math.ceil(unit_margin_px / TILE_SIZE))
    for u in other_units:
        ux = int(u.x // TILE_SIZE)
        uy = int(u.y // TILE_SIZE)
        for dy in range(-tile_margin_unit, tile_margin_unit+1):
            for dx in range(-tile_margin_unit, tile_margin_unit+1):
                xx = ux+dx
                yy = uy+dy
                if in_bounds(xx, yy):
                    blocked[yy][xx] = True

    return blocked

def find_path_bfs(grid, start_tile, goal_tile):
    """
    BFS classique en 4 directions, sans marge supplémentaire.
    Renvoie la liste de tuiles (x, y) menant de start_tile à goal_tile.
    Ne nécessite aucune modification externe.
    """
    (sx, sy) = start_tile
    (gx, gy) = goal_tile

    if not in_bounds(sx, sy) or not in_bounds(gx, gy):
        return []
    if (sx, sy) == (gx, gy):
        return []

    visited = [[False]*len(grid[0]) for _ in range(len(grid))]
    visited[sy][sx] = True
    parent = {}
    parent[(sx, sy)] = None
    queue = collections.deque()
    queue.append((sx, sy))

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == (gx, gy):
            break
        for (dx, dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx_ = cx + dx
            ny_ = cy + dy
            if in_bounds(nx_, ny_):
                if not visited[ny_][nx_]:
                    if grid[ny_][nx_] != T_MOUNTAIN:
                        visited[ny_][nx_] = True
                        parent[(nx_, ny_)] = (cx, cy)
                        queue.append((nx_, ny_))

    if (gx, gy) not in parent:
        return []

    path=[]
    cur=(gx,gy)
    while cur is not None:
        path.append(cur)
        cur=parent[cur]
    path.reverse()
    return path[1:]

def find_path_any_angle(
    grid, start_tile, goal_tile,
    other_units=None,
    mountain_margin_px=16,
    unit_margin_px=16
):
    """
    BFS en 8 directions (any-angle) + simplification du chemin:
      1) On construit un blocked_map tenant compte des marges (montagnes+units)
      2) BFS en 8 directions sur tuiles
      3) Reconstitution du chemin tuiles => pixels
      4) Simplification (line_of_sight)
      5) Retour au format tuiles (sans exiger de modif externe).
    """
    (sx, sy) = start_tile
    (gx, gy) = goal_tile

    if not in_bounds(sx, sy) or not in_bounds(gx, gy):
        return []
    if (sx, sy) == (gx, gy):
        return []

    if other_units is None:
        other_units = []

    blocked_map = build_blocked_map(
        grid, other_units,
        mountain_margin_px=mountain_margin_px,
        unit_margin_px=unit_margin_px
    )
    if blocked_map[sy][sx] or blocked_map[gy][gx]:
        return []

    visited = [[False]*len(grid[0]) for _ in range(len(grid))]
    visited[sy][sx] = True
    parent = {}
    parent[(sx, sy)] = None
    queue = collections.deque()
    queue.append((sx, sy))

    # 8 directions
    directions_8 = [(1,0),(-1,0),(0,1),(0,-1),
                    (1,1),(1,-1),(-1,1),(-1,-1)]

    found=False
    while queue:
        cx, cy = queue.popleft()
        if (cx,cy)==(gx,gy):
            found=True
            break
        for (dx,dy) in directions_8:
            nx_ = cx+dx
            ny_ = cy+dy
            if in_bounds(nx_, ny_):
                if not blocked_map[ny_][nx_]:
                    if not visited[ny_][nx_]:
                        visited[ny_][nx_] = True
                        parent[(nx_,ny_)] = (cx,cy)
                        queue.append((nx_,ny_))

    if not found:
        return []

    # On récupère le chemin "tuiles"
    path=[]
    cur=(gx,gy)
    while cur is not None:
        path.append(cur)
        cur=parent[cur]
    path.reverse()
    # retire la tuile de départ (pour compat)
    path = path[1:]

    # Convertit en px
    px_path = [
        (tx*TILE_SIZE + TILE_SIZE/2, ty*TILE_SIZE + TILE_SIZE/2)
        for (tx, ty) in path
    ]

    # Simplification any-angle
    px_path = simplify_path(px_path, blocked_map)

    # Convertit de nouveau en tuiles
    tile_path=[]
    for (px,py) in px_path:
        tx=int(px//TILE_SIZE)
        ty=int(py//TILE_SIZE)
        tile_path.append((tx,ty))

    return tile_path

def simplify_path(px_path, blocked_map):
    """
    Simplifie le chemin en sautant des points si line_of_sight est valide.
    """
    if len(px_path) < 2:
        return px_path

    newpath = [px_path[0]]
    current = 0
    while current < len(px_path)-1:
        best = current+1
        for nxt in range(current+2, len(px_path)):
            if line_of_sight(px_path[current], px_path[nxt], blocked_map):
                best = nxt
            else:
                break
        newpath.append(px_path[best])
        current = best
        if best >= len(px_path)-1:
            break

    return newpath

def line_of_sight(p1, p2, blocked_map):
    """
    Vérifie si le segment [p1..p2] intersecte blocked_map.
    """
    return not segment_blocked_bresenham(p1, p2, blocked_map)

def segment_blocked_bresenham(p1, p2, blocked_map):
    """
    Parcourt en mode Bresenham le segment [p1..p2]
    et vérifie si on intersecte une case 'blocked'.
    """
    (x1, y1) = p1
    (x2, y2) = p2

    tx1=int(x1//TILE_SIZE)
    ty1=int(y1//TILE_SIZE)
    tx2=int(x2//TILE_SIZE)
    ty2=int(y2//TILE_SIZE)

    dx = abs(tx2 - tx1)
    sx = 1 if tx1 < tx2 else -1
    dy = -abs(ty2 - ty1)
    sy = 1 if ty1 < ty2 else -1
    err = dx + dy

    cx, cy = tx1, ty1
    while True:
        if in_bounds(cx,cy):
            if blocked_map[cy][cx]:
                return True
        if (cx, cy) == (tx2, ty2):
            break
        e2 = 2*err
        if e2 >= dy:
            err += dy
            cx += sx
        if e2 <= dx:
            err += dx
            cy += sy

    return False
