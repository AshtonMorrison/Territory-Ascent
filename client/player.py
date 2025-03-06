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


    def update(self):
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()

        if keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_d]:
            self.rect.x += self.speed

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