# Engineering/units.py

import math
# N.B. On conserve 'distance' et 'in_bounds' si besoin
# On n'utilise plus BFS pour l'IA, donc on n'importe plus find_path_bfs ici.
from .pathfinding import distance, in_bounds
from .consts import (
    MOVE_SPEED, WATER_SLOW_FACTOR, ENCIRCLED_TICK_LIMIT,
    T_DEEP_WATER, T_LAKE, T_RIVER,
    TILE_SIZE, UNIT_RADIUS, FPS
)

class Unit:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.is_selected = False

        # On n’utilise plus BFS pour l’IA
        self.dest_px = None
        self.dest_py = None

        self.blocked = False
        self.encircled_ticks = 0
        self.target_enemy = None
        self.chase_cooldown = 0
        self.cap_capture_time = 0.0
        self.front_side = None
        self.hp = 100
        self.attack_tick = 0

    def get_tile_pos(self):
        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        return (tx, ty)

    def update(self, game, all_units, grid, movement_allowed):
        if not movement_allowed:
            self.resolve_collisions(all_units)
            if self.attack_tick>0:
                self.hp -= self.attack_tick
                self.attack_tick=0
                if self.hp<=0:
                    self.encircled_ticks=999999
            return

        self.resolve_collisions(all_units)
        if self.attack_tick>0:
            self.hp -= self.attack_tick
            self.attack_tick=0
            if self.hp<=0:
                self.encircled_ticks=999999

        if self.blocked:
            return

        # IA chase => direct line
        if self.target_enemy:
            if self.target_enemy not in all_units:
                self.target_enemy=None
                self.dest_px=None
                self.dest_py=None
            else:
                self.chase_cooldown-=1
                if self.chase_cooldown<=0:
                    self.chase_cooldown=15
                    # On vise la position courante de l’ennemi
                    ex,ey=self.target_enemy.x, self.target_enemy.y
                    self.dest_px=ex
                    self.dest_py=ey

        # Déplacement direct en ligne (joueur ou IA)
        if self.dest_px is not None and self.dest_py is not None:
            self.move_direct_line(grid)

        if game.is_unit_in_enemy_zone(self):
            self.encircled_ticks+=1
        else:
            self.encircled_ticks=0

        game.update_capital_capture(self)

    def resolve_collisions(self, all_units):
        for u in all_units:
            if u is not self:
                d = distance(self.x, self.y, u.x, u.y)
                if d < 2*UNIT_RADIUS:
                    overlap = 2*UNIT_RADIUS - d
                    if d>0:
                        dx = (self.x-u.x)/d
                        dy = (self.y-u.y)/d
                        self.x += dx*(overlap/2)
                        self.y += dy*(overlap/2)
                        u.x -= dx*(overlap/2)
                        u.y -= dy*(overlap/2)

    def move_direct_line(self, grid):
        dx=self.dest_px - self.x
        dy=self.dest_py - self.y
        dist_=math.hypot(dx, dy)
        if dist_<1:
            self.x=self.dest_px
            self.y=self.dest_py
            self.dest_px=None
            self.dest_py=None
            return
        tilex=int(self.x//TILE_SIZE)
        tiley=int(self.y//TILE_SIZE)
        t=None
        if in_bounds(tilex,tiley):
            t=grid[tiley][tilex]
        if t in (T_DEEP_WATER, T_LAKE, T_RIVER):
            step=(MOVE_SPEED*WATER_SLOW_FACTOR)*TILE_SIZE
        else:
            step=MOVE_SPEED*TILE_SIZE
        if dist_>step:
            self.x+=(dx/dist_)*step
            self.y+=(dy/dist_)*step
        else:
            self.x=self.dest_px
            self.y=self.dest_py
            self.dest_px=None
            self.dest_py=None

def distance(x1,y1,x2,y2):
    return math.hypot(x2 - x1, y2 - y1)

class AI:
    def __init__(self, team):
        self.team=team

    def update(self, game, movement_allowed):
        if not movement_allowed:
            return
        if self.team=="red":
            myunits=game.red_units
            foes=game.blue_units
        else:
            myunits=game.blue_units
            foes=game.red_units

        if not foes:
            return

        for u in myunits:
            if u.blocked:
                u.dest_px=None
                u.dest_py=None
                u.target_enemy=None
                u.blocked=False
                continue
            bestd=999999
            bestf=None
            for f in foes:
                d=distance(u.x,u.y,f.x,f.y)
                if d<bestd:
                    bestd=d
                    bestf=f
            u.target_enemy=bestf
