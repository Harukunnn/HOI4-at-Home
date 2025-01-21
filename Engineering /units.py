# Engineering/units.py
import math
from .pathfinding import find_path_bfs, distance, in_bounds
from .consts import (
    MOVE_SPEED, WATER_SLOW_FACTOR, ENCIRCLED_TICK_LIMIT,
    T_DEEP_WATER, T_LAKE, T_RIVER,
    TILE_SIZE, UNIT_RADIUS
)
from .consts import FPS

class Unit:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.is_selected = False
        self.path = []
        self.dest_tile = None
        self.blocked = False
        self.encircled_ticks = 0
        self.target_enemy = None
        self.chase_cooldown = 0
        self.cap_capture_time = 0.0
        self.front_side = None

    def get_tile_pos(self):
        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        return (tx, ty)

    def update(self, game, all_units, grid, movement_allowed):
        if not movement_allowed:
            return

        # collisions
        for u in all_units:
            if u is not self:
                d = distance(self.x, self.y, u.x, u.y)
                if d < 2*UNIT_RADIUS:
                    overlap = 2*UNIT_RADIUS - d
                    if d > 0:
                        dx = (self.x-u.x)/d
                        dy = (self.y-u.y)/d
                        self.x += dx*(overlap/2)
                        self.y += dy*(overlap/2)
                        u.x -= dx*(overlap/2)
                        u.y -= dy*(overlap/2)

        if self.blocked:
            return

        # IA chase
        if self.target_enemy:
            if self.target_enemy not in all_units:
                self.target_enemy = None
                self.path = []
                self.dest_tile = None
            else:
                self.chase_cooldown -= 1
                if self.chase_cooldown<=0:
                    self.chase_cooldown=10
                    ex,ey = self.target_enemy.get_tile_pos()
                    sx,sy = self.get_tile_pos()
                    newp = find_path_bfs(grid,(sx,sy),(ex,ey))
                    self.path = newp
                    self.dest_tile=(ex,ey)

        # move with water slow
        if self.path:
            (tx,ty) = self.path[0]
            from .consts import TILE_SIZE
            from .consts import MOVE_SPEED
            from .consts import T_DEEP_WATER, T_LAKE, T_RIVER

            (px,py) = (tx*TILE_SIZE + TILE_SIZE/2, ty*TILE_SIZE + TILE_SIZE/2)
            dx = px - self.x
            dy = py - self.y
            dist_ = math.hypot(dx, dy)

            # Check terrain => water => slow
            t = grid[ty][tx]
            if t in (T_DEEP_WATER, T_LAKE, T_RIVER):
                step = (MOVE_SPEED*WATER_SLOW_FACTOR)*TILE_SIZE
            else:
                step = (MOVE_SPEED)*TILE_SIZE

            if dist_>step:
                self.x += (dx/dist_)*step
                self.y += (dy/dist_)*step
            else:
                self.x=px
                self.y=py
                self.path.pop(0)
                if not self.path:
                    self.dest_tile=None

        # encirclement
        if game.is_unit_in_enemy_zone(self):
            self.encircled_ticks += 1
        else:
            self.encircled_ticks = 0

        # capture capital
        game.update_capital_capture(self)

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
                u.path=[]
                u.dest_tile=None
                u.target_enemy=None
                u.blocked=False
                continue
            # plus proche
            bestd=999999
            bestf=None
            for f in foes:
                d = distance(u.x,u.y,f.x,f.y)
                if d<bestd:
                    bestd=d
                    bestf=f
            u.target_enemy=bestf

#
# Fin units.py

