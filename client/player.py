import pygame
from shared import constants
import math
import os

class Player(pygame.sprite.Sprite):
    def __init__(self, color, x, y, width, height, in_air):
        super().__init__()

        # Load image
        self.color = color
        self.image = pygame.Surface([width, height])
        self.image.fill(color)

        # Position
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)

        # Jumping
        self.dragging = False
        self.drag_start_pos = None
        self.drag_vector = pygame.math.Vector2(0, 0)
        self.in_air = in_air
        self.preserve_drag_state = ( False )

    def update(self, x, y, in_air):
        
        # Save drag state if needed
        drag_info = None
        if self.preserve_drag_state and self.dragging:
            drag_info = {
                "dragging": self.dragging,
                "drag_start_pos": self.drag_start_pos,
                "drag_vector": self.drag_vector,
            }

        # Update rect position
        self.rect.bottomleft = (x, y)

        # Update in_air status
        self.in_air = in_air

        # Restore drag state if needed
        if drag_info:
            self.dragging = drag_info["dragging"]
            self.drag_start_pos = drag_info["drag_start_pos"]
            self.drag_vector = drag_info["drag_vector"]

    @staticmethod
    def _load_and_scale_image(path, width, height):
        try:
            image = pygame.image.load(os.path.join("client", path))
            return pygame.transform.scale(image, (width, height))
        except (pygame.error, FileNotFoundError):
            return None
