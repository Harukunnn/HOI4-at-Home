# main.py

import tkinter as tk
import time
import random

from Engineering.consts import (
    WIDTH, HEIGHT, TILE_SIZE, NX, NY,
    FPS, INITIAL_DELAY, CAPTURE_TIME,
    T_PLAIN, UNIT_RADIUS, STAR_SIZE,
    COLOR_BLUE, COLOR_RED, COLOR_HIGHLIGHT,
    ENCIRCLED_TICK_LIMIT
)
from Engineering.generation import generate_map
from Engineering.pathfinding import in_bounds
from Engineering.front import generate_initial_front, add_front_points_on_cross, check_side
from Engineering.units import Unit, AI

class HOI4FrontInvisibleGame:
    def __init__(self, root):
        self.root = root
        self.root.title("HOI4 splitted + Victory Animation")

        self.top_frame = tk.Frame(self.root, bg="#444444")
        self.top_frame.pack(side="top", fill="x")

        quit_btn = tk.Button(self.top_frame, text="Quitter", command=self.quit_game, fg="white", bg="#AA0000")
        quit_btn.pack(side="left", padx=5, pady=2)

        self.info_label = tk.Label(self.top_frame, text="HOI4 splitted", fg="white", bg="#444444", font=("Arial",12,"bold"))
        self.info_label.pack(side="left", padx=5)

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.pack(side="top", fill="both", expand=True)

        self.canvas.focus_set()
        self.canvas.bind("<Escape>", lambda e: self.quit_game())

        self.shift_held = False
        self.canvas.bind("<KeyPress-Shift_L>", lambda e: self.set_shift(True))
        self.canvas.bind("<KeyRelease-Shift_L>", lambda e: self.set_shift(False))

        # Génération de la carte
        self.grid = generate_map(NX, NY)

        # Capitales
        self.blue_cap = (3, NY//2)
        self.red_cap  = (NX-4, NY//2)
        self.grid[self.blue_cap[1]][self.blue_cap[0]] = T_PLAIN
        self.grid[self.red_cap[1]][self.red_cap[0]]   = T_PLAIN

        # Création d’unités
        self.blue_units = self.create_units_around_cap(self.blue_cap, "blue")
        self.red_units  = self.create_units_around_cap(self.red_cap, "red")
        self.all_units  = self.blue_units + self.red_units

        self.ai_red = AI("red")

        # État du jeu
        self.running = True
        self.frame_count = 0
        self.selected_units = []
        self.dragging = False
        self.drag_start = (0,0)
        self.drag_end   = (0,0)

        # Chrono
        self.start_time = time.time()
        self.game_started = False
        self.play_start_time = 0

        # Ligne de front
        self.front_points = generate_initial_front(num_points=25)

        # Timer capture capital
        self.cap_red_timer  = 0.0
        self.cap_blue_timer = 0.0

        # Label/mécanisme de victoire
        self.victory_label = None
        self.victory_mode  = False  # pour savoir si on est en animation de victoire
        self.victory_phase = 0      # pour animer (clignoter)

        # Binds souris
        self.canvas.bind("<Button-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<Button-3>", self.on_right_click)

        self.game_loop()

    def set_shift(self,val):
        self.shift_held=val

    def quit_game(self):
        # simple close
        self.running=False
        self.root.quit()

    def create_units_around_cap(self, cap, team):
        units=[]
        placed=0
        from Engineering.consts import MIN_TROOPS_PER_TEAM
        (cx,cy) = cap
        while placed<MIN_TROOPS_PER_TEAM:
            rx = random.randint(-3,3)
            ry = random.randint(-3,3)
            tx = cx+rx
            ty = cy+ry
            if in_bounds(tx,ty):
                if self.grid[ty][tx] == T_PLAIN:
                    px = tx*TILE_SIZE + TILE_SIZE/2
                    py = ty*TILE_SIZE + TILE_SIZE/2
                    u  = Unit(px,py,team)
                    units.append(u)
                    placed+=1
        return units

    def game_loop(self):
        if not self.running:
            return

        self.frame_count+=1
        now=time.time()
        if not self.game_started:
            if now-self.start_time>=INITIAL_DELAY:
                self.game_started=True
                self.play_start_time=time.time()
            movement_allowed=False
        else:
            movement_allowed=True

        # Si on est en "victoire", on continue juste l'animation
        if not self.victory_mode:
            self.ai_red.update(self, movement_allowed)
            for u in self.all_units:
                u.update(self, self.all_units, self.grid, movement_allowed)
                if self.cross_front(u):
                    self.front_points=add_front_points_on_cross(self.front_points, u.x,u.y)

            dead=[]
            for u in self.all_units:
                if u.encircled_ticks>ENCIRCLED_TICK_LIMIT:
                    dead.append(u)
            for du in dead:
                self.all_units.remove(du)
                if du in self.blue_units:
                    self.blue_units.remove(du)
                else:
                    self.red_units.remove(du)
                if du in self.selected_units:
                    self.selected_units.remove(du)

            self.check_victory()

        self.draw()
        if self.victory_mode:
            self.victory_phase=(self.victory_phase+1)%60  # pour clignoter
        from Engineering.consts import FPS
        self.root.after(int(1000/FPS), self.game_loop)

    def draw(self):
        self.canvas.delete("all")

        from Engineering.consts import tile_color, NX, NY, TILE_SIZE
        for y in range(NY):
            for x in range(NX):
                c=tile_color(self.grid[y][x])
                self.canvas.create_rectangle(
                    x*TILE_SIZE, y*TILE_SIZE,
                    (x+1)*TILE_SIZE, (y+1)*TILE_SIZE,
                    fill=c, outline=""
                )

        (rx,ry)=self.red_cap
        (bx,by)=self.blue_cap
        rpx=rx*TILE_SIZE+TILE_SIZE/2
        rpy=ry*TILE_SIZE+TILE_SIZE/2
        bpx=bx*TILE_SIZE+TILE_SIZE/2
        bpy=by*TILE_SIZE+TILE_SIZE/2

        from Engineering.consts import COLOR_RED, COLOR_BLUE
        self.draw_star(rpx,rpy,STAR_SIZE,COLOR_RED)
        self.draw_star(bpx,bpy,STAR_SIZE,COLOR_BLUE)

        for u in self.all_units:
            self.draw_unit(u)

        if len(self.front_points)>1:
            coords=[]
            for p in self.front_points:
                coords.append(p[0])
                coords.append(p[1])
            self.canvas.create_line(coords, fill="black", width=6, smooth=True)

        self.canvas.create_rectangle(0,0,160,70, fill="#222222", outline="#666666", width=2)
        from Engineering.consts import INITIAL_DELAY, CAPTURE_TIME
        if not self.game_started:
            left=INITIAL_DELAY-(time.time()-self.start_time)
            if left<0:left=0
            txt=f"Début dans {int(left)} s"
            self.canvas.create_text(10,10, text=txt, anchor="nw", fill="white", font=("Helvetica",16,"bold"))
        else:
            e=time.time()-self.play_start_time
            txt=f"Time : {int(e)} s"
            self.canvas.create_text(10,10, text=txt, anchor="nw", fill="white", font=("Helvetica",16,"bold"))
            if self.cap_red_timer>0:
                leftC=CAPTURE_TIME-self.cap_red_timer
                if leftC<0:leftC=0
                self.canvas.create_text(10,30, text=f"RedCap => {int(leftC)}s", anchor="nw", fill="red", font=("Helvetica",12,"bold"))
            if self.cap_blue_timer>0:
                leftC=CAPTURE_TIME-self.cap_blue_timer
                if leftC<0:leftC=0
                self.canvas.create_text(10,50, text=f"BlueCap => {int(leftC)}s", anchor="nw", fill="blue", font=("Helvetica",12,"bold"))

        if self.victory_label:
            from Engineering.consts import WIDTH, HEIGHT
            # petite animation de clignotement
            alpha=1.0
            if (self.victory_phase<30):
                alpha=1.0
            else:
                alpha=0.3
            # on peut changer la couleur ou la taille
            color = f"#{int(alpha*255):02x}{int(alpha*255):02x}00"
            self.canvas.create_text(
                WIDTH//2, HEIGHT//2,
                text=self.victory_label,
                fill=color,
                font=("Helvetica",28,"bold"),
                anchor="center"
            )

        if self.dragging:
            sx,sy=self.drag_start
            ex,ey=self.drag_end
            self.canvas.create_rectangle(sx,sy,ex,ey, outline="yellow", width=2, dash=(4,4))

    def draw_unit(self, u):
        from Engineering.consts import UNIT_RADIUS, COLOR_RED, COLOR_BLUE, COLOR_HIGHLIGHT, TILE_SIZE
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
        if u.team=="blue" and u.dest_tile:
            tx,ty=u.dest_tile
            px=tx*TILE_SIZE+TILE_SIZE/2
            py=ty*TILE_SIZE+TILE_SIZE/2
            self.draw_arrow(u.x,u.y, px,py)

    def draw_star(self,cx,cy,size,color):
        import math
        self.canvas.create_rectangle(cx-size-5, cy-size-5, cx+size+5, cy+size+5, outline="black", width=2)
        points=[]
        nb=5
        for i in range(nb*2):
            angle=i*math.pi/nb
            r=size if i%2==0 else size/2
            px=cx+math.cos(angle)*r
            py=cy+math.sin(angle)*r
            points.append((px,py))
        fl=[]
        for (px,py) in points:
            fl.append(px)
            fl.append(py)
        self.canvas.create_polygon(fl, fill=color, outline=color)

    def draw_arrow(self,x0,y0,x1,y1):
        self.canvas.create_line(x0,y0,x1,y1, fill="black", width=2, smooth=True)
        import math
        angle=math.atan2(y1-y0,x1-x0)
        arr_len=10
        arr_angle=math.radians(20)
        xA=x1-arr_len*math.cos(angle-arr_angle)
        yA=y1-arr_len*math.sin(angle-arr_angle)
        xB=x1-arr_len*math.cos(angle+arr_angle)
        yB=y1-arr_len*math.sin(angle+arr_angle)
        self.canvas.create_polygon([(x1,y1),(xA,yA),(xB,yB)], fill="black")

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
            self.handle_click(event.x,event.y)
        else:
            x1,x2=sorted([sx,ex])
            y1,y2=sorted([sy,ey])
            if not self.shift_held:
                self.clear_selection()
            for u in self.blue_units:
                if x1<=u.x<=x2 and y1<=u.y<=y2:
                    u.is_selected=True
                    if u not in self.selected_units:
                        self.selected_units.append(u)

    def handle_click(self,mx,my):
        import math
        from Engineering.consts import UNIT_RADIUS
        clicked_unit=None
        for u in self.all_units:
            if math.hypot(u.x-mx, u.y-my)<=UNIT_RADIUS+2:
                clicked_unit=u
                break
        if clicked_unit:
            if not self.shift_held:
                self.clear_selection()
            if clicked_unit.team=="blue":
                clicked_unit.is_selected=True
                if clicked_unit not in self.selected_units:
                    self.selected_units.append(clicked_unit)
            else:
                if self.selected_units:
                    for su in self.selected_units:
                        su.target_enemy=clicked_unit
                        su.path=[]
                        su.dest_tile=None
        else:
            from Engineering.pathfinding import find_path_bfs
            tx=mx//TILE_SIZE
            ty=my//TILE_SIZE
            if self.selected_units:
                for su in self.selected_units:
                    su.target_enemy=None
                    sx,sy=su.get_tile_pos()
                    su.path=find_path_bfs(self.grid,(sx,sy),(tx,ty))
                    su.dest_tile=(tx,ty)

    def on_right_click(self,event):
        self.clear_selection()

    def clear_selection(self):
        for u in self.selected_units:
            u.is_selected=False
        self.selected_units=[]

    def cross_front(self, unit):
        old_side = getattr(unit,"front_side",None)
        new_side = check_side(self.front_points, unit.x, unit.y)
        unit.front_side=new_side
        if old_side and old_side!=new_side:
            return True
        return False

    def is_unit_in_enemy_zone(self, unit):
        side=check_side(self.front_points, unit.x, unit.y)
        if unit.team=="blue":
            return (side=="left")
        else:
            return (side=="right")

    def update_capital_capture(self, unit):
        import math
        from Engineering.consts import UNIT_RADIUS, FPS, TILE_SIZE
        if unit.team=="blue":
            rx,ry=self.red_cap
            rpx=rx*TILE_SIZE+TILE_SIZE/2
            rpy=ry*TILE_SIZE+TILE_SIZE/2
            d=math.hypot(unit.x-rpx, unit.y-rpy)
            if d<UNIT_RADIUS+5:
                if not self.is_enemy_on_capital("red"):
                    unit.cap_capture_time+=1.0/FPS
                    if unit.cap_capture_time>self.cap_red_timer:
                        self.cap_red_timer=unit.cap_capture_time
                else:
                    unit.cap_capture_time=0
            else:
                unit.cap_capture_time=0
        else:
            bx,by=self.blue_cap
            bpx=bx*TILE_SIZE+TILE_SIZE/2
            bpy=by*TILE_SIZE+TILE_SIZE/2
            d=math.hypot(unit.x-bpx, unit.y-bpy)
            if d<UNIT_RADIUS+5:
                if not self.is_enemy_on_capital("blue"):
                    unit.cap_capture_time+=1.0/FPS
                    if unit.cap_capture_time>self.cap_blue_timer:
                        self.cap_blue_timer=unit.cap_capture_time
                else:
                    unit.cap_capture_time=0
            else:
                unit.cap_capture_time=0

    def is_enemy_on_capital(self, cap_team):
        import math
        from Engineering.consts import UNIT_RADIUS, TILE_SIZE
        if cap_team=="red":
            rx,ry=self.red_cap
            rpx=rx*TILE_SIZE+TILE_SIZE/2
            rpy=ry*TILE_SIZE+TILE_SIZE/2
            for u in self.red_units:
                if math.hypot(u.x-rpx, u.y-rpy)<UNIT_RADIUS+5:
                    return True
            return False
        else:
            bx,by=self.blue_cap
            bpx=bx*TILE_SIZE+TILE_SIZE/2
            bpy=by*TILE_SIZE+TILE_SIZE/2
            for u in self.blue_units:
                if math.hypot(u.x-bpx, u.y-bpy)<UNIT_RADIUS+5:
                    return True
            return False

    def check_victory(self):
        if not self.blue_units:
            self.show_victory_animation("Victoire Rouge (plus d'unités bleues)!")
            return
        if not self.red_units:
            self.show_victory_animation("Victoire Bleue (plus d'unités rouges)!")
            return
        if self.cap_red_timer>=CAPTURE_TIME:
            self.show_victory_animation("Victoire Bleue (capitale rouge capturée)!")
            return
        if self.cap_blue_timer>=CAPTURE_TIME:
            self.show_victory_animation("Victoire Rouge (capitale bleue capturée)!")
            return

    def show_victory_animation(self, msg):
        self.victory_label = msg
        self.victory_mode  = True
        self.victory_phase = 0

    def stop_game(self):
        self.running=False
        self.root.quit()

def main():
    root=tk.Tk()
    game=HOI4FrontInvisibleGame(root)
    root.mainloop()

if __name__=="__main__":
    main()
