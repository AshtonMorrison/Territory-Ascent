import pygame
from shared import constants
import math
import os

class Player(pygame.sprite.Sprite):
    def __init__(self, color, x, y, width, height):
        super().__init__()

        # Load image
        self.image = self._load_and_scale_image("assets/player.png", width, height)
        if self.image is None:
            self.image = pygame.Surface([width, height])
            self.image.fill(color)

        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)

        # Movement
        self.speed = 5
        self.position = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(0, 0) # To be used for Jumping and Gravity only

        # Jumping
        self.is_jumping = False
        self.jump_speed = -15
        self.max_fall_speed = 10

    def update(self, tile_groups):
        self.acceleration = pygame.math.Vector2(0, constants.Y_GRAVITY)
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()

        # Movement (Left, Right) (No acceleration)
        if keys[pygame.K_a]:
            self.velocity.x = -self.speed
        elif keys[pygame.K_d]:
            self.velocity.x = self.speed
        else:
            self.velocity.x = 0

        # Jumping (Acceleration)
        if mouse_pressed[0] and not self.is_jumping:
            self.is_jumping = True
            self.acceleration.y = self.jump_speed

        # Apply acceleration to velocity
        self.velocity.y += self.acceleration.y

        # Predict next position
        next_position = self.position + self.velocity + 0.5 * self.acceleration

        # Create a temporary rect for collision detection
        next_rect = self.rect.copy()
        next_rect.bottomleft = next_position

        # Collision detection BEFORE updating position
        touched_ground = pygame.sprite.spritecollide(self, tile_groups["ground"], False, collided = lambda sprite, tile: next_rect.colliderect(tile.rect))
        touched_platform = pygame.sprite.spritecollide(self, tile_groups["platform"], False, collided = lambda sprite, tile: next_rect.colliderect(tile.rect))

        # Ground Collision
        if touched_ground:
            # Prevent further downward movement
            if self.velocity.y > 0:  # Only adjust if moving downwards
                self.velocity.y = 0
                self.acceleration.y = 0
                next_position.y = touched_ground[0].rect.top
                self.is_jumping = False

        # Platform Collision
        if touched_platform:
            # Prevent further downward movement
            if self.velocity.y > 0:  # Only adjust if moving downwards
                self.velocity.y = 0
                self.acceleration.y = 0
                next_position.y = touched_platform[0].rect.top
                self.is_jumping = False

        # Update position
        self.position = next_position
        self.rect.bottomleft = self.position

    @staticmethod
    def _load_and_scale_image(path, width, height):
        try:
            image = pygame.image.load(os.path.join("client", path))
            return pygame.transform.scale(image, (width, height))
        except (pygame.error, FileNotFoundError):
            return None