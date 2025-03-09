# Network settings
PORT = 5555
HOST = "localhost" # Will change later when server side gets made

# Game settings
SCREEN_WIDTH = 640 
SCREEN_HEIGHT = 360
FPS = 60

# Tile settings
TILE_SIZE = 16
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = -(SCREEN_HEIGHT // -TILE_SIZE)
DEFAULT_PLATFORM_COLOR = (120, 120, 120)

# World Settings
Y_GRAVITY = 1