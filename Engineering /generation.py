# Engineering/generation.py

import random
# Au lieu d'un import relatif avec ".", on importe depuis "Engineering.consts"
# (Assurez-vous d'avoir un __init__.py dans le dossier Engineering et de lancer Python
#  en considérant "Engineering" comme un package.)
from Engineering.consts import (
    NX, NY,
    T_DEEP_WATER, T_RIVER, T_PLAIN, T_FOREST,
    T_MOUNTAIN, T_BRIDGE, T_LAKE
)
from Engineering.pathfinding import in_bounds

def generate_map(nx, ny):
    grid = [[T_PLAIN for _ in range(nx)] for __ in range(ny)]
    add_mountains_with_20pct_sin(grid, count=5)
    ensure_at_least_one_mountain(grid)
    ensure_scenic_mountain_border(grid)
    add_lakes(grid, count=3)
    ensure_at_least_one_large_lake(grid)
    add_rivers_forked(grid, min_count=1, max_count=2)
    add_forests_in_blobs(grid, ratio=0.20)
    ensure_minimum_forest(grid, min_blobs=2)
    return grid

def add_mountains_with_20pct_sin(grid, count=5):
    for _ in range(count):
        use_sin = (random.random() < 0.2)
        place_mountain_blob(grid, size=random.randint(15,30), use_sin=use_sin)

def ensure_at_least_one_mountain(grid):
    has_mountain = False
    for row in grid:
        if T_MOUNTAIN in row:
            has_mountain = True
            break
    if not has_mountain:
        place_mountain_blob(grid, size=random.randint(15,30), use_sin=False)

def ensure_scenic_mountain_border(grid):
    nx = len(grid[0])
    ny = len(grid)
    if random.random() < 0.5:
        for x in range(nx):
            if random.random() < 0.1:
                place_mountain_blob(grid, size=random.randint(8,15), use_sin=True)
    else:
        for y in range(ny):
            if random.random() < 0.1:
                place_mountain_blob(grid, size=random.randint(8,15), use_sin=True)

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
        directions = [(1,0),(0,1),(-1,0),(0,-1)]
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

def add_lakes(grid, count=3):
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
        rx = random.randint(3,8)
        ry = random.randint(3,8)
        for y in range(ny):
            for x in range(nx):
                dx = x - cx
                dy = y - cy
                if (dx*dx)/(rx*rx) + (dy*dy)/(ry*ry) <= 1.0:
                    grid[y][x] = T_LAKE

def ensure_at_least_one_large_lake(grid):
    nx = len(grid[0])
    ny = len(grid)
    has_big = False
    for y in range(ny):
        for x in range(nx):
            if grid[y][x] == T_LAKE:
                cnt = 0
                frontier = [(x,y)]
                used = {(x,y)}
                while frontier:
                    cx,cy = frontier.pop()
                    cnt += 1
                    for (dx,dy) in [(1,0),(0,1),(-1,0),(0,-1)]:
                        nx_ = cx+dx
                        ny_ = cy+dy
                        if in_bounds(nx_, ny_):
                            if (nx_,ny_) not in used:
                                if grid[ny_][nx_] == T_LAKE:
                                    used.add((nx_, ny_))
                                    frontier.append((nx_, ny_))
                if cnt > 25:
                    has_big = True
                    break
        if has_big:
            break
    if not has_big:
        place_lake_blob(grid, size=40)

def place_lake_blob(grid, size=40):
    nx = len(grid[0])
    ny = len(grid)
    cx = random.randint(10, max(10,nx-10))
    cy = random.randint(10, max(10,ny-10))
    frontier = [(cx,cy)]
    used = {(cx,cy)}
    grid[cy][cx] = T_LAKE

    while frontier and len(used) < size:
        x,y = frontier.pop()
        directions = [(1,0),(-1,0),(0,1),(0,-1)]
        random.shuffle(directions)
        for dx,dy in directions:
            nx_ = x+dx
            ny_ = y+dy
            if in_bounds(nx_, ny_):
                if (nx_,ny_) not in used:
                    if grid[ny_][nx_]==T_PLAIN:
                        used.add((nx_,ny_))
                        frontier.append((nx_,ny_))
                        grid[ny_][nx_] = T_LAKE

def add_rivers_forked(grid, min_count=1, max_count=2):
    nb = random.randint(min_count,max_count)
    for _ in range(nb):
        create_river_fork(grid)

def create_river_fork(grid):
    nx = len(grid[0])
    ny = len(grid)
    path = []
    start_x = random.randint(0, nx-1)
    x = start_x
    y = 0
    w = 1
    while y < ny:
        path.append((x,y))
        if random.random()<0.7:
            y += 1
        else:
            x += random.choice([-1,1])
            x = max(0, min(nx-1,x))
        if len(path)>100:
            break
    for (rx,ry) in path:
        for dx in range(-w, w+1):
            for dy in range(-w, w+1):
                nx_ = rx+dx
                ny_ = ry+dy
                if in_bounds(nx_, ny_):
                    grid[ny_][nx_] = T_RIVER
    fork_points = []
    step = len(path)//3 + 1
    for i in range(len(path)//3, len(path), step):
        if i < len(path):
            fork_points.append(path[i])
    for fpt in fork_points:
        if random.random()<0.5:
            fx,fy = fpt
            create_small_river_branch(grid, fx, fy)

    riv=[]
    for j in range(ny):
        for i in range(nx):
            if grid[j][i]==T_RIVER:
                riv.append((i,j))
    random.shuffle(riv)
    if riv:
        bx,by=riv.pop()
        grid[by][bx] = T_BRIDGE

def create_small_river_branch(grid, sx, sy):
    nx = len(grid[0])
    ny = len(grid)
    x = sx
    y = sy
    for _ in range(random.randint(5,30)):
        grid[y][x] = T_RIVER
        dirs = [(1,0),(0,1),(-1,0),(0,-1)]
        d = random.choice(dirs)
        x += d[0]
        y += d[1]
        x = max(0, min(nx-1,x))
        y = max(0, min(ny-1,y))

def add_forests_in_blobs(grid, ratio=0.20):
    nx = len(grid[0])
    ny = len(grid)
    area = nx*ny
    approx_count = int(area*ratio/50)
    if approx_count < 2:
        approx_count=2
    if approx_count>25:
        approx_count=25
    for _ in range(approx_count):
        place_forest_blob(grid)

def place_forest_blob(grid):
    nx = len(grid[0])
    ny = len(grid)
    sizeW = random.randint(3,10)
    sizeH = random.randint(5,15)
    size = random.randint(sizeW, sizeW*sizeH)
    tries=0
    while tries<100:
        tries+=1
        sx = random.randint(0, nx-1)
        sy = random.randint(0, ny-1)
        if grid[sy][sx]==T_PLAIN:
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
        for (dx,dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx_ = x+dx
            ny_ = y+dy
            if in_bounds(nx_, ny_):
                if (nx_,ny_) not in used:
                    if grid[ny_][nx_]==T_PLAIN:
                        used.add((nx_, ny_))
                        grid[ny_][nx_] = T_FOREST
                        frontier.append((nx_, ny_))

def ensure_minimum_forest(grid, min_blobs=2):
    nx=len(grid[0])
    ny=len(grid)
    count_forest = 0
    visited=set()
    for y in range(ny):
        for x in range(nx):
            if grid[y][x]==T_FOREST and (x,y) not in visited:
                count_forest+=1
                stack=[(x,y)]
                visited.add((x,y))
                while stack:
                    cx,cy=stack.pop()
                    for (dx,dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
                        nx_=cx+dx
                        ny_=cy+dy
                        if in_bounds(nx_, ny_):
                            if (nx_,ny_) not in visited:
                                if grid[ny_][nx_]==T_FOREST:
                                    visited.add((nx_,ny_))
                                    stack.append((nx_,ny_))
    if count_forest<min_blobs:
        for _ in range(min_blobs-count_forest):
            place_forest_blob(grid)
