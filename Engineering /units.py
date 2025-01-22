# Engineering/units.py

import math
from .pathfinding import distance, in_bounds
from .consts import (
    MOVE_SPEED, WATER_SLOW_FACTOR, ENCIRCLED_TICK_LIMIT,
    T_DEEP_WATER, T_LAKE, T_RIVER, T_MOUNTAIN,
    TILE_SIZE, UNIT_RADIUS, FPS
)

class Unit:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.is_selected = False

        # Déplacement direct en pixels (pour IA et joueur)
        self.dest_px = None
        self.dest_py = None

        # Gestion de collisions et d'encerclement
        self.blocked = False
        self.encircled_ticks = 0

        # Cible IA directe
        self.target_enemy = None
        self.chase_cooldown = 0

        # Capture capital
        self.cap_capture_time = 0.0

        # Aide pour le front
        self.front_side = None

        # HP et dégâts
        self.hp = 100
        self.attack_tick = 0

        # Morale / Fatigue (optimisations internes)
        self.morale = 100.0
        self.fatigue = 0.0

    def get_tile_pos(self):
        """Retourne la tuile (tx, ty) courante."""
        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        return (tx, ty)

    def update(self, game, all_units, grid, movement_allowed):
        """
        Met à jour l’unité chaque frame:
         - collisions
         - dégâts
         - IA chase => direct line
         - mouvement direct line
         - encerclement
         - capture capital
         - morale/fatigue
        Sans rien changer dans les autres scripts.
        """
        self.resolve_collisions(all_units)

        # Applique dégâts en attente
        if self.attack_tick > 0:
            self.hp -= self.attack_tick
            self.attack_tick = 0
            if self.hp <= 0:
                # “mort”
                self.encircled_ticks = 999999

        # Phase de placement => pas de mouvement
        if not movement_allowed:
            self.update_morale_and_fatigue(moving=False)
            return

        # Si bloqué, on annule l'action de ce tour
        if self.blocked:
            self.blocked = False
            self.dest_px = None
            self.dest_py = None
            self.update_morale_and_fatigue(moving=False)
            return

        # IA => direct line
        self.ia_chase_logic(all_units)

        # Déplacement direct en ligne droite (joueur ou IA)
        self.move_direct_line(grid)

        # Encerclement
        if game.is_unit_in_enemy_zone(self):
            self.encircled_ticks += 1
        else:
            self.encircled_ticks = 0

        # Capture capital
        game.update_capital_capture(self)

        # Maj morale/fatigue
        self.update_morale_and_fatigue(moving=(self.dest_px is not None))

    def resolve_collisions(self, all_units):
        """
        Évite que 2 unités se superposent (distance < 2*UNIT_RADIUS).
        """
        r2 = (2*UNIT_RADIUS)*(2*UNIT_RADIUS)
        for u in all_units:
            if u is not self:
                dx = self.x - u.x
                dy = self.y - u.y
                dist2 = dx*dx + dy*dy
                if dist2 < r2 and dist2 > 1e-9:
                    d = math.sqrt(dist2)
                    overlap = (2*UNIT_RADIUS) - d
                    dxn = dx/d
                    dyn = dy/d
                    self.x += dxn*(overlap/2)
                    self.y += dyn*(overlap/2)
                    u.x -= dxn*(overlap/2)
                    u.y -= dyn*(overlap/2)

    def ia_chase_logic(self, all_units):
        """
        L’IA vise la position courante de l’ennemi (self.target_enemy).
        """
        if not self.target_enemy:
            return
        if self.target_enemy not in all_units:
            # Ennemi disparu
            self.target_enemy = None
            self.dest_px = None
            self.dest_py = None
            return
        self.chase_cooldown -= 1
        if self.chase_cooldown <= 0:
            self.chase_cooldown = 15
            ex, ey = self.target_enemy.x, self.target_enemy.y
            self.dest_px = ex
            self.dest_py = ey

    def move_direct_line(self, grid):
        """
        Mouvement direct vers (dest_px, dest_py).
        Ne traverse pas T_LAKE ou T_MOUNTAIN: si la future position
        aboutit sur un lac ou montagne, on annule le déplacement.
        """
        if self.dest_px is None or self.dest_py is None:
            return

        dx = self.dest_px - self.x
        dy = self.dest_py - self.y
        dist_ = math.hypot(dx, dy)
        if dist_ < 1:
            # Arrivé
            self.x = self.dest_px
            self.y = self.dest_py
            self.dest_px = None
            self.dest_py = None
            return

        # Tuile courante
        tilex = int(self.x // TILE_SIZE)
        tiley = int(self.y // TILE_SIZE)
        tile_terrain = None
        if in_bounds(tilex, tiley):
            tile_terrain = grid[tiley][tilex]

        # Calcule la vitesse de base
        base_speed = MOVE_SPEED
        if self.morale < 40:
            base_speed *= 0.75
        # On ralentit sur l’eau
        if tile_terrain in (T_DEEP_WATER, T_RIVER):
            base_speed *= WATER_SLOW_FACTOR
        # Fatigue
        if self.fatigue > 50:
            base_speed *= 0.8

        step = base_speed * TILE_SIZE
        if dist_ > step:
            # Prochaine position
            newx = self.x + (dx/dist_) * step
            newy = self.y + (dy/dist_) * step
        else:
            # On atteint la cible
            newx = self.dest_px
            newy = self.dest_py

        # Vérif: la tuile où on veut aller est-elle T_LAKE ou T_MOUNTAIN?
        nxt_tx = int(newx // TILE_SIZE)
        nxt_ty = int(newy // TILE_SIZE)

        if in_bounds(nxt_tx, nxt_ty):
            future_terrain = grid[nxt_ty][nxt_tx]
            # Interdit de traverser lac/montagne
            if future_terrain in (T_LAKE, T_MOUNTAIN):
                # On annule ce tour: ne bouge pas
                self.dest_px = None
                self.dest_py = None
                return
        else:
            # Hors map => on annule également
            self.dest_px = None
            self.dest_py = None
            return

        # Sinon on fait le déplacement
        self.x = newx
        self.y = newy

        # Si on a atteint la cible
        if dist_ <= step:
            self.dest_px = None
            self.dest_py = None

    def update_morale_and_fatigue(self, moving=False):
        """
        Ajuste la morale et la fatigue.
        Si HP<30 => morale baisse (un peu + si encercled).
        Si on bouge => fatigue += 0.5, sinon on récupère.
        """
        if self.hp < 30:
            drop = 0.2 if self.encircled_ticks>0 else 0.1
            self.morale -= drop
        else:
            self.morale += 0.05
        self.morale = max(0, min(100, self.morale))

        if moving:
            self.fatigue += 0.5
        else:
            self.fatigue -= 0.3
        self.fatigue = max(0, min(100, self.fatigue))

def distance(x1,y1,x2,y2):
    """Distance euclidienne simple."""
    return math.hypot(x2 - x1, y2 - y1)

class AI:
    def __init__(self, team):
        self.team = team

    def update(self, game, movement_allowed):
        if not movement_allowed:
            return

        if self.team == "red":
            myunits = game.red_units
            foes     = game.blue_units
        else:
            myunits = game.blue_units
            foes     = game.red_units

        if not foes:
            return

        for u in myunits:
            if u.blocked:
                u.dest_px = None
                u.dest_py = None
                u.target_enemy = None
                u.blocked = False
                continue
            bestd = float('inf')
            bestf = None
            for f in foes:
                dx = (u.x - f.x)
                dy = (u.y - f.y)
                dist2 = dx*dx + dy*dy
                if dist2 < bestd:
                    bestd  = dist2
                    bestf  = f
            u.target_enemy = bestf
