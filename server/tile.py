import pygame
import os
from shared import constants


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, image_integer, sub_group=""):
        super().__init__()

        self.color = None

        if image_integer == 1:
            self.image = pygame.Surface([width, height])
            ground_color = (170, 120, 80)
            border_color = (150, 100, 60)

            self.image.fill(border_color)
            pygame.draw.rect(
                self.image, ground_color, [0, height // 2, width, height // 2]
            )

            sub_group.add(self)
            self.color = ground_color

        if image_integer == 2:
            self.image = pygame.Surface([width, height])
            platform_color = (
                constants.DEFAULT_PLATFORM_COLOR
            )  # Use default platform color for now; will have to adjust for coloured occupation later
            border_color = (
                platform_color[0] - 30,
                platform_color[1] - 30,
                platform_color[2] - 30,
            )

            self.image.fill(border_color)
            pygame.draw.rect(
                self.image, platform_color, [0, height // 2, width, height // 2]
            )

            sub_group.add(self)
            self.color = platform_color

        # Get rects and positions
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        # In Use
        self.occupied_by = None

    def update(self, players): # For platform tiles

        if self.occupied_by is not None:
        # Check if the occupying player is still colliding with the tile

            # Create a slightly larger rect for collision detection
            larger_rect = self.rect.inflate(0, 2)
            larger_rect.center = self.rect.center

            # Check if the player is still colliding with the tile
            if any(
                player.color == self.occupied_by
                and larger_rect.colliderect(player.rect)
                for player in players
            ):
                if self.color != self.occupied_by:
                    self.color = self.occupied_by
                    return True
                return False
            
            # No longer occupied
            else:
                self.occupied_by = None
                if self.color != constants.DEFAULT_PLATFORM_COLOR:
                    self.color = constants.DEFAULT_PLATFORM_COLOR
                    return True
                return False

