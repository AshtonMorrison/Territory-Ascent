import pygame
import pygame.freetype
import subprocess
import sys
import os
import multiprocessing
from server.server import get_ipv4, encode_ip
from shared import constants


class TextInput:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False
        self.inactive_color = pygame.Color("lightskyblue3")
        self.active_color = pygame.Color("dodgerblue2")
        self.font = pygame.font.SysFont(constants.FONT_NAME, 28)
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_speed = 500

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Was active and now inactive
            was_active = self.active
            # Check if clicked on input box
            self.active = self.rect.collidepoint(event.pos)
            # Reset cursor visibility on activation change
            if not was_active and self.active:
                self.cursor_visible = True
                self.cursor_timer = pygame.time.get_ticks()
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
            # Reset cursor visibility on keypress
            self.cursor_visible = True
            self.cursor_timer = pygame.time.get_ticks()
        return None

    def update(self):
        # Handle cursor blinking
        if self.active:
            current_time = pygame.time.get_ticks()
            if current_time - self.cursor_timer > self.cursor_blink_speed:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time

    def draw(self, screen):
        # Change color based on active state
        color = self.active_color if self.active else self.inactive_color
        pygame.draw.rect(screen, color, self.rect, 2)

        # Render text
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))

        # Draw cursor if active
        if self.active and self.cursor_visible:
            cursor_pos = self.rect.x + 5 + self.font.size(self.text)[0]
            cursor_rect = pygame.Rect(
                cursor_pos, self.rect.y + 5, 2, self.font.get_height()
            )
            pygame.draw.rect(screen, (255, 255, 255), cursor_rect)


class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = pygame.font.SysFont(constants.FONT_NAME, 28)
        self.color = pygame.Color("lightskyblue3")
        self.hover = False

    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        color = pygame.Color("dodgerblue2") if self.hover else self.color
        pygame.draw.rect(screen, color, self.rect, 2)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)


def server_process_entry(stop_event=None):
    """Entry point for server process"""
    from server.server import GameServer

    server = GameServer()
    if stop_event:
        # Create a monitoring thread to check for stop event
        def monitor_stop():
            stop_event.wait()
            server.running = False

        import threading

        monitor = threading.Thread(target=monitor_stop)
        monitor.daemon = True
        monitor.start()

    server.start()


def client_process_entry(code, stop_event=None):
    """Entry point for client process"""
    from client.game import GameClient

    client = GameClient(code)
    if stop_event:
        # Create a monitoring thread to check for stop event
        def monitor_stop():
            stop_event.wait()
            client.running = False

        import threading

        monitor = threading.Thread(target=monitor_stop)
        monitor.daemon = True
        monitor.start()

    client.run()


def run_server():
    """Start the server either as a subprocess or using multiprocessing"""
    # Check if running as bundled executable
    if getattr(sys, "frozen", False):
        # We're running in a bundle - use multiprocessing
        stop_event = multiprocessing.Event()
        process = multiprocessing.Process(
            target=server_process_entry, args=(stop_event,)
        )
        process.daemon = True
        process.start()
        return process, stop_event
    else:
        # We're running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
        return (
            subprocess.Popen([sys.executable, "-m", "server.server"], cwd=base_path),
            None,
        )


def run_client(code):
    """Start the client either as a subprocess or using multiprocessing"""
    if getattr(sys, "frozen", False):
        # We're running in a bundle - use multiprocessing
        stop_event = multiprocessing.Event()
        process = multiprocessing.Process(
            target=client_process_entry, args=(code, stop_event)
        )
        process.daemon = True
        process.start()
        return process, stop_event
    else:
        # We're running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
        return (
            subprocess.Popen(
                [sys.executable, "-m", "client.game", code], cwd=base_path
            ),
            None,
        )


def is_process_running(process):
    """Check if a process is running"""
    if process is None:
        return False
    # Check if it's a subprocess.Popen object
    if hasattr(process, "poll"):
        return process.poll() is None
    # Check if it's a multiprocessing process
    elif hasattr(process, "is_alive"):
        return process.is_alive()
    return False


def main():
    # Initialize multiprocessing support
    if getattr(sys, "frozen", False):
        multiprocessing.freeze_support()

    pygame.init()
    screen = pygame.display.set_mode((500, 400))
    pygame.display.set_caption("Launcher")

    title_font = pygame.font.SysFont(constants.FONT_NAME, 35)
    label_font = pygame.font.SysFont(constants.FONT_NAME, 25)

    text_input = TextInput(75, 140, 350, 40)
    server_button = Button(75, 210, 350, 40, "Start Server")
    connect_button = Button(75, 260, 350, 40, "Connect to Server")
    instructions_button = Button(75, 330, 350, 40, "Instructions")

    server_process = None
    client_process = None
    server_stop_event = None
    client_stop_event = None
    server_code = None

    show_instructions = False
    instructions_text = [
        "How to Play (Placeholder):",
        "",
        "Movement Controls:",
        "Use A and D keys to move left and right",
        "Click and drag to jump",
        "",
        "Game Objective:",
        "Race to reach the goal",
        "If you step on an occupied tile, you reset",
        "",
        "Click anywhere to close",
    ]

    running = True
    while running:
        screen.fill((20, 20, 30))
        mouse_pos = pygame.mouse.get_pos()

        # Update UI elements
        text_input.update()
        server_button.update(mouse_pos)
        connect_button.update(mouse_pos)
        instructions_button.update(mouse_pos)

        # Check if server has closed
        if server_process and not is_process_running(server_process):
            server_process = None
            server_code = None
            server_stop_event = None
            if client_process:
                if hasattr(client_process, "terminate"):
                    client_process.terminate()
                if client_stop_event:
                    client_stop_event.set()
                client_process = None
                client_stop_event = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if show_instructions:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    show_instructions = False
                continue

            result = text_input.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if server_button.rect.collidepoint(event.pos):
                    if not server_process:
                        server_process, server_stop_event = run_server()
                        # Wait briefly for server to start
                        pygame.time.wait(1000)
                        # Get the server code
                        server_code = encode_ip(get_ipv4())
                        # Start client with the server code
                        client_process, client_stop_event = run_client(server_code)

                elif connect_button.rect.collidepoint(event.pos):
                    code_to_use = ""
                    if text_input.text:
                        code_to_use = text_input.text
                    elif server_code is not None:
                        code_to_use = server_code

                    if code_to_use:
                        client_process, client_stop_event = run_client(code_to_use)

                elif instructions_button.rect.collidepoint(event.pos):
                    show_instructions = True

        title_surface = title_font.render("Placeholder Name", True, (255, 255, 255))
        title_rect = title_surface.get_rect(centerx=screen.get_width() // 2, y=40)
        screen.blit(title_surface, title_rect)

        # Check if showing instructions
        if show_instructions:

            instruction_panel = pygame.Surface((450, 320))
            instruction_panel.fill((40, 40, 60))

            pygame.draw.rect(
                instruction_panel,
                (100, 100, 180),
                (0, 0, instruction_panel.get_width(), instruction_panel.get_height()),
                2,
            )

            panel_rect = instruction_panel.get_rect(
                center=(screen.get_width() // 2, screen.get_height() // 2)
            )
            screen.blit(instruction_panel, panel_rect)

            # Draw instructions text
            y_offset = panel_rect.top + 20
            for line in instructions_text:
                if line == "How to Play:":
                    text = title_font.render(line, True, (255, 255, 100))
                    text_rect = text.get_rect(
                        centerx=screen.get_width() // 2, y=y_offset
                    )
                    y_offset += 30
                elif line == "Movement Controls:" or line == "Game Objective:":
                    text = label_font.render(line, True, (180, 180, 255))
                    text_rect = text.get_rect(x=panel_rect.left + 30, y=y_offset)
                    y_offset += 25
                elif line == "":
                    y_offset += 10
                    continue
                else:
                    text = label_font.render(line, True, (255, 255, 255))
                    text_rect = text.get_rect(x=panel_rect.left + 40, y=y_offset)
                    y_offset += 22

                screen.blit(text, text_rect)
        else:
            # Draw regular UI elements
            if server_code:
                # Display server code
                code_label = label_font.render(
                    "Your Server Code:", True, (200, 200, 200)
                )
                code_label_rect = code_label.get_rect(
                    centerx=screen.get_width() // 2, y=100
                )
                screen.blit(code_label, code_label_rect)

                code_font = pygame.font.SysFont(constants.FONT_NAME, 30)
                code_surface = code_font.render(server_code, True, (255, 255, 100))
                code_rect = code_surface.get_rect(
                    centerx=screen.get_width() // 2, y=130
                )
                screen.blit(code_surface, code_rect)
            else:
                # Display input field and label
                input_label = label_font.render(
                    "Enter Server Code:", True, (200, 200, 200)
                )
                input_label_rect = input_label.get_rect(
                    centerx=screen.get_width() // 2, y=110
                )
                screen.blit(input_label, input_label_rect)
                text_input.draw(screen)

            if not server_process:
                server_button.draw(screen)

            connect_button.draw(screen)
            instructions_button.draw(screen)

        pygame.display.flip()

    # Clean up processes before exiting
    if server_process:
        if hasattr(server_process, "terminate"):
            server_process.terminate()
        if server_stop_event:
            server_stop_event.set()

    if client_process:
        if hasattr(client_process, "terminate"):
            client_process.terminate()
        if client_stop_event:
            client_stop_event.set()

    pygame.quit()


if __name__ == "__main__":
    main()
