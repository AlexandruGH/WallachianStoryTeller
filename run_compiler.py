import subprocess
import sys

with open("compiler_output.txt", "w") as f:
    try:
        result = subprocess.run([sys.executable, "exhaustive_compiler.py"], capture_output=True, text=True)
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\nReturn Code: {result.returncode}")
    except Exception as e:
        f.write(f"Exception: {e}")
