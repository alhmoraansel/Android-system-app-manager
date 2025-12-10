# Manage-system-apps

## NOTE:
1. ADB must be installed on your pc, and added to PATH, you can use chocolatey for installation of adb. (verify by running adb devices).
2. USB Debugging must be enabled in device you are working (Tip: you can disable usb debugging or whole of developer's options after removing apps you dont want).
3. The executable file is complete in itself, but if it causes error (or won't open), just install python-latest, and tkinter.
4. The exe file may take time (at most 10 seconds) to load for the first time.
5. Make sure to connect device before opening or it may show an error.


Manage the system managed apps, remove them or reinstall them as required.

## Features and Functionality

This application provides a graphical user interface (GUI) to manage Android packages on a connected device via ADB (Android Debug Bridge).  It allows you to:

*   **Uninstall Packages:**  Remove selected packages from the device.
*   **Install Existing Packages:** Reinstall previously uninstalled system apps.
*   **Load Package List:** Load a list of package names from a text file (`.txt`).
*   **Get Installed Packages:** Retrieve a list of installed packages directly from the connected Android device, saving them to `installed_packages.txt` and `all_installed_packages.txt`.  Includes the ability to retrieve *all* packages, or only those that appear to the user (system apps).
*   **Filtering:** Filter the displayed package list by typing in a filter box.
*   **Select All/Clear Selection:** Conveniently select or deselect all packages in the list.
*   **Save/Load Selection:** Save the currently selected packages to a file (`saved_selection.txt`) and load them later.
*   **Diff View:**  Display a list of packages that are present in the "all packages" list but *not* in the "installed packages" list, helping to identify system apps that have been removed.
*   **Logging:** Provides detailed logging of all operations, with output to a text box in the GUI and also to log files (`uninstall_log.txt`, `install_existing_log.txt`).

## Technology Stack

*   **Python 3:** The application is written in Python 3.
*   **Tkinter:**  The GUI is built using the Tkinter library.
*   **subprocess:** Used to execute ADB commands.
*   **os:** Used for file system operations.
*   **datetime:** Used for timestamping log entries.
*   **threading:** Used to execute ADB commands in the background, preventing the GUI from freezing.

## Prerequisites

*   **Python 3:**  Make sure you have Python 3 installed on your system.
*   **ADB (Android Debug Bridge):** ADB must be installed and configured on your system, and accessible in your system's PATH.  Download the Android SDK Platform Tools.
*   **Android Device:** An Android device connected to your computer via USB with USB debugging enabled.  You may need to authorize your computer on your device.
*   **Tkinter:** Tkinter is usually included with Python installations, but you may need to install it separately on some systems. You can install it via pip:

    ```bash
    pip install tk
    ```

## Installation Instructions

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/alhmoraansel/Manage-system-apps.git
    cd Manage-system-apps
    ```

2.  **Install Dependencies (if needed):** While most dependencies are standard, ensure Tkinter is installed:

    ```bash
    pip install tk
    ```

## Usage Guide

1.  **Connect your Android device:** Ensure your device is connected via USB and USB debugging is enabled. Authorize your computer on the device if prompted. Verify the device is connected using:

    ```bash
    adb devices
    ```

2.  **Run the script:**

    ```bash
    python uninstall.py
    ```

3.  **Using the GUI:**

    *   **Choose File:** Click "Choose File" to load a list of package names from a text file. Package names should be listed one per line. Comments can be added to the file using `#` at the beginning of a line.  Example:

        ```
        # List of packages to uninstall
        com.android.chrome
        com.google.android.youtube
        ```

    *   **Get Packages:** Click "Get Packages" to retrieve the list of installed packages from the device and display them. This saves the list to `installed_packages.txt`. This list shows packages installed for the current user (typically user 0).
    *   **Get All Packages:** Click "Get All Packages" to retrieve *all* packages from the device, including system packages, even if not specifically installed for the current user. This saves the list to `all_installed_packages.txt`.
    *   **Filter:** Type in the filter box to narrow down the displayed list of packages.
    *   **Select All/Clear Selection:** Use the "Select All" checkbox to select all displayed packages, or the "Clear Selection" button to deselect all packages.
    *   **Select Packages:** Check the checkboxes next to the packages you want to uninstall or install. Packages displayed with a different style indicate if they are currently installed on the device.
    *   **Uninstall:** Click "Uninstall" to uninstall the selected packages.  The script uses the command `adb shell pm uninstall --user 0 <package_name>`.  Progress and results are logged in the log textbox and `uninstall_log.txt`.
    *   **Install Existing:** Click "Install Existing" to reinstall selected packages. The script uses the command `adb shell pm install-existing <package_name>`. Progress and results are logged in the log textbox and `install_existing_log.txt`. This command is useful for reinstalling system apps that have been uninstalled but are still present on the device.
    *   **Save Selection:** Saves the currently selected packages to `saved_selection.txt` in the same directory as the script.
    *   **Load Selection:** Loads a previously saved selection from `saved_selection.txt`. If a `saved_selection.txt` exists when the script is first run, the selection will be loaded automatically.  If the saved packages are not in the currently displayed list, the script will automatically retrieve *all* packages from the device to ensure that the selected packages are displayed.
    *   **Clear Selection:** Clears all currently selected checkboxes.
    *   **Show Diff:**  Compares `all_installed_packages.txt` to `installed_packages.txt` and displays a list of packages that are present in the "all" list but not in the "installed" list.  This helps identify system apps that have been removed.  Requires that you have run both "Get Packages" and "Get All Packages" first.  Click "Show Diff" again to exit the diff view and return to the previous package list.

4.  **Log Files:** The script generates `uninstall_log.txt` and `install_existing_log.txt` in the same directory as the script. These files contain detailed logs of the uninstall and install processes.

## API Documentation

This project does not expose a public API. It is a standalone GUI application designed for direct user interaction.  The core functionality is provided by the `uninstall_packages`, `install_existing_packages`, `load_package_list` and `get_installed_packages` functions within the `uninstall.py` script.

## Contributing Guidelines

Contributions are welcome! To contribute:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them with descriptive messages.
4.  Submit a pull request.

## License Information

No license specified. All rights reserved.

## Contact/Support Information

For questions or support, please open an issue on the GitHub repository: [https://github.com/alhmoraansel/Manage-system-apps](https://github.com/alhmoraansel/Manage-system-apps)
