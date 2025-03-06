import pygame
from shared import constants
import math

class Player(pygame.sprite.Sprite):
    def __init__(self, color, width, height):
        super().__init__()

        self.image = pygame.Surface([width, height])
        self.image.fill(color)

        self.rect = self.image.get_rect()
        self.rect.x = constants.SCREEN_WIDTH // 2
        self.rect.y = constants.SCREEN_HEIGHT // 2

        self.speed = 5

        # Jumping
        self.is_jumping = False
        self.max_jump_height = 20
        self.y_velocity = self.max_jump_height
        self.x_direction = 0  # -1 for left, 1 for right, 0 for none


    def update(self):
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        
        # Ground Movement
        if not self.is_jumping:
            if keys[pygame.K_a]:
                self.x_direction = -1
                self.rect.x -= self.speed
            elif keys[pygame.K_d]:
                self.x_direction = 1
                self.rect.x += self.speed
            else:
                self.x_direction = 0  # No key pressed
        else:
            # Air Movement (Maintain Momentum)
            self.rect.x += self.x_direction * self.speed

        # Jumping
        if mouse_pressed[0] and not self.is_jumping:
            self.is_jumping = True

        if self.is_jumping:
            self.rect.y -= self.y_velocity
            self.y_velocity -= constants.Y_GRAVITY
            if self.y_velocity < -self.max_jump_height:
                self.is_jumping = False
                self.y_velocity = self.max_jump_height
            
        # Keep player within bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > constants.SCREEN_WIDTH:
            self.rect.right = constants.SCREEN_WIDTH
        if self.rect.top < 0:
            self.rect.top = 0
        if self.rect.bottom > constants.SCREEN_HEIGHT:
            self.rect.bottom = constants.SCREEN_HEIGHT