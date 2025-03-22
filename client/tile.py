import pygame
import os
from shared import constants


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, image_integer):
        super().__init__()

        self.width = width
        self.height = height
        self.image = pygame.Surface([self.width, self.height])

        if image_integer == 1:
            ground_color = (170, 120, 80)
            border_color = (150, 100, 60)

            self.image.fill(border_color)
            pygame.draw.rect(
                self.image, ground_color, [0, self.height // 2, self.width, self.height // 2]
            )


        if image_integer == 2:
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
                self.image, platform_color, [0, self.height // 2, self.width, self.height // 2]
            )

        if image_integer == 3:
            goal_color = (0, 0, 0) 

            self.image.fill(goal_color)
            pygame.draw.rect(
                self.image, goal_color, [0, height // 2, width, height // 2]
            )

        # Get rects and positions
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def update(self, color):

        pygame.draw.rect(self.image, color, [0, self.height // 2, self.width, self.height // 2])