import socket
import json
import threading
import pygame
from shared import constants
from .tile import Tile
from .player import Player
from .tilemaps import sample_tile_map


class GameServer:
    def __init__(self, host="0.0.0.0"):
        self.host = host
        self.port = constants.PORT
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True
        self.server.settimeout(1.0)
        self.clients = {}  # Maps client address to player objects

        self.sprite_groups = {
            "ground": pygame.sprite.Group(),  # Used for Collision
            "platform": pygame.sprite.Group(),  # Used for Collision
            "players": pygame.sprite.Group(),  # Used for Collision
        }

        self.lock = threading.Lock()
        self.clock = pygame.time.Clock()

        # Player Colors
        self.unused_colors = [
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "pink",
            "cyan",
        ]  # 8 Players, should be fine
        self.used_colors = []

        # Tilemap
        self.tile_size = constants.TILE_SIZE
        self.tile_dict = (
            {}
        )  # used to access tiles by (x, y) coordinates. MIGHT NOT NEED DEPENDING ON LATER IMPLEMENTATION
        self.tile_data = []  # used for initial sending of tile map to clients

        # Tilemap layout (0: empty, 1: ground, 2: platform)
        self.tile_map = sample_tile_map

        self.create_tile_map()

    def create_tile_map(self):
        for row in range(len(self.tile_map)):
            for col in range(len(self.tile_map[row])):
                x = col * self.tile_size
                y = row * self.tile_size

                # Ground
                if self.tile_map[row][col] == 1:
                    self.tile_dict[(x, y)] = Tile(
                        x,
                        y,
                        self.tile_size,
                        self.tile_size,
                        1,
                        self.sprite_groups["ground"],
                    )
                    self.tile_data.append({"x": x, "y": y, "type": 1})

                # Platform
                elif self.tile_map[row][col] == 2:
                    self.tile_dict[(x, y)] = Tile(
                        x,
                        y,
                        self.tile_size,
                        self.tile_size,
                        2,
                        self.sprite_groups["platform"],
                    )
                    self.tile_data.append({"x": x, "y": y, "type": 2})

    def handle_client(self, conn, addr):
        print(f"New connection: {addr}")
        color = self.get_color()
        if color == "Error: No more colors available":
            conn.sendall(json.dumps("Error: No more colors available").encode())
            conn.close()
            return
        player = Player(color, 100, 100, self.tile_size, self.tile_size)
        player.conn = conn  # Store connection for broadcasting
        self.clients[addr] = player
        self.sprite_groups["players"].add(player)

        # Send initial information (tile map, player location, tile state, etc)
        conn.sendall(
            json.dumps(
                {
                    "type": "INITIAL",
                    "TileMap": self.tile_data,
                    "Players": self.get_player_state(),
                    "YourPlayer": color,
                    "MapState": self.get_map_state(),
                }
            ).encode()
        )

        try:
            while self.running:
                try:
                    data = ""
                    while True:
                        chunk = conn.recv(2048).decode()
                        if not chunk:
                            break
                        data += chunk
                        try:
                            player_data = json.loads(data)
                            break  # Successfully parsed JSON, exit loop
                        except json.JSONDecodeError:
                            # Incomplete JSON, continue receiving
                            continue

                    # Handle client input
                    if player_data["type"] == "DISCONNECT":
                        conn.sendall("DISCONNECTED".encode())
                        break

                    # Parse client input, PLAYER UPDATE AND TILE UPDATE DO NOT GET DONE HERE
                    # They are done in the game loop, you must somehow send the input to the game loop
                    # and then update the player there, maybe saving the input as a tag or in a queue in the player object
                    # Currently I have tag implemented, but if that doesnt work for you try the queue method

                    # Handle movement input
                    elif player_data["type"] == "MOVE":
                        # player = self.clients[addr]
                        if player_data["direction"] in ["left", "right"]:
                            player.direction = player_data["direction"]
                        else:
                            print(f"Invalid direction: {player_data['direction']}")
                    
                    # Handle jump input 
                    elif player_data["type"] == "JUMP":
                        # player = self.clients[addr]
                        player.jump = True
                        player.drag_vector = pygame.math.Vector2(
                            player_data["drag_x"],
                            player_data["drag_y"]
                        )

                except socket.timeout:
                    continue
        except Exception as e:
            print(f"Error with client {addr}: {e}")
        finally:
            conn.close()
            self.unused_colors.append(player.color)
            self.used_colors.remove(player.color)
            with self.lock:
                del self.clients[addr]
            print(f"Client {addr} disconnected.")

    def get_player_state(self):
        return [
            {"x": p.position.x, "y": p.position.y, "color": p.color, "in_air": p.in_air}
            for p in self.clients.values()
        ]

    def get_map_state(self):
        # TO BE ADDED FOR WHEN TILES ACTUALLY CHANGE
        # So, [{"x": t.x, "y": t.y, "color": t.color} for t in self.updated_tiles] or something similar
        pass

    def get_color(self):
        if len(self.unused_colors) == 0:
            return "Error: No more colors available"
        color = self.unused_colors.pop(0)
        self.used_colors.append(color)
        return color

    def broadcast(self):
        """Broadcasts game state to all connected clients"""
        game_state = {
            "type": "STATE",
            "players": self.get_player_state(),
            "map": self.get_map_state(),
        }
        message = json.dumps(game_state).encode()

        with self.lock:
            for addr, player in list(self.clients.items()):
                try:
                    player.conn.sendall(message)
                except:
                    print(f"Failed to send to {addr}")
                    del self.clients[addr]

    def stop(self):
        """Cleanly stop the server"""
        self.running = False
        # Create a temporary socket to unblock accept()
        try:
            tmp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tmp_socket.connect((self.host, self.port))
            tmp_socket.close()
        except:
            pass

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Server listening on {self.host}:{self.port}")
        print(f"IP address of server is: 192.168.0.203 not, {socket.gethostbyname(socket.gethostname())}")

        # Start game loop thread
        game_thread = threading.Thread(target=self.game_loop)
        game_thread.daemon = True
        game_thread.start()

        # Accept connections
        try:
            while self.running:
                try:
                    conn, addr = self.server.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client, args=(conn, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            self.stop()
            # Clean up
            for addr, player in list(self.clients.items()):
                try:
                    player.conn.sendall(json.dumps({"type": "SHUTTING DOWN"}).encode())
                    player.conn.close()
                except:
                    pass
            self.server.close()
            print("Server shut down complete")

    def game_loop(self):
        """Main game loop running at 60 FPS"""
        while self.running:
            # Update all players
            with self.lock:
                for player in self.clients.values():
                    player.update(self.sprite_groups)

            # Update tiles
            # for tile in self.sprite_groups["platform"]:
            # tile.update(self.sprite_groups)

            # Broadcast state
            self.broadcast()

            # Maintain 60 FPS
            self.clock.tick(60)


if __name__ == "__main__":
    server = GameServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
