import tkinter as tk
import math
import random
import collections
import time

####################################
# PARAMÈTRES GLOBAUX
####################################

WIDTH, HEIGHT = 800, 600
TILE_SIZE = 10
NX = WIDTH // TILE_SIZE
NY = HEIGHT // TILE_SIZE
FPS = 30

UNIT_RADIUS = 6       # Unités plus grosses
MOVE_SPEED = 0.1      # Vitesse plus lente
ENCIRCLED_TICK_LIMIT = 300
STAR_SIZE = 6

INITIAL_DELAY = 20.0  # Freeze initial (secondes)

# Types de terrain
T_DEEP_WATER = 0
T_RIVER      = 1
T_PLAIN      = 2
T_FOREST     = 3
T_MOUNTAIN   = 4
T_BRIDGE     = 5
T_LAKE       = 6

# Couleurs de terrain
COLOR_DEEP_WATER = "#3B6FD2"
COLOR_RIVER      = "#0096FF"
COLOR_BRIDGE     = "#987B5B"
COLOR_PLAIN      = "#85C57A"
COLOR_FOREST     = "#3D8B37"
COLOR_MOUNTAIN   = "#AAAAAA"
COLOR_LAKE       = "#4C8BC8"

# Couleurs équipes
COLOR_RED  = "#DC1414"
COLOR_BLUE = "#1414DC"
COLOR_HIGHLIGHT = "yellow"

MIN_TROOPS_PER_TEAM = 10

####################################
# FONCTIONS UTILES
####################################

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def in_bounds(tx, ty):
    return 0 <= tx < NX and 0 <= ty < NY

def tile_center_px(tx, ty):
    return (tx*TILE_SIZE + TILE_SIZE/2, ty*TILE_SIZE + TILE_SIZE/2)

def is_blocked(t):
    """Cases infranchissables."""
    return (t == T_DEEP_WATER or t == T_RIVER or t == T_MOUNTAIN or t == T_LAKE)

def is_walkable(t):
    return (t == T_PLAIN or t == T_FOREST or t == T_BRIDGE)

####################################
# GÉNÉRATION DE LA CARTE
####################################

def generate_map(nx, ny):
    """
    Génère une carte :
    - Tout en plaines,
    - Ajout de clusters de montagne (2..6 x 2..6),
    - Ajout de lacs elliptiques (2..4),
    - Ajout de 1..3 rivières (chacune >=12 de long, largeur 1..3, 1..2 ponts),
    - Ajout de forêts aléatoires (environ 8%).
    """
    # Base en plaine
    grid = [[T_PLAIN for _ in range(nx)] for __ in range(ny)]

    # Montagnes regroupées
    add_mountain_clusters(grid, count=3)

    # Lacs elliptiques
    add_lakes(grid, count=2)

    # Rivières
    riv_count = random.randint(1,3)
    for _ in range(riv_count):
        create_river(grid)

    # Forêts ~ 8%
    add_forests(grid, ratio=0.08)

    return grid

def add_mountain_clusters(grid, count=3):
    """Ajoute 'count' clusters de montagnes (2..6 blocs de large/haut)."""
    for _ in range(count):
        w = random.randint(2,6)
        h = random.randint(2,6)
        x0 = random.randint(0, NX - w - 1)
        y0 = random.randint(0, NY - h - 1)
        for yy in range(y0, y0+h):
            for xx in range(x0, x0+w):
                grid[yy][xx] = T_MOUNTAIN

def add_lakes(grid, count=2):
    """
    Ajoute quelques lacs elliptiques (infranchissables).
    """
    for _ in range(count):
        cx = random.randint(10, NX-10)
        cy = random.randint(10, NY-10)
        rx = random.randint(3, 6)
        ry = random.randint(3, 6)
        for y in range(NY):
            for x in range(NX):
                dx = x - cx
                dy = y - cy
                if (dx*dx)/(rx*rx) + (dy*dy)/(ry*ry) <= 1.0:
                    grid[y][x] = T_LAKE

def create_river(grid):
    """
    Crée une "rivière" d'au moins 12 tuiles, largeur (1..3),
    serpentant. 1..2 ponts.
    """
    length_min = 12
    sx = random.randint(0, NX//2)
    sy = 0  # on part du haut
    path=[]
    cx, cy = sx, sy
    w = random.randint(1,3)
    steps=0
    while steps<1000 and len(path)<60:
        path.append((cx,cy))
        # direction random
        dir_choice = random.choice([(1,0),(0,1),(1,1),(-1,1),(1,-1)])
        dist = random.randint(1,10)
        for _ in range(dist):
            cx += dir_choice[0]
            cy += dir_choice[1]
            if in_bounds(cx,cy):
                path.append((cx,cy))
            else:
                break
        steps+=dist
        if len(path)>=length_min and random.random()<0.25:
            break

    # Applique la largeur w
    for (x,y) in path:
        for dx in range(-w,w+1):
            for dy in range(-w,w+1):
                nx_ = x+dx
                ny_ = y+dy
                if in_bounds(nx_, ny_):
                    grid[ny_][nx_] = T_RIVER

    # 1..2 ponts
    nb_bridges = random.randint(1,2)
    river_positions=[]
    for (x,y) in path:
        if in_bounds(x,y) and grid[y][x] == T_RIVER:
            river_positions.append((x,y))
    random.shuffle(river_positions)
    for _ in range(nb_bridges):
        if not river_positions:
            break
        bx,by = river_positions.pop()
        grid[by][bx] = T_BRIDGE

def add_forests(grid, ratio=0.08):
    """
    Convertit environ ratio% des plaines en forêts.
    """
    for y in range(NY):
        for x in range(NX):
            if grid[y][x] == T_PLAIN:
                if random.random()<ratio:
                    grid[y][x] = T_FOREST

####################################
# PATHFINDING
####################################

def find_path(grid, start_tile, goal_tile):
    (sx,sy) = start_tile
    (gx,gy) = goal_tile
    if not in_bounds(sx,sy) or not in_bounds(gx,gy):
        return []
    if (sx,sy)==(gx,gy):
        return []

    blocked_types = (T_DEEP_WATER, T_RIVER, T_MOUNTAIN, T_LAKE)
    visited = set()
    visited.add((sx,sy))
    parent=dict()
    parent[(sx,sy)] = None
    queue = collections.deque()
    queue.append((sx,sy))

    while queue:
        cx,cy = queue.popleft()
        if (cx,cy)==(gx,gy):
            break
        for (dx,dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx_ = cx+dx
            ny_ = cy+dy
            if in_bounds(nx_,ny_):
                if (nx_,ny_) not in visited:
                    if grid[ny_][nx_] not in blocked_types:
                        visited.add((nx_, ny_))
                        parent[(nx_, ny_)] = (cx,cy)
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

####################################
# FRONT : POINTS ET LIGNE
####################################

def generate_initial_front():
    """
    Génère un jeu de ~25 points (ou +) pour la "ligne de front" initiale,
    allant du haut à bas, pas droite (e.g. sinusoïde).
    """
    points=[]
    num_points = 25
    # x =  (some function), y = from 0..height
    # On crée, par exemple, un y segmenté.  
    # On veut un front "depuis tout en haut" (y=0) jusqu'en bas (y=HEIGHT).
    # On va en px direct.  => On peut faire un x ~ 1/2 width + un offset sin.
    for i in range(num_points):
        frac = i/(num_points-1)
        py = frac*HEIGHT
        # offset sin
        sin_off = 80*math.sin(frac*2*math.pi)
        px = WIDTH//2 + sin_off
        points.append((px,py))
    return points

def add_front_points_on_cross(front_points, xCross, yCross):
    """
    Quand un point (unité) traverse la ligne,
    on ajoute 1..2 points invisibles autour pour "pousser" localement.
    On insère ces points dans la liste, on relisse ensuite.
    """
    if len(front_points)<2:
        return front_points
    # Cherchons le plus proche point
    best_i=None
    best_d=999999
    for i,p in enumerate(front_points):
        d=distance(p[0],p[1], xCross,yCross)
        if d<best_d:
            best_d=d
            best_i=i
    # On insère un point avant ou après best_i
    # pour simuler un bombement local
    # ex: on insère (xCross +/- random, yCross +/- random)
    dx = random.uniform(-20,20)
    dy = random.uniform(-20,20)
    new_pt = (xCross+dx, yCross+dy)
    front_points.insert(best_i, new_pt)

    # Limiter la taille => s'il y a trop de points, on peut élaguer
    if len(front_points)>45:
        # on supprime le plus loin
        # ex: on supprime la 2eme moitie
        front_points.pop(random.randint(len(front_points)//2, len(front_points)-1))

    return front_points

def smooth_front(points, passes=2):
    """
    Lisse la liste de points "front"
    """
    if len(points)<3:
        return points
    for _ in range(passes):
        newpts=[]
        newpts.append(points[0])
        for i in range(1,len(points)-1):
            x=(points[i-1][0]+points[i][0]+points[i+1][0])/3
            y=(points[i-1][1]+points[i][1]+points[i+1][1])/3
            newpts.append((x,y))
        newpts.append(points[-1])
        points=newpts
    return points

####################################
# UNITÉ & IA
####################################

class Unit:
    def __init__(self, x,y,team):
        self.x=x
        self.y=y
        self.team=team
        self.is_selected=False
        self.path=[]
        self.dest_tile=None
        self.blocked=False
        self.encircled_ticks=0
        self.target_enemy=None
        self.chase_cooldown=0

    def get_tile_pos(self):
        tx=int(self.x//TILE_SIZE)
        ty=int(self.y//TILE_SIZE)
        return (tx,ty)

    def update(self, game, all_units, grid, movement_allowed):
        if not movement_allowed:
            return

        # collisions
        for u in all_units:
            if u is not self:
                d=distance(self.x,self.y,u.x,u.y)
                if d<2*UNIT_RADIUS:
                    overlap=2*UNIT_RADIUS-d
                    if d>0:
                        dx=(self.x-u.x)/d
                        dy=(self.y-u.y)/d
                        self.x+=dx*(overlap/2)
                        self.y+=dy*(overlap/2)
                        u.x-=dx*(overlap/2)
                        u.y-=dy*(overlap/2)

        # Attaque en temps réel
        if self.target_enemy!=None:
            if self.target_enemy not in all_units:
                self.target_enemy=None
                self.path=[]
                self.dest_tile=None
            else:
                self.chase_cooldown-=1
                if self.chase_cooldown<=0:
                    self.chase_cooldown=10
                    ex,ey=self.target_enemy.get_tile_pos()
                    sx,sy=self.get_tile_pos()
                    p=find_path(grid,(sx,sy),(ex,ey))
                    self.path=p
                    self.dest_tile=(ex,ey)

        # Deplacement
        if self.path:
            (px,py)=tile_center_px(self.path[0][0], self.path[0][1])
            dx=px-self.x
            dy=py-self.y
            dist=math.hypot(dx,dy)
            step=MOVE_SPEED*TILE_SIZE
            if dist>step:
                self.x+=(dx/dist)*step
                self.y+=(dy/dist)*step
            else:
                self.x=px
                self.y=py
                self.path.pop(0)
                if not self.path:
                    self.dest_tile=None

        # Encerclement => si je suis "de l'autre cote" de la front
        # (Simplification => on regarde si je suis a gauche/droite ?)
        # Ici, on check juste si "je suis a la gauche de la courbe" (rouge) 
        # ou "a la droite de la courbe" (bleue).
        # => plus tard, BFS ?
        # Pour l'instant, on fait un BFS sur la "control_map" ?
        # Non, on fait plus simple => on check crossing
        if self.team=="blue":
            # si je suis "côté rouge" => encircled
            if game.is_unit_in_enemy_zone(self, "red"):
                self.encircled_ticks+=1
            else:
                self.encircled_ticks=0
        else:
            if game.is_unit_in_enemy_zone(self, "blue"):
                self.encircled_ticks+=1
            else:
                self.encircled_ticks=0

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

        for u in myunits:
            if u.blocked:
                u.path=[]
                u.dest_tile=None
                u.target_enemy=None
                u.blocked=False
                continue
            if not foes:
                return
            # plus proche
            bestd=999999
            bestf=None
            for f in foes:
                d=distance(u.x,u.y,f.x,f.y)
                if d<bestd:
                    bestd=d
                    bestf=f
            u.target_enemy=bestf

####################################
# JEU
####################################

class HOI4FrontAdvancedGame:
    def __init__(self, root):
        self.root=root
        self.root.title("HOI4-like : Rivières, Lacs, Montagnes, Large front, Points invisibles")
        self.canvas=tk.Canvas(self.root,width=WIDTH,height=HEIGHT,bg="white")
        self.canvas.pack()

        # Génération
        self.grid = generate_map(NX,NY)

        # Capitals
        self.blue_cap = (3, NY//2)
        self.red_cap  = (NX-4, NY//2)
        # Forcer en plaines
        self.grid[self.blue_cap[1]][self.blue_cap[0]] = T_PLAIN
        self.grid[self.red_cap[1]][self.red_cap[0]]   = T_PLAIN

        # Units
        self.blue_units=self.create_units_around_cap(self.blue_cap, "blue")
        self.red_units =self.create_units_around_cap(self.red_cap,  "red")
        self.all_units =self.blue_units+self.red_units

        self.ai_red = AI("red")

        self.running=True
        self.frame_count=0
        self.selected_units=[]
        self.dragging=False
        self.drag_start=(0,0)
        self.drag_end=(0,0)
        self.victory_label=None

        # Freeze
        self.start_time=time.time()
        self.game_started=False

        # On génère une ligne de front initiale courbe
        self.front_points = generate_initial_front()  
        # => ~25 points
        # on peut lisser un peu
        self.front_points = smooth_front(self.front_points, 2)

        self.canvas.bind("<Button-1>",self.on_left_press)
        self.canvas.bind("<B1-Motion>",self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>",self.on_left_release)
        self.canvas.bind("<Button-3>",self.on_right_click)

        self.game_loop()

    def create_units_around_cap(self, cap, team):
        (cx,cy) = cap
        units=[]
        placed=0
        while placed<MIN_TROOPS_PER_TEAM:
            rx = random.randint(-3,3)
            ry = random.randint(-3,3)
            tx=cx+rx
            ty=cy+ry
            if in_bounds(tx,ty) and is_walkable(self.grid[ty][tx]):
                (px,py)=tile_center_px(tx,ty)
                u=Unit(px,py,team)
                units.append(u)
                placed+=1
        return units

    def game_loop(self):
        if not self.running:
            return

        self.frame_count+=1

        # Freeze
        now=time.time()
        if not self.game_started:
            if now-self.start_time>=INITIAL_DELAY:
                self.game_started=True
                self.play_start_time=time.time()
            movement_allowed=False
        else:
            movement_allowed=True

        # IA
        self.ai_red.update(self, movement_allowed)

        # Update units
        for u in self.all_units:
            u.update(self, self.all_units, self.grid, movement_allowed)
            # Check crossing front
            # si l'unité traverse la ligne => on insère des points
            if self.cross_front(u):
                # on rajoute des points invisibles autour
                self.front_points = add_front_points_on_cross(
                    self.front_points,
                    u.x,u.y
                )
                # on re-lisse
                self.front_points = smooth_front(self.front_points, 2)

        # Encerclement => destruction
        dead=[]
        for u in self.all_units:
            if u.encircled_ticks>ENCIRCLED_TICK_LIMIT:
                dead.append(u)
        for du in dead:
            self.all_units.remove(du)
            if du in self.red_units:
                self.red_units.remove(du)
            else:
                self.blue_units.remove(du)
            if du in self.selected_units:
                self.selected_units.remove(du)

        # check victory
        self.check_victory()

        # draw
        self.draw()

        if self.running:
            self.root.after(int(1000/FPS), self.game_loop)

    def cross_front(self, unit):
        """
        Détermine si l'unité "traverse" la ligne de front 
        (ex: côté gauche => côté droit).
        Simplification : on regarde la position relative 
        par rapport au polygone formé par front_points ?
        => On va juste checker si la position de l'unité 
           se situe d'un côté ou l'autre (param > 0).
        => On fait un test binaire : 
           on regarde le signe de la "signed distance" 
           par rapport à la polyligne. 
           S'il change, c'est qu'on a franchi la courbe.

        Pour simplifier encore plus : 
        on compare la position de l'unité 
        à la "x" de la front (interpolation à la y de l'unité).
        """
        # On cherche 2 points de la front dont la y encadre l'unité
        yU=unit.y
        # On balaye
        above=[]
        below=[]
        for p in self.front_points:
            if p[1]<yU:
                above.append(p)
            else:
                below.append(p)
        # S'il y a aucun point en dessous ou au dessus, 
        # on dit qu'on n'a pas franchi
        if not above or not below:
            return False

        # On cherche le point "le plus proche en Y" qui est juste au dessus 
        # et celui juste en dessous pour approx la x de la front
        pAbove = max(above, key=lambda pp: pp[1])
        pBelow = min(below, key=lambda pp: pp[1])
        # interpolation
        dy = pBelow[1]-pAbove[1]
        if abs(dy)<1e-6:
            # front quasi horizontal
            midx=(pAbove[0]+pBelow[0])/2
        else:
            t = (yU - pAbove[1])/dy
            midx = pAbove[0] + t*(pBelow[0]-pAbove[0])

        # si unit.x < midx => côté gauche, si > => côté droit
        # on check s'il y a un changement par rapport à la frame précédente
        # => on pourrait stocker la "side" dans l'unité
        old_side = getattr(unit,"front_side", None)
        new_side = "left" if unit.x < midx else "right"
        unit.front_side = new_side
        if old_side is not None and old_side!=new_side:
            # => on a franchi
            return True
        else:
            return False

    def is_unit_in_enemy_zone(self, unit, enemy_team):
        """
        Renvoie True si (x,y) se trouve dans la zone "enemy_team" 
        par rapport à la front_points (proto).
        => On détermine si c'est "left" ou "right" par rapport 
           à la polyligne, selon si l'unité est "enemy_side" ou pas.
        """
        # Meme code que cross_front, 
        # sauf qu'on renvoie si on est "left" ou "right".
        # Si team==blue => on dit "red zone" = right ?
        # ou on inverser. 
        # => On fait un param => si enemy_team=="red" => 
        #    la zone rouge est "left" (ou "right"?). 
        #    la zone bleue est l'autre. 
        # On doit être cohérent.
        # Pour simplifier => on define "blue zone" = right, 
        # "red zone"= left (ou inverse).
        if enemy_team=="red":
            # on suppose "red" => left
            desired_side="left"
        else:
            desired_side="right"

        yU=unit.y
        above=[]
        below=[]
        for p in self.front_points:
            if p[1]<yU:
                above.append(p)
            else:
                below.append(p)
        if not above or not below:
            return False
        pAbove = max(above, key=lambda pp: pp[1])
        pBelow = min(below, key=lambda pp: pp[1])
        dy = pBelow[1]-pAbove[1]
        if abs(dy)<1e-6:
            midx=(pAbove[0]+pBelow[0])/2
        else:
            t=(yU-pAbove[1])/dy
            midx=pAbove[0]+t*(pBelow[0]-pAbove[0])
        side = "left" if unit.x<midx else "right"
        return (side==desired_side)

    def draw(self):
        self.canvas.delete("all")

        # Dessin terrain
        for y in range(NY):
            for x in range(NX):
                t=self.grid[y][x]
                color=tile_color(t)
                self.canvas.create_rectangle(
                    x*TILE_SIZE, y*TILE_SIZE,
                    (x+1)*TILE_SIZE,(y+1)*TILE_SIZE,
                    fill=color, outline=""
                )

        # Capitals
        (rx,ry)=self.red_cap
        (bx,by)=self.blue_cap
        rpx,rpy=tile_center_px(rx,ry)
        bpx,bpy=tile_center_px(bx,by)
        self.draw_star(rpx,rpy,STAR_SIZE,COLOR_RED)
        self.draw_star(bpx,bpy,STAR_SIZE,COLOR_BLUE)

        # Units
        for u in self.all_units:
            self.draw_unit(u)

        # Front line => on a self.front_points
        if len(self.front_points)>1:
            coords=[]
            for p in self.front_points:
                coords.append(p[0])
                coords.append(p[1])
            # on fait un trait plus large (6) 
            self.canvas.create_line(coords, fill="black", width=6, smooth=True)

        # rectangle selection
        if self.dragging:
            sx,sy=self.drag_start
            ex,ey=self.drag_end
            self.canvas.create_rectangle(
                sx,sy,ex,ey,
                outline="yellow",width=2, dash=(4,4)
            )

        # Timer UI
        self.canvas.create_rectangle(0,0,130,40, fill="#222222", outline="#777777",width=2)
        if not self.game_started:
            left=INITIAL_DELAY-(time.time()-self.start_time)
            if left<0:left=0
            txt=f"Début dans {int(left)} s"
        else:
            e=time.time()-self.play_start_time
            txt=f"Time : {int(e)} s"

        self.canvas.create_text(
            10,10,
            text=txt,
            anchor="nw",
            fill="white",
            font=("Arial",14,"bold")
        )

        # Victoire
        if self.victory_label:
            self.canvas.create_text(
                WIDTH//2, HEIGHT//2,
                text=self.victory_label,
                fill="yellow",
                font=("Arial",24,"bold"),
                anchor="center"
            )

    def draw_unit(self,u):
        color = COLOR_BLUE if u.team=="blue" else COLOR_RED
        self.canvas.create_oval(
            u.x-UNIT_RADIUS, u.y-UNIT_RADIUS,
            u.x+UNIT_RADIUS, u.y+UNIT_RADIUS,
            fill=color, outline=""
        )
        if u.is_selected:
            self.canvas.create_oval(
                u.x-(UNIT_RADIUS+2), u.y-(UNIT_RADIUS+2),
                u.x+(UNIT_RADIUS+2), u.y+(UNIT_RADIUS+2),
                outline=COLOR_HIGHLIGHT, width=2
            )
        # Flèche => only for blue
        if u.team=="blue" and u.dest_tile:
            (px,py)=tile_center_px(u.dest_tile[0], u.dest_tile[1])
            self.draw_arrow(u.x,u.y,px,py)

    def draw_star(self,cx,cy,size,color):
        pts=[]
        nb=5
        for i in range(nb*2):
            angle=i*math.pi/nb
            r=size if i%2==0 else size/2
            px=cx+math.cos(angle)*r
            py=cy+math.sin(angle)*r
            pts.append((px,py))
        fl=[]
        for (px,py) in pts:
            fl.append(px)
            fl.append(py)
        self.canvas.create_polygon(fl, fill=color, outline=color)

    def draw_arrow(self,x0,y0,x1,y1):
        self.canvas.create_line(x0,y0,x1,y1, fill="black", width=2, smooth=True)
        angle=math.atan2(y1-y0,x1-x0)
        arr_len=10
        arr_angle=math.radians(20)
        xA=x1-arr_len*math.cos(angle-arr_angle)
        yA=y1-arr_len*math.sin(angle-arr_angle)
        xB=x1-arr_len*math.cos(angle+arr_angle)
        yB=y1-arr_len*math.sin(angle+arr_angle)
        self.canvas.create_polygon(
            [(x1,y1),(xA,yA),(xB,yB)],
            fill="black"
        )

    def on_left_press(self,event):
        self.dragging=True
        self.drag_start=(event.x,event.y)
        self.drag_end=(event.x,event.y)

    def on_left_drag(self,event):
        if self.dragging:
            self.drag_end=(event.x,event.y)

    def on_left_release(self,event):
        if not self.dragging:
            return
        self.dragging=False
        sx,sy=self.drag_start
        ex,ey=(event.x,event.y)
        dx=abs(ex-sx)
        dy=abs(ey-sy)
        if dx<3 and dy<3:
            self.handle_simple_click(event.x,event.y)
        else:
            x1,x2=sorted([sx,ex])
            y1,y2=sorted([sy,ey])
            self.clear_selection()
            for u in self.blue_units:
                if x1<=u.x<=x2 and y1<=u.y<=y2:
                    u.is_selected=True
                    self.selected_units.append(u)

    def handle_simple_click(self,mx,my):
        # check if clicked a unit
        clicked_unit=None
        for u in self.all_units:
            if distance(mx,my,u.x,u.y)<=UNIT_RADIUS+2:
                clicked_unit=u
                break
        if clicked_unit:
            if clicked_unit.team=="blue":
                self.clear_selection()
                clicked_unit.is_selected=True
                self.selected_units.append(clicked_unit)
            else:
                # Attaque
                if self.selected_units:
                    for su in self.selected_units:
                        su.target_enemy=clicked_unit
                        su.path=[]
                        su.dest_tile=None
        else:
            # terrain => move
            if self.selected_units:
                tx=mx//TILE_SIZE
                ty=my//TILE_SIZE
                for su in self.selected_units:
                    su.target_enemy=None
                    stx,sty=su.get_tile_pos()
                    su.path=find_path(self.grid,(stx,sty),(tx,ty))
                    su.dest_tile=(tx,ty)

    def on_right_click(self,event):
        self.clear_selection()

    def clear_selection(self):
        for u in self.selected_units:
            u.is_selected=False
        self.selected_units=[]

    def check_victory(self):
        if not self.blue_units:
            self.victory_label="Victoire Rouge!"
            self.stop_game()
            return
        if not self.red_units:
            self.victory_label="Victoire Bleue!"
            self.stop_game()
            return

        # capital
        (rx,ry)=self.red_cap
        (bx,by)=self.blue_cap
        rpx,rpy=tile_center_px(rx,ry)
        bpx,bpy=tile_center_px(bx,by)
        for u in self.blue_units:
            if distance(u.x,u.y,rpx,rpy)<2*TILE_SIZE:
                self.victory_label="Victoire Bleue!"
                self.stop_game()
                return
        for u in self.red_units:
            if distance(u.x,u.y,bpx,bpy)<2*TILE_SIZE:
                self.victory_label="Victoire Rouge!"
                self.stop_game()
                return

    def stop_game(self):
        self.running=False

    # Méthodes pour test "zone ennemie"
    def is_unit_in_enemy_zone(self, unit, enemy_team):
        """
        On check la "side" par rapport a la front line => see cross_front logic.
        On re-emploie la meme technique => side=left or right.
        Si enemy_team=="red" => la zone rouge c'est 'left' 
        (on arbitre ça), 
        la zone bleue c'est 'right'.
        """
        if enemy_team=="red":
            desired_side="left"
        else:
            desired_side="right"

        yU=unit.y
        above=[]
        below=[]
        for p in self.front_points:
            if p[1]<yU:
                above.append(p)
            else:
                below.append(p)
        if not above or not below:
            return False
        pAbove = max(above, key=lambda pp: pp[1])
        pBelow = min(below, key=lambda pp: pp[1])
        dy=pBelow[1]-pAbove[1]
        if abs(dy)<1e-6:
            midx=(pAbove[0]+pBelow[0])/2
        else:
            t=(yU-pAbove[1])/dy
            midx=pAbove[0]+t*(pBelow[0]-pAbove[0])
        side = "left" if unit.x<midx else "right"
        return (side==desired_side)


####################################
# FRONT POINTS : initial
####################################

def generate_initial_front():
    """
    Crée ~25 points depuis haut..bas, 
    en px, sinusoïde pour ne pas etre droit.
    """
    points=[]
    num=25
    for i in range(num):
        frac=i/(num-1)
        y=frac*HEIGHT
        x=(WIDTH/2)+80*math.sin(frac*2*math.pi)
        points.append((x,y))
    return points

def smooth_front(points, passes=2):
    if len(points)<3:
        return points
    for _ in range(passes):
        newpts=[]
        newpts.append(points[0])
        for i in range(1,len(points)-1):
            x=(points[i-1][0]+points[i][0]+points[i+1][0])/3
            y=(points[i-1][1]+points[i][1]+points[i+1][1])/3
            newpts.append((x,y))
        newpts.append(points[-1])
        points=newpts
    return points

def add_front_points_on_cross(front_points, xCross, yCross):
    """
    On insère un point ou deux autour de (xCross,yCross)
    pour "bomber" localement le front.
    """
    if len(front_points)<2:
        return front_points

    best_i=0
    best_d=999999
    for i,p in enumerate(front_points):
        d=distance(p[0],p[1], xCross,yCross)
        if d<best_d:
            best_d=d
            best_i=i
    # On insère
    dx = random.uniform(-20,20)
    dy = random.uniform(-20,20)
    new_p = (xCross+dx, yCross+dy)
    front_points.insert(best_i, new_p)

    # On peut en insérer un 2eme
    if random.random()<0.5:
        dx2 = random.uniform(-20,20)
        dy2 = random.uniform(-20,20)
        front_points.insert(best_i, (xCross+dx2,yCross+dy2))

    # Contrôle la taille => 50 points max
    if len(front_points)>50:
        # remove random in second half
        idx = random.randint(len(front_points)//2, len(front_points)-1)
        front_points.pop(idx)
    return front_points


####################################
# Couleur
####################################

def tile_color(t):
    if t==T_DEEP_WATER:
        return COLOR_DEEP_WATER
    if t==T_RIVER:
        return COLOR_RIVER
    if t==T_BRIDGE:
        return COLOR_BRIDGE
    if t==T_PLAIN:
        return COLOR_PLAIN
    if t==T_FOREST:
        return COLOR_FOREST
    if t==T_MOUNTAIN:
        return COLOR_MOUNTAIN
    if t==T_LAKE:
        return COLOR_LAKE
    return "#000000"


####################################
# MAIN
####################################

def main():
    root=tk.Tk()
    game=HOI4FrontAdvancedGame(root)
    root.mainloop()

if __name__=="__main__":
    main()
