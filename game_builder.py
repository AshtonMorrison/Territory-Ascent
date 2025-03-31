import PyInstaller.__main__
import os
import sys
import shutil


def build_exe(debug=False):
    # Get the current directory
    base_path = os.path.dirname(os.path.abspath(__file__))

    # Create a clean build folder
    if os.path.exists(os.path.join(base_path, "build")):
        shutil.rmtree(os.path.join(base_path, "build"))
    if os.path.exists(os.path.join(base_path, "dist")):
        shutil.rmtree(os.path.join(base_path, "dist"))

    # Basic command
    cmd = [
        "runner.py",  # Your main script
        "--name=Territory Ascent",  # Name of the output executable
        "--noconfirm",  # Overwrite output without asking
        "--hidden-import=pygame",
        "--hidden-import=client.game",
        "--hidden-import=server.server",
        "--hidden-import=msgpack",
        "--hidden-import=multiprocessing",
        "--hidden-import=multiprocessing.pool",
    ]

    # Determine the proper path separator for PyInstaller
    separator = ";" if os.name == "nt" else ":"

    # Add data files
    cmd.extend(
        [
            f"--add-data=shared{separator}shared",
            f"--add-data=server{separator}server",
            f"--add-data=client{separator}client",
        ]
    )

    # Add debug options if needed
    if debug:
        cmd.append("--debug=all")
        cmd.remove("--windowed")  # Show console for debug output
    else:
        cmd.append("--onefile")  # Single file only in release mode

    # Clean option
    cmd.append("--clean")

    # Run PyInstaller
    PyInstaller.__main__.run(cmd)

    print(f"Build completed! Check the 'dist' folder for your executable.")


if __name__ == "__main__":
    debug_mode = "--debug" in sys.argv
    build_exe(debug_mode)
