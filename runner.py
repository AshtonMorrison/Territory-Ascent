import pygame
import pygame.freetype # Keep the import in case original code used it implicitly
import subprocess
import sys
import os
import multiprocessing
import signal  # Import signal handling module
import time    # Import time for sleep/timeouts

# Assuming these imports work correctly relative to runner.py's location
try:
    from server.server import get_ipv4, encode_ip
    from shared import constants
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure server/ and shared/ directories are accessible.")
    sys.exit(1)


# --- Original UI Classes (TextInput, Button) ---

class TextInput:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False
        self.inactive_color = pygame.Color("lightskyblue3")
        self.active_color = pygame.Color("dodgerblue2")
        # Use the original font definition
        self.font = pygame.font.SysFont(constants.FONT_NAME, 28)
        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_blink_speed = 500 # ms

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            was_active = self.active
            self.active = self.rect.collidepoint(event.pos)
            if not was_active and self.active:
                self.cursor_visible = True
                self.cursor_timer = pygame.time.get_ticks()
            # Original didn't explicitly hide cursor on deactivate, but might be good
            # elif was_active and not self.active:
            #    self.cursor_visible = False
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                # Original returned text on Enter
                return self.text
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            # Original check for adding text
            elif event.unicode.isprintable(): # Filter non-printable keys
                self.text += event.unicode
            # Reset cursor on keypress
            self.cursor_visible = True
            self.cursor_timer = pygame.time.get_ticks()
        return None

    def update(self):
        if self.active:
            current_time = pygame.time.get_ticks()
            if current_time - self.cursor_timer > self.cursor_blink_speed:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time
        # Ensure cursor isn't shown if inactive (Good practice)
        if not self.active:
            self.cursor_visible = False

    def draw(self, screen):
        color = self.active_color if self.active else self.inactive_color
        pygame.draw.rect(screen, color, self.rect, 2) # Original border width

        # Original text rendering
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        # Original blit position (with small padding)
        screen.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))

        if self.active and self.cursor_visible:
            # Original cursor calculation and drawing
            # Calculate width of text to position cursor correctly
            text_width = self.font.size(self.text)[0]
            cursor_pos_x = self.rect.x + 5 + text_width
            # Ensure cursor stays within bounds if text is too long (optional but good)
            # cursor_pos_x = min(cursor_pos_x, self.rect.right - 5)
            cursor_height = self.font.get_height()
            cursor_rect = pygame.Rect(
                cursor_pos_x, self.rect.y + (self.rect.height - cursor_height) // 2, # Center vertically
                2, cursor_height
            )
            pygame.draw.rect(screen, (255, 255, 255), cursor_rect)


class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        # Original font definition
        self.font = pygame.font.SysFont(constants.FONT_NAME, 28)
        self.color = pygame.Color("lightskyblue3")
        self.hover_color = pygame.Color("dodgerblue2") # Added hover color from original logic
        self.text_color = (255, 255, 255) # Assuming white text
        self.hover = False

    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        # Original color logic based on hover state
        color = self.hover_color if self.hover else self.color
        pygame.draw.rect(screen, color, self.rect, 2) # Original border width

        # Original text rendering and centering
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)


# --- Process Entry Points (Unchanged logic, no naming) ---

def server_process_entry(stop_event=None):
    """Entry point for server process"""
    print(f"[Server Process {os.getpid()}] Starting...") # Keep logs for debugging
    from server.server import GameServer
    server = GameServer()

    if stop_event:
        def monitor_stop():
            stop_event.wait() # Block until event is set
            print(f"[Server Process {os.getpid()}] Stop event received, signaling shutdown.")
            server.running = False # Signal the server's main loop to stop

        import threading
        monitor = threading.Thread(target=monitor_stop, daemon=True)
        monitor.start()

    try:
        server.start() # Assumes this loop checks server.running
    except Exception as e:
        print(f"[Server Process {os.getpid()}] Error: {e}")
    finally:
        print(f"[Server Process {os.getpid()}] Exited.")


def client_process_entry(code, stop_event=None):
    """Entry point for client process"""
    print(f"[Client Process {os.getpid()}] Starting with code: {code}") # Keep logs
    from client.game import GameClient
    client = GameClient(code)

    if stop_event:
        def monitor_stop():
            stop_event.wait()
            print(f"[Client Process {os.getpid()}] Stop event received, signaling shutdown.")
            client.running = False # Signal the client's main loop to stop

        import threading
        monitor = threading.Thread(target=monitor_stop, daemon=True)
        monitor.start()

    try:
        client.run() # Assumes this loop checks client.running
    except Exception as e:
        print(f"[Client Process {os.getpid()}] Error: {e}")
    finally:
        print(f"[Client Process {os.getpid()}] Exited.")


# --- Process Management (Improved logic) ---

def run_server():
    """Start the server using the appropriate method."""
    if getattr(sys, "frozen", False):
        print("Starting server using multiprocessing...")
        stop_event = multiprocessing.Event()
        # Ensure daemon=True so it doesn't block launcher exit if launcher crashes
        process = multiprocessing.Process(
            target=server_process_entry, args=(stop_event,), daemon=True
        )
        process.start()
        print(f"Server process ({process.pid}) started via multiprocessing.")
        return process, stop_event
    else:
        print("Starting server using subprocess...")
        base_path = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, "-m", "server.server"]
        try:
            # Use Popen for non-blocking execution
            process = subprocess.Popen(cmd, cwd=base_path)
            print(f"Server process ({process.pid}) started via subprocess.")
            return process, None # No stop event for subprocess
        except FileNotFoundError:
            print(f"Error: Could not find server.server module. Command: {' '.join(cmd)}")
            return None, None
        except Exception as e:
            print(f"Error starting server subprocess: {e}")
            return None, None


def run_client(code):
    """Start the client using the appropriate method."""
    if not code:
        print("Error: Cannot start client without a code.")
        return None, None

    if getattr(sys, "frozen", False):
        print(f"Starting client for code {code} using multiprocessing...")
        stop_event = multiprocessing.Event()
        process = multiprocessing.Process(
            target=client_process_entry, args=(code, stop_event,), daemon=True
        )
        process.start()
        print(f"Client process ({process.pid}) started via multiprocessing.")
        return process, stop_event
    else:
        print(f"Starting client for code {code} using subprocess...")
        base_path = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, "-m", "client.game", code]
        try:
            process = subprocess.Popen(cmd, cwd=base_path)
            print(f"Client process ({process.pid}) started via subprocess.")
            return process, None # No stop event for subprocess
        except FileNotFoundError:
             print(f"Error: Could not find client.game module. Command: {' '.join(cmd)}")
             return None, None
        except Exception as e:
            print(f"Error starting client subprocess: {e}")
            return None, None


def is_process_running(process):
    """Check if a process (multiprocessing or subprocess) is running."""
    if process is None:
        return False
    try:
        if isinstance(process, multiprocessing.Process):
            # Check if the process object itself exists and is alive
            return process.is_alive()
        elif isinstance(process, subprocess.Popen):
            # Check if the subprocess has terminated
            return process.poll() is None
    except Exception as e:
        # Can happen if process handle becomes invalid after termination
        # print(f"Error checking process status: {e}") # Optional debug log
        return False
    return False # Should not be reached if process is valid object


# --- Cleanup Logic (Improved logic) ---

def cleanup_processes(server_proc, server_evt, client_proc, client_evt):
    """Attempt graceful shutdown of child processes."""
    print("Initiating cleanup...")
    processes_to_wait_gracefully = []

    # 1. Signal multiprocessing processes to stop via event
    if client_proc and client_evt and isinstance(client_proc, multiprocessing.Process):
        print(f"Signaling client process ({client_proc.pid}) via event...")
        try:
            client_evt.set()
            processes_to_wait_gracefully.append(("Client", client_proc))
        except Exception as e:
            print(f"Error setting client stop event: {e}") # Log error but continue

    if server_proc and server_evt and isinstance(server_proc, multiprocessing.Process):
        print(f"Signaling server process ({server_proc.pid}) via event...")
        try:
            server_evt.set()
            processes_to_wait_gracefully.append(("Server", server_proc))
        except Exception as e:
            print(f"Error setting server stop event: {e}")

    # 2. Wait for multiprocessing processes to join (graceful shutdown timeout)
    graceful_shutdown_timeout = 2.0 # seconds to wait for clean exit
    start_wait = time.time()

    for name, proc in processes_to_wait_gracefully:
        if is_process_running(proc): # Check if it didn't already die
            print(f"Waiting up to {graceful_shutdown_timeout:.1f}s for {name} ({proc.pid}) to join...")
            join_timeout = max(0.1, graceful_shutdown_timeout - (time.time() - start_wait))
            try:
                proc.join(timeout=join_timeout)
                if proc.is_alive():
                    print(f"{name} ({proc.pid}) did not exit gracefully after event.")
                else:
                     print(f"{name} ({proc.pid}) joined successfully.")
            except Exception as e:
                 print(f"Error joining {name} process ({proc.pid}): {e}")


    # 3. Terminate any remaining processes (multiprocessing or subprocess)
    print("Checking for processes needing termination...")
    processes_to_terminate = []
    if is_process_running(client_proc):
        processes_to_terminate.append(("Client", client_proc))
    if is_process_running(server_proc):
        # Avoid double-adding if it was already in the list but failed join
        if ("Server", server_proc) not in [(n,p) for n, p in processes_to_wait_gracefully if p == server_proc]:
             processes_to_terminate.append(("Server", server_proc))


    if processes_to_terminate:
        for name, proc in processes_to_terminate:
            print(f"Terminating {name} ({proc.pid})...")
            try:
                proc.terminate()
                # Short wait after terminate for OS cleanup (optional)
                if isinstance(proc, multiprocessing.Process):
                    proc.join(timeout=0.5) # Short join after terminate
                elif isinstance(proc, subprocess.Popen):
                    proc.wait(timeout=0.5) # Wait for subprocess after terminate
            except (ProcessLookupError, subprocess.TimeoutExpired, AttributeError):
                pass # Process already gone or didn't die quickly/error during access
            except Exception as e:
                print(f"Error during termination of {name} ({proc.pid}): {e}")
    else:
        print("No processes needed termination.")

    print("Cleanup finished.")


# --- Main Function (Original UI layout, improved process handling) ---

def main():
    # --- Multiprocessing setup for frozen apps ---
    if getattr(sys, "frozen", False):
        # This is crucial for bundled executables, call it early.
        multiprocessing.freeze_support()
        # Optional: Set start method if default ('fork' on Linux/macOS) causes issues
        # if sys.platform != 'win32':
        #     # 'spawn' is generally safer with GUI libs but slower
        #     try:
        #         multiprocessing.set_start_method('spawn', force=True)
        #         print("Set multiprocessing start method to 'spawn'")
        #     except RuntimeError:
        #          print("Could not force multiprocessing start method to 'spawn'")

    pygame.init()
    # Ensure font module is initialized (good practice)
    if not pygame.font.get_init():
        pygame.font.init()
    # If freetype was used anywhere (even implicitly by SysFont sometimes)
    if 'pygame.freetype' in sys.modules and not pygame.freetype.get_init():
         try:
            pygame.freetype.init()
         except Exception: # Handle cases where freetype might not be available/init fails
            print("Pygame freetype init failed.")


    # Original screen dimensions and caption
    screen_width = 500
    screen_height = 400
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Launcher") # Original caption
    clock = pygame.time.Clock() # For potential frame rate limiting

    # Original font definitions
    title_font = pygame.font.SysFont(constants.FONT_NAME, 35)
    label_font = pygame.font.SysFont(constants.FONT_NAME, 25)
    # Note: Ensure constants.FONT_NAME is valid on the target system

    # Original UI Element Initialization
    text_input = TextInput(75, 140, 350, 40)
    server_button = Button(75, 210, 350, 40, "Start Server")
    connect_button = Button(75, 260, 350, 40, "Connect to Server")
    instructions_button = Button(75, 330, 350, 40, "Instructions")

    # Process tracking variables
    server_process = None
    client_process = None
    server_stop_event = None # Only used for multiprocessing
    client_stop_event = None # Only used for multiprocessing
    server_code = None # Store the code when server is started by launcher
    last_process_check_time = 0
    process_check_interval = 1500 # Check every 1.5 seconds

    # Original instructions state and text
    show_instructions = False
    instructions_text = [
        "How to Play Territory Ascent:",
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

    # --- Signal Handling Setup ---
    running = True
    def handle_exit_signal(sig, frame):
        nonlocal running
        print(f"Received signal {sig}, initiating shutdown...")
        running = False # Trigger normal exit from the main loop

    # Catch Ctrl+C and termination signals to allow graceful cleanup
    signal.signal(signal.SIGINT, handle_exit_signal)
    signal.signal(signal.SIGTERM, handle_exit_signal)

    # --- Main Loop ---
    while running:
        current_time = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        # --- Event Handling (Original Logic) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("QUIT event received.")
                running = False

            if show_instructions:
                # Original instruction closing logic
                if event.type == pygame.MOUSEBUTTONDOWN:
                    show_instructions = False
                continue # Skip other UI interaction when instructions are shown

            # Handle text input field events
            result = text_input.handle_event(event)
            # Note: Original code didn't use 'result' directly here,
            # connection was tied to button clicks. Keep that behavior.

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left click
                    if server_button.rect.collidepoint(event.pos):
                        # Original logic: Start server and client only if server isn't running
                        if not is_process_running(server_process):
                            print("Start Server button clicked.")
                            server_process, server_stop_event = run_server()
                            if server_process:
                                # Original: Wait briefly, get code, start client
                                print("Waiting briefly for server to initialize...")
                                pygame.time.wait(1000) # Original wait time
                                try:
                                    ipv4 = get_ipv4()
                                    if ipv4:
                                        server_code = encode_ip(ipv4)
                                        print(f"Server started. Code: {server_code}")
                                        # Start client automatically ONLY if not already running
                                        if not is_process_running(client_process):
                                            print("Automatically starting client...")
                                            client_process, client_stop_event = run_client(server_code)
                                        else:
                                             print("Client already running, not starting another.")
                                    else:
                                        print("Could not determine server IP after starting.")
                                        # Consider stopping the server if IP failed? Optional.
                                        # cleanup_processes(server_process, server_stop_event, None, None)
                                        # server_process, server_stop_event = None, None
                                except Exception as e:
                                     print(f"Error getting/encoding IP: {e}")
                                     # Maybe cleanup server process here too?
                            else:
                                print("Failed to start server process.")
                        else:
                            print("Server is already running.") # Button shouldn't be shown, but safety check

                    elif connect_button.rect.collidepoint(event.pos):
                        print("Connect button clicked.")
                        code_to_use = text_input.text.strip() # Use entered text

                        # Original logic: Connect using entered code OR existing server code if input is empty
                        if not code_to_use and server_code:
                             print("Input field empty, using own server code.")
                             code_to_use = server_code

                        if code_to_use:
                            if not is_process_running(client_process):
                                print(f"Attempting to connect with code: {code_to_use}")
                                client_process, client_stop_event = run_client(code_to_use)
                            else:
                                print("Client is already running.")
                        else:
                            print("No code entered and no local server code available.")

                    elif instructions_button.rect.collidepoint(event.pos):
                        print("Instructions button clicked.")
                        show_instructions = True

        # --- Update UI Elements (Original Logic) ---
        text_input.update()
        # Only update buttons if they are potentially clickable
        if not is_process_running(server_process):
            server_button.update(mouse_pos)
        connect_button.update(mouse_pos)
        instructions_button.update(mouse_pos)

        # --- Process State Checks (Improved Logic) ---
        # Periodically check if processes ended unexpectedly
        if current_time - last_process_check_time > process_check_interval:
            server_was_running = is_process_running(server_process)
            client_was_running = is_process_running(client_process)

            if server_process and not server_was_running:
                print("Detected server process has stopped unexpectedly.")
                server_process = None
                server_code = None # Clear the code display
                server_stop_event = None # Clear the event handle
                # Don't kill client - let it handle disconnect

            if client_process and not client_was_running:
                print("Detected client process has stopped unexpectedly.")
                client_process = None
                client_stop_event = None # Clear the event handle

            # Only update check time if checks were actually performed
            if server_was_running or client_was_running or server_process or client_process:
                 last_process_check_time = current_time


        # --- Drawing (Original Logic) ---
        screen.fill((20, 20, 30)) # Original background

        # Draw Title (Original)
        title_surface = title_font.render("Territory Ascent", True, (255, 255, 255))
        title_rect = title_surface.get_rect(centerx=screen.get_width() // 2, y=40)
        screen.blit(title_surface, title_rect)

        if show_instructions:
            # --- Draw Instructions Panel (Original) ---
            # Create a semi-transparent overlay or a distinct panel
            instruction_panel = pygame.Surface((450, 320), pygame.SRCALPHA) # Use SRCALPHA for potential transparency
            instruction_panel.fill((40, 40, 60, 230)) # Darker, semi-transparent background

            # Draw border (optional, but nice)
            pygame.draw.rect(
                instruction_panel,
                (100, 100, 180, 255), # Opaque border color
                instruction_panel.get_rect(), # Use panel's rect
                2, # Border width
                border_radius=5 # Rounded corners
            )

            # Center the panel on the screen
            panel_rect = instruction_panel.get_rect(
                center=(screen_width // 2, screen_height // 2)
            )
            screen.blit(instruction_panel, panel_rect)

            # Draw instructions text (Original formatting and positioning)
            y_offset = panel_rect.top + 20 # Start drawing text inside the panel
            line_height_map = {
                "How to Play Territory Ascent:": 35, # Larger title font needs more space
                "Movement Controls:": 28, # Header font
                "Game Objective:": 28, # Header font
                "": 10, # Blank line spacing
                "default": 22 # Default line spacing
            }
            for i, line in enumerate(instructions_text):
                font_to_use = label_font # Default font
                color = (255, 255, 255) # Default color
                x_offset = panel_rect.left + 40 # Default indent for items

                # Apply original formatting rules
                if i == 0: # Title
                    font_to_use = title_font
                    color = (255, 255, 100) # Yellowish
                    # Center title within the panel
                    temp_surf = font_to_use.render(line, True, color)
                    x_offset = panel_rect.centerx - temp_surf.get_width() // 2
                elif line == "Movement Controls:" or line == "Game Objective:":
                    font_to_use = label_font # Using label font as header here
                    color = (180, 180, 255) # Light blue/purple
                    x_offset = panel_rect.left + 30 # Less indent for headers
                elif line == "":
                    y_offset += line_height_map[""] # Add space for blank line
                    continue
                elif line == "Click anywhere to close":
                     color = (200, 200, 200) # Dimmer color for footer
                     # Center footer
                     temp_surf = font_to_use.render(line, True, color)
                     x_offset = panel_rect.centerx - temp_surf.get_width() // 2


                text_surf = font_to_use.render(line, True, color)
                screen.blit(text_surf, (x_offset, y_offset))

                # Increment y_offset based on line type
                y_offset += line_height_map.get(line, line_height_map["default"])

        else:
            # --- Draw Main UI (Original Logic) ---
            # Check if server is running *locally* and has a code
            if is_process_running(server_process) and server_code:
                # Display server code (Original layout)
                code_label = label_font.render(
                    "Your Server Code:", True, (200, 200, 200)
                )
                code_label_rect = code_label.get_rect(
                    centerx=screen.get_width() // 2, y=100 # Original position
                )
                screen.blit(code_label, code_label_rect)

                # Use a slightly larger font for the code itself if desired
                code_display_font = pygame.font.SysFont(constants.FONT_NAME, 30)
                code_surface = code_display_font.render(server_code, True, (255, 255, 100))
                code_rect = code_surface.get_rect(
                    centerx=screen.get_width() // 2, y=130 # Original position
                )
                screen.blit(code_surface, code_rect)

                # Do not draw the input field or server button when showing code
            else:
                # Display input field and label (Original layout)
                input_label = label_font.render(
                    "Enter Server Code:", True, (200, 200, 200)
                )
                input_label_rect = input_label.get_rect(
                    centerx=screen.get_width() // 2, y=110 # Original position
                )
                screen.blit(input_label, input_label_rect)
                text_input.draw(screen) # Draw the input field itself

                # Draw server button only if server process isn't running
                server_button.draw(screen)

            # Always draw Connect and Instructions buttons (Original)
            connect_button.draw(screen)
            instructions_button.draw(screen)

        pygame.display.flip()
        clock.tick(60) # Limit frame rate (optional but good practice)
        # --- End of Main Loop ---

    # --- Cleanup ---
    print("Main loop exited. Starting cleanup...")
    # Pass all handles to the cleanup function
    cleanup_processes(server_process, server_stop_event, client_process, client_stop_event)

    pygame.quit()
    print("Pygame quit.")
    sys.exit(0) # Explicit exit


if __name__ == "__main__":
    # Crucial for multiprocessing safety, especially on Windows/macOS 'spawn'
    main()