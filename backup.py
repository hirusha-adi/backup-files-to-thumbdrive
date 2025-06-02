import json
import os
import subprocess
from datetime import datetime
import shutil
import time
import string
import ctypes
import sys

def is_drive_connected_with_label(target_label):
    """Check if a removable drive with the given volume label is connected"""
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            try:
                # Get volume label using ctypes (Windows only)
                volume_name_buffer = ctypes.create_unicode_buffer(1024)
                file_system_name_buffer = ctypes.create_unicode_buffer(1024)
                serial_number = max_component_length = file_system_flags = ctypes.c_ulong()
                result = ctypes.windll.kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(drive),
                    volume_name_buffer,
                    ctypes.sizeof(volume_name_buffer),
                    ctypes.byref(serial_number),
                    ctypes.byref(max_component_length),
                    ctypes.byref(file_system_flags),
                    file_system_name_buffer,
                    ctypes.sizeof(file_system_name_buffer)
                )
                if result and volume_name_buffer.value == target_label:
                    return drive
            except Exception as e:
                continue
    return None


def main():
    # Load config
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Failed to load config.json: {e}")
        sys.exit(1)

    destination_type = config["destination"].get("type")
    destination_value = config["destination"].get("value")
    sources = config.get("sources", [])

    if not sources:
        print("No sources provided in config.")
        sys.exit(1)

    seven_zip_exe = "./tools/7za.exe"
    temp_dir = "./work"
    os.makedirs(temp_dir, exist_ok=True)

    # Generate archive filename
    archive_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".7z"
    temp_archive_path = os.path.join(temp_dir, archive_name)

    # Build 7za command
    cmd = [seven_zip_exe, "a", temp_archive_path] + sources

    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("✅ Archive created locally:", temp_archive_path)
    except subprocess.CalledProcessError as e:
        print("❌ Error while creating archive:")
        print(e.stderr)
        sys.exit(1)

    # Handle destination
    if destination_type == "directory":
        try:
            os.makedirs(destination_value, exist_ok=True)
            final_path = os.path.join(destination_value, archive_name)
            shutil.copy2(temp_archive_path, final_path)
            print("✅ Archive copied to:", final_path)
        except Exception as e:
            print(f"❌ Failed to copy to directory destination: {e}")
            sys.exit(1)

    elif destination_type == "drive":
        print("🔄 Waiting for drive named 'MOH AMBANPO' to be connected...")
        while True:
            drive_letter = is_drive_connected_with_label("MOH AMBANPO")
            if drive_letter:
                backup_dir = os.path.join(drive_letter, "backups")
                try:
                    os.makedirs(backup_dir, exist_ok=True)
                    final_path = os.path.join(backup_dir, archive_name)
                    shutil.copy2(temp_archive_path, final_path)
                    print(f"✅ Archive copied to USB drive: {final_path}")
                    break
                except Exception as e:
                    print(f"❌ Failed to copy to drive: {e}")
                    time.sleep(10)  # Retry again
            else:
                print("⌛ Drive not found yet. Retrying in 10 seconds...")
                time.sleep(10)
    else:
        print(f"❌ Unknown destination type: {destination_type}")
        sys.exit(1)


if __name__ == "__main__":
    main()
