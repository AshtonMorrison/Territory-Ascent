import pygame
import os


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, tile_type):
        super().__init__()

        # Load assets
        self.assets = {
            "air": self._load_and_scale_image("assets/air.png", width, height),
            "ground": self._load_and_scale_image("assets/ground.png", width, height),
            "platform": self._load_and_scale_image(
                "assets/platform.png", width, height
            ),
        }

        # Fallback colors if assets not found
        self.tile_colors = {
            "air": (255, 255, 255),  # White
            "ground": (139, 69, 19),  # Brown
            "platform": (100, 100, 100),  # Gray
        }

        self.tile_type = tile_type

        # Try to use asset, fallback to colored rectangle
        self.image = self.assets.get(tile_type)
        if self.image is None:
            self.image = pygame.Surface([width, height])
            self.image.fill(self.tile_colors[tile_type])

        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    @staticmethod
    def _load_and_scale_image(path, width, height):
        try:
            image = pygame.image.load(os.path.join("client", path))
            return pygame.transform.scale(image, (width, height))
        except (pygame.error, FileNotFoundError):
            return None
