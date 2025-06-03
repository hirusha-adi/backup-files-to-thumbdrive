import json
import os
import subprocess
from datetime import datetime
import shutil
import time
import string
import ctypes
import sys
import typing as t

class DirectoryConfig(t.TypedDict):
    output_path: str


class DriveConfig(t.TypedDict):
    drive_name: str
    sub_directory: str


class Destination(t.TypedDict):
    type: t.Literal["directory", "drive", "both"]
    directory_config: DirectoryConfig
    drive_config: DriveConfig 


class ConfigDict(t.TypedDict):
    count: int
    work_path: str
    destination: Destination
    sources: t.List[str]


class Config:
    __config_path = os.path.join(os.getcwd(), "config.json")
    with open(__config_path, "r") as f:
        _data: ConfigDict = json.load(f)

    __config: ConfigDict = _data
    count: int = __config.get("count", 7)
    work_path: str = __config.get(
        "work_path", os.path.join(os.getcwd(), "work"))
    os.makedirs(work_path, exist_ok=True)

    __destination: Destination = __config.get("destination")
    destination_type: t.Literal["directory", "drive", "both"] = __destination.get("type")

    _directory_config: DirectoryConfig = __destination.get("directory_config")
    directory_config_ouput_path: str = _directory_config.get("output_path")

    _drive_config: DriveConfig = __destination.get("drive_config")
    drive_config_drive_name: str = _drive_config.get("drive_name")
    drive_config_sub_directory: str = _drive_config.get("sub_directory")

    sources: t.List[str] = __config.get("sources")


def is_drive_connected_with_label(target_label: str) -> t.Optional[str]:
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
                print(f"[DEBUG] Failed to get volume information for drive {drive}: {e}")
                continue
    return None


def main():
    tools_7z_exe = os.path.join("tools", "7za.exe")
    if not os.path.exists(tools_7z_exe):
        print("❌ 7-Zip tool not found:", tools_7z_exe)
        sys.exit(1)

    archive_file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".7z"
    tmp_file_path = os.path.join(Config.work_path, archive_file_name)

    zip_command = [tools_7z_exe, "a", tmp_file_path] + Config.sources

    try:
        os.system(" ".join(zip_command))
        # result = subprocess.run(z_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # print(result)
        print("✅ Archive created locally:", tmp_file_path)
    except subprocess.CalledProcessError as e:
        print("❌ Error while creating archive:", e.stderr)

    # Handle destination
    if Config.destination_type == "directory":
        try:
            os.makedirs(Config.directory_config_ouput_path, exist_ok=True)
            final_path = os.path.join(
                Config.directory_config_ouput_path, archive_file_name)

            # TODO: write a copy with retry later
            shutil.copy2(tmp_file_path, final_path)

            print("✅ Archive copied to:", final_path)
        except Exception as e:
            print(f"❌ Failed to copy to directory destination: {e}")
            sys.exit(1)

    elif Config.destination_type == "drive":
        print(
            f"🔄 Waiting for drive named '{Config.drive_config_drive_name}' to be connected...")
        while True:
            drive_letter = is_drive_connected_with_label(
                Config.drive_config_drive_name)
            if drive_letter:
                backup_dir = os.path.join(drive_letter, os.path.join(
                    Config.drive_config_sub_directory))
                try:
                    os.makedirs(backup_dir, exist_ok=True)
                    final_path = os.path.join(backup_dir, archive_file_name)
                    shutil.copy2(tmp_file_path, final_path)
                    print(f"✅ Archive copied to USB drive: {final_path}")
                    break
                except Exception as e:
                    print(f"❌ Failed to copy to drive: {e}")
                    time.sleep(10)  # Retry again
            else:
                print("⌛ Drive not found yet. Retrying in 10 seconds...")
                time.sleep(10)
    elif Config.destination_type == "both":
        print(f"❌ Unknown destination type: {Config.destination_type}")
        sys.exit(1)

    else:
        print("[ERROR] Unknown destination type:", Config.destination_type)
        sys.exit(1)


if __name__ == "__main__":
    main()
