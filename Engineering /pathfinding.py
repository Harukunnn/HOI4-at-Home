# Engineering/pathfinding.py

import math
import collections
from .consts import NX, NY, T_MOUNTAIN, TILE_SIZE

def in_bounds(tx, ty):
    return (0 <= tx < NX and 0 <= ty < NY)

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def build_blocked_map(grid, other_units, mountain_margin_px=16, unit_margin_px=16):
    """
    Construit une map 'blocked[y][x]' en tenant compte d'une marge autour des montagnes
    et des autres unités.
    """
    ny = len(grid)
    nx = len(grid[0])
    blocked = [[False]*nx for _ in range(ny)]

    # marge en cases pour les montagnes
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

    # marge en cases pour les unités
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
    BFS classique en 4 directions SANS marge autour des montagnes/units,
    comme avant (pour compat).
    """
    (sx, sy) = start_tile
    (gx, gy) = goal_tile

    if not in_bounds(sx, sy) or not in_bounds(gx, gy):
        return []
    if (sx, sy) == (gx, gy):
        return []

    visited = set()
    visited.add((sx, sy))
    parent = {}
    parent[(sx, sy)] = None
    queue = collections.deque()
    queue.append((sx, sy))

    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) == (gx, gy):
            break
        for (dx, dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx_ = cx+dx
            ny_ = cy+dy
            if in_bounds(nx_, ny_):
                if (nx_, ny_) not in visited:
                    if grid[ny_][nx_] != T_MOUNTAIN:
                        visited.add((nx_, ny_))
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

def find_path_any_angle(grid, start_tile, goal_tile,
                        other_units=None,
                        mountain_margin_px=16,
                        unit_margin_px=16):
    """
    BFS en 8 directions + lissage "any-angle", contournant montagnes/units à distance.
    """
    (sx,sy) = start_tile
    (gx,gy) = goal_tile

    if not in_bounds(sx,sy) or not in_bounds(gx,gy):
        return []
    if (sx,sy) == (gx,gy):
        return []

    if other_units is None:
        other_units=[]

    blocked_map = build_blocked_map(grid, other_units,
                                    mountain_margin_px=mountain_margin_px,
                                    unit_margin_px=unit_margin_px)
    if blocked_map[sy][sx] or blocked_map[gy][gx]:
        return []

    visited=set()
    visited.add((sx,sy))
    parent={}
    parent[(sx,sy)] = None
    from collections import deque
    queue = deque()
    queue.append((sx,sy))

    # 8 directions
    directions_8 = [(1,0),(-1,0),(0,1),(0,-1),
                    (1,1),(1,-1),(-1,1),(-1,-1)]

    found=False
    while queue:
        cx,cy = queue.popleft()
        if (cx,cy)==(gx,gy):
            found=True
            break
        for (dx,dy) in directions_8:
            nx_ = cx+dx
            ny_ = cy+dy
            if in_bounds(nx_, ny_):
                if not blocked_map[ny_][nx_]:
                    if (nx_,ny_) not in visited:
                        visited.add((nx_,ny_))
                        parent[(nx_,ny_)] = (cx,cy)
                        queue.append((nx_,ny_))

    if not found:
        return []

    # Reconstruit chemin
    path=[]
    cur=(gx,gy)
    while cur is not None:
        path.append(cur)
        cur=parent[cur]
    path.reverse()
    # retire le premier
    path=path[1:]

    # on convertit en px
    px_path = [(t[0]*TILE_SIZE+TILE_SIZE/2, t[1]*TILE_SIZE+TILE_SIZE/2) for t in path]
    px_path = simplify_path(px_path, blocked_map)

    # retransforme en tuiles
    tile_path=[]
    for (px,py) in px_path:
        tx=int(px//TILE_SIZE)
        ty=int(py//TILE_SIZE)
        tile_path.append((tx,ty))
    return tile_path

def simplify_path(px_path, blocked_map):
    """
    Lisse la liste px_path en sautant des points
    via line_of_sight.
    """
    if len(px_path)<2:
        return px_path
    newpath=[px_path[0]]
    current=0
    while current<len(px_path)-1:
        best = current+1
        for nxt in range(current+2, len(px_path)):
            if line_of_sight(px_path[current], px_path[nxt], blocked_map):
                best=nxt
            else:
                break
        newpath.append(px_path[best])
        current=best
        if best>=len(px_path)-1:
            break
    return newpath

def line_of_sight(p1, p2, blocked_map):
    return not segment_blocked_bresenham(p1, p2, blocked_map)

def segment_blocked_bresenham(p1, p2, blocked_map):
    (x1,y1)=p1
    (x2,y2)=p2
    tx1=int(x1//TILE_SIZE)
    ty1=int(y1//TILE_SIZE)
    tx2=int(x2//TILE_SIZE)
    ty2=int(y2//TILE_SIZE)
    dx=abs(tx2-tx1)
    sx=1 if tx1<tx2 else -1
    dy=-abs(ty2-ty1)
    sy=1 if ty1<ty2 else -1
    err=dx+dy
    cx,cy=tx1,ty1
    while True:
        if in_bounds(cx,cy):
            if blocked_map[cy][cx]:
                return True
        if (cx,cy)==(tx2,ty2):
            break
        e2=2*err
        if e2>=dy:
            err+=dy
            cx+=sx
        if e2<=dx:
            err+=dx
            cy+=sy
    return False
