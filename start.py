#!/usr/bin/env python3
"""
Deployment Script for Cultural Events RAG Assistant

This script provides a simple interface to start all services (API + UI)
with proper environment validation and health checks.

Usage:
    python start.py                # Start both API and UI
    python start.py --api-only     # Start only API
    python start.py --ui-only      # Start only UI
    python start.py --check        # Check prerequisites
    python start.py --rebuild      # Rebuild FAISS index before starting
"""

import os
import sys
import subprocess
import time
import argparse
from pathlib import Path
from typing import Optional
import signal


class ServiceManager:
    """Manage API and UI services."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.api_process: Optional[subprocess.Popen] = None
        self.ui_process: Optional[subprocess.Popen] = None
        self.api_port = int(os.getenv("API_PORT", "8000"))
        self.ui_port = int(os.getenv("STREAMLIT_PORT", "8501"))

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully."""
        print("\n🛑 Shutting down services...")
        self.stop_services()
        sys.exit(0)

    def check_prerequisites(self) -> bool:
        """Verify all prerequisites are met."""
        print("🔍 Checking prerequisites...")
        print()

        checks_passed = True

        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 11):
            print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print(f"❌ Python 3.11+ required (found {python_version.major}.{python_version.minor})")
            checks_passed = False

        # Check Poetry
        try:
            result = subprocess.run(
                ["poetry", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✅ {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Poetry not found. Install: https://python-poetry.org/docs/#installation")
            checks_passed = False

        # Check .env file
        env_file = self.project_root / ".env"
        if env_file.exists():
            print(f"✅ .env file found")

            # Check for required keys
            with open(env_file) as f:
                env_content = f.read()

            if "MISTRAL_API_KEY" in env_content:
                # Check if it's set to a real value (not placeholder)
                if "your_mistral_api_key" not in env_content.lower():
                    print("✅ MISTRAL_API_KEY configured")
                else:
                    print("⚠️  MISTRAL_API_KEY is placeholder - update in .env")
                    checks_passed = False
            else:
                print("❌ MISTRAL_API_KEY missing in .env")
                checks_passed = False
        else:
            print("❌ .env file not found. Copy from .env.example")
            checks_passed = False

        # Check database
        db_file = self.project_root / "data" / "events.db"
        if db_file.exists():
            size_mb = db_file.stat().st_size / (1024 * 1024)
            print(f"✅ Events database found ({size_mb:.1f} MB)")
        else:
            print("⚠️  Events database not found - run data ingestion first")

        # Check FAISS index
        index_dir = self.project_root / "data" / "faiss_index"
        if index_dir.exists() and (index_dir / "index.faiss").exists():
            print(f"✅ FAISS index found")
        else:
            print("⚠️  FAISS index not found - will be created on first run")

        print()
        return checks_passed

    def rebuild_index(self):
        """Rebuild FAISS index."""
        print("🔨 Rebuilding FAISS index...")
        rebuild_script = self.project_root / "scripts" / "rebuild_index.py"

        if not rebuild_script.exists():
            print("⚠️  Rebuild script not found, skipping...")
            return

        try:
            subprocess.run(
                ["poetry", "run", "python", str(rebuild_script)],
                cwd=self.project_root,
                check=True
            )
            print("✅ FAISS index rebuilt successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to rebuild index: {e}")
            sys.exit(1)

    def start_api(self):
        """Start FastAPI server."""
        print(f"🚀 Starting API server on port {self.api_port}...")

        cmd = [
            "poetry", "run", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.api_port),
            "--reload"
        ]

        self.api_process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Wait for API to be ready
        time.sleep(3)

        if self.api_process.poll() is None:
            print(f"✅ API server started: http://localhost:{self.api_port}")
            print(f"   Swagger docs: http://localhost:{self.api_port}/docs")
            return True
        else:
            print("❌ API server failed to start")
            return False

    def start_ui(self):
        """Start Streamlit UI."""
        print(f"🚀 Starting Streamlit UI on port {self.ui_port}...")

        ui_file = self.project_root / "src" / "frontend" / "app.py"
        if not ui_file.exists():
            print(f"❌ UI file not found: {ui_file}")
            return False

        cmd = [
            "poetry", "run", "streamlit", "run",
            str(ui_file),
            "--server.port", str(self.ui_port),
            "--server.address", "0.0.0.0"
        ]

        self.ui_process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Wait for UI to be ready
        time.sleep(5)

        if self.ui_process.poll() is None:
            print(f"✅ Streamlit UI started: http://localhost:{self.ui_port}")
            return True
        else:
            print("❌ Streamlit UI failed to start")
            return False

    def stop_services(self):
        """Stop all running services."""
        if self.api_process:
            print("🛑 Stopping API server...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.api_process.kill()

        if self.ui_process:
            print("🛑 Stopping Streamlit UI...")
            self.ui_process.terminate()
            try:
                self.ui_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ui_process.kill()

    def monitor_services(self):
        """Monitor services and keep them running."""
        print()
        print("=" * 80)
        print("SERVICES RUNNING")
        print("=" * 80)
        print(f"API: http://localhost:{self.api_port}")
        print(f"UI:  http://localhost:{self.ui_port}")
        print()
        print("Press Ctrl+C to stop all services")
        print("=" * 80)
        print()

        try:
            while True:
                # Check if processes are still running
                if self.api_process and self.api_process.poll() is not None:
                    print("❌ API server stopped unexpectedly")
                    self.stop_services()
                    sys.exit(1)

                if self.ui_process and self.ui_process.poll() is not None:
                    print("❌ Streamlit UI stopped unexpectedly")
                    self.stop_services()
                    sys.exit(1)

                time.sleep(1)

        except KeyboardInterrupt:
            pass  # Handled by signal handler


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Start Cultural Events RAG Assistant services"
    )
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Start only the API server"
    )
    parser.add_argument(
        "--ui-only",
        action="store_true",
        help="Start only the Streamlit UI"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check prerequisites and exit"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild FAISS index before starting"
    )

    args = parser.parse_args()

    # Get project root
    project_root = Path(__file__).parent

    # Initialize manager
    manager = ServiceManager(project_root)

    # Check prerequisites
    print("=" * 80)
    print("CULTURAL EVENTS RAG ASSISTANT - DEPLOYMENT")
    print("=" * 80)
    print()

    if not manager.check_prerequisites():
        print()
        print("❌ Prerequisites check failed. Please fix the issues above.")
        sys.exit(1)

    if args.check:
        print("✅ All prerequisites satisfied!")
        sys.exit(0)

    # Rebuild index if requested
    if args.rebuild:
        manager.rebuild_index()
        print()

    # Start services
    print("=" * 80)
    print("STARTING SERVICES")
    print("=" * 80)
    print()

    try:
        if args.ui_only:
            if manager.start_ui():
                manager.monitor_services()
        elif args.api_only:
            if manager.start_api():
                manager.monitor_services()
        else:
            # Start both
            api_ok = manager.start_api()
            time.sleep(2)
            ui_ok = manager.start_ui()

            if api_ok and ui_ok:
                manager.monitor_services()
            else:
                print()
                print("❌ Failed to start all services")
                manager.stop_services()
                sys.exit(1)

    finally:
        manager.stop_services()


if __name__ == "__main__":
    main()
