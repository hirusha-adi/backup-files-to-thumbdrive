# 🔐 Backup Files to Thumbdrive

This is a lightweight backup tool for Windows that automates the process of archiving your important folders into .7z files and saving them either to a local folder, a USB drive (based on its volume label), or both.

It supports rotating backups, so it only keeps a fixed number of recent archives and deletes the older ones automatically. All activity is logged in the `./logs/` folder using rotating log files.

Features:
- Backup files to:
  - 📁 A local directory
  - 🔌 A removable USB drive (by volume label)
- Archive rotation using configurable `count` limit
- Smart USB detection and retry
- Logs all activity to rotating log files in the .`/logs/` folder

The script uses `7za.exe`, the standalone command-line version of 7-Zip. If you don’t want to use the pre-included one located at `./tools/7za.exe`, you can get the latest version from the [official 7-Zip website](https://www.7-zip.org/download.html) or [click here](https://www.7-zip.org/a/7z2409-extra.7z) to directly download the version used in this project.

Start by cloning this repository.

Next, install [Python 3](https://www.python.org/downloads/release/python-390/) (if you haven’t already), and then install the required Python dependencies using:

```bash
pip install -r requirements.txt
```

After that, you’ll want to edit the `./config.json` file. This file contains all the settings needed to tell the script what to back up and where to send the backups. While JSON doesn't support comments, here's an example that explains each setting:

```json
{
    // the number of rotating backup archives to keep at destinations
    "count": 3,

    // will be used a temporary work folder
    "work_path": ".\\work",

    // detination related configuration
    "destination": {

        // the destination type, the possible values are:
        //      directory
        //      drive
        //      both
        "type": "both",

        // these settings will be used if type is directory or both
        "directory_config": {

            // output directory to save the zip files to
            "output_path": "F:\\Desktop\\"

        },

        // these settings will be used if type is drive or both
        "drive_config": {

            // volume label of the usb drive to look for
            "drive_name": "KINGSTON",

            // directory to put the backup archives to 
            "sub_directory": "Backups\\OfficePC"

        }
    },

    // a list of directories include in the archive
    "sources": [
        "F:\\Documents\\Important"
    ]
}
```

Once you’ve finished editing the configuration file, make sure the `./run_backup.bat` script points to the correct folder path where your Python files are. You can then use this batch file to launch the backup process.

To automate the backups, you can create a task in Windows Task Scheduler that runs `run_backup.bat` at a schedule, whenver you want. Or, you can simply run the Python script manually any time you want to back things up.

If something goes wrong, check the log files saved inside `./logs/` named after the day and time of script execution. 
