import pygame
import math

########################
# Configuration globale
########################

WIDTH, HEIGHT = 800, 600
FPS = 30

# Couleurs
GREEN = (100, 170, 100)
RED   = (220,  20,  20)
BLUE  = ( 20,  20, 220)
BLACK = (  0,   0,   0)
YELLOW= (255, 215,   0)
GRAY  = (120, 120, 120)
DARK_GREEN = (  0, 100,   0)
LIGHT_BLUE = (  0, 150, 255)

# Rayons et tailles
UNIT_RADIUS = 10
STAR_SIZE = 15    # Taille "générale" pour dessiner l'étoile
SQUARE_SIZE = 10  # Taille pour les points de capture (carrés)

# Distances / logique
MOVE_SPEED = 2    # Vitesse de déplacement des unités
ENCIRCLED_TICK_LIMIT = 180  # Nombre de ticks avant destruction si unité encerclée (~6 secondes à 30 FPS)


##########################################
# Classes / Structures de données de base
##########################################

class Unit:
    """
    Représente une unité sur la carte.
    - x, y : position
    - team : "red" ou "blue"
    - is_selected : booléen pour savoir si l'unité est sélectionnée
    - path : liste de tuples (x, y) représentant le chemin à parcourir
    - blocked : True si l'unité est bloquée par une unité ennemie en face à face
    - encircled_ticks : compte combien de frames l’unité est considérée comme encerclée
    """
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.is_selected = False
        self.path = []
        self.blocked = False
        self.encircled_ticks = 0

    def draw(self, surface):
        color = RED if self.team == "red" else BLUE
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), UNIT_RADIUS)

        # Si l'unité est sélectionnée, on dessine un petit cercle de surbrillance
        if self.is_selected:
            pygame.draw.circle(surface, YELLOW, (int(self.x), int(self.y)), UNIT_RADIUS+2, 2)

    def update(self, units, terrain):
        """
        Met à jour la position de l’unité (suivant path),
        vérifie si elle est bloquée ou encerclée, etc.
        """
        # Si bloquée (face à face), on ne bouge pas
        if self.blocked:
            return

        # Avance vers le prochain point du path si disponible
        if self.path:
            target_x, target_y = self.path[0]
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)
            if dist > MOVE_SPEED:
                # Mouvement partiel
                self.x += (dx / dist) * MOVE_SPEED
                self.y += (dy / dist) * MOVE_SPEED
            else:
                # On est arrivé sur ce segment, on le retire
                self.x, self.y = target_x, target_y
                self.path.pop(0)

        # Check collisions (face-à-face) avec unités ennemies
        for u in units:
            if u != self and u.team != self.team:
                if distance(self.x, self.y, u.x, u.y) < UNIT_RADIUS * 2:
                    # Face à face
                    self.blocked = True
                    u.blocked = True

        # Vérification d'encerclement simplifiée :
        # On considère qu'une unité est "encerclée" si elle se trouve
        # dans le territoire adverse (au-delà de la ligne de front)
        # ET qu'aucun chemin ne la relie à sa zone d'origine.
        # --> Ici, on va simplement checker si l'unité est de l'autre côté
        #     d'une ligne noire, on incrémente un compteur. 
        #     Si le compteur dépasse ENCIRCLED_TICK_LIMIT, l'unité meurt.
        if is_unit_in_enemy_territory(self, terrain):
            self.encircled_ticks += 1
        else:
            self.encircled_ticks = 0


def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


################################
# Fonctions de dessin du décor
################################

def draw_map(surface):
    """
    Dessine le décor "style HOI4 simplifié" : fond vert, quelques montagnes,
    rivières bleues, frontière noire, etc.
    """
    surface.fill(GREEN)

    # Dessiner quelques "montagnes" (amas gris)
    mountains = [
        (200, 100), (500, 80), (600, 300), (300, 400)
    ]
    for mx, my in mountains:
        pygame.draw.circle(surface, GRAY, (mx, my), 40)

    # Dessiner quelques "forêts" (zones vert foncé)
    forests = [
        (120, 250), (220, 320), (450, 200), (650, 400)
    ]
    for fx, fy in forests:
        pygame.draw.circle(surface, DARK_GREEN, (fx, fy), 50)

    # Dessiner des rivières (lignes bleues)
    rivers = [
        [(50,50), (100,100), (150,150), (200,200)],
        [(700,100), (650,150), (600,200), (550,300), (500,350)]
    ]
    for river_points in rivers:
        pygame.draw.lines(surface, LIGHT_BLUE, False, river_points, 4)

    # Dessiner la ligne de front (frontière) en noir
    # Ici, on suppose juste une grande ligne courbe
    front_line_points = [
        (400, 0), (390, 50), (380, 100), (370, 150),
        (360, 200), (350, 250), (340, 300), (330, 350),
        (320, 400), (310, 450), (300, 500), (290, 550), (280, 600)
    ]
    pygame.draw.lines(surface, BLACK, False, front_line_points, 5)


def draw_capture_points(surface, captures, capital_red, capital_blue):
    """
    Dessine les carrés jaunes (captures) et les étoiles (capitales).
    """
    # Points de capture (carrés jaunes)
    for (cx, cy) in captures:
        pygame.draw.rect(surface, YELLOW, (cx - SQUARE_SIZE//2, 
                                           cy - SQUARE_SIZE//2, 
                                           SQUARE_SIZE, 
                                           SQUARE_SIZE))

    # Capitales (étoiles)
    draw_star(surface, capital_red[0], capital_red[1], STAR_SIZE, YELLOW)
    draw_star(surface, capital_blue[0], capital_blue[1], STAR_SIZE, YELLOW)


def draw_star(surface, x, y, size, color):
    """
    Dessine une étoile à 5 branches autour du centre (x, y).
    """
    points = []
    num_branches = 5
    for i in range(num_branches * 2):
        angle = i * math.pi / num_branches
        radius = size if i % 2 == 0 else size / 2
        px = x + math.cos(angle) * radius
        py = y + math.sin(angle) * radius
        points.append((px, py))
    pygame.draw.polygon(surface, color, points)


##################################
# Fonctions de logique de terrain
##################################

def is_unit_in_enemy_territory(unit, terrain):
    """
    Détection simplifiée de territoire : 
    - On prend la ligne de front (la liste front_line_points) 
      et on détermine de quel côté de la ligne se trouve l'unité.
    - Si l'unité est du côté opposé à son équipe, on considère 
      qu'elle est en territoire ennemi.
    """
    front_line_points = terrain["front_line_points"]
    # On va compter combien de segments de la ligne 
    # sont "coupés" par un rayon horizontal partant de l'unité.
    # S’il est pair vs impair, on peut déduire de quel côté on est (technique du "ray casting").

    # Pour simplifier énormément, on va juste regarder la position X de l'unité
    # par rapport à la "moyenne" X de la ligne.  
    # Dans l’exemple, on suppose que la ligne descend verticalement 
    # autour de x=350 à x=400. 
    # -> si l’unité bleue se trouve > moy_x, on dit "en territoire rouge".
    #    si l’unité rouge se trouve < moy_x, on dit "en territoire bleu".
    xs = [p[0] for p in front_line_points]
    moy_x = sum(xs) / len(xs)

    if unit.team == "blue" and unit.x > moy_x:
        return True
    if unit.team == "red" and unit.x < moy_x:
        return True
    return False


##################
# Initialisation
##################

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Mini HOI4-like")
    clock = pygame.time.Clock()

    # Créons quelques unités pour chaque équipe
    # (positions de départ approximatives)
    blue_units = [
        Unit(100, 100, "blue"),
        Unit(130, 200, "blue"),
        Unit(150, 300, "blue")
    ]
    red_units = [
        Unit(700, 100, "red"),
        Unit(680, 200, "red"),
        Unit(650, 300, "red")
    ]
    all_units = blue_units + red_units

    # Points de capture (en jaune, carrés)
    capture_points = [
        (200, 500),
        (600, 150)
    ]

    # Capitales (étoiles)
    capital_red = (700, 500)
    capital_blue = (100, 500)

    # Stockons les données du "terrain" (rivières, frontière, etc.)
    front_line_points = [
        (400, 0), (390, 50), (380, 100), (370, 150),
        (360, 200), (350, 250), (340, 300), (330, 350),
        (320, 400), (310, 450), (300, 500), (290, 550), (280, 600)
    ]
    terrain = {
        "front_line_points": front_line_points
    }

    selected_unit = None
    running = True

    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic gauche
                    mx, my = event.pos

                    # Vérifie si on clique sur une unité pour la sélectionner / désélectionner
                    clicked_unit = None
                    for u in all_units:
                        if distance(mx, my, u.x, u.y) < UNIT_RADIUS:
                            clicked_unit = u
                            break
                    
                    if clicked_unit:
                        # Sélectionne l'unité cliquée, désélectionne les autres
                        for u in all_units:
                            u.is_selected = False
                        clicked_unit.is_selected = True
                        selected_unit = clicked_unit
                    else:
                        # Si on a déjà une unité sélectionnée, on lui assigne un chemin vers (mx, my)
                        if selected_unit:
                            # Ici, on simplifie : on lui donne un seul segment de chemin
                            selected_unit.path = [(mx, my)]

                if event.button == 3:  # Clic droit => annuler la sélection
                    if selected_unit:
                        selected_unit.is_selected = False
                    selected_unit = None

        # Mise à jour des unités
        for u in all_units:
            u.update(all_units, terrain)

        # Suppression des unités mortes (encerclées trop longtemps)
        for u in all_units:
            if u.encircled_ticks > ENCIRCLED_TICK_LIMIT:
                # L'unité meurt
                all_units.remove(u)

        # Vérification des conditions de victoire :
        # 1) Si toutes les unités d'une équipe sont mortes -> l'autre équipe gagne
        blue_alive = any(u for u in all_units if u.team == "blue")
        red_alive = any(u for u in all_units if u.team == "red")

        if not blue_alive:
            print("Victoire de l'équipe Rouge (toutes les unités bleues sont détruites)!")
            running = False
        if not red_alive:
            print("Victoire de l'équipe Bleue (toutes les unités rouges sont détruites)!")
            running = False

        # 2) Si la capitale d'une équipe est "occupée" par une unité ennemie
        # (c'est-à-dire qu'une unité ennemie est assez proche de la capitale)
        for u in all_units:
            if u.team == "blue":
                if distance(u.x, u.y, capital_red[0], capital_red[1]) < 30:
                    print("Victoire de l'équipe Bleue (capitale rouge capturée)!")
                    running = False
            else:
                # Équipe rouge
                if distance(u.x, u.y, capital_blue[0], capital_blue[1]) < 30:
                    print("Victoire de l'équipe Rouge (capitale bleue capturée)!")
                    running = False

        # Dessin
        draw_map(screen)
        draw_capture_points(screen, capture_points, capital_red, capital_blue)

        # Dessiner les unités
        for u in all_units:
            u.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
