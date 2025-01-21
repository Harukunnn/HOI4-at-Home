# Engineering/front.py

import random
import math
from .consts import WIDTH, HEIGHT
from .pathfinding import distance

def generate_initial_front(num_points=25):
    """
    Front initial droit : x=WIDTH/2, y=0..HEIGHT
    """
    points=[]
    for i in range(num_points):
        frac=i/(num_points-1)
        x=WIDTH/2
        y=frac*HEIGHT
        points.append((x,y))
    return points

def add_front_points_on_cross(front_points, xC, yC):
    if len(front_points)<2:
        return front_points
    best_i=0
    best_d=999999
    for i,p in enumerate(front_points):
        d=distance(xC,yC, p[0],p[1])
        if d<best_d:
            best_d=d
            best_i=i
    dx = random.uniform(-20,20)
    dy = random.uniform(-20,20)
    newp=(xC+dx,yC+dy)
    front_points.insert(best_i,newp)
    if random.random()<0.5:
        dx2 = random.uniform(-20,20)
        dy2 = random.uniform(-20,20)
        front_points.insert(best_i,(xC+dx2,yC+dy2))
    if len(front_points)>50:
        idx = random.randint(len(front_points)//2, len(front_points)-1)
        front_points.pop(idx)
    return front_points

def check_side(front_points, xU, yU):
    """
    Renvoie 'left' ou 'right' 
    en comparant l'unité (xU,yU) à la polyligne front_points.
    On fait la même astuce "above/below" qu'avant.
    """
    above=[]
    below=[]
    for p in front_points:
        if p[1]<yU:
            above.append(p)
        else:
            below.append(p)
    if not above or not below:
        return "left"
    pA = max(above, key=lambda pt: pt[1])
    pB = min(below, key=lambda pt: pt[1])
    dy=pB[1]-pA[1]
    if abs(dy)<1e-6:
        midx=(pA[0]+pB[0])/2
    else:
        t=(yU-pA[1])/dy
        midx=pA[0]+t*(pB[0]-pA[0])
    return "left" if xU<midx else "right"

def distance(x1,y1,x2,y2):
    return math.hypot(x2-x1,y2-y1)

#
# Fin front.py

