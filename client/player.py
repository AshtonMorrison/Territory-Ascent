import pygame


class Player(pygame.sprite.Sprite):
    def __init__(self, color, x, y, width, height, in_air):
        super().__init__()

        self.color = color
        border_color = (0, 0, 0)  # Black border
        border_thickness = 1

        self.image = pygame.Surface([width, height])
        self.image.fill(border_color)

        inner_width = width - (2 * border_thickness)
        inner_height = height - (2 * border_thickness)
        inner_x = border_thickness
        inner_y = border_thickness

        inner_rect = pygame.Rect(inner_x, inner_y, inner_width, inner_height)
        pygame.draw.rect(self.image, self.color, inner_rect)


        # Rect
        self.rect = self.image.get_rect()
        self.rect.bottomleft = (x, y)

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
