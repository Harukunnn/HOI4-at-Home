# Engineering/generation.py
import random
from .consts import (
    NX, NY,
    T_DEEP_WATER, T_RIVER, T_PLAIN, T_FOREST, T_MOUNTAIN, T_BRIDGE, T_LAKE
)

from .consts import TILE_SIZE  # si besoin
from .consts import COLOR_DEEP_WATER, COLOR_RIVER, COLOR_BRIDGE, COLOR_PLAIN
# etc. - on n'importe que ce qui est utile

from .pathfinding import in_bounds  # si besoin

def generate_map(nx, ny):
    grid = [[T_PLAIN for _ in range(nx)] for __ in range(ny)]
    add_mountains_with_20pct_sin(grid, count=4)
    add_lakes(grid, count=2)
    nb_riv = random.randint(1,3)
    for _ in range(nb_riv):
        create_river_less_sin(grid)
    add_forests(grid, ratio=0.08)
    return grid

def add_mountains_with_20pct_sin(grid, count=4):
    for _ in range(count):
        use_sin = (random.random()<0.2)
        place_mountain_blob(grid, size=random.randint(8,15), use_sin=use_sin)

def place_mountain_blob(grid, size=10, use_sin=False):
    import random
    cx = random.randint(5, len(grid[0]) - 5)
    cy = random.randint(5, len(grid)   - 5)
    frontier = [(cx,cy)]
    used = set()
    used.add((cx,cy))
    grid[cy][cx] = T_MOUNTAIN

    while frontier and len(used)<size:
        x,y = frontier.pop()
        directions = [(1,0),(0,1),(-1,0),(0,-1)]
        if use_sin:
            random.shuffle(directions)
        for (dx,dy) in directions:
            nx_=x+dx
            ny_=y+dy
            if in_bounds(nx_, ny_):
                if (nx_, ny_) not in used:
                    if random.random()<0.8:
                        used.add((nx_, ny_))
                        frontier.append((nx_, ny_))
                        grid[ny_][nx_]=T_MOUNTAIN

def add_lakes(grid, count=2):
    import math
    nx = len(grid[0])
    ny = len(grid)
    for _ in range(count):
        cx = random.randint(10, nx-10)
        cy = random.randint(10, ny-10)
        rx = random.randint(3,6)
        ry = random.randint(3,6)
        for y in range(ny):
            for x in range(nx):
                dx = x-cx
                dy = y-cy
                if (dx*dx)/(rx*rx) + (dy*dy)/(ry*ry) <=1.0:
                    grid[y][x]=T_LAKE

def create_river_less_sin(grid):
    nx = len(grid[0])
    ny = len(grid)
    import math
    path=[]
    start_x = random.randint(0, nx-1)
    x=start_x
    y=0
    w=random.randint(1,2)
    while y<ny:
        path.append((x,y))
        if random.random()<0.66:
            y+=1
        else:
            x+=random.choice([-1,1])
            if x<0: x=0
            if x>=nx: x=nx-1
        if len(path)>120:
            break

    for (rx,ry) in path:
        for dx in range(-w,w+1):
            for dy in range(-w,w+1):
                nx_ = rx+dx
                ny_ = ry+dy
                if in_bounds(nx_, ny_):
                    grid[ny_][nx_] = T_RIVER

    # 1 pont
    riv=[]
    for j in range(ny):
        for i in range(nx):
            if grid[j][i]==T_RIVER:
                riv.append((i,j))
    random.shuffle(riv)
    if riv:
        bx,by=riv.pop()
        grid[by][bx] = T_BRIDGE

def add_forests(grid, ratio=0.08):
    ny=len(grid)
    nx=len(grid[0])
    for y in range(ny):
        for x in range(nx):
            if grid[y][x]==T_PLAIN:
                if random.random()<ratio:
                    grid[y][x]=T_FOREST

#
# Fin generation.py
