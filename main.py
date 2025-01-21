# main.py

import tkinter as tk
import time
import random

from Engineering.consts import (
    WIDTH, HEIGHT, TILE_SIZE, NX, NY,
    FPS, INITIAL_DELAY, CAPTURE_TIME,
    T_PLAIN, UNIT_RADIUS, STAR_SIZE,
    COLOR_BLUE, COLOR_RED, COLOR_HIGHLIGHT,
    ENCIRCLED_TICK_LIMIT, T_MOUNTAIN, T_LAKE, T_RIVER
)
from Engineering.generation import generate_map
from Engineering.pathfinding import in_bounds
from Engineering.front import generate_initial_front, add_front_points_on_cross, check_side
# => on n'importe plus BFS si on n'en a plus besoin
from Engineering.units import Unit, AI, distance
from collections import deque

def compute_team_zone(grid, cap, forbidden):
    (cx, cy)=cap
    if not in_bounds(cx, cy):
        return set()
    visited=set()
    visited.add((cx, cy))
    q=deque()
    q.append((cx, cy))
    while q:
        x,y=q.popleft()
        for (dx,dy) in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx_=x+dx
            ny_=y+dy
            if in_bounds(nx_, ny_):
                if (nx_,ny_) not in visited:
                    if (nx_,ny_) not in forbidden:
                        visited.add((nx_,ny_))
                        q.append((nx_,ny_))
    return visited

def forbidden_mountain_lake_river(grid):
    forb=set()
    ny=len(grid)
    nx=len(grid[0])
    for y in range(ny):
        for x in range(nx):
            if grid[y][x] in (T_MOUNTAIN,T_LAKE,T_RIVER):
                forb.add((x,y))
    return forb

class HOI4FrontInvisibleGame:
    def __init__(self, root):
        self.root=root
        self.root.title("HOI4 - Everyone moves direct line, capture capital fix")

        self.top_frame=tk.Frame(self.root, bg="#444444")
        self.top_frame.pack(side="top", fill="x")

        quit_btn=tk.Button(self.top_frame, text="Quitter", command=self.quit_game, fg="white", bg="#AA0000")
        quit_btn.pack(side="left", padx=5, pady=2)

        self.info_label=tk.Label(self.top_frame, text="HOI4 direct-line", fg="white", bg="#444444", font=("Arial",12,"bold"))
        self.info_label.pack(side="left", padx=5)

        self.canvas=tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="white")
        self.canvas.pack(side="top", fill="both", expand=True)

        self.canvas.focus_set()
        self.canvas.bind("<Escape>", lambda e: self.quit_game())

        self.shift_held=False
        self.canvas.bind("<KeyPress-Shift_L>", lambda e: self.set_shift(True))
        self.canvas.bind("<KeyRelease-Shift_L>", lambda e: self.set_shift(False))

        self.grid=generate_map(NX,NY)

        self.blue_cap=(3, NY//2)
        self.red_cap=(NX-4, NY//2)
        self.grid[self.blue_cap[1]][self.blue_cap[0]]=T_PLAIN
        self.grid[self.red_cap[1]][self.red_cap[0]]=T_PLAIN

        self.blue_units=[]
        self.red_units=[]
        self.create_initial_units("blue", 10)
        self.create_initial_units("red", 10)

        self.all_units=self.blue_units+self.red_units
        self.ai_red=AI("red")

        self.running=True
        self.frame_count=0
        self.selected_units=[]
        self.dragging=False
        self.drag_start=(0,0)
        self.drag_end=(0,0)
        self.victory_label=None

        self.start_time=time.time()
        self.game_started=False
        self.play_start_time=0

        self.front_points=generate_initial_front(num_points=25)

        self.cap_red_timer=0.0
        self.cap_blue_timer=0.0

        # Phase initial
        self.placement_phase=True
        self.blue_zone=compute_team_zone(self.grid, self.blue_cap, forbidden_mountain_lake_river(self.grid))
        self.red_zone = compute_team_zone(self.grid, self.red_cap,  forbidden_mountain_lake_river(self.grid))

        self.ai_place_red_units()

        self.canvas.bind("<Button-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)
        self.canvas.bind("<Button-3>", self.on_right_click)

        self.game_loop()

    def update_capital_capture(self, unit):
        import math
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

    def is_unit_in_enemy_zone(self, unit):
        side=check_side(self.front_points, unit.x, unit.y)
        if unit.team=="blue":
            return (side=="left")
        else:
            return (side=="right")

    def create_initial_units(self, team, number):
        cx,cy = (self.blue_cap if team=="blue" else self.red_cap)
        for _ in range(number):
            px=cx*TILE_SIZE+TILE_SIZE/2
            py=cy*TILE_SIZE+TILE_SIZE/2
            u=Unit(px,py,team)
            if team=="blue":
                self.blue_units.append(u)
            else:
                self.red_units.append(u)

    def set_shift(self,val):
        self.shift_held=val

    def quit_game(self):
        self.running=False
        self.root.quit()

    def ai_place_red_units(self):
        if not self.red_zone or not self.red_units:
            return
        bx=sum([u.x for u in self.blue_units])/len(self.blue_units)
        tile_bx=int(bx//TILE_SIZE)
        zone_list=list(self.red_zone)
        if tile_bx<NX//2:
            zone_list.sort(key=lambda p: p[0], reverse=True)
        else:
            zone_list.sort(key=lambda p: p[0])
        i=0
        for u in self.red_units:
            if i<len(zone_list):
                tx,ty=zone_list[i]
                i+=1
                u.x=tx*TILE_SIZE+TILE_SIZE/2
                u.y=ty*TILE_SIZE+TILE_SIZE/2

    def game_loop(self):
        if not self.running:
            return
        self.frame_count+=1
        now=time.time()
        dt=now-self.start_time
        if dt>=INITIAL_DELAY and self.placement_phase:
            self.placement_phase=False
            self.game_started=True
            self.play_start_time=time.time()

        movement_allowed=(not self.placement_phase)

        if self.game_started:
            self.ai_red.update(self, movement_allowed)

        self.resolve_combat()
        for u in self.all_units:
            u.update(self, self.all_units, self.grid, movement_allowed)

        dead=[]
        for u in self.all_units:
            if u.encircled_ticks>ENCIRCLED_TICK_LIMIT:
                dead.append(u)
            if u.hp<=0:
                dead.append(u)
        for du in dead:
            if du in self.all_units:
                self.all_units.remove(du)
                if du in self.red_units:
                    self.red_units.remove(du)
                else:
                    self.blue_units.remove(du)
                if du in self.selected_units:
                    self.selected_units.remove(du)

        self.check_victory()
        self.draw()
        if self.running:
            self.root.after(int(1000/FPS), self.game_loop)

    def resolve_combat(self):
        ATTACK_RANGE=40
        for u in self.all_units:
            enemy_count=0
            ally_count=0
            for v in self.all_units:
                if v is not u:
                    d=distance(u.x,u.y,v.x,v.y)
                    if d<ATTACK_RANGE:
                        if v.team!=u.team:
                            enemy_count+=1
                        else:
                            ally_count+=1
            if enemy_count>ally_count and enemy_count>0:
                dmg=5
                if u.encircled_ticks>0:
                    dmg=10
                u.attack_tick=dmg

    def draw(self):
        self.canvas.delete("all")
        from Engineering.consts import tile_color
        for y in range(NY):
            for x in range(NX):
                c=tile_color(self.grid[y][x])
                self.canvas.create_rectangle(
                    x*TILE_SIZE,y*TILE_SIZE,
                    (x+1)*TILE_SIZE,(y+1)*TILE_SIZE,
                    fill=c, outline=""
                )
        rpx=self.red_cap[0]*TILE_SIZE+TILE_SIZE/2
        rpy=self.red_cap[1]*TILE_SIZE+TILE_SIZE/2
        bpx=self.blue_cap[0]*TILE_SIZE+TILE_SIZE/2
        bpy=self.blue_cap[1]*TILE_SIZE+TILE_SIZE/2
        self.draw_star(rpx,rpy,STAR_SIZE,COLOR_RED)
        self.draw_star(bpx,bpy,STAR_SIZE,COLOR_BLUE)

        if len(self.front_points)>1:
            coords=[]
            for p in self.front_points:
                coords.append(p[0])
                coords.append(p[1])
            self.canvas.create_line(coords, fill="black", width=6, smooth=True)

        for u in self.all_units:
            self.draw_unit(u)

        self.canvas.create_rectangle(0,0,190,80, fill="#222222", outline="#666666", width=2)
        if self.placement_phase:
            left=INITIAL_DELAY-(time.time()-self.start_time)
            if left<0:left=0
            txt=f"Placement : {int(left)}s"
            self.canvas.create_text(10,10,text=txt,anchor="nw",fill="white",font=("Arial",14,"bold"))
        else:
            e=time.time()-self.play_start_time
            txt=f"Time : {int(e)}s"
            self.canvas.create_text(10,10,text=txt,anchor="nw",fill="white",font=("Arial",14,"bold"))

        if self.cap_red_timer>0:
            leftC=CAPTURE_TIME-self.cap_red_timer
            if leftC<0:leftC=0
            self.canvas.create_text(10,30,text=f"RedCap => {int(leftC)}s",anchor="nw",fill="red",font=("Arial",12,"bold"))
        if self.cap_blue_timer>0:
            leftC=CAPTURE_TIME-self.cap_blue_timer
            if leftC<0:leftC=0
            self.canvas.create_text(10,50,text=f"BlueCap => {int(leftC)}s",anchor="nw",fill="blue",font=("Arial",12,"bold"))

        if self.victory_label:
            self.canvas.create_text(
                WIDTH//2, HEIGHT//2,
                text=self.victory_label,
                fill="yellow",
                font=("Arial",24,"bold"),
                anchor="center"
            )

        if self.dragging:
            sx,sy=self.drag_start
            ex,ey=self.drag_end
            self.canvas.create_rectangle(sx,sy,ex,ey, outline="yellow", width=2, dash=(4,4))

    def draw_unit(self,u):
        color=(COLOR_BLUE if u.team=="blue" else COLOR_RED)
        self.canvas.create_oval(
            u.x-UNIT_RADIUS,u.y-UNIT_RADIUS,
            u.x+UNIT_RADIUS,u.y+UNIT_RADIUS,
            fill=color, outline=""
        )
        if u.is_selected:
            self.canvas.create_oval(
                u.x-(UNIT_RADIUS+2),u.y-(UNIT_RADIUS+2),
                u.x+(UNIT_RADIUS+2),u.y+(UNIT_RADIUS+2),
                outline=COLOR_HIGHLIGHT,width=2
            )
        # HP
        bar_w=30
        bar_h=4
        leftx=u.x-bar_w/2
        topy=u.y-UNIT_RADIUS-10
        ratio=u.hp/100
        if ratio<0: ratio=0
        self.canvas.create_rectangle(leftx,topy, leftx+bar_w, topy+bar_h, fill="#444444")
        self.canvas.create_rectangle(leftx,topy, leftx+bar_w*ratio, topy+bar_h, fill="green")

    def draw_star(self,cx,cy,size,color):
        import math
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
        self.canvas.create_rectangle(cx-size-5, cy-size-5, cx+size+5, cy+size+5, outline="black", width=2)
        self.canvas.create_polygon(fl, fill=color, outline=color)

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
        clicked_unit=None
        for u in self.all_units:
            d=math.hypot(u.x-mx, u.y-my)
            if d<=UNIT_RADIUS+2:
                clicked_unit=u
                break
        if clicked_unit:
            # cliquer sur un ennemi => attaquer
            if clicked_unit.team!="blue":
                if self.selected_units:
                    for su in self.selected_units:
                        su.target_enemy=clicked_unit
                        su.dest_px=None
                        su.dest_py=None
            else:
                # cliquer sur un allié => select
                if not self.shift_held:
                    self.clear_selection()
                clicked_unit.is_selected=True
                if clicked_unit not in self.selected_units:
                    self.selected_units.append(clicked_unit)
        else:
            tx=mx//TILE_SIZE
            ty=my//TILE_SIZE
            if self.placement_phase:
                if (tx,ty) in self.blue_zone:
                    for su in self.selected_units:
                        su.x=tx*TILE_SIZE+TILE_SIZE/2
                        su.y=ty*TILE_SIZE+TILE_SIZE/2
            else:
                # On se déplace en ligne droite => on stock la dest en px
                px=tx*TILE_SIZE+TILE_SIZE/2
                py=ty*TILE_SIZE+TILE_SIZE/2
                for su in self.selected_units:
                    su.target_enemy=None
                    su.dest_px=px
                    su.dest_py=py

    def on_right_click(self,event):
        self.clear_selection()

    def clear_selection(self):
        for u in self.selected_units:
            u.is_selected=False
        self.selected_units=[]

    def check_victory(self):
        if not self.blue_units:
            self.victory_label="Victoire Rouge (plus de bleus)!"
        if not self.red_units:
            self.victory_label="Victoire Bleue (plus de rouges)!"
        if self.cap_red_timer>=CAPTURE_TIME:
            self.victory_label="Victoire Bleue (capitale rouge)!"
        if self.cap_blue_timer>=CAPTURE_TIME:
            self.victory_label="Victoire Rouge (capitale bleue)!"

    def stop_game(self):
        self.running=False
        self.root.quit()

def main():
    root=tk.Tk()
    game=HOI4FrontInvisibleGame(root)
    root.mainloop()

if __name__=="__main__":
    main()
