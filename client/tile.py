import pygame
import os
from shared import constants


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, image_integer, main_group, sub_group=""):
        super().__init__()

        # Fallback colors if assets not found
        self.tile_colors = {
            "ground": (139, 69, 19),  # Brown
            "platform": (100, 100, 100),  # Gray
        }

        # Load image and add to group
        if image_integer == 1:
            self.image = self._load_and_scale_image("assets/ground.png", width, height)
            if self.image is None:
                self.image = pygame.Surface([width, height])
                self.image.fill(self.tile_colors["ground"])
            sub_group.add(self)

        if image_integer == 2:
            # Create platform with default color and dark border
            self.image = pygame.Surface([width, height])
            platform_color = constants.DEFAULT_PLATFORM_COLOR  # Use default platform color
            border_color = (platform_color[0] - 30, platform_color[1] - 30, platform_color[2] - 30)

            self.image.fill(border_color)
            pygame.draw.rect(self.image, platform_color, [0, height // 2, width, height // 2])

            sub_group.add(self)

        main_group.add(self)

        # Get rects and positions
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    @staticmethod
    def _load_and_scale_image(path, width, height):
        try:
            image = pygame.image.load(os.path.join("client", path))
            return pygame.transform.scale(image, (width, height))
        except (pygame.error, FileNotFoundError):
            return None
