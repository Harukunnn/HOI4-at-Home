# Engineering/front.py

import random
import math
from .consts import WIDTH, HEIGHT
from .pathfinding import distance

def generate_initial_front(num_points=25):
    """
    Crée une ligne de front verticale (x=WIDTH/2),
    de y=0 à y=HEIGHT, en 'num_points' segments.
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
    Quand une unité traverse, on insère localement
    1 ou 2 points autour (xC,yC), pour “courber” la ligne
    et simuler un mouvement du front.
    """
    if len(front_points) < 2:
        return front_points

    best_i = 0
    best_d = 999999
    for i, p in enumerate(front_points):
        d = distance(p[0], p[1], xC, yC)
        if d < best_d:
            best_d = d
            best_i = i

    dx = random.uniform(-20, 20)
    dy = random.uniform(-20, 20)
    newp = (xC + dx, yC + dy)
    front_points.insert(best_i, newp)

    if random.random() < 0.5:
        dx2 = random.uniform(-20, 20)
        dy2 = random.uniform(-20, 20)
        front_points.insert(best_i, (xC + dx2, yC + dy2))

    if len(front_points) > 50:
        idx = random.randint(len(front_points)//2, len(front_points)-1)
        front_points.pop(idx)

    return front_points

def update_front_line(front_points, units, dt=1.0, influence_radius=80, push_strength=0.1):
    """
    Fait évoluer la ligne de front au fil du temps,
    en “poussant” légèrement les points vers la position
    moyenne des unités proches, dans un rayon 'influence_radius'.
    dt ~ la durée (en s ou en fraction de frame) pour moduler le pas.

    push_strength ~ le facteur de poussée (0.1 = 10%)

    Idée simplifiée :
    - Pour chaque point du front, on regarde les unités
      à < influence_radius.
    - On calcule la moyenne (xU,yU) de ces unités
      et on rapproche le point du front d’un certain pourcentage
      (push_strength * dt) de la distance.
    - On peut aussi “lisser” la ligne in fine.
    """

    if len(front_points) < 2 or not units:
        return

    new_front = []
    for i, (fx, fy) in enumerate(front_points):
        # On cherche toutes les unités proches
        close_units = []
        for u in units:
            d = distance(fx, fy, u.x, u.y)
            if d < influence_radius:
                close_units.append(u)

        if not close_units:
            new_front.append((fx, fy))
            continue

        # On calcule la moyenne
        mx = sum(u.x for u in close_units) / len(close_units)
        my = sum(u.y for u in close_units) / len(close_units)

        # On rapproche (fx,fy) de (mx,my)
        dx = mx - fx
        dy = my - fy
        new_fx = fx + dx * push_strength * dt
        new_fy = fy + dy * push_strength * dt
        new_front.append((new_fx, new_fy))

    # Optionnel : on applique un “lissage final” de la ligne
    new_front = smooth_front(new_front, passes=1)

    # On remplace
    front_points[:] = new_front  # modifie in place

def smooth_front(points, passes=1):
    """
    Lissage simple : on remplace chaque point par la
    moyenne de lui + ses voisins (type "moving average").
    On peut répéter 'passes' fois.
    """
    if len(points) < 3:
        return points
    result = points
    for _ in range(passes):
        newpts = [result[0]]
        for i in range(1, len(result)-1):
            px = (result[i-1][0] + result[i][0] + result[i+1][0]) / 3
            py = (result[i-1][1] + result[i][1] + result[i+1][1]) / 3
            newpts.append((px, py))
        newpts.append(result[-1])
        result = newpts
    return result

def check_side(front_points, xU, yU):
    """
    Détermine si (xU,yU) est à 'gauche' ou 'droite' de la ligne.
    On fait l'astuce : on sépare la ligne en points au dessus/au dessous
    puis on interpole pour trouver midx => left si xU < midx else right
    """
    above = []
    below = []
    for p in front_points:
        if p[1] < yU:
            above.append(p)
        else:
            below.append(p)
    if not above or not below:
        return "left"
    pA = max(above, key=lambda pt: pt[1])
    pB = min(below, key=lambda pt: pt[1])
    dy = pB[1] - pA[1]
    if abs(dy) < 1e-6:
        midx = (pA[0] + pB[0]) / 2
    else:
        t = (yU - pA[1]) / dy
        midx = pA[0] + t * (pB[0] - pA[0])
    return "left" if xU < midx else "right"
