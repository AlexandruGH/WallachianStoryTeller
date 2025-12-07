import subprocess
import sys
import os

# Get path to exhaustive_compiler.py relative to this script
script_dir = os.path.dirname(os.path.abspath(__file__))
compiler_script = os.path.join(script_dir, "exhaustive_compiler.py")

with open("compiler_output.txt", "w") as f:
    try:
        result = subprocess.run([sys.executable, compiler_script], capture_output=True, text=True)
        f.write("STDOUT:\n")
        f.write(result.stdout)
        f.write("\nSTDERR:\n")
        f.write(result.stderr)
        f.write(f"\nReturn Code: {result.returncode}")
    except Exception as e:
        f.write(f"Exception: {e}")
