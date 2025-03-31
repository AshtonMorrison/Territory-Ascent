# Network settings
PORT = 5555
HOST = "0.0.0.0"

# Game settings
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 360
FPS = 45

# Tile settings
TILE_SIZE = 16
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = -(SCREEN_HEIGHT // -TILE_SIZE)
DEFAULT_PLATFORM_COLOR = (120, 120, 120)

# World Settings
Y_GRAVITY = 60 / FPS 

# Font settings
FONT_NAME = "Segoe UI Symbol"
