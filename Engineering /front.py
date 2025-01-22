# Engineering/front.py

import random
import math
from .consts import WIDTH, HEIGHT
from .pathfinding import distance

def generate_initial_front(num_points=25):
    """
    Crée une ligne de front initiale, verticale (x = WIDTH/2),
    allant de y=0 à y=HEIGHT, répartie en 'num_points' segments.
    """
    points = []
    for i in range(num_points):
        frac = i / (num_points - 1)
        x = WIDTH / 2
        y = frac * HEIGHT
        points.append((x, y))
    return points

def add_front_points_on_cross(front_points, xC, yC):
    """
    Ajoute localement 1 ou 2 points autour de (xC, yC)
    quand une unité traverse la ligne, pour courber la ligne de front.
    """
    if len(front_points) < 2:
        return front_points

    best_i = 0
    best_d = float('inf')
    for i, (fx, fy) in enumerate(front_points):
        d = distance(fx, fy, xC, yC)
        if d < best_d:
            best_d = d
            best_i = i

    dx = random.uniform(-20, 20)
    dy = random.uniform(-20, 20)
    newp = (xC + dx, yC + dy)
    front_points.insert(best_i, newp)

    # On ajoute éventuellement un second point pour plus de variété
    if random.random() < 0.5:
        dx2 = random.uniform(-20, 20)
        dy2 = random.uniform(-20, 20)
        front_points.insert(best_i, (xC + dx2, yC + dy2))

    # On limite la taille de la liste
    if len(front_points) > 50:
        idx = random.randint(len(front_points)//2, len(front_points)-1)
        front_points.pop(idx)

    return front_points

def update_front_line(
    front_points, units, dt=1.0,
    influence_radius=80,
    push_strength=0.1,
    smooth_passes=1,
    beautify=False
):
    """
    Fait évoluer la ligne de front dans le temps, en “poussant”
    chaque point vers la moyenne des unités proches (< influence_radius).

    Paramètres:
    - dt : delta time (ex: 1.0/FPS ou 1.0)
    - influence_radius : distance max (pixels) d’influence d’une unité
    - push_strength : intensité (ex: 0.1 => 10% du chemin en 1 update)
    - smooth_passes : nb de passes de lissage final
    - beautify : si True, applique un spline Catmull-Rom pour un rendu plus doux

    Cette fonction ne requiert AUCUNE modification dans d’autres scripts.
    """
    if len(front_points) < 2 or not units:
        return

    new_front = []
    # Pour optimiser, on évite la racine carrée en comparant dist^2 < radius^2
    rad2 = influence_radius**2

    for (fx, fy) in front_points:
        close_units = []
        for u in units:
            dx = (u.x - fx)
            dy = (u.y - fy)
            dist2 = dx*dx + dy*dy
            if dist2 < rad2:
                close_units.append(u)

        if not close_units:
            new_front.append((fx, fy))
            continue

        # moyenne (mx, my)
        sx = sum(u.x for u in close_units)
        sy = sum(u.y for u in close_units)
        n = len(close_units)
        mx = sx / n
        my = sy / n

        dx = mx - fx
        dy = my - fy
        new_fx = fx + dx * push_strength * dt
        new_fy = fy + dy * push_strength * dt
        new_front.append((new_fx, new_fy))

    # Lissage local
    new_front = smooth_front(new_front, passes=smooth_passes)

    # Optionnel : Catmull-Rom pour un rendu plus fluide
    if beautify and len(new_front) >= 4:
        new_front = catmull_rom_spline(new_front, steps=6)

    front_points[:] = new_front

def smooth_front(points, passes=1):
    """
    Lissage local par moyenne glissante: chaque point devient
    la moyenne de lui-même + ses 2 voisins.
    """
    if len(points) < 3:
        return points

    result = points[:]
    for _ in range(passes):
        tmp = [result[0]]  # le premier reste tel quel
        for i in range(1, len(result) - 1):
            px = (result[i-1][0] + result[i][0] + result[i+1][0]) / 3
            py = (result[i-1][1] + result[i][1] + result[i+1][1]) / 3
            tmp.append((px, py))
        tmp.append(result[-1])  # le dernier reste
        result = tmp
    return result

def catmull_rom_spline(pts, steps=10):
    """
    Génère une liste de points en Catmull-Rom Spline, 
    subdivisant chaque segment 'steps' fois.
    """
    if len(pts) < 4:
        return pts

    new_pts = []
    # On parcourt tous les segments
    for i in range(len(pts) - 1):
        p0 = pts[max(i-1, 0)]
        p1 = pts[i]
        p2 = pts[i+1]
        p3 = pts[min(i+2, len(pts)-1)]
        for t in range(steps):
            tau = t / float(steps)
            x, y = catmull_rom_position(p0, p1, p2, p3, tau)
            new_pts.append((x, y))
    # On ajoute le dernier point
    new_pts.append(pts[-1])
    return new_pts

def catmull_rom_position(p0, p1, p2, p3, t, alpha=0.5):
    """
    Retourne la position (x, y) sur la Catmull-Rom Spline
    entre p1 et p2, pour t in [0..1].
    alpha=0.5 => centripetal spline plus stable.
    """
    x0, y0 = p0
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    t2 = t*t
    t3 = t2*t

    # coefficients standard
    a0 = -0.5*t3 + t2 - 0.5*t
    a1 = 1.5*t3 - 2.5*t2 + 1.0
    a2 = -1.5*t3 + 2.0*t2 + 0.5*t
    a3 = 0.5*t3 - 0.5*t2

    x = a0*x0 + a1*x1 + a2*x2 + a3*x3
    y = a0*y0 + a1*y1 + a2*y2 + a3*y3
    return (x, y)

def check_side(front_points, xU, yU):
    """
    Détermine si (xU,yU) est à gauche ou à droite du front.
    On divise front_points en deux: 'above' (y < yU) et 'below' (y >= yU).
    On prend pA = max(above, y) et pB=min(below, y),
    on interpole la coord x midx => si xU < midx => "left" sinon "right".
    """
    above = []
    below = []
    for (fx, fy) in front_points:
        if fy < yU:
            above.append((fx, fy))
        else:
            below.append((fx, fy))

    if not above or not below:
        return "left"

    pA = max(above, key=lambda pt: pt[1])  # plus grand y
    pB = min(below, key=lambda pt: pt[1])  # plus petit y
    dy = pB[1] - pA[1]
    if abs(dy) < 1e-9:
        midx = (pA[0] + pB[0]) / 2
    else:
        t = (yU - pA[1]) / dy
        midx = pA[0] + t*(pB[0] - pA[0])

    return "left" if xU < midx else "right"
