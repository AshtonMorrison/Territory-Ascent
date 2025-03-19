import pygame
from shared import constants
import math
import os

class Player(pygame.sprite.Sprite):
    def __init__(self, color, x, y, width, height):
        super().__init__()

        # Load image
        self.color = color
        self.image = pygame.Surface([width, height])
        self.image.fill(color)

        # Position
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)

        # Jumping
        self.in_air = False
        self.dragging = False
        self.drag_start_pos = None
        self.drag_vector = pygame.math.Vector2(0, 0)
        

    def update(self):
        pass

    @staticmethod
    def _load_and_scale_image(path, width, height):
        try:
            image = pygame.image.load(os.path.join("client", path))
            return pygame.transform.scale(image, (width, height))
        except (pygame.error, FileNotFoundError):
            return None