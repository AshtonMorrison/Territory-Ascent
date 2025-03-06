import pygame
from shared import constants
from .player import Player

class GameClient:
    def __init__(self):
        pygame.init()

        # Display
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption("371 Multiplayer Game")

        # Clock for FPS
        self.clock = pygame.time.Clock()

        # Player Setup
        self.all_sprites = pygame.sprite.Group()
        self.player = Player((255, 0, 0), 50, 50)
        self.all_sprites.add(self.player)

    def update(self):
        self.all_sprites.update()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Everything gets done to the back buffer
            # Update Game
            self.update()

            # Drawing
            self.screen.fill((255, 255, 255))
            self.all_sprites.draw(self.screen)

            # FPS Limit
            self.clock.tick(constants.FPS)

            # Flip the back buffer to the front
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    client = GameClient()
    client.run()
