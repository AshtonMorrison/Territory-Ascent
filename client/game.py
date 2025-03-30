import pygame
from shared import constants
from .tile import Tile
from .player import Player
import math
import socket
import threading
import msgpack
import base64


def decode_ip(encoded):
    padded = encoded + "=" * (4 - len(encoded) % 4)  # Fix padding
    return socket.inet_ntoa(base64.urlsafe_b64decode(padded))


def is_valid_ip(ip):
    try:
        # Try to convert the IP string to its packed binary form using inet_aton
        socket.inet_aton(ip)
        return True  # Valid IP
    except socket.error:
        return False  # Invalid IP


class GameClient:
    def __init__(self, game_code=None):
        pygame.init()
        self.game_code = game_code

        # Logical resolution
        self.scaled_surface = pygame.Surface(
            (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )
        self.window_size = (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        self.fullscreen = False

        # Create initial screen
        self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        pygame.display.set_caption("Multiplayer Platformer")

        # Clock for FPS
        self.clock = pygame.time.Clock()

        # Connection
        self.conn = None

        # Tile Dictionary
        self.tile_dict = {}
        self.tile_size = constants.TILE_SIZE

        # Player Dictionary, SELF.ME IS THE COLOR OF THE CLIENTS PLAYER
        self.me = None
        self.player_dict = {}

        self.lock = threading.Lock()

        # Game Logic
        self.running = False
        self.waiting = False
        self.ready = False

        self.winner = None
        self.winner_display_start_time = None

        # Countdown
        self.font = pygame.font.SysFont(constants.FONT_NAME, 150)
        self.countdown = 0
        self.go_timer = 0

        # Button properties
        self.button_color = (100, 100, 100)
        self.button_hover_color = (150, 150, 150)
        self.button_rect = pygame.Rect(
            constants.SCREEN_WIDTH // 2 - 75,  # Center horizontally at the top
            20,  # Position 20 pixels from the top (adjustable)
            150,
            50,
        )
        self.button_text_color = (255, 255, 255)
        self.button_font = pygame.font.SysFont(None, 40)
        self.button_text = self.button_font.render(
            "Ready", True, self.button_text_color
        )
        self.button_text_rect = self.button_text.get_rect(
            midleft=(self.button_rect.left + 10, self.button_rect.centery)
        )

    def receive_message(self, conn):
        # First, receive the 4-byte header that contains the length
        length_data = b""
        while len(length_data) < 4:
            chunk = conn.recv(4 - len(length_data))
            if not chunk:
                raise Exception("Error: Connection lost while receiving length header.")
            length_data += chunk

        # Convert the 4-byte length data to an integer
        message_length = int.from_bytes(length_data, byteorder="big")

        # Now, receive the actual message of the specified length
        message_data = b""
        while len(message_data) < message_length:
            chunk = conn.recv(message_length - len(message_data))
            if not chunk:
                raise Exception("Error: Connection lost while receiving message.")
            message_data += chunk

        return message_data

    def send_message(self, conn, message):
        message_pack = msgpack.packb(message)
        length_message = len(message_pack).to_bytes(4, byteorder="big")
        conn.sendall(length_message + message_pack)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window_size = pygame.display.get_desktop_sizes()[0]
            self.screen = pygame.display.set_mode(self.window_size, pygame.FULLSCREEN)
        else:
            self.window_size = (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
            self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)

    def connect(self):  # Used to connect to server and parse initial data from server
        try:
            if self.game_code is None:
                code = input("Enter the game code or IP address: ")
            else:
                code = self.game_code

            if len(code) > 6:
                ip = code
            else:
                ip = decode_ip(code)
                if not is_valid_ip(ip):
                    print("Invalid Code")
                    raise ValueError("Game Code not valid")
            print(f"will attempt to connect to server at {ip}")
            # Create a socket
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Connect to the server
            server_address = (
                ip,
                constants.PORT,
            )

            try:
                conn.connect(server_address)
                print(f"Connected to {server_address}")
            except Exception as e:
                print("connection failed: check IP address, or game code")
                return None, "Failed to connect\n" + str(e)

            # Receive initial data
            try:
                data = self.receive_message(conn)
            except Exception as e:
                conn.close()
                return None, str(e)

            try:
                initial_data = msgpack.unpackb(data)
            except msgpack.UnpackException as e:
                return None, str(e)

            # Check for error message
            if initial_data == "Error: No more colors available":
                e = "Error: Server full, No more player slots available"
                conn.close()
                return None, str(e)

            # Parse initial data
            if initial_data["type"] == "INITIAL":
                self.me = initial_data["YourPlayer"]
                print(f"You are {self.me} player")

                # Create players
                player_data = initial_data["Players"]
                for player_info in player_data:
                    self.create_player(
                        player_info["color"],
                        player_info["x"],
                        player_info["y"],
                        player_info["in_air"],
                    )

                # Set waiting room flag
                self.waiting = True

            else:
                e = "Error: Invalid initial data received from server"
                self.disconnect(conn)
                return None, str(e)

            return conn, None  # Return the connection object and no error

        except socket.error as e:
            return None, str(e)

    def disconnect(self, conn):  # Used to gracefully disconnect from server
        try:
            with self.lock:
                # Send disconnect message to server
                self.send_message(conn, {"type": "DISCONNECT"})

                # Receive confirmation from server
                try:
                    server_response = self.receive_message(conn)
                    response = msgpack.unpackb(server_response)
                    if response == "DISCONNECTED":
                        print("Successfully disconnected from server")
                    else:
                        print("Error: Disconnection confirmation not received")
                except Exception as e:
                    print(f"Error during disconnection: {e}")

        except socket.error as e:
            print(f"Socket error during disconnection: {e}")
        finally:
            with self.lock:
                conn.close()

    def create_tile_map(
        self, tile_data
    ):  # Used to create the tile map from info from server
        self.tile_dict = {}
        for tile_info in tile_data:
            x = tile_info["x"]
            y = tile_info["y"]
            tile_type = tile_info["type"]
            self.tile_dict[(x, y)] = Tile(
                x, y, self.tile_size, self.tile_size, tile_type
            )

    def create_player(
        self, color, x, y, in_air
    ):  # Used to create a player from info from server
        self.player_dict[color] = Player(
            color, x, y, self.tile_size, self.tile_size, in_air
        )

    def handle_inputs(
        self, conn
    ):  # Used to handle inputs from user, must convert these inputs to messages to send to server
        me = self.player_dict[self.me]
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        mouse_pos = self.get_mouse_pos()

        if self.waiting:
            if self.check_button_click(mouse_pos, mouse_pressed):
                self.send_message(conn, {"type": "READY"})
                self.ready = True

        elif self.countdown <= 0:

            # Movement (Left, Right) (No acceleration) (No moving while jumping or dragging)
            if not me.dragging and not me.in_air:
                if keys[pygame.K_a] and not keys[pygame.K_d]:
                    self.send_message(conn, {"type": "MOVE", "direction": "left"})
                elif keys[pygame.K_d] and not keys[pygame.K_a]:
                    self.send_message(conn, {"type": "MOVE", "direction": "right"})

            # Mouse Drag Jumping
            if mouse_pressed[0] and not me.in_air and not me.dragging:
                me.dragging = True
                me.preserve_drag_state = True
                me.drag_start_pos = pygame.math.Vector2(
                    mouse_pos
                )  # Record start position

            if me.dragging and not me.in_air:
                drag_end_pos = pygame.math.Vector2(mouse_pos)
                me.drag_vector = (
                    me.drag_start_pos - drag_end_pos
                )  # Vector from start to end

                # Limit the drag vector length to prevent excessive speeds
                max_drag_length = 125  # Adjust as needed
                if me.drag_vector.length() > max_drag_length:
                    me.drag_vector = me.drag_vector.normalize() * max_drag_length

                if not mouse_pressed[0]:
                    me.dragging = False
                    me.preserve_drag_state = False  # Disable preserving drag state
                    # Send jump message with drag vector
                    self.send_message(
                        conn,
                        {
                            "type": "JUMP",
                            "drag_x": me.drag_vector.x,
                            "drag_y": me.drag_vector.y,
                        },
                    )

    def check_button_click(self, mouse_pos, mouse_pressed):
        """Check if the button is clicked."""

        # Check if the mouse is within the button bounds
        if (
            self.button_rect.collidepoint(mouse_pos)
            and mouse_pressed[0]
            and not self.ready
        ):
            return True
        else:
            return False

    def get_mouse_pos(self):
        """Get the mouse position scaled to the logical resolution."""

        mouse_pos = pygame.mouse.get_pos()
        scaled_mouse_pos = (
            mouse_pos[0] * constants.SCREEN_WIDTH // self.window_size[0],
            mouse_pos[1] * constants.SCREEN_HEIGHT // self.window_size[1],
        )
        return scaled_mouse_pos

    def update(
        self, conn
    ):  # Used to update the game state from the servers broadcast (Player locations, tile colors), RUNS ON SEPERATE THREAD
        try:
            while self.running:
                try:
                    data = self.receive_message(conn)

                    try:
                        update_data = msgpack.unpackb(data)
                    except msgpack.UnpackException as e:
                        print(f"MessagePack Unpack error: {e}")
                        self.running = False
                        break

                    # Parse update data
                    if update_data["type"] == "SHUTTING DOWN":
                        print("Server Shut Down")
                        self.running = False
                        break

                    elif update_data["type"] == "ROUND OVER":
                        winner = update_data["winner"]
                        print(f"Round Over! {winner} got the point!")

                    elif update_data["type"] == "GAME OVER":
                        self.winner = update_data["winner"]
                        print(f"Game Over! {winner} wins!")

                        # Record the time when the winner message was processed
                        self.winner_display_start_time = pygame.time.get_ticks()

                        self.waiting = True
                        self.ready = False
                        
                        for p in self.player_dict.values():
                            p.wins = 0

                    elif update_data["type"] == "NEW GAME":
                        self.waiting = False

                        # Reset Players
                        player_data = update_data["Players"]

                        # Reset countdown
                        self.countdown = 999

                        current_player_colors = set()
                        with self.lock:
                            current_player_colors = set(self.player_dict.keys())
                        updated_player_colors = set()

                        wins_dict= update_data["PlayerWins"]

                        for player_info in player_data:
                            color = player_info["color"]
                            x = player_info["x"]
                            y = player_info["y"]
                            in_air = player_info["in_air"]
                            wins = wins_dict[color]
                            updated_player_colors.add(color)

                            with self.lock:
                                if color in self.player_dict:
                                    self.player_dict[color].update(x, y, in_air)
                                else:
                                    self.create_player(color, x, y, in_air)

                                self.player_dict[color].wins = wins

                        # Remove players that have disconnected
                        for color in current_player_colors - updated_player_colors:
                            with self.lock:
                                del self.player_dict[color]

                        # Reset tile map
                        tile_data = update_data["TileMap"]
                        self.create_tile_map(tile_data)

                        
                    elif update_data["type"] == "STATE":
                        # Update player locations
                        player_data = update_data["players"]

                        # Check for new players and update existing players
                        current_player_colors = set()
                        with self.lock:
                            current_player_colors = set(self.player_dict.keys())
                        updated_player_colors = set()

                        for player_info in player_data:
                            color = player_info["color"]
                            x = player_info["x"]
                            y = player_info["y"]
                            in_air = player_info["in_air"]
                            updated_player_colors.add(color)

                            with self.lock:
                                if color in self.player_dict:
                                    self.player_dict[color].update(x, y, in_air)

                                else:
                                    self.create_player(color, x, y, in_air)

                        # Remove players that have disconnected
                        for color in current_player_colors - updated_player_colors:
                            with self.lock:
                                del self.player_dict[color]

                        # Update tile colors
                        tile_data = update_data["tiles"]
                        if tile_data is not None:
                            with self.lock:
                                for tile_info in tile_data:
                                    x = tile_info["x"]
                                    y = tile_info["y"]
                                    color = tile_info["color"]
                                    self.tile_dict[(x, y)].update(color)

                    elif update_data["type"] == "COUNTDOWN":
                        self.countdown = update_data["value"]
                        if self.countdown == 0:
                            # Start the GO timer when countdown reaches zero
                            self.go_timer = pygame.time.get_ticks()
                        print(f"Game starting in {self.countdown} seconds")

                except Exception as e:
                    print(f"Error receiving message: {e}")
                    self.running = False
                    break

        except socket.error as e:
            print(f"Socket error during update: {e}")
        finally:
            self.running = False

    def draw(self):
        # Render everything onto the internal surface
        self.scaled_surface.fill((255, 255, 255))
        if self.winner:
            # Display winner text
            words = f"Winner is: {self.winner}!"
            font = pygame.font.SysFont(constants.FONT_NAME, 50)
            text = font.render(words, True, self.winner)
            text_rect = text.get_rect(center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2))

            # Outline the text in black
            outline_width = 2  # Adjust as needed
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx*dx + dy*dy <= outline_width*outline_width: # Draw only in a circle
                        outline_rect = text_rect.move(dx, dy)
                        outline = font.render(words, True, (0, 0, 0))  # Black outline
                        self.scaled_surface.blit(outline, outline_rect)

            # Draw the text in the player's color
            self.scaled_surface.blit(text, text_rect)

        else:
            if self.waiting:

                # Draw "Ready" button with shadow
                mouse_pos = self.get_mouse_pos()
                if self.button_rect.collidepoint(mouse_pos):
                    button_color = self.button_hover_color
                else:
                    button_color = self.button_color

                # Shadow effect for the button (slightly offset)
                shadow_offset = (
                    5,
                    5,
                )  # You can adjust this for shadow direction and spread
                shadow_color = (50, 50, 50)  # Dark shadow color

                # Draw shadow for the button (rounded corners)
                pygame.draw.rect(
                    self.scaled_surface,
                    shadow_color,
                    self.button_rect.move(*shadow_offset),
                    border_radius=12,
                )
                self.scaled_surface.blit(
                    self.button_text, self.button_text_rect.move(*shadow_offset)
                )

                # Draw the button itself (rounded corners)
                pygame.draw.rect(
                    self.scaled_surface, button_color, self.button_rect, border_radius=12
                )
                self.scaled_surface.blit(self.button_text, self.button_text_rect)

                # Draw checkmark box (always visible)
                checkmark_box_size = 30
                checkmark_box_rect = pygame.Rect(
                    self.button_rect.right
                    - checkmark_box_size
                    - 10,  # Position box to the right
                    self.button_rect.centery - checkmark_box_size // 2,
                    checkmark_box_size,
                    checkmark_box_size,
                )

                # White box background for the checkmark
                pygame.draw.rect(
                    self.scaled_surface,
                    (255, 255, 255),
                    checkmark_box_rect,
                    border_radius=5,
                )  # White box with rounded corners
                pygame.draw.rect(
                    self.scaled_surface, (0, 0, 0), checkmark_box_rect, 2
                )  # Black border

                # Draw checkmark if ready
                if self.ready:
                    checkmark_font = pygame.font.SysFont("Arial", 25)
                    checkmark_text = checkmark_font.render(
                        "\u2713", True, (0, 255, 0)
                    )  # Unicode checkmark
                    checkmark_rect = checkmark_text.get_rect(
                        center=checkmark_box_rect.center
                    )
                    self.scaled_surface.blit(checkmark_text, checkmark_rect)

            else:
                # Draw tiles
                for t in self.tile_dict.values():
                    self.scaled_surface.blit(t.image, t.rect)

            # Draw players
            with self.lock:
                for p in self.player_dict.values():
                    self.scaled_surface.blit(p.image, p.rect)

                    if self.waiting:
                        font = pygame.font.SysFont(constants.FONT_NAME, 20)
                        words = p.color if p.color != self.me else "You"
                        text = font.render(words, True, p.color)
                        text_rect = text.get_rect(center=(p.rect.centerx, p.rect.bottom + 15))

                        # Outline the text in black
                        outline_width = 2  # Adjust as needed
                        for dx in range(-outline_width, outline_width + 1):
                            for dy in range(-outline_width, outline_width + 1):
                                if dx*dx + dy*dy <= outline_width*outline_width: # Draw only in a circle
                                    outline_rect = text_rect.move(dx, dy)
                                    outline = font.render(words, True, (0, 0, 0))  # Black outline
                                    self.scaled_surface.blit(outline, outline_rect)

                        # Draw the text in the player's color
                        self.scaled_surface.blit(text, text_rect)

            # Draw drag vector if dragging
            if self.me and self.player_dict[self.me].dragging:
                start_pos = self.player_dict[self.me].rect.center
                end_pos = (
                    start_pos[0] + self.player_dict[self.me].drag_vector[0],
                    start_pos[1] + self.player_dict[self.me].drag_vector[1],
                )
                pygame.draw.line(self.scaled_surface, (0, 0, 255), start_pos, end_pos, 3)

                # Draw arrowhead
                angle = math.atan2(start_pos[1] - end_pos[1], start_pos[0] - end_pos[0])
                arrow_length = 12
                arrow_angle = math.pi / 4
                left_arrow = (
                    end_pos[0] + arrow_length * math.cos(angle + arrow_angle),
                    end_pos[1] + arrow_length * math.sin(angle + arrow_angle),
                )
                right_arrow = (
                    end_pos[0] + arrow_length * math.cos(angle - arrow_angle),
                    end_pos[1] + arrow_length * math.sin(angle - arrow_angle),
                )

                pygame.draw.line(self.scaled_surface, (0, 0, 255), end_pos, left_arrow, 3)
                pygame.draw.line(self.scaled_surface, (0, 0, 255), end_pos, right_arrow, 3)

            current_time = pygame.time.get_ticks()

            # Draw countdown if active
            if self.countdown > 0:
                # Create a semi-transparent overlay
                overlay = pygame.Surface(
                    (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT), pygame.SRCALPHA
                )
                overlay.fill((0, 0, 0, 128))
                self.scaled_surface.blit(overlay, (0, 0))

                # Render countdown text
                countdown_text = self.font.render(
                    str(self.countdown if self.countdown != 999 else ""),
                    True,
                    (255, 255, 255),
                )
                text_rect = countdown_text.get_rect(
                    center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2)
                )
                self.scaled_surface.blit(countdown_text, text_rect)

                ready_font = pygame.font.SysFont(constants.FONT_NAME, 70)
                ready_text = ready_font.render("Get Ready!", True, (255, 255, 255))
                ready_rect = ready_text.get_rect(
                    center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2 - 100)
                )
                self.scaled_surface.blit(ready_text, ready_rect)
                
                # Display scores at the bottom
                score_font = pygame.font.SysFont(constants.FONT_NAME, 30)
                y_offset = 0
                x_offset = 0
                count = 0
                for color, player in self.player_dict.items():
                    word = color if color != self.me else "You"
                    score_text = score_font.render(f"{word}: {player.wins}", True, color)
                    score_rect = score_text.get_rect(
                        center=(
                            constants.SCREEN_WIDTH // 5 + x_offset,
                            constants.SCREEN_HEIGHT - 80 + y_offset,
                        )
                    )

                    # Outline the text in black
                    outline_width = 2  # Adjust as needed
                    for dx in range(-outline_width, outline_width + 1):
                        for dy in range(-outline_width, outline_width + 1):
                            if dx*dx + dy*dy <= outline_width*outline_width: # Draw only in a circle
                                outline_rect = score_rect.move(dx, dy)
                                outline = score_font.render(f"{word}: {player.wins}", True, (0, 0, 0))  # Black outline
                                self.scaled_surface.blit(outline, outline_rect)

                    self.scaled_surface.blit(score_text, score_rect)
                    x_offset += constants.SCREEN_WIDTH // 5  # Move to the next column

                    count += 1
                    if count == 4:  # Move to the next row after 4 players
                        y_offset = 40
                        x_offset = 0

            elif self.countdown == 0 and self.go_timer > 0:
                if current_time - self.go_timer < 1000:
                    go_text = self.font.render("GO!", True, (0, 151, 0))
                    go_rect = go_text.get_rect(
                        center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2)
                    )
                    self.scaled_surface.blit(go_text, go_rect)
                else:
                    self.go_timer = 0

        # Scale the internal surface to fit the window using nearest-neighbor scaling
        scaled_surface = pygame.transform.scale(self.scaled_surface, self.window_size)
        self.screen.blit(scaled_surface, (0, 0))

        pygame.display.flip()  # Update screen

    def run(self):  # RUNS ON MAIN THREAD

        self.conn, e = self.connect()

        if self.conn is None:
            print(f"Failed to connect to server with {e}")
            return

        self.running = True

        # Start update thread
        update_thread = threading.Thread(target=self.update, args=(self.conn,))
        update_thread.daemon = True
        update_thread.start()

        # Main loop
        while self.running:
            current_time = pygame.time.get_ticks()

            # Check if a winner is set AND the timer was started
            if self.winner is not None and self.winner_display_start_time is not None:
                # Check if 3000 milliseconds (3 seconds) have passed
                if current_time - self.winner_display_start_time >= 3000:
                    self.winner = None  
                    self.winner_display_start_time = None 
                    
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:  # Adjust only in windowed mode
                        self.window_size = (event.w, event.h)
                        self.screen = pygame.display.set_mode(
                            self.window_size, pygame.RESIZABLE
                        )
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()

            # Everything gets done to the back buffer
            # Input handling
            self.handle_inputs(self.conn)

            # Drawing
            self.draw()

            # FPS Limit
            self.clock.tick(constants.FPS)

        update_thread.join()
        self.disconnect(self.conn)
        pygame.quit()


if __name__ == "__main__":
    import sys

    game_code = sys.argv[1] if len(sys.argv) > 1 else None
    client = GameClient(game_code)
    try:
        client.run()
    except KeyboardInterrupt:
        client.disconnect(client.conn)
        pygame.quit()
