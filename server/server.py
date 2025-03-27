import socket
import msgpack
import threading
import pygame
import random
from shared import constants
from .tile import Tile
from .player import Player
from . import tilemaps

# for encoding IP
import base64


def get_ipv4():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def encode_ip(ip):
    packed_ip = socket.inet_aton(ip)
    return base64.urlsafe_b64encode(packed_ip).decode().rstrip("=")


class GameServer:
    def __init__(self):
        self.host = constants.HOST
        self.port = constants.PORT
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )  # Enable SO_REUSEADDR
        self.server.settimeout(1.0)

        self.sprite_groups = {
            "ground": pygame.sprite.Group(),  # Used for Collision
            "platform": pygame.sprite.Group(),  # Used for Collision
            "goal": pygame.sprite.Group(),  # Used for Collision
            "players": pygame.sprite.Group(),  # Used for Collision and Broadcasting
            "waiting-players": pygame.sprite.Group(),  # Used for Waiting Room
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
        self.changed_tiles = []  # used for sending tile changes to clients
        self.tile_data = []  # used for initial sending of tile map to clients

        self.waiting_map = tilemaps.waiting_room
        self.game_maps = [tilemaps.game_1, tilemaps.game_2]
        self.current_map = None

        # Game Logic
        self.winner = None
        self.player_ready = {}  # Track which players are ready

        self.running = False  # Game Loop
        self.waiting = False  # Waiting Room
        self.game_running = False  # Game Running

    def create_tile_map(self, map):
        self.tile_data = []
        for row in range(len(map)):
            for col in range(len(map[row])):
                x = col * self.tile_size
                y = row * self.tile_size

                # Ground
                if map[row][col] == 1:
                    Tile(
                        x,
                        y,
                        self.tile_size,
                        self.tile_size,
                        1,
                        self.sprite_groups["ground"],
                    )
                    self.tile_data.append({"x": x, "y": y, "type": 1})

                # Platform
                elif map[row][col] == 2:
                    Tile(
                        x,
                        y,
                        self.tile_size,
                        self.tile_size,
                        2,
                        self.sprite_groups["platform"],
                    )
                    self.tile_data.append({"x": x, "y": y, "type": 2})

                # Goal
                elif map[row][col] == 3:
                    Tile(
                        x,
                        y,
                        self.tile_size,
                        self.tile_size,
                        3,
                        self.sprite_groups["goal"],
                    )
                    self.tile_data.append({"x": x, "y": y, "type": 3})

    def receive_message(self, sock):
        # First, receive the 4-byte header that contains the length
        length_data = b""
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                raise Exception("Error: Connection lost while receiving length header.")
            length_data += chunk

        # Convert the 4-byte length data to an integer
        message_length = int.from_bytes(length_data, byteorder="big")

        # Now, receive the actual message of the specified length
        message_data = b""
        while len(message_data) < message_length:
            chunk = sock.recv(message_length - len(message_data))
            if not chunk:
                raise Exception("Error: Connection lost while receiving message.")
            message_data += chunk

        return message_data

    def send_message(self, conn, message):
        message_pack = msgpack.packb(message)
        length_message = len(message_pack).to_bytes(4, byteorder="big")
        conn.sendall(length_message + message_pack)

    def handle_client(self, conn, addr):
        print(f"New connection: {addr}")
        color = self.get_color()
        if color == "Error: No more colors available":
            self.send_message(conn, "Error: No more colors available")
            conn.close()
            return

        player = Player(
            color, self.current_map["spawn"], self.tile_size, self.tile_size
        )
        player.conn = conn  # Store connection for broadcasting
        player.addr = addr  # Store address
        self.sprite_groups["players"].add(player)

        # Send initial game state
        initial_state = {
            "type": "INITIAL",
            "Players": self.get_player_state(),
            "TileMap": self.tile_data,
            "YourPlayer": player.color,
        }
        self.send_message(conn, initial_state)

        try:
            while self.running:
                try:
                    try:
                        data = self.receive_message(conn)
                        player_data = msgpack.unpackb(data)

                        # Handle disconnect input
                        if player_data["type"] == "DISCONNECT":
                            self.send_message(conn, "DISCONNECTED")
                            break

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
                                player_data["drag_x"], player_data["drag_y"]
                            )

                    except Exception as e:
                        print(f"Error processing message from {addr}: {e}")
                        break

                except socket.timeout:
                    continue
        except Exception as e:
            print(f"Error with client {addr}: {e}")
        finally:
            conn.close()
            self.unused_colors.append(player.color)
            self.used_colors.remove(player.color)
            with self.lock:
                self.sprite_groups["players"].remove(player)
            print(f"Client {addr} disconnected.")

    def get_player_state(self):
        return [
            {"x": p.position.x, "y": p.position.y, "color": p.color, "in_air": p.in_air}
            for p in self.sprite_groups["players"]
        ]

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
            "tiles": self.changed_tiles,
        }

        message = msgpack.packb(game_state)
        length_message = len(message).to_bytes(4, byteorder="big")

        with self.lock:
            for player in self.sprite_groups["players"]:
                try:
                    player.conn.sendall(length_message + message)
                except:
                    print(f"Failed to send to {player.addr}")
                    self.sprite_groups["players"].remove(player)

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

        # Clean up
        message = msgpack.packb({"type": "SHUTTING DOWN"})
        length_message = len(message).to_bytes(4, byteorder="big")

        for player in self.sprite_groups["players"]:
            try:
                player.conn.sendall(length_message + message)
                player.conn.close()
            except:
                pass

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"Server listening on {self.host}:{self.port}")
        print(f"IP address of server is: {get_ipv4()}")
        print(f"the code is: {encode_ip(get_ipv4())}")

        # Create waiting room
        self.current_map = self.game_maps[0]
        self.create_tile_map(self.current_map["map"])
        self.waiting = True

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
            self.server.close()
            print("Server shut down complete")

    def reset_game(self):
        """Resets the game state for a new round."""

        # Reset Tile Groups
        self.sprite_groups["ground"].empty()
        self.sprite_groups["platform"].empty()
        self.sprite_groups["goal"].empty()

        # Choose a new random map
        self.current_map = random.choice(self.game_maps)
        self.create_tile_map(self.current_map["map"])

        # Reset player positions
        with self.lock:
            for player in self.sprite_groups["players"]:
                player.reset_position(self.current_map["spawn"])

        # Reset winner
        self.winner = None

        # Send new game state to all players (including those in waiting room)
        new_state = {
            "type": "NEW GAME",
            "Players": self.get_player_state(),
            "TileMap": self.tile_data,
        }
        message = msgpack.packb(new_state)
        length_message = len(message).to_bytes(4, byteorder="big")
        with self.lock:
            for player in (
                self.sprite_groups["players"] or self.sprite_groups["waiting-players"]
            ):
                try:
                    player.conn.sendall(length_message + message)
                except:
                    print(f"Failed to send to {player.addr}")
                    player.conn.close()
                    if player in self.sprite_groups["players"]:
                        self.sprite_groups["players"].remove(player)
                    else:
                        self.sprite_groups["waiting-players"].remove(player)



    def game_over(self):
        if self.winner is not None:
            message = msgpack.packb({"type": "WINNER", "color": self.winner.color})
            length_message = len(message).to_bytes(4, byteorder="big")
            with self.lock:
                for player in self.sprite_groups["players"]:
                    try:
                        player.conn.sendall(length_message + message)
                    except:
                        print(f"Failed to send to {player.addr}")
                        player.conn.close()
                        self.sprite_groups["players"].remove(player)

            self.reset_game()

            self.countdown()

            self.game_running = True

    def game_loop(self):
        """Main game loop running at 45 FPS"""
        self.running = True
        while self.running:
            while self.waiting:
                self.game_running = True
                self.waiting = False

                pygame.time.wait(3000)
                for countdown_val in range(3, -1, -1):
                    message = msgpack.packb(
                        {"type": "COUNTDOWN", "countdown": countdown_val}
                    )
                    length_message = len(message).to_bytes(4, byteorder="big")
                    with self.lock:
                        for player in self.sprite_groups["players"]:
                            try:
                                player.conn.sendall(length_message + message)
                            except:
                                print(f"Failed to send to {player.addr}")
                                player.conn.close()
                                self.sprite_groups["players"].remove(player)

                    # Process updates for 1 second while waiting for countdown
                    start_time = pygame.time.get_ticks()
                    while pygame.time.get_ticks() - start_time < 1000:
                        # Update all players even during countdown
                        with self.lock:
                            for player in self.sprite_groups["players"]:
                                # Don't check for goal during countdown
                                player.update(
                                    self.sprite_groups,
                                    self.current_map["spawn"],
                                    check_goal=False,
                                )

                            for tile in self.sprite_groups["platform"]:
                                changed = tile.update(self.sprite_groups["players"])
                                if changed:
                                    self.changed_tiles.append(
                                        {
                                            "x": tile.rect.x,
                                            "y": tile.rect.y,
                                            "color": tile.color,
                                        }
                                    )

                        # Broadcast state
                        self.broadcast()

                        # Clear changed tiles
                        self.changed_tiles = []

                        # Small delay to prevent CPU hogging
                        pygame.time.wait(10)

            while self.game_running:
                # Update all players
                with self.lock:
                    for player in self.sprite_groups["players"]:
                        reached_goal = player.update(
                            self.sprite_groups,
                            self.current_map["spawn"],
                            check_goal=True,
                        )
                        if reached_goal:
                            self.winner = player
                            self.game_running = False
                            break

                    for tile in self.sprite_groups["platform"]:
                        changed = tile.update(self.sprite_groups["players"])
                        if changed:
                            self.changed_tiles.append(
                                {
                                    "x": tile.rect.x,
                                    "y": tile.rect.y,
                                    "color": tile.color,
                                }
                            )

                # Broadcast state
                self.broadcast()

                # Clear changed tiles
                self.changed_tiles = []

                # Maintain 45 FPS
                self.clock.tick(constants.FPS)

            self.game_over()

        server.stop()


if __name__ == "__main__":
    server = GameServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
