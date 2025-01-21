import tkinter as tk
import math
import random
import collections
import time

#####################################
# Paramètres globaux
#####################################

WIDTH, HEIGHT = 800, 600
TILE_SIZE = 10
NX = WIDTH  // TILE_SIZE
NY = HEIGHT // TILE_SIZE

FPS = 30
UNIT_RADIUS = 4
MOVE_SPEED = 0.1  # Vitesse réduite
ENCIRCLED_TICK_LIMIT = 300
STAR_SIZE = 6

# Temps de "phase d'analyse" en secondes
INITIAL_DELAY = 15.0

# Types de terrain
T_DEEP_WATER = 0
T_RIVER      = 1
T_PLAIN      = 2
T_FOREST     = 3
T_MOUNTAIN   = 4
T_BRIDGE     = 5

# Couleurs terrain
COLOR_DEEP_WATER = "#3B6FD2"
COLOR_RIVER      = "#0096FF"
COLOR_BRIDGE     = "#987B5B"
COLOR_PLAIN      = "#85C57A"
COLOR_FOREST     = "#3D8B37"
COLOR_MOUNTAIN   = "#AAAAAA"

# Couleurs équipes
COLOR_RED        = "#DC1414"
COLOR_BLUE       = "#1414DC"
COLOR_HIGHLIGHT  = "yellow"

MIN_TROOPS_PER_TEAM = 10


#####################################
# Fonctions utilitaires
#####################################

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def in_bounds(tx, ty):
    return 0 <= tx < NX and 0 <= ty < NY

def tile_center_px(tx, ty):
    return (tx*TILE_SIZE + TILE_SIZE/2, ty*TILE_SIZE + TILE_SIZE/2)


#####################################
# Génération du terrain
#####################################

def generate_terrain(nx, ny):
    """
    Crée un “continent” central entouré d’eau,
    puis ajoute forêts, montagnes, rivières et ponts.
    """
    hm = generate_continent_heightmap(nx, ny)

    grid = []
    for y in range(ny):
        row = []
        for x in range(nx):
            h = hm[y][x]
            if h < 0.1:
                row.append(T_DEEP_WATER)
            elif h < 0.4:
                row.append(T_PLAIN)
            elif h < 0.6:
                row.append(T_FOREST)
            else:
                row.append(T_MOUNTAIN)
        grid.append(row)

    # Rivières
    nb_rivieres = 2
    for _ in range(nb_rivieres):
        create_river(grid, hm)

    # Ponts
    place_bridges(grid, nb_bridges=12)
    return grid

def generate_continent_heightmap(nx, ny):
    cx, cy = nx/2, ny/2
    radius = min(nx, ny)*0.45
    raw = [[random.random() for _ in range(nx)] for __ in range(ny)]

    for y in range(ny):
        for x in range(nx):
            dist_c = math.hypot(x - cx, y - cy)
            factor = max(0, 1.0 - dist_c / radius)
            raw[y][x] *= factor

    for _ in range(2):
        raw = smooth_heightmap(raw)
    return raw

def smooth_heightmap(hm):
    ny = len(hm)
    nx = len(hm[0])
    new_hm = [[0]*nx for _ in range(ny)]
    for y in range(ny):
        for x in range(nx):
            val_sum = 0
            count = 0
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    nx_ = x + dx
                    ny_ = y + dy
                    if 0 <= nx_ < nx and 0 <= ny_ < ny:
                        val_sum += hm[ny_][nx_]
                        count += 1
            new_hm[y][x] = val_sum / count
    return new_hm

def create_river(grid, hm):
    """
    Creuse une rivière depuis le haut (y=0) où h>0.5,
    en suivant la pente.
    """
    top_candidates = []
    for x in range(NX):
        if hm[0][x] > 0.5:
            top_candidates.append(x)
    if not top_candidates:
        return

    start_x = random.choice(top_candidates)
    start_y = 0

    path = []
    cx, cy = start_x, start_y
    for _ in range(NY*2):
        path.append((cx, cy))
        if cy >= NY-1:
            break
        candidates = []
        for (dx, dy) in [(0,1),(1,0),(-1,0),(1,1),(-1,1)]:
            nx_ = cx+dx
            ny_ = cy+dy
            if in_bounds(nx_, ny_):
                candidates.append((nx_, ny_))
        if not candidates:
            break
        candidates.sort(key=lambda pos: hm[pos[1]][pos[0]])
        best = candidates[0]
        if hm[best[1]][best[0]] >= hm[cy][cx]:
            break
        cx, cy = best

    for (rx, ry) in path:
        if grid[ry][rx] != T_DEEP_WATER:
            grid[ry][rx] = T_RIVER

def place_bridges(grid, nb_bridges=10):
    river_positions = []
    for y in range(NY):
        for x in range(NX):
            if grid[y][x] == T_RIVER:
                river_positions.append((x, y))
    random.shuffle(river_positions)
    for _ in range(nb_bridges):
        if not river_positions:
            break
        x, y = river_positions.pop()
        grid[y][x] = T_BRIDGE

def is_blocked(t):
    return (t == T_DEEP_WATER or t == T_RIVER or t == T_MOUNTAIN)

def is_walkable(t):
    return (t == T_PLAIN or t == T_FOREST or t == T_BRIDGE)


#####################################
# Pathfinding & Contrôle de territoire
#####################################

def find_path(grid, start_tile, goal_tile, avoid_encirclement_test=None):
    (sx, sy) = start_tile
    (gx, gy) = goal_tile
    if not in_bounds(sx, sy) or not in_bounds(gx, gy):
        return []
    if (sx, sy) == (gx, gy):
        return []

    blocked_types = {T_DEEP_WATER, T_RIVER, T_MOUNTAIN}
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
                    t = grid[ny_][nx_]
                    if t not in blocked_types:
                        if avoid_encirclement_test and avoid_encirclement_test(nx_, ny_):
                            continue
                        visited.add((nx_, ny_))
                        parent[(nx_, ny_)] = (cx, cy)
                        queue.append((nx_, ny_))

    if (gx, gy) not in parent:
        return []
    path = []
    cur = (gx, gy)
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path[1:]

def compute_territory_control(grid, red_cap_tile, blue_cap_tile):
    dist_red = [[999999]*NX for _ in range(NY)]
    rx, ry = red_cap_tile
    if in_bounds(rx, ry) and not is_blocked(grid[ry][rx]):
        dist_red[ry][rx] = 0
        q = collections.deque()
        q.append((rx, ry))
        while q:
            cx, cy = q.popleft()
            for (dx, dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx_ = cx+dx
                ny_ = cy+dy
                if in_bounds(nx_, ny_):
                    if dist_red[ny_][nx_] > 999998:
                        if not is_blocked(grid[ny_][nx_]):
                            dist_red[ny_][nx_] = dist_red[cy][cx] + 1
                            q.append((nx_, ny_))

    dist_blue = [[999999]*NX for _ in range(NY)]
    bx, by = blue_cap_tile
    if in_bounds(bx, by) and not is_blocked(grid[by][bx]):
        dist_blue[by][bx] = 0
        q = collections.deque()
        q.append((bx, by))
        while q:
            cx, cy = q.popleft()
            for (dx, dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx_ = cx+dx
                ny_ = cy+dy
                if in_bounds(nx_, ny_):
                    if dist_blue[ny_][nx_] > 999998:
                        if not is_blocked(grid[ny_][nx_]):
                            dist_blue[ny_][nx_] = dist_blue[cy][cx] + 1
                            q.append((nx_, ny_))

    control_map = [["neutral"]*NX for _ in range(NY)]
    for j in range(NY):
        for i in range(NX):
            dr = dist_red[j][i]
            db = dist_blue[j][i]
            if dr < 999999 or db < 999999:
                if dr < db:
                    control_map[j][i] = "red"
                elif db < dr:
                    control_map[j][i] = "blue"
                else:
                    control_map[j][i] = "neutral"
            else:
                control_map[j][i] = "neutral"
    return control_map

def get_front_line(control_map):
    segments = []
    for y in range(NY):
        for x in range(NX):
            c0 = control_map[y][x]
            for (dx, dy) in [(1,0),(0,1)]:
                nx_ = x+dx
                ny_ = y+dy
                if in_bounds(nx_, ny_):
                    c1 = control_map[ny_][nx_]
                    if c0 != c1 and c0 != "neutral" and c1 != "neutral":
                        x0, y0 = tile_center_px(x, y)
                        x1, y1 = tile_center_px(nx_, ny_)
                        segments.append(((x0,y0),(x1,y1)))
    return segments


#####################################
# Unit & IA
#####################################

class Unit:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team  # "blue" ou "red"
        self.is_selected = False
        self.path = []
        self.dest_tile = None
        self.blocked = False
        self.encircled_ticks = 0

    def get_tile_pos(self):
        tx = int(self.x // TILE_SIZE)
        ty = int(self.y // TILE_SIZE)
        return (tx, ty)

    def update(self, all_units, control_map, grid, movement_allowed):
        """
        Si movement_allowed == False, ne pas bouger.
        """
        if self.blocked or not movement_allowed:
            return

        # Avancer
        if self.path:
            (tx, ty) = self.path[0]
            px, py = tile_center_px(tx, ty)
            dx = px - self.x
            dy = py - self.y
            dist = math.hypot(dx, dy)
            step = MOVE_SPEED * TILE_SIZE
            if dist > step:
                self.x += (dx/dist)*step
                self.y += (dy/dist)*step
            else:
                self.x = px
                self.y = py
                self.path.pop(0)
                if not self.path:
                    self.dest_tile = None

        # Blocage face‐à‐face
        for u in all_units:
            if u is not self and u.team != self.team:
                if distance(self.x, self.y, u.x, u.y) < 2*UNIT_RADIUS:
                    self.blocked = True
                    u.blocked = True

        # Encerclement
        tx, ty = self.get_tile_pos()
        if in_bounds(tx, ty):
            c = control_map[ty][tx]
            if (self.team=="blue" and c=="red") or (self.team=="red" and c=="blue"):
                self.encircled_ticks += 1
            else:
                self.encircled_ticks = 0


def ai_red(game, movement_allowed):
    """
    IA : calcule le path seulement si movement_allowed == True
    """
    if not movement_allowed:
        return

    blue_tiles = [u.get_tile_pos() for u in game.blue_units]
    for r_unit in game.red_units:
        if r_unit.blocked:
            r_unit.path = []
            r_unit.dest_tile = None
            r_unit.blocked = False
            continue
        if not r_unit.path:
            sx, sy = r_unit.get_tile_pos()
            candidate_paths = []
            # Cherche la plus proche unité bleue
            for b_pos in blue_tiles:
                pathb = find_path(
                    game.grid, (sx, sy), b_pos,
                    avoid_encirclement_test=lambda tx, ty: dangerous_for_red(game.control_map, tx, ty)
                )
                if pathb:
                    candidate_paths.append((len(pathb), b_pos, pathb))
            if candidate_paths:
                candidate_paths.sort(key=lambda c: c[0])
                chosen = candidate_paths[0]
                r_unit.path = chosen[2]
                r_unit.dest_tile = chosen[1]
            else:
                # vise la capitale bleue
                (cbx, cby) = game.blue_capital_tile
                path_cap = find_path(
                    game.grid, (sx, sy), (cbx, cby),
                    avoid_encirclement_test=lambda tx, ty: dangerous_for_red(game.control_map, tx, ty)
                )
                if path_cap:
                    r_unit.path = path_cap
                    r_unit.dest_tile = (cbx, cby)

def dangerous_for_red(control_map, tx, ty):
    if not in_bounds(tx, ty):
        return True
    return (control_map[ty][tx] == "blue")


#####################################
# Jeu principal - Single Canvas
#####################################

class SingleCanvasHOI4Game:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini HOI4-like - Single Canvas - Enhanced Selection")

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.pack()

        # Génération carte
        self.grid = generate_terrain(NX, NY)

        # Capitales (on s'assure qu'elles ne soient pas bloquées)
        self.blue_capital_tile = (3, NY//2)
        self.red_capital_tile  = (NX-4, NY//2)
        for (cx, cy) in [self.blue_capital_tile, self.red_capital_tile]:
            if is_blocked(self.grid[cy][cx]):
                # Convertit la tuile en plaine
                self.grid[cy][cx] = T_PLAIN

        # Création d’unités
        self.blue_units = self.create_units("blue")
        self.red_units  = self.create_units("red")
        self.all_units  = self.blue_units + self.red_units

        # Contrôle de territoire
        self.control_map = compute_territory_control(self.grid, self.red_capital_tile, self.blue_capital_tile)
        self.front_segments = get_front_line(self.control_map)

        self.running = True
        self.frame_count = 0
        self.recalc_interval = 10
        self.IA_interval = 5

        # Sélection
        self.selected_units = []
        self.dragging = False
        self.drag_start = (0,0)
        self.drag_end = (0,0)

        # Pour dessiner le rectangle
        self.select_rect_id = None

        # Gestion du "freeze" initial (15 s)
        self.start_time = time.time()

        # Bind
        self.canvas.bind("<Button-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<Button-3>", self.on_right_click)

        self.game_loop()

    def create_units(self, team):
        units = []
        if team == "blue":
            x_min, x_max = 1, NX//2 - 2
        else:
            x_min, x_max = NX//2 + 2, NX - 2
        count_placed = 0
        tries = 0
        while count_placed < MIN_TROOPS_PER_TEAM and tries < 10000:
            tries += 1
            tx = random.randint(x_min, x_max)
            ty = random.randint(1, NY-2)
            if is_walkable(self.grid[ty][tx]):
                px, py = tile_center_px(tx, ty)
                u = Unit(px, py, team)
                units.append(u)
                count_placed += 1
        return units

    def game_loop(self):
        if not self.running:
            return

        self.frame_count += 1

        # Contrôle si on est encore dans les 15 s de "freeze"
        elapsed = time.time() - self.start_time
        movement_allowed = (elapsed >= INITIAL_DELAY)

        # Recalcule territoire
        if self.frame_count % self.recalc_interval == 1:
            self.control_map = compute_territory_control(
                self.grid, self.red_capital_tile, self.blue_capital_tile
            )
            self.front_segments = get_front_line(self.control_map)

        # Débloquer
        for u in self.all_units:
            u.blocked = False

        # IA rouge (sauf si freeze)
        if self.frame_count % self.IA_interval == 1:
            ai_red(self, movement_allowed)

        # Update unités
        for u in self.all_units:
            u.update(self.all_units, self.control_map, self.grid, movement_allowed)

        # Encerclement
        dead_units = []
        for u in self.all_units:
            if u.encircled_ticks > ENCIRCLED_TICK_LIMIT:
                dead_units.append(u)
        for du in dead_units:
            self.all_units.remove(du)
            if du in self.red_units:
                self.red_units.remove(du)
            else:
                self.blue_units.remove(du)
            if du in self.selected_units:
                self.selected_units.remove(du)

        # Check victoire
        self.check_victory()

        # Dessin
        self.draw()

        self.root.after(int(1000/FPS), self.game_loop)

    def draw(self):
        self.canvas.delete("all")

        # Dessin carte
        for y in range(NY):
            for x in range(NX):
                t = self.grid[y][x]
                color = tile_color(t)
                self.canvas.create_rectangle(
                    x*TILE_SIZE, y*TILE_SIZE,
                    (x+1)*TILE_SIZE, (y+1)*TILE_SIZE,
                    fill=color, outline=""
                )

        # Ligne de front
        for (p0, p1) in self.front_segments:
            self.canvas.create_line(
                p0[0], p0[1],
                p1[0], p1[1],
                fill="black", width=2
            )

        # Capitales
        rx, ry = self.red_capital_tile
        bx, by = self.blue_capital_tile
        rpx, rpy = tile_center_px(rx, ry)
        bpx, bpy = tile_center_px(bx, by)
        self.draw_star(rpx, rpy, STAR_SIZE, COLOR_RED)
        self.draw_star(bpx, bpy, STAR_SIZE, COLOR_BLUE)

        # Unités
        for u in self.all_units:
            self.draw_unit(u)

        # Rectangle de sélection en cours
        if self.dragging:
            (sx, sy) = self.drag_start
            (ex, ey) = self.drag_end
            self.canvas.create_rectangle(
                sx, sy, ex, ey,
                outline="yellow", width=2, dash=(4,4)
            )

    def draw_unit(self, unit):
        color = COLOR_RED if unit.team == "red" else COLOR_BLUE
        x, y = unit.x, unit.y
        self.canvas.create_oval(
            x - UNIT_RADIUS, y - UNIT_RADIUS,
            x + UNIT_RADIUS, y + UNIT_RADIUS,
            fill=color, outline=""
        )
        if unit.is_selected:
            self.canvas.create_oval(
                x - (UNIT_RADIUS+2), y - (UNIT_RADIUS+2),
                x + (UNIT_RADIUS+2), y + (UNIT_RADIUS+2),
                outline=COLOR_HIGHLIGHT, width=2
            )

        # On ne dessine la flèche que pour les unités bleues
        # (Pour ne pas voir les flèches adverses)
        if unit.team == "blue" and unit.dest_tile:
            dx, dy = tile_center_px(unit.dest_tile[0], unit.dest_tile[1])
            self.draw_arrow(x, y, dx, dy)

    def draw_star(self, cx, cy, size, color):
        points = []
        nb = 5
        for i in range(nb*2):
            angle = i*math.pi/nb
            r = size if i%2==0 else size/2
            px = cx + math.cos(angle)*r
            py = cy + math.sin(angle)*r
            points.append((px, py))
        fl = []
        for (px, py) in points:
            fl.append(px)
            fl.append(py)
        self.canvas.create_polygon(fl, fill=color, outline=color)

    def draw_arrow(self, x0, y0, x1, y1):
        self.canvas.create_line(x0, y0, x1, y1, fill="black", width=2)
        angle = math.atan2(y1 - y0, x1 - x0)
        arrow_len = 10
        arrow_angle = math.radians(20)
        xA = x1 - arrow_len*math.cos(angle - arrow_angle)
        yA = y1 - arrow_len*math.sin(angle - arrow_angle)
        xB = x1 - arrow_len*math.cos(angle + arrow_angle)
        yB = y1 - arrow_len*math.sin(angle + arrow_angle)
        self.canvas.create_polygon(
            [(x1,y1),(xA,yA),(xB,yB)],
            fill="black"
        )

    #########################
    # Gestion de la sélection
    #########################

    def on_left_press(self, event):
        """Début du clic gauche : on note la position, on ne sait pas encore si clic ou drag."""
        self.dragging = True
        self.drag_start = (event.x, event.y)
        self.drag_end = (event.x, event.y)

    def on_left_drag(self, event):
        """On déplace la souris en maintenant => on dessine un rectangle."""
        if self.dragging:
            self.drag_end = (event.x, event.y)

    def on_left_release(self, event):
        """Relâchement du clic gauche : rectangle ou clic simple ?"""
        if not self.dragging:
            return
        self.dragging = False

        sx, sy = self.drag_start
        ex, ey = (event.x, event.y)
        dx = abs(ex - sx)
        dy = abs(ey - sy)

        # Seuil plus petit => 3 px
        if dx < 3 and dy < 3:
            # -> simple clic
            self.handle_simple_click(event.x, event.y)
        else:
            # -> rectangle
            x1, x2 = sorted([sx, ex])
            y1, y2 = sorted([sy, ey])
            self.clear_selection()

            for u in self.blue_units:
                # On check la bounding box
                if x1 <= u.x <= x2 and y1 <= u.y <= y2:
                    u.is_selected = True
                    self.selected_units.append(u)

    def handle_simple_click(self, mx, my):
        """Un clic rapide / court => soit on clique sur une unité, soit sur le terrain."""
        clicked_unit = None
        for u in self.all_units:
            if distance(mx, my, u.x, u.y) <= UNIT_RADIUS+2:
                clicked_unit = u
                break

        if clicked_unit is not None:
            if clicked_unit.team == "blue":
                # Sélectionne UNIQUEMENT cette unité
                self.clear_selection()
                clicked_unit.is_selected = True
                self.selected_units.append(clicked_unit)
            else:
                # C'est une unité ennemie => ordonne aux unités sélectionnées de l'attaquer
                if self.selected_units:
                    # BFS vers la case de l'ennemi
                    ex_tile = clicked_unit.get_tile_pos()
                    for su in self.selected_units:
                        sx, sy = su.get_tile_pos()
                        path = find_path(self.grid, (sx, sy), ex_tile)
                        su.path = path
                        su.dest_tile = ex_tile
        else:
            # On a cliqué dans le vide => ordre de déplacement
            # pour toutes les unités déjà sélectionnées
            if self.selected_units:
                tx = mx // TILE_SIZE
                ty = my // TILE_SIZE
                for su in self.selected_units:
                    sx, sy = su.get_tile_pos()
                    path = find_path(self.grid, (sx, sy), (tx, ty))
                    su.path = path
                    su.dest_tile = (tx, ty)

    def on_right_click(self, event):
        """Clic droit => on pourrait ignorer ou ajouter une autre fonctionnalité."""
        # Par exemple, on peut vider la sélection
        self.clear_selection()

    def clear_selection(self):
        for u in self.selected_units:
            u.is_selected = False
        self.selected_units = []

    #########################
    # Fin sélection
    #########################

    def check_victory(self):
        if not self.red_units:
            print("Victoire des Bleus (plus d'unités rouges)!")
            self.stop_game()
            return
        if not self.blue_units:
            print("Victoire des Rouges (plus d'unités bleues)!")
            self.stop_game()
            return

        rx, ry = self.red_capital_tile
        bx, by = self.blue_capital_tile
        rpx, rpy = tile_center_px(rx, ry)
        bpx, bpy = tile_center_px(bx, by)

        # Capitale rouge capturée ?
        for u in self.blue_units:
            if distance(u.x, u.y, rpx, rpy) < 2*TILE_SIZE:
                print("Victoire des Bleus (capitale rouge capturée)!")
                self.stop_game()
                return

        # Capitale bleue capturée ?
        for u in self.red_units:
            if distance(u.x, u.y, bpx, bpy) < 2*TILE_SIZE:
                print("Victoire des Rouges (capitale bleue capturée)!")
                self.stop_game()
                return

    def stop_game(self):
        self.running = False
        self.root.quit()


###################################
# Fonctions couleur
###################################

def tile_color(t):
    if t == T_DEEP_WATER:
        return COLOR_DEEP_WATER
    if t == T_RIVER:
        return COLOR_RIVER
    if t == T_BRIDGE:
        return COLOR_BRIDGE
    if t == T_PLAIN:
        return COLOR_PLAIN
    if t == T_FOREST:
        return COLOR_FOREST
    if t == T_MOUNTAIN:
        return COLOR_MOUNTAIN
    return "#000000"


###################################
# Main
###################################

def main():
    root = tk.Tk()
    game = SingleCanvasHOI4Game(root)
    root.mainloop()

if __name__ == "__main__":
    main()
