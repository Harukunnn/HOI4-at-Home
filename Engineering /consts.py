# Engineering/consts.py

WIDTH, HEIGHT = 800, 600
TILE_SIZE = 10

NX = WIDTH // TILE_SIZE
NY = HEIGHT // TILE_SIZE

FPS = 30

UNIT_RADIUS = 6
MOVE_SPEED = 0.1
WATER_SLOW_FACTOR = 0.5
ENCIRCLED_TICK_LIMIT = 300
STAR_SIZE = 6

INITIAL_DELAY = 20.0
CAPTURE_TIME = 10.0

T_DEEP_WATER = 0
T_RIVER      = 1
T_PLAIN      = 2
T_FOREST     = 3
T_MOUNTAIN   = 4
T_BRIDGE     = 5
T_LAKE       = 6

COLOR_DEEP_WATER = "#3B6FD2"
COLOR_RIVER      = "#0096FF"
COLOR_BRIDGE     = "#987B5B"
COLOR_PLAIN      = "#85C57A"
COLOR_FOREST     = "#3D8B37"
COLOR_MOUNTAIN   = "#AAAAAA"
COLOR_LAKE       = "#4C8BC8"

COLOR_RED        = "#DC1414"
COLOR_BLUE       = "#1414DC"
COLOR_HIGHLIGHT  = "yellow"

MIN_TROOPS_PER_TEAM = 10

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
    if t == T_LAKE:
        return COLOR_LAKE
    return "#000000"
