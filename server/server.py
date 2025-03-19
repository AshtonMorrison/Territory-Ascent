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
        self.tile_groups = {
            "ground": pygame.sprite.Group(),  # Used for Collision
            "platform": pygame.sprite.Group(),  # Used for Collision
        }
        self.lock = threading.Lock()

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
                        self.tile_groups["ground"],
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
                        self.tile_groups["platform"],
                    )
                    self.tile_data.append({"x": x, "y": y, "type": 2})

    def handle_client(self, conn, addr):
        print(f"New connection: {addr}")
        player = Player((255, 0, 0), 100, 100, self.tile_size, self.tile_size)
        player.conn = conn  # Store connection for broadcasting
        self.clients[addr] = player

        # Send initial tile map
        conn.sendall(json.dumps({"type": "MAP", "TileMap": self.tile_data}).encode())

        try:
            while self.running:
                try:
                    data = conn.recv(1024).decode()
                    if not data:
                        break

                    # Parse client input
                    message = json.loads(data)
                    if message["type"] == "INPUT":
                        # Update player based on input
                        self.clients[addr].handle_input(message["input"])
                        # Broadcast new state to all clients
                        self.broadcast()
                except socket.timeout:
                    continue
        except Exception as e:
            print(f"Error with client {addr}: {e}")
        finally:
            conn.close()
            with self.lock:
                del self.clients[addr]
            print(f"Client {addr} disconnected.")

    def get_player_state(self):
        return [
            {"x": p.position.x, "y": p.position.y, "color": p.color}
            for p in self.clients.values()
        ]

    def get_map_state(self):
        # TO BE ADDED FOR WHEN TILES ACTUALLY CHANGE
        # So, [{"x": t.x, "y": t.y, "color": t.color} for t in self.tiles] or something similar
        pass

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

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Server listening on {self.host}:{self.port}")

        # Start game loop thread
        threading.Thread(target=self.game_loop).start()

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
            self.running = False  # Signal threads to stop
        finally:
            # Clean up
            for addr, player in list(self.clients.items()):
                try:
                    player.conn.close()
                except:
                    pass
            self.server.close()
            print("Server shut down complete")

    def game_loop(self):
        """Main game loop running at 60 FPS"""
        clock = pygame.time.Clock()
        while self.running:
            # Update all players
            with self.lock:
                for player in self.clients.values():
                    player.update(self.tile_groups)

            # Broadcast state
            self.broadcast()

            # Maintain 60 FPS
            clock.tick(60)


if __name__ == "__main__":
    try:
        server = GameServer()
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
