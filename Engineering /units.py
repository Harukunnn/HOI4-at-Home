# Engineering/units.py

import math
from .pathfinding import find_path_bfs, distance, in_bounds
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
        self.path = []
        self.dest_tile = None
        self.blocked = False
        self.encircled_ticks = 0
        self.target_enemy = None
        self.chase_cooldown = 0
        self.cap_capture_time = 0.0
        self.front_side = None

        # Nouveau : gestion des points de vie et dégâts
        self.hp = 100
        self.attack_tick = 0  # dégâts subis ce frame

    def get_tile_pos(self):
        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        return (tx, ty)

    def update(self, game, all_units, grid, movement_allowed):
        # Si freeze/placement => pas de mouvement normal
        if not movement_allowed:
            # On remet à zéro l'attaque_tick
            if self.attack_tick > 0:
                # subit les dégâts
                self.hp -= self.attack_tick
                self.attack_tick = 0
                if self.hp <= 0:
                    self.encircled_ticks = 999999  # force destruction dans main
            return

        # Collisions
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

        # On applique éventuellement les dégâts en fin de frame
        if self.attack_tick > 0:
            self.hp -= self.attack_tick
            self.attack_tick = 0
            if self.hp <= 0:
                self.encircled_ticks = 999999

        if self.blocked:
            return

        # Poursuite d'un ennemi
        if self.target_enemy:
            if self.target_enemy not in all_units:
                self.target_enemy = None
                self.path = []
                self.dest_tile = None
            else:
                self.chase_cooldown -= 1
                if self.chase_cooldown <= 0:
                    self.chase_cooldown = 10
                    ex, ey = self.target_enemy.get_tile_pos()
                    sx, sy = self.get_tile_pos()
                    newp = find_path_bfs(grid, (sx,sy), (ex,ey))
                    self.path = newp
                    self.dest_tile = (ex,ey)

        # Déplacement
        if self.path:
            (tx,ty) = self.path[0]
            px = tx*TILE_SIZE + TILE_SIZE/2
            py = ty*TILE_SIZE + TILE_SIZE/2
            dx = px - self.x
            dy = py - self.y
            dist_ = math.hypot(dx, dy)

            # Sur l'eau => plus lent
            t = grid[ty][tx]
            if t in (T_DEEP_WATER, T_LAKE, T_RIVER):
                step = MOVE_SPEED * WATER_SLOW_FACTOR * TILE_SIZE
            else:
                step = MOVE_SPEED * TILE_SIZE

            if dist_ > step:
                self.x += (dx/dist_)*step
                self.y += (dy/dist_)*step
            else:
                self.x = px
                self.y = py
                self.path.pop(0)
                if not self.path:
                    self.dest_tile=None

        # Encerclement => on incrémente
        if game.is_unit_in_enemy_zone(self):
            self.encircled_ticks += 1
        else:
            self.encircled_ticks = 0

        # Capture capital => main le gère via update_capital_capture

class AI:
    def __init__(self, team):
        self.team = team

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

        # On cherche la plus proche unité ennemie pour chaque
        for u in myunits:
            if u.blocked:
                u.path=[]
                u.dest_tile=None
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
