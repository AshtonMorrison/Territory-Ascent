import pygame
import os


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
            self.image = self._load_and_scale_image("assets/platform.png", width, height)
            if self.image is None:
                self.image = pygame.Surface([width, height])
                self.image.fill(self.tile_colors["platform"])
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
