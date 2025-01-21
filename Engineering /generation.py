# Engineering/generation.py

import random
from .consts import (
    NX, NY,
    T_DEEP_WATER, T_RIVER, T_PLAIN, T_FOREST,
    T_MOUNTAIN, T_BRIDGE, T_LAKE
)
from .pathfinding import in_bounds

def generate_map(nx, ny):
    grid = [[T_PLAIN for _ in range(nx)] for __ in range(ny)]
    add_mountains_with_20pct_sin(grid, count=4)
    ensure_at_least_one_mountain(grid)  # Ajout : garantit au moins 1 montagne
    add_lakes(grid, count=2)
    nb_riv = random.randint(1,3)
    for _ in range(nb_riv):
        create_river_less_sin(grid)
    add_forests_in_blobs(grid, ratio=0.08)  # Ajout : forêts regroupées
    return grid

def add_mountains_with_20pct_sin(grid, count=4):
    for _ in range(count):
        use_sin = (random.random() < 0.2)
        place_mountain_blob(grid, size=random.randint(8,15), use_sin=use_sin)

def ensure_at_least_one_mountain(grid):
    has_mountain = False
    for row in grid:
        if T_MOUNTAIN in row:
            has_mountain = True
            break
    if not has_mountain:
        # On place un petit blob (8..15)
        place_mountain_blob(grid, size=random.randint(8,15), use_sin=False)

def place_mountain_blob(grid, size=10, use_sin=False):
    nx = len(grid[0])
    ny = len(grid)
    cx = random.randint(5, max(5, nx-5))
    cy = random.randint(5, max(5, ny-5))
    frontier = [(cx, cy)]
    used = set()
    used.add((cx, cy))
    grid[cy][cx] = T_MOUNTAIN

    while frontier and len(used) < size:
        x, y = frontier.pop()
        directions = [(1,0), (0,1), (-1,0), (0,-1)]
        if use_sin:
            random.shuffle(directions)
        for (dx, dy) in directions:
            nx_ = x+dx
            ny_ = y+dy
            if in_bounds(nx_, ny_):
                if (nx_, ny_) not in used:
                    if random.random() < 0.8:
                        used.add((nx_, ny_))
                        frontier.append((nx_, ny_))
                        grid[ny_][nx_] = T_MOUNTAIN

def add_lakes(grid, count=2):
    nx = len(grid[0])
    ny = len(grid)
    for _ in range(count):
        if nx < 20 or ny < 20:
            return
        left = 10
        right = max(10, nx-10)
        top = 10
        bottom = max(10, ny-10)
        cx = random.randint(left, right)
        cy = random.randint(top, bottom)
        rx = random.randint(3,6)
        ry = random.randint(3,6)
        for y in range(ny):
            for x in range(nx):
                dx = x - cx
                dy = y - cy
                if (dx*dx)/(rx*rx) + (dy*dy)/(ry*ry) <= 1.0:
                    grid[y][x] = T_LAKE

def create_river_less_sin(grid):
    nx = len(grid[0])
    ny = len(grid)
    path = []
    start_x = random.randint(0, nx-1)
    x = start_x
    y = 0
    w = random.randint(1,2)
    while y < ny:
        path.append((x,y))
        if random.random() < 0.66:
            y += 1
        else:
            x += random.choice([-1,1])
            x = max(0, min(nx-1, x))
        if len(path) > 120:
            break
    for (rx, ry) in path:
        for dx in range(-w, w+1):
            for dy in range(-w, w+1):
                nx_ = rx+dx
                ny_ = ry+dy
                if in_bounds(nx_, ny_):
                    grid[ny_][nx_] = T_RIVER

    riv = []
    for j in range(ny):
        for i in range(nx):
            if grid[j][i] == T_RIVER:
                riv.append((i,j))
    random.shuffle(riv)
    if riv:
        bx, by = riv.pop()
        grid[by][bx] = T_BRIDGE

#
# Nouvelle logique de forêts : on crée des “blobs” de forêts
# en plus de la précédente. On supprime l'ancienne add_forests
# et on crée add_forests_in_blobs.
#

def add_forests_in_blobs(grid, ratio=0.08):
    # On calcule un “nombre approximatif” de blocs de forêts
    # basé sur ratio et la taille de la map.
    nx = len(grid[0])
    ny = len(grid)
    # par ex. on veut 1 blob de forêt pour ~chaque 3..4% du ratio
    area = nx*ny
    approx_count = int(area * ratio / 50)  # ajuster
    if approx_count < 2:
        approx_count = 2
    if approx_count > 15:
        approx_count = 15

    for _ in range(approx_count):
        place_forest_blob(grid)

def place_forest_blob(grid):
    nx = len(grid[0])
    ny = len(grid)
    # On choisit un point de départ (sur T_PLAIN) => BFS
    # dimension “largeur 2..8, longueur 1..12”
    # On traduit par un BFS de size random(2..96).
    sizeW = random.randint(2,8)
    sizeH = random.randint(1,12)
    size = random.randint(sizeW, sizeW*sizeH)  # ex: BFS size entre [2..(8*12)=96]

    tries=0
    while tries<100:
        tries+=1
        sx = random.randint(0, nx-1)
        sy = random.randint(0, ny-1)
        if grid[sy][sx] == T_PLAIN:
            fill_forest_blob(grid, sx, sy, size)
            break

def fill_forest_blob(grid, sx, sy, max_size):
    from collections import deque
    frontier = deque()
    used = set()
    frontier.append((sx,sy))
    used.add((sx,sy))

    grid[sy][sx] = T_FOREST

    while frontier and len(used)<max_size:
        x,y = frontier.popleft()
        for (dx,dy) in [(1,0),(0,1),(-1,0),(0,-1)]:
            nx_ = x+dx
            ny_ = y+dy
            if in_bounds(nx_, ny_):
                if (nx_,ny_) not in used:
                    if grid[ny_][nx_] == T_PLAIN:
                        used.add((nx_, ny_))
                        grid[ny_][nx_] = T_FOREST
                        frontier.append((nx_, ny_))
