# Engineering/units.py

import math
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

        # Aide pour le front (pas besoin d’autre script modifié)
        self.front_side = None

        # HP et dégâts
        self.hp = 100
        self.attack_tick = 0

        # Nouvelles optimisations internes (aucune modif externe requise)
        # Morale : baisse si HP bas
        self.morale = 100.0
        # Vitesse variable selon 'fatigue'
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
         - morale/fatigue internes
        Sans exiger de modif des autres scripts.
        """
        # On gère collisions même si on ne peut pas bouger
        self.resolve_collisions(all_units)

        # On applique les dégâts accumulés
        if self.attack_tick > 0:
            self.hp -= self.attack_tick
            self.attack_tick = 0
            if self.hp <= 0:
                # si HP tombe à 0 => “mort”
                self.encircled_ticks = 999999

        if not movement_allowed:
            # on ne bouge pas => on update morale/fatigue
            self.update_morale_and_fatigue(moving=False)
            return

        # Si on est “bloqué”, on skip le mouvement
        if self.blocked:
            # on reset ?
            self.blocked=False
            self.dest_px=None
            self.dest_py=None
            self.update_morale_and_fatigue(moving=False)
            return

        # IA chase => direct line
        self.ia_chase_logic(all_units)

        # Déplacement direct (joueur ou IA)
        self.move_direct_line(grid)

        # Encerclement
        if game.is_unit_in_enemy_zone(self):
            self.encircled_ticks += 1
        else:
            self.encircled_ticks = 0

        # Capture capital
        game.update_capital_capture(self)

        # Mise à jour morale/fatigue
        self.update_morale_and_fatigue(moving=(self.dest_px is not None))

    def resolve_collisions(self, all_units):
        """
        Évite que 2 unités se superposent.
        On fait un bounding check rapide => distance < 2*UNIT_RADIUS => on corrige.
        """
        # Petit micro-optim: on évite la racine carrée quand c’est possible
        # (pas de modif à l'extérieur)
        r2 = (2*UNIT_RADIUS)*(2*UNIT_RADIUS)
        for u in all_units:
            if u is not self:
                dx = self.x - u.x
                dy = self.y - u.y
                dist2 = dx*dx + dy*dy
                if dist2 < r2 and dist2>1e-9:
                    d=math.sqrt(dist2)
                    overlap=(2*UNIT_RADIUS)-d
                    # On repousse
                    dxn=dx/d
                    dyn=dy/d
                    self.x+=dxn*(overlap/2)
                    self.y+=dyn*(overlap/2)
                    u.x-=dxn*(overlap/2)
                    u.y-=dyn*(overlap/2)

    def ia_chase_logic(self, all_units):
        """
        Gestion IA chase. On vise la position courante de l’ennemi le plus proche
        (stocké dans self.target_enemy).
        """
        if not self.target_enemy:
            return
        if self.target_enemy not in all_units:
            self.target_enemy = None
            self.dest_px = None
            self.dest_py = None
            return
        self.chase_cooldown -= 1
        if self.chase_cooldown <= 0:
            self.chase_cooldown = 15
            # On vise la position courante de l’ennemi
            ex, ey = self.target_enemy.x, self.target_enemy.y
            self.dest_px = ex
            self.dest_py = ey

    def move_direct_line(self, grid):
        """
        Mouvement direct en ligne droite vers (dest_px, dest_py).
        On ralentit sur l’eau, pas de BFS => performance.
        """
        if self.dest_px is None or self.dest_py is None:
            return

        dx = self.dest_px - self.x
        dy = self.dest_py - self.y
        dist_ = math.hypot(dx, dy)
        if dist_ < 1:
            self.x = self.dest_px
            self.y = self.dest_py
            self.dest_px = None
            self.dest_py = None
            return

        tilex = int(self.x // TILE_SIZE)
        tiley = int(self.y // TILE_SIZE)
        # on check terrain
        t = None
        if in_bounds(tilex, tiley):
            t = grid[tiley][tilex]
        # On calcule le pas
        base_speed = MOVE_SPEED
        # On ralentit si la morale est basse
        if self.morale < 40:
            base_speed *= 0.75
        # On ralenti si l’eau
        if t in (T_DEEP_WATER, T_LAKE, T_RIVER):
            base_speed *= WATER_SLOW_FACTOR

        # On réduit encore si fatigue>50?
        if self.fatigue > 50:
            base_speed *= 0.8

        step = base_speed * TILE_SIZE
        if dist_ > step:
            self.x += (dx/dist_) * step
            self.y += (dy/dist_) * step
        else:
            self.x = self.dest_px
            self.y = self.dest_py
            self.dest_px = None
            self.dest_py = None

    def update_morale_and_fatigue(self, moving=False):
        """
        Ajuste la morale et la fatigue :
          - La morale baisse si HP est faible
          - La fatigue monte quand on bouge
          - La fatigue descend lentement quand on ne bouge pas
        Sans exiger de modif dans d'autres scripts.
        """
        # Morale: on la maintient ~100 si HP=100
        # si HP<30 => morale baisse
        if self.hp < 30:
            # Baisse plus si encercled
            drop = 0.2 if self.encircled_ticks>0 else 0.1
            self.morale -= drop
        else:
            # on remonte
            self.morale += 0.05
        self.morale = max(0, min(100, self.morale))

        if moving:
            # on augmente la fatigue
            self.fatigue += 0.5
        else:
            # on récupère un peu
            self.fatigue -= 0.3
        self.fatigue = max(0, min(100, self.fatigue))

def distance(x1,y1,x2,y2):
    """Distance euclidienne simple."""
    return math.hypot(x2 - x1, y2 - y1)

class AI:
    def __init__(self, team):
        self.team = team

    def update(self, game, movement_allowed):
        """
        Met à jour l’IA (rouge ou bleu), identique à avant
        mais plus optimisé (recherche ennemi plus proche).
        Aucune modif dans d’autres scripts.
        """
        if not movement_allowed:
            return

        if self.team == "red":
            myunits = game.red_units
            foes = game.blue_units
        else:
            myunits = game.blue_units
            foes = game.red_units

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
            # On parcourt foes => plus proche
            for f in foes:
                dx = (u.x - f.x)
                dy = (u.y - f.y)
                dist2 = dx*dx + dy*dy
                if dist2<bestd:
                    bestd=dist2
                    bestf=f
            u.target_enemy = bestf
