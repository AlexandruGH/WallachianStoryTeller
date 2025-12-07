import subprocess
import sys

with open("validate_output.txt", "w", encoding='utf-8') as f:
    try:
        result = subprocess.run([sys.executable, "validate_and_graph.py"], capture_output=True, text=True, encoding='utf-8')
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\nReturn Code: {result.returncode}")
    except Exception as e:
        f.write(f"Exception: {e}")
