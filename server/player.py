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

        # Position and Rect
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)
        self.position = pygame.math.Vector2(x, y)

        # Movement
        self.speed = 5
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(0, 0) # To be used for Jumping and Gravity only

        # Jumping
        self.in_air = False
        self.max_fall_speed = 10

        # Server side stuff
        self.conn = None
        # POTENTIALLY ADD TAGS FOR MOVEMENT TO GO FROM CLIENT HANDLE TO GAME LOOP UPDATE
        self.direction = None
        self.jump = False
        self.drag_vector = pygame.math.Vector2(0, 0)


    def update(self, tile_groups):
        self.acceleration = pygame.math.Vector2(0, constants.Y_GRAVITY)

        # Movement (Left, Right) (No acceleration) (No moving while jumping or dragging)
        if not self.in_air: 
            if self.direction == "left":
                self.velocity.x = -self.speed
            elif self.direction == "right":
                self.velocity.x = self.speed
            else:
                self.velocity.x = 0

        # Jumping
        if self.jump and not self.in_air:
            self.acceleration = self.drag_vector / 10 # Divide by a factor to control the power
            self.in_air = True

        self.direction = None
        self.jump = None

        # Apply acceleration to velocity
        self.velocity += self.acceleration
      
        # Predict next position
        next_position = self.position + self.velocity + 0.5 * self.acceleration

        # Create a temporary rect for collision detection
        next_rect = self.rect.copy()
        next_rect.bottomleft = next_position

        # Collision detection for next position
        touched_ground = pygame.sprite.spritecollide(self, tile_groups["ground"], False, collided = lambda sprite, tile: next_rect.colliderect(tile.rect))
        touched_platform = pygame.sprite.spritecollide(self, tile_groups["platform"], False, collided = lambda sprite, tile: next_rect.colliderect(tile.rect))

        # Ground Collision, TO BE CHANGED IF HOLES ARE ADDED TO MAP
        if touched_ground:
            self.velocity.y = 0
            self.acceleration.y = 0
            next_position.y = touched_ground[0].rect.top
            self.in_air = False

        # Platform Collision
        if touched_platform:
            tile = touched_platform[0]

            # Horizontal Collision
            if self.velocity.x > 0 and next_rect.right > tile.rect.left and self.rect.bottom > tile.rect.top + 1 and self.rect.top < tile.rect.bottom - 1:  # Left Side Collision
                next_position.x = tile.rect.left - self.rect.width
                self.velocity.x = 0
                self.acceleration.x = 0
            elif self.velocity.x < 0 and next_rect.left < tile.rect.right and self.rect.bottom > tile.rect.top + 1 and self.rect.top < tile.rect.bottom - 1:  # Right Side Collision
                next_position.x = tile.rect.right
                self.velocity.x = 0
                self.acceleration.x = 0

            # Vertical Collision
            if self.velocity.y > 0 and next_rect.bottom > tile.rect.top and self.rect.bottom < tile.rect.top + 1:  # Top Side Collision
                next_position.y = tile.rect.top
                self.velocity.y = 0
                self.acceleration.y = 0
                self.in_air = False
            elif self.velocity.y < 0 and next_rect.top < tile.rect.bottom and self.rect.top > tile.rect.bottom - 1:  # Bottom Side Collision
                next_position.y = tile.rect.bottom + self.rect.height
                self.velocity.y = 0
                self.acceleration.y = 0


        # Screen Border Collision
        if next_position.x < 0: # Left
            next_position.x = 0
            self.velocity.x = 0
            self.acceleration.x = 0
        elif next_position.x + self.rect.width > constants.SCREEN_WIDTH: # Right
            next_position.x = constants.SCREEN_WIDTH - self.rect.width
            self.velocity.x = 0
            self.acceleration.x = 0
        elif next_position.y < 0: # Top
            next_position.y = 0
            self.velocity.y = 0
            self.acceleration.y = 0
        
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