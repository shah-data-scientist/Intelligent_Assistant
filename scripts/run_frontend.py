"""Helper script to run the Streamlit frontend."""

import subprocess
import sys
from pathlib import Path


def main():
    """Run the Streamlit app."""
    project_root = Path(__file__).parent.parent
    app_path = project_root / "src" / "frontend" / "app.py"

    if not app_path.exists():
        print(f"Error: Streamlit app not found at {app_path}")
        sys.exit(1)

    print("Starting Streamlit app...")
    print("App URL: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server.\n")

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_path),
                "--server.address=localhost",
                "--server.port=8501",
                "--server.headless=true",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        print("\nShutting down Streamlit app...")
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
