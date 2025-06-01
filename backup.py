import json
import os
import subprocess
from datetime import datetime
import shutil

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

destination = config["destination"]["path"]
sources = config["sources"]

# Prepare paths
seven_zip_exe = "./tools/7za.exe"
temp_dir = "./work"
os.makedirs(temp_dir, exist_ok=True)
os.makedirs(destination, exist_ok=True)

# Generate archive filename
archive_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".7z"
temp_archive_path = os.path.join(temp_dir, archive_name)
final_archive_path = os.path.join(destination, archive_name)

# Build 7za command
cmd = [seven_zip_exe, "a", temp_archive_path] + sources

# Run the command
try:
    result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print("Archive created locally:", temp_archive_path)

    # Copy to destination
    shutil.copy2(temp_archive_path, final_archive_path)
    print("Archive copied to destination:", final_archive_path)

except subprocess.CalledProcessError as e:
    print("Error while creating archive:")
    print(e.stderr)
