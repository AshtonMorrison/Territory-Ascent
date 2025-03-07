import pygame
from shared import constants
from .player import Player
from .tile import Tile


class GameClient:
    def __init__(self):
        pygame.init()

        # Display
        self.screen = pygame.display.set_mode(
            (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )
        pygame.display.set_caption("371 Multiplayer Game")

        # Clock for FPS
        self.clock = pygame.time.Clock()

        # Player Setup
        self.player_sprites = pygame.sprite.Group()
        self.player = Player(
            (255, 0, 0), constants.TILE_SIZE * 2, constants.TILE_SIZE * 2
        )  # Make player 2x2 tiles
        self.player.rect.x = constants.TILE_SIZE * 19  # Center position
        self.player.rect.y = constants.TILE_SIZE * 18
        self.player_sprites.add(self.player)

        # Tile Map Setup
        self.tile_size = constants.TILE_SIZE
        self.tiles = {
            "air": pygame.sprite.Group(),
            "ground": pygame.sprite.Group(),
            "platform": pygame.sprite.Group(),
        }

        # Tilemap layout (0: empty, 1: ground, 2: platform)
        self.tile_map = [
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 40,
            [0] * 3 + [2] * 4 + [0] * 26 + [2] * 4 + [0] * 3,
            [0] * 40,
            [0] * 6 + [2] * 4 + [0] * 20 + [2] * 4 + [0] * 6,
            [0] * 40,
            [0] * 9 + [2] * 4 + [0] * 14 + [2] * 4 + [0] * 9,
            [0] * 40,
            [0] * 12 + [2] * 4 + [0] * 8 + [2] * 4 + [0] * 12,
            [0] * 40,
            [0] * 40,
            [1] * 40,
            [1] * 40,
            [1] * 40,
        ]

        self.create_tile_map()

    def create_tile_map(self):
        tile_types = {0: "air", 1: "ground", 2: "platform"}

        for row_index, row in enumerate(self.tile_map):
            for col_index, tile_value in enumerate(row):
                x = col_index * self.tile_size
                y = row_index * self.tile_size
                tile = Tile(
                    x, y, self.tile_size, self.tile_size, tile_types[tile_value]
                )
                self.tiles[tile_types[tile_value]].add(tile)

    def update(self):
        self.player_sprites.update()

    def draw(self):
        self.screen.fill((255, 255, 255))
        for tile_group in self.tiles.values():
            tile_group.draw(self.screen)
        self.player_sprites.draw(self.screen)

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
            self.draw()

            # FPS Limit
            self.clock.tick(constants.FPS)

            # Flip the back buffer to the front
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    client = GameClient()
    client.run()
