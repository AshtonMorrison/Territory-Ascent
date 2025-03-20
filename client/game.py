import pygame
from shared import constants
from .tile import Tile
from .player import Player
import math
import socket
import threading
import json


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

        # Tile Dictionary
        self.tile_dict = {}
        self.tile_size = constants.TILE_SIZE

        # Player Dictionary, SELF.ME IS THE COLOR OF THE CLIENTS PLAYER
        self.me = None
        self.player_dict = {}

        self.lock = threading.Lock()

        self.running = False

    def connect(self):  # Used to connect to server and parse initial data from server
        try:
            ip = input("Enter the server IP: ")

            # Create a socket
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Connect to the server
            server_address = (
                ip,
                constants.PORT,
            )  # Replace with your server's IP and port
            conn.connect(server_address)
            print(f"Connected to {server_address}")

            # Receive initial data
            data = ""
            while True:
                chunk = conn.recv(2048).decode()
                if not chunk:
                    break
                data += chunk
                try:
                    initial_data = json.loads(data)
                    break  # Successfully parsed JSON, exit loop
                except json.JSONDecodeError:
                    # Incomplete JSON, continue receiving
                    continue

            # Check for error message
            if initial_data == "Error: No more colors available":
                e = "Error: Server full, No more player slots available"
                conn.close()
                return None, e

            initial_data = json.loads(data)

            # Parse initial data
            if initial_data["type"] == "INITIAL":
                self.me = initial_data["YourPlayer"]
                print(f"You are {self.me} player")

                # Create tile map
                tile_data = initial_data["TileMap"]
                self.create_tile_map(tile_data)

                # Create players
                player_data = initial_data["Players"]
                for player_info in player_data:
                    self.create_player(
                        player_info["color"], player_info["x"], player_info["y"]
                    )

                # TO DO WHEN TILES UPDATE AND A PLAYER JOINS LATE INTO THE GAME
                # map_data = initial_data["MapState"]
                # call tile.update() for each tile in map_data to change its color

            else:
                e = "Error: Invalid initial data received from server"
                self.disconnect(conn)
                return None, e

            return conn, None  # Return the connection object and no error

        except socket.error as e:
            return None, e

    def disconnect(self, conn):  # Used to gracefully disconnect from server
        try:
            with self.lock:
                # Send disconnect message to server
                message = {"type": "DISCONNECT"}
                conn.sendall(json.dumps(message).encode())

                # Receive confirmation from server
                response = conn.recv(2048).decode()
                if response == "DISCONNECTED":
                    print("Successfully disconnected from server")
                else:
                    print("Error: Disconnection confirmation not received")

        except socket.error as e:
            print(f"Socket error during disconnection: {e}")
        finally:
            with self.lock:
                conn.close()

    def create_tile_map(
        self, tile_data
    ):  # Used to create the tile map from info from server
        for tile_info in tile_data:
            x = tile_info["x"]
            y = tile_info["y"]
            tile_type = tile_info["type"]
            self.tile_dict[(x, y)] = Tile(
                x, y, self.tile_size, self.tile_size, tile_type
            )

    def create_player(
        self, color, x, y
    ):  # Used to create a player from info from server
        self.player_dict[color] = Player(color, x, y, self.tile_size, self.tile_size)

    def handle_inputs(
        self, conn
    ):  # Used to handle inputs from user, must convert these inputs to messages to send to server
        me = self.player_dict[self.me]
        keys = pygame.key.get_pressed()
        mouse_pressed = pygame.mouse.get_pressed()
        mouse_pos = pygame.mouse.get_pos()

        # Movement (Left, Right) (No acceleration) (No moving while jumping or dragging)
        if not me.dragging:
                if keys[pygame.K_a] and not keys[pygame.K_d]:
                    message = {"type": "MOVE", "direction": "left"}
                    conn.sendall(json.dumps(message).encode())
                elif keys[pygame.K_d] and not keys[pygame.K_a]:
                    message = {"type": "MOVE", "direction": "right"}
                    conn.sendall(json.dumps(message).encode())

        # Mouse Drag Jumping
        if mouse_pressed[0] and not me.dragging:
            me.dragging = True
            me.drag_start_pos = pygame.math.Vector2(mouse_pos)  # Record start position

        if me.dragging:
            drag_end_pos = pygame.math.Vector2(mouse_pos)
            me.drag_vector = (
                me.drag_start_pos - drag_end_pos
            )  # Vector from start to end

            # Limit the drag vector length to prevent excessive speeds
            max_drag_length = 200  # Adjust as needed
            if me.drag_vector.length() > max_drag_length:
                me.drag_vector = me.drag_vector.normalize() * max_drag_length

            if not mouse_pressed[0]:
                me.dragging = False
                # Send jump message with drag vector
                message = {
                    "type": "JUMP",
                    "drag_x": me.drag_vector.x,
                    "drag_y": me.drag_vector.y,
                }
                conn.sendall(json.dumps(message).encode())
        pass

    def update(
        self, conn
    ):  # Used to update the game state from the servers broadcast (Player locations, tile colors), RUNS ON SEPERATE THREAD
        try:
            while self.running:
                # Receive data
                data = ""
                while True:
                    chunk = conn.recv(2048).decode()
                    if not chunk:
                        break
                    data += chunk
                    try:
                        update_data = json.loads(data)
                        break  # Successfully parsed JSON, exit loop
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue

                if not data:
                    break

                # Parse update data
                if update_data["type"] == "SHUTTING DOWN":
                    print("Server Shut Down")
                    self.running = False
                if update_data["type"] == "STATE":
                    # Update player locations
                    player_data = update_data["players"]

                    # Check for new players and update existing players
                    current_player_colors = set(self.player_dict.keys())
                    updated_player_colors = set()

                    for player_info in player_data:
                        color = player_info["color"]
                        x = player_info["x"]
                        y = player_info["y"]
                        updated_player_colors.add(color)

                        with self.lock:
                            if color in self.player_dict:
                                self.player_dict[color].update(x, y)

                            else:
                                self.create_player(color, x, y)

                    # Remove players that have disconnected
                    for color in current_player_colors - updated_player_colors:
                        with self.lock:
                            del self.player_dict[color]

                    # TO DO WHEN TILES UPDATE
                    # map_data = update_data["map"]
                    # call tile.update() for each tile in map_data to change its color

        except socket.error as e:
            print(f"Socket error during update: {e}")

    def draw(self):
        # Make background white
        self.screen.fill((255, 255, 255))

        # Draw tiles
        for t in self.tile_dict.values():
            self.screen.blit(t.image, t.rect)

        # Draw players
        for p in self.player_dict.values():
            self.screen.blit(p.image, p.rect)

        # Draw drag vector if dragging
        if self.player_dict[self.me].dragging:
            start_pos = self.player_dict[self.me].rect.center
            end_pos = start_pos + self.player_dict[self.me].drag_vector
            pygame.draw.line(self.screen, (0, 0, 255), start_pos, end_pos, 3)

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

            pygame.draw.line(self.screen, (0, 0, 255), end_pos, left_arrow, 3)
            pygame.draw.line(self.screen, (0, 0, 255), end_pos, right_arrow, 3)

    def run(self):  # RUNS ON MAIN THREAD
        conn, e = self.connect()

        if conn is None:
            print(f"Failed to connect to server with {e}")
            return
        
        self.running = True

        # Start update thread
        update_thread = threading.Thread(target=self.update, args=(conn,))
        update_thread.daemon = True
        update_thread.start()

        # Main loop
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # Everything gets done to the back buffer
            # Input handling
            self.handle_inputs(conn)

            # Drawing
            self.draw()

            # FPS Limit
            self.clock.tick(constants.FPS)

            # Flip the back buffer to the front
            pygame.display.flip()

        update_thread.join()
        self.disconnect(conn)
        pygame.quit()


if __name__ == "__main__":
    client = GameClient()
    client.run()
