import pygame
from shared import constants


class Player(pygame.sprite.Sprite):
    def __init__(self, color, spawn, width, height):
        super().__init__()

        # Load image
        self.color = color
        self.image = pygame.Surface([width, height])
        self.image.fill(color)

        # Position and Rect
        x = spawn[0]
        y = spawn[1]
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)
        self.position = pygame.math.Vector2(x, y)

        # Movement
        self.speed = 3 * constants.Y_GRAVITY
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(
            0, 0
        )  # To be used for Jumping and Gravity only

        # Jumping
        self.in_air = False
        self.max_fall_speed = 10

        # Server side stuff
        self.conn = None
        self.addr = None

        # POTENTIALLY ADD TAGS FOR MOVEMENT TO GO FROM CLIENT HANDLE TO GAME LOOP UPDATE
        self.direction = None
        self.jump = False
        self.drag_vector = pygame.math.Vector2(0, 0)

    def reset_position(self, Coordinates):
        self.position.x = Coordinates[0]
        self.position.y = Coordinates[1]
        self.rect.bottomleft = self.position
        self.velocity = pygame.math.Vector2(0, 0)
        self.acceleration = pygame.math.Vector2(0, 0)

    def update(
        self, tile_groups, spawn, check_goal=True
    ):  # returns True if player reaches goal
        self.acceleration = pygame.math.Vector2(0, constants.Y_GRAVITY)

        # Movement (Left, Right) (No acceleration) (No moving while jumping or dragging)
        if self.direction == "left":
            self.velocity.x = -self.speed
        elif self.direction == "right":
            self.velocity.x = self.speed
        elif not self.in_air:
            self.velocity.x = 0

        # Jumping
        if self.jump:
            self.acceleration = (
                self.drag_vector / 10
            )  # Divide by a factor to control the power
            self.in_air = True

        self.direction = None
        self.jump = None

        # Apply acceleration to velocity
        self.velocity += self.acceleration * constants.Y_GRAVITY

        # Predict next position
        next_position = self.position + self.velocity + 0.5 * self.acceleration

        # Create a temporary rect for collision detection
        next_rect = self.rect.copy()
        next_rect.bottomleft = next_position

        # Collision detection for next position
        touched_ground = pygame.sprite.spritecollide(
            self,
            tile_groups["ground"],
            False,
            collided=lambda sprite, tile: next_rect.colliderect(tile.rect),
        )
        touched_platform = pygame.sprite.spritecollide(
            self,
            tile_groups["platform"],
            False,
            collided=lambda sprite, tile: next_rect.colliderect(tile.rect),
        )

        if check_goal:
            # Check if player reached the goal
            touched_goal = pygame.sprite.spritecollide(
                self,
                tile_groups["goal"],
                False,
                collided=lambda sprite, tile: next_rect.colliderect(tile.rect),
            )
            if touched_goal:
                return True

        if not touched_ground and not touched_platform:
            self.in_air = True

        # Ground Collision
        if touched_ground:

            tile = touched_ground[0]

            # Horizontal Collision
            if (
                self.velocity.x > 0
                and next_rect.right > tile.rect.left
                and self.rect.bottom > tile.rect.top + 1
                and self.rect.top < tile.rect.bottom - 1
            ):  # Left Side Collision
                next_position.x = tile.rect.left - self.rect.width
                self.velocity.x = 0
                self.acceleration.x = 0
            elif (
                self.velocity.x < 0
                and next_rect.left < tile.rect.right
                and self.rect.bottom > tile.rect.top + 1
                and self.rect.top < tile.rect.bottom - 1
            ):  # Right Side Collision
                next_position.x = tile.rect.right
                self.velocity.x = 0
                self.acceleration.x = 0

            # Vertical Collision
            if (
                self.velocity.y > 0
                and next_rect.bottom > tile.rect.top
                and self.rect.bottom < tile.rect.top + 1
            ):  # Top Side Collision
                next_position.y = tile.rect.top
                self.velocity.y = 0
                self.acceleration.y = 0
                self.in_air = False
            elif (
                self.velocity.y < 0
                and next_rect.top < tile.rect.bottom
                and self.rect.top > tile.rect.bottom - 1
            ):  # Bottom Side Collision
                next_position.y = tile.rect.bottom + self.rect.height
                self.velocity.y = 0
                self.acceleration.y = 0

        # Platform Collision
        if touched_platform:

            # Check for occupied platforms
            for tile in touched_platform:
                if tile.occupied_by is not None and tile.occupied_by != self.color:
                    # RESET POSITION
                    self.reset_position(spawn)
                    return False

                else:
                    if (
                        self.velocity.y > 0
                        and next_rect.bottom > tile.rect.top
                        and self.rect.bottom < tile.rect.top + 1
                    ):  # Make sure player is on top of platform
                        tile.occupied_by = self.color

            tile = touched_platform[0]

            # Horizontal Collision
            if (
                self.velocity.x > 0
                and next_rect.right > tile.rect.left
                and self.rect.bottom > tile.rect.top + 1
                and self.rect.top < tile.rect.bottom - 1
            ):  # Left Side Collision
                next_position.x = tile.rect.left - self.rect.width
                self.velocity.x = 0
                self.acceleration.x = 0
            elif (
                self.velocity.x < 0
                and next_rect.left < tile.rect.right
                and self.rect.bottom > tile.rect.top + 1
                and self.rect.top < tile.rect.bottom - 1
            ):  # Right Side Collision
                next_position.x = tile.rect.right
                self.velocity.x = 0
                self.acceleration.x = 0

            # Vertical Collision
            if (
                self.velocity.y > 0
                and next_rect.bottom > tile.rect.top
                and self.rect.bottom < tile.rect.top + 1
            ):  # Top Side Collision
                next_position.y = tile.rect.top
                self.velocity.y = 0
                self.acceleration.y = 0
                self.in_air = False
            elif (
                self.velocity.y < 0
                and next_rect.top < tile.rect.bottom
                and self.rect.top > tile.rect.bottom - 1
            ):  # Bottom Side Collision
                next_position.y = tile.rect.bottom + self.rect.height
                self.velocity.y = 0
                self.acceleration.y = 0

        # Screen Border Collision
        if next_position.x < 0:  # Left
            next_position.x = 0
            self.velocity.x = 0
            self.acceleration.x = 0
        elif next_position.x + self.rect.width > constants.SCREEN_WIDTH:  # Right
            next_position.x = constants.SCREEN_WIDTH - self.rect.width
            self.velocity.x = 0
            self.acceleration.x = 0
        elif next_position.y < 0:  # Top
            next_position.y = 0
            self.velocity.y = 0
            self.acceleration.y = 0
        elif next_rect.bottom > constants.SCREEN_HEIGHT:  # Bottom
            self.reset_position(spawn)
            return False

        # Update position
        self.position = next_position
        self.rect.bottomleft = self.position

        return False
