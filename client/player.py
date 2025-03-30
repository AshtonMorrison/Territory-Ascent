import pygame


class Player(pygame.sprite.Sprite):
    def __init__(self, color, x, y, width, height, in_air):
        super().__init__()

        # Create the image with the player color
        self.color = color
        self.image = pygame.Surface([width, height])

        # Fill the player image with the given color
        self.image.fill(self.color)

        # Add black border around the player (outline)
        border_thickness = 2  # Adjust border thickness as needed
        border_color = (0, 0, 0)  # Black border

        # Drawing the border: Inflate the player's rect to draw the border
        border_rect = self.image.get_rect().inflate(
            border_thickness * 2, border_thickness * 2
        )

        # Fill the surface with border color before drawing the actual player sprite
        border_surface = pygame.Surface(
            [width + border_thickness * 2, height + border_thickness * 2]
        )
        border_surface.fill(border_color)
        border_rect.topleft = (
            -border_thickness,
            -border_thickness,
        )  # Position the border correctly

        # Add the player image inside the border surface
        border_surface.blit(self.image, (border_thickness, border_thickness))

        # Update the image and rect
        self.image = border_surface
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

        # Jumping
        self.dragging = False
        self.drag_start_pos = None
        self.drag_vector = pygame.math.Vector2(0, 0)
        self.in_air = in_air
        self.preserve_drag_state = False
        
        # Wins
        self.wins = 0

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
