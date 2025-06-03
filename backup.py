# -*- coding: utf-8 -*-
# Author: Hirusha Adikari
# Source: https://github.com/hirusha-adi/backup-files-to-thumbdrive
#

import ctypes
import json
import logging
import os
import shutil
import string
import sys
import time
import typing as t
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ----------------------------------------------------------------------------------
#                                      Logging
# ----------------------------------------------------------------------------------

os.makedirs(os.path.join(os.getcwd(), "logs"), exist_ok=True)

# Timestamped log file name (e.g., logs/2025-06-03_18-45-00.log)
log_filename = datetime.now().strftime("logs/%Y-%m-%d_%H-%M-%S.log")

# Formating for logs
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT = (
    "[%(asctime)s] "
    "[%(levelname)s] "
    "[%(module)s:%(funcName)s:%(lineno)d] "
    "[PID:%(process)d|TID:%(thread)d] "
    "%(message)s"
)

# File handler with rotating log (optional)
file_handler = RotatingFileHandler(log_filename, maxBytes=5*1024*1024, backupCount=3)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# Configure root logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Prevent duplicate logs in interactive sessions
logger.propagate = False

logger.debug("Loggger initiated")

# ----------------------------------------------------------------------------------
#                          Type Hinting (for config.json)
# ----------------------------------------------------------------------------------

class DirectoryConfig(t.TypedDict):
    output_path: str


class DriveConfig(t.TypedDict):
    drive_name: str
    sub_directory: str

mode_type = t.Literal["directory", "drive", "both"]

class Destination(t.TypedDict):
    type: mode_type
    directory_config: DirectoryConfig
    drive_config: DriveConfig 


class ConfigDict(t.TypedDict):
    count: int
    work_path: str
    destination: Destination
    sources: t.List[str]

logger.debug("Type hints initiated")

# ----------------------------------------------------------------------------------
#                                 Load config.json
# ----------------------------------------------------------------------------------

class Config:
    __config_path = os.path.join(os.getcwd(), "config.json")
    
    try:
        with open(__config_path, "r") as f:
            _data: ConfigDict = json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at '{__config_path}'.")
        sys.exit()
    except Exception as e:
        logger.error(f"An unknown error happened when trying to open the configuration file: {e}")
        sys.exit()

    __config: ConfigDict = _data
    
    count: int = __config.get("count", 7)
    
    work_path: str = __config.get("work_path", os.path.join(os.getcwd(), "work"))
    os.makedirs(work_path, exist_ok=True)
    logger.debug(f"Created directory at {work_path}")

    __destination: Destination = __config.get("destination")
    
    destination_type: mode_type = __destination.get("type")
    if not(destination_type in ("directory", "drive", "both")):
        logger.error("Please keep the `type` in the configuration file as one of 'directory', 'drive' or 'both'")
        sys.exit()

    _directory_config: DirectoryConfig = __destination.get("directory_config")
    directory_config_ouput_path: str = _directory_config.get("output_path")

    _drive_config: DriveConfig = __destination.get("drive_config")
    drive_config_sub_directory: str = _drive_config.get("sub_directory")

    # We are checking for the volume label, not the volume GUI path or drive letter
    #   If the drive is FAT/FAT32, max length for volume label is 11 characters
    #   If the drive is NTFS, max length for volume label is 32 characters
    # I set the max lenth as 32 to make it work on the best case scenario
    # This hopefull wont be any major issue
    drive_config_drive_name: str = _drive_config.get("drive_name")
    if len(drive_config_drive_name) >= 32:
        logger.error("Please keep the `drive_name` in the configuration file as less than 32 characters")
        
    sources: t.List[str] = __config.get("sources")
        
    if len(sources) == 0:
        logger.error("Nothing to back up")
        sys.exit()

logger.debug("Loaded and validated the configuration successfully.")

# ----------------------------------------------------------------------------------
#                                Support Functions
# ----------------------------------------------------------------------------------

def is_drive_connected_with_label(target_label: str) -> t.Optional[str]:
    """Check if a removable drive with the given volume label is connected"""
    # this is complete AI slop
    # i have no idea about windll or any low level windows interface
    # oh gosh i should learn more
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
                    logger.info(f"Found drive with label: {target_label} at {drive}")
                    return drive
                else:
                    logger.debug(f"Drive path found at {drive} but with label: {volume_name_buffer.value}")
            except Exception as e:
                logger.debug(f"An error occured while trying to access drive: {drive} :- {e}")
                continue
        else:
            logger.debug(f"Drive path does not exist at: {drive}")
    return None

def copy_with_retry(src: str, dst: str, retries: t.Optional[int] = 5, delay: t.Optional[int] = 1):
    if retries and delay:
        for _ in range(retries):
            try:
                shutil.copy2(src, dst)
                logger.info(f"Copied {src} to {dst}")
                return
            except PermissionError as e:
                logger.error(f"PermissionError: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
    else:
        logger.error(f"Invalid arguments for copy_with_retry: {src} {dst} {retries} {delay} in copy_with_retry()")
    logger.error(f"Failed to copy {src} after {retries} retries.")

def rotate_backups(directory: str, max_count: int):
    try:
        files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.endswith(".7z") and os.path.isfile(os.path.join(directory, f))
        ]
        files.sort(key=lambda x: os.path.getctime(x))
        if len(files) > max_count:
            for f in files[:-max_count]:
                try:
                    os.remove(f)
                    logger.info(f"Removed old backup: {f}")
                except Exception as e:
                    logger.warning(f"Failed to delete old backup {f}: {e}")
    except Exception as e:
        logger.warning(f"Failed to rotate backups in {directory}: {e}")


# ----------------------------------------------------------------------------------
#                                  Backup Modes
# ----------------------------------------------------------------------------------

def run_mode_directory(tmp_file_path: str, archive_file_name: str):
    try:
        os.makedirs(Config.directory_config_ouput_path, exist_ok=True)
        final_path = os.path.join(Config.directory_config_ouput_path, archive_file_name)
        copy_with_retry(src=tmp_file_path, dst=final_path, retries=5, delay=1)
        rotate_backups(Config.directory_config_ouput_path, Config.count)
        logger.info(f"Archive copied to: {final_path}")
    except Exception as e:
        logger.error(f"Failed to copy temporary archive to target destination directory: {e}")
        sys.exit()
    logger.info("Successfully ran the directory mode")

def run_mode_drive(tmp_file_path: str, archive_file_name: str):
    logger.info(f"Waiting for drive named '{Config.drive_config_drive_name}' to be connected...")
    while True:
        drive_letter = is_drive_connected_with_label(Config.drive_config_drive_name)
        if drive_letter:
            backup_dir = os.path.join(drive_letter, Config.drive_config_sub_directory)
            try:
                os.makedirs(backup_dir, exist_ok=True)
                logger.debug(f"Backup directory created at: {backup_dir} in USB drive.")
                
                final_path = os.path.join(backup_dir, archive_file_name)
                copy_with_retry(src=tmp_file_path, dst=final_path, retries=5, delay=1)
                rotate_backups(backup_dir, Config.count)
                logger.info(f"Archive copied to USB drive: {final_path}")
                break
            except Exception as e:
                logger.error(f"Failed to copy to drive: {e}. Retrying in 10 seconds...")
                time.sleep(10)
        else:
            logger.warning(f"Drive with label {Config.drive_config_drive_name} not found yet. Retrying in 10 seconds...")
            time.sleep(10)
    logger.info("Successfully ran the drive mode")

# ----------------------------------------------------------------------------------
#                                  Main Function
# ----------------------------------------------------------------------------------

def main():
    
    # Zip the files
    # ------------------------------------------------------------------------------
    
    tools_7z_exe = os.path.join("tools", "7za.exe")
    if not os.path.exists(tools_7z_exe):
        logger.error("7-zip binary (7za.exe) not found at '.\\tools\\7za.exe'")
        sys.exit()

    archive_file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".7z"
    tmp_file_path = os.path.join(Config.work_path, archive_file_name)
    
    logger.info(f"Archive name: {tmp_file_path}")
    logger.debug(f"Temporary archive will be made at: {tmp_file_path}")
    
    zip_command = [tools_7z_exe, "a", tmp_file_path] + Config.sources
    logger.info(f"Running command: {' '.join(zip_command)}")

    try:
        os.system(" ".join(zip_command))
        logger.info(f"Temporary archive created at: {tmp_file_path}")
    except Exception as e:
        logger.error(f"Error while creating archive: {e}")
        sys.exit()

    # Copy files based on model
    # ------------------------------------------------------------------------------
    
    if Config.destination_type == "directory":
        run_mode_directory(tmp_file_path=tmp_file_path, archive_file_name=archive_file_name)
        

    elif Config.destination_type == "drive":
        run_mode_drive(tmp_file_path=tmp_file_path, archive_file_name=archive_file_name)
                
    elif Config.destination_type == "both":
        run_mode_directory(tmp_file_path=tmp_file_path, archive_file_name=archive_file_name)
        run_mode_drive(tmp_file_path=tmp_file_path, archive_file_name=archive_file_name)
        logger.info("Successfully ran both modes")
        
    else:
        logger.error("Unknown destination type:", Config.destination_type)
        sys.exit()
        
    logger.info("All operations performed successfully!")


if __name__ == "__main__":
    main()
