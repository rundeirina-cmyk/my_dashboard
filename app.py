import subprocess
import sys

if __name__ == '__main__':
    subprocess.run([
        sys.executable,
        "-m", "streamlit",
        "run", "dashboard.py",
        "--server.port", "8080",
        "--server.address", "0.0.0.0"
    ])
