# Engineering/pathfinding.py
from .consts import (
    T_MOUNTAIN, # on bloque que les montagnes
)

def in_bounds(tx, ty):
    from .consts import NX, NY
    return (0<=tx<NX and 0<=ty<NY)

def find_path_bfs(grid, start_tile, goal_tile):
    from collections import deque
    (sx,sy) = start_tile
    (gx,gy) = goal_tile
    if not in_bounds(sx,sy) or not in_bounds(gx,gy):
        return []
    if (sx,sy)==(gx,gy):
        return []
    visited=set()
    visited.add((sx,sy))
    parent={}
    parent[(sx,sy)]=None
    queue=deque()
    queue.append((sx,sy))

    while queue:
        cx,cy = queue.popleft()
        if (cx,cy)==(gx,gy):
            break
        for (dx,dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx_=cx+dx
            ny_=cy+dy
            if in_bounds(nx_,ny_):
                if (nx_,ny_) not in visited:
                    # On ne bloque QUE MOUNTAIN
                    if grid[ny_][nx_]!=T_MOUNTAIN:
                        visited.add((nx_,ny_))
                        parent[(nx_,ny_)] = (cx,cy)
                        queue.append((nx_,ny_))

    if (gx,gy) not in parent:
        return []
    path=[]
    cur=(gx,gy)
    while cur is not None:
        path.append(cur)
        cur=parent[cur]
    path.reverse()
    return path[1:]


