import pygame
import pygame.freetype
import subprocess
import sys
import socket
import base64
import os
from server.server import get_ipv4, encode_ip
import threading


class TextInput:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False
        self.color = pygame.Color("lightskyblue3")
        self.font = pygame.font.Font(None, 32)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return None

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, 2)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))


class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.Font(None, 32)
        self.color = pygame.Color("lightskyblue3")

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, 2)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)


def run_server():
    # Get the parent directory path
    base_path = os.path.dirname(os.path.abspath(__file__))
    return subprocess.Popen([sys.executable, "-m", "server.server"], cwd=base_path)


def run_client(code):
    # Get the parent directory path
    base_path = os.path.dirname(os.path.abspath(__file__))
    return subprocess.Popen([sys.executable, "-m", "client.game", code], cwd=base_path)


def is_process_running(process):
    if process is None:
        return False
    return process.poll() is None


def main():
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("Game Launcher")

    text_input = TextInput(50, 100, 300, 40)
    server_button = Button(50, 160, 300, 40, "Start Server")
    connect_button = Button(50, 220, 300, 40, "Connect to Server")

    server_process = None
    client_process = None
    server_code = None

    running = True
    while running:
        screen.fill((0, 0, 0))

        # Check if server has closed
        if server_process and not is_process_running(server_process):
            server_process = None
            server_code = None
            if client_process:
                client_process.terminate()
                client_process = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            result = text_input.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if server_button.rect.collidepoint(event.pos):
                    if not server_process:
                        server_process = run_server()
                        # Wait briefly for server to start
                        pygame.time.wait(1000)
                        # Get the server code
                        server_code = encode_ip(get_ipv4())
                        # Start client with the server code
                        client_process = run_client(server_code)

                elif connect_button.rect.collidepoint(event.pos):
                    if text_input.text:
                        client_process = run_client(text_input.text)

        # Draw UI elements
        if server_code:
            code_font = pygame.font.Font(None, 36)
            code_surface = code_font.render(
                f"Server Code: {server_code}", True, (255, 255, 255)
            )
            screen.blit(code_surface, (50, 50))
        else:
            text_input.draw(screen)

        server_button.draw(screen)
        connect_button.draw(screen)

        pygame.display.flip()

    if server_process:
        server_process.terminate()
    if client_process:
        client_process.terminate()
    pygame.quit()


if __name__ == "__main__":
    main()
