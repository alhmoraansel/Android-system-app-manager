import subprocess
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
from tkinter import scrolledtext
import threading  # Import the threading module
import sys # Import sys to check the operating system

# Define CREATE_NO_WINDOW flag for Windows
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

# Global variables to manage state
is_diff_view_active = False
diff_list = []
existing_packages = [] # To store the list of packages currently installed on the device

def uninstall_packages(package_list, adb_command="adb", log_textbox=None):
    """
    Uninstalls APK packages from a list using ADB and updates a log textbox.
    Runs in a separate thread.

    Args:
        package_list (list): A list of package names to uninstall.
        adb_command (str, optional): The ADB command. Defaults to "adb".
        log_textbox (tk.Text, optional): A Tkinter Text widget for logging.
    """
    log_file = "uninstall_log.txt"

    # Create the log file
    with open(log_file, "w") as f:
        now = datetime.now()
        f.write(f"Script started at {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Uninstalling packages using adb shell pm uninstall --user 0...\n\n")

    # Function to update log in textbox and file
    def update_log(message):
        if log_textbox:
            # Use window.after to update the GUI from the thread
            log_textbox.after(0, log_textbox.insert, tk.END, message + "\n")
            log_textbox.after(0, log_textbox.see, tk.END)  # Auto-scroll to the bottom
        with open(log_file, "a") as lf:
            lf.write(message + "\n")

    # Uninstall each package in the list
    for package_name in package_list:
        message = f"Attempting to uninstall package: {package_name}"
        print(message)
        update_log(message)

        # Use adb shell pm uninstall --user 0
        try:
            process = subprocess.run(
                [adb_command, "shell", "pm", "uninstall", "--user", "0", package_name],
                capture_output=True,
                text=True,
                check=True,  # Raise an exception for non-zero exit codes
                creationflags=CREATE_NO_WINDOW # Add this flag for Windows
            )
            # Log success
            message = f"Package '{package_name}' uninstalled successfully."
            update_log(message)
            print(message)

        except subprocess.CalledProcessError as e:
            # Log failure
            message = f"Failed to uninstall package: {package_name}"
            update_log(message)
            update_log(f"Error: {e.stderr.strip()}") # Use strip() to remove trailing newline
            print(message)
            print(f"Error: {e.stderr.strip()}")

    # Log Completion
    now = datetime.now()
    update_log(f"\nUninstallation process complete.")
    update_log(f"Script ended at {now.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\nProcess complete. Log file: {log_file}")

def install_existing_packages(package_list, adb_command="adb", log_textbox=None):
    """
    Installs existing APK packages from a list using ADB and saves logs.
    Runs in a separate thread.

    Args:
        package_list (list): A list of package names to install.
        adb_command (str, optional): The ADB command. Defaults to "adb".
        log_textbox (tk.Text, optional): Tkinter Text widget for logging.
    """
    log_file = "install_existing_log.txt"

    # Create the log file
    with open(log_file, "w") as f:
        now = datetime.now()
        f.write(f"Script started at {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Installing existing packages using adb shell pm install-existing...\n\n")

    def update_log(message):
        if log_textbox:
            # Use window.after to update the GUI from the thread
            log_textbox.after(0, log_textbox.insert, tk.END, message + "\n")
            log_textbox.after(0, log_textbox.see, tk.END)  # Auto-scroll to the bottom
        with open(log_file, "a") as lf:
            lf.write(message + "\n")

    # Install each package in the list
    for package_name in package_list:
        message = f"Attempting to install existing package: {package_name}"
        print(message)
        update_log(message)

        # Use adb shell pm install-existing
        try:
            process = subprocess.run(
                [adb_command, "shell", "pm", "install-existing", package_name],
                capture_output=True,
                text=True,
                check=True,  # Raise an exception for non-zero exit codes
                creationflags=CREATE_NO_WINDOW # Add this flag for Windows
            )
            # Log success
            message = f"Package '{package_name}' installed successfully."
            update_log(message)
            print(message)

        except subprocess.CalledProcessError as e:
            # Log failure
            message = f"Failed to install existing package: {package_name}"
            update_log(message)
            update_log(f"Error: {e.stderr.strip()}") # Use strip()
            print(message)
            print(f"Error: {e.stderr.strip()}")

    # Log Completion
    now = datetime.now()
    update_log(f"\nInstallation process complete.")
    update_log(f"Script ended at {now.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\nInstallation process complete. Log file: {log_file}")

def load_package_list(file_path, package_list_var, log_textbox=None):
    """Loads package names from a text file and updates the list variable.

    Args:
        file_path (str): Path to the text file.
        package_list_var (tk.Variable): Tkinter variable to store the package list.
        log_textbox (tk.Text, optional): Tkinter Text widget for logging.
    """
    global is_diff_view_active # Reset diff view
    is_diff_view_active = False
    package_list = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                package_name = line.strip()
                if package_name and not package_name.startswith("#"):
                    package_list.append(package_name)
    except Exception as e:
        error_message = f"Error reading file: {e}"
        messagebox.showerror("Error", error_message)
        if log_textbox:
            log_textbox.insert(tk.END, error_message + "\n")
            log_textbox.see(tk.END)
        package_list_var.set([]) # Clear the variable on error
        return []  # Important: Return an empty list on error
    package_list_var.set(package_list)  # Update the Tkinter variable
    if log_textbox:
        log_textbox.insert(tk.END, f"Loaded {len(package_list)} packages from {os.path.basename(file_path)}.\n")
        log_textbox.see(tk.END)
    return package_list  # Return package list for further processing

def get_installed_packages(adb_command="adb", log_textbox=None, all_packages=False):
    """Gets the list of installed packages from the Android device using ADB.
    Saves the list to a text file (installed_packages.txt) and returns the list.
    Args:
        adb_command: The ADB command.
        log_textbox: Tkinter Text widget for logging.
        all_packages: if true list all packages.
    """
    global is_diff_view_active # Reset diff view
    is_diff_view_active = False
    try:
        cmd = [adb_command, "shell", "pm", "list", "packages"]
        if all_packages:
            cmd.append("-a")
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=CREATE_NO_WINDOW # Add this flag for Windows
        )
        packages = process.stdout.strip().split('\n')
        # Remove "package:" prefix
        packages = [p.replace("package:", "").strip() for p in packages]

        # Save to file
        file_name = "installed_packages.txt" if not all_packages else "all_installed_packages.txt"
        with open(file_name, "w") as f:
            f.write("\n".join(packages))
        if log_textbox:
            log_textbox.insert(tk.END, f"Installed packages list retrieved ({file_name}).\n")
            log_textbox.see(tk.END)
        return packages

    except subprocess.CalledProcessError as e:
        error_message = f"Error getting package list: {e.stderr.strip()}"
        messagebox.showerror("Error", error_message)
        if log_textbox:
            log_textbox.insert(tk.END, error_message + "\n")
            log_textbox.see(tk.END)
        return []

def create_gui():
    """Creates the main GUI window."""
    window = tk.Tk()
    window.title("ADB Package Uninstaller/Installer")
    window.geometry("800x600")
    window.minsize(640, 480)
    window.configure(bg="#f0f0f0")

    # Style for buttons
    button_style = ttk.Style()
    button_style.configure("TButton",
        padding=10,
        relief="flat",
        borderwidth=0,
        font=("Arial", 10, "bold"),
        background="#4CAF50",
        foreground="#000000",
        highlightthickness=2,
        highlightcolor="#388E3C",
        highlightbackground="#f0f0f0",
    )
    button_style.map("TButton",
        background=[("active", "#66BB6A"), ("disabled", "#f0f0f0")],
        foreground=[("active", "#000000"), ("disabled", "#B8B8B8")],
        relief=[("active", "raised")],
        borderwidth=[("active", 2)]
    )
    # Style for labels
    label_style = ttk.Style()
    label_style.configure("TLabel",
        font=("Arial", 10, "bold"),
        foreground="#555",
        background="#f0f0f0"
    )

    # Package list variable
    package_list_var = tk.Variable(value=[])

    # PanedWindow for the two-panel layout
    paned_window = ttk.Panedwindow(window, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # Left frame for package list and controls
    left_frame = ttk.Frame(paned_window, style='TFrame')
    paned_window.add(left_frame, weight=1)

    # Right frame for the log textbox
    right_frame = ttk.Frame(paned_window, style='TFrame')
    paned_window.add(right_frame, weight=1)

    # Frame for buttons and file selection (inside left_frame)
    controls_frame = ttk.Frame(left_frame, style='TFrame')
    controls_frame.pack(anchor="nw", padx=10, pady=10, fill=tk.X)

    # Label and button for file selection
    file_label = ttk.Label(controls_frame, text="Package List:", style="TLabel")
    file_label.pack(side="left", padx=(0, 5))

    def select_file():
        """Opens a file dialog to select the package list file."""
        global is_diff_view_active # Reset diff view
        is_diff_view_active = False
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            global loaded_packages
            loaded_packages = load_package_list(file_path, package_list_var, window.log_textbox)
            file_path_label.config(text=os.path.basename(file_path), foreground="#2196F3")
            update_package_listbox()
        else:
            file_path_label.config(text="No file", foreground="#555")
        # Ensure diff button state is correct after file selection
        update_diff_button_state()


    file_button = ttk.Button(controls_frame, text="Choose File", command=select_file, style="TButton")
    file_button.pack(side="left", padx=(0, 10))

    file_path_label = ttk.Label(controls_frame, text="No file", style="TLabel")
    file_path_label.pack(side="left", padx=(0, 10))

    # Entry for filtering packages
    filter_entry = tk.Entry(controls_frame, font=("Arial", 9, "bold"), relief="solid", borderwidth=1)
    filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    filter_entry.bind("<KeyRelease>", lambda event: update_package_listbox())
    filter_entry.configure(highlightcolor="#707070")

    # Button to get installed packages
    get_packages_button = ttk.Button(controls_frame, text="Get Packages", command=lambda: handle_get_packages(False), style="TButton")
    get_packages_button.pack(side="left", padx=(0, 0))

    get_all_packages_button = ttk.Button(controls_frame, text="Get All Packages", command=lambda: handle_get_packages(True), style="TButton")
    get_all_packages_button.pack(side="left", padx=(0, 0))

    # Frame for Select All Checkbox
    select_all_frame = ttk.Frame(left_frame, style='TFrame')
    select_all_frame.pack(anchor=tk.NW, padx=10, pady=(10, 0))

    # Checkbox Frame and Scrollbar
    checkbox_frame = ttk.Frame(left_frame)
    checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    canvas = tk.Canvas(checkbox_frame, bg="#f0f0f0", highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(checkbox_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    inner_frame = ttk.Frame(canvas, style='TFrame')
    canvas.create_window((0, 0), window=inner_frame, anchor='nw')

    def on_mousewheel(event):
        """Handle mousewheel scrolling."""
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    checkboxes = []
    select_all_var = tk.BooleanVar(value=False)

    def update_package_listbox():
        """Updates the listbox with checkboxes based on the current package list and filter."""
        nonlocal checkboxes
        # Destroy existing checkboxes
        for cb, _, _, _ in checkboxes:
            cb.destroy()
        checkboxes = []

        filter_text = filter_entry.get().lower()

        # Determine which list to display
        if is_diff_view_active:
            current_package_list = diff_list
        else:
            current_package_list = package_list_var.get()

        if current_package_list:
            for package in current_package_list:
                if filter_text in package.lower():
                    selected = tk.BooleanVar(value=select_all_var.get())

                    if is_diff_view_active:
                         # Use MissingPackageCheckbutton style for diff view
                         cb = ttk.Checkbutton(inner_frame, text=package, variable=selected, style="MissingPackageCheckbutton.TCheckbutton")
                    else:
                        # Original logic for installed/all packages view
                        is_existing_on_device = package in existing_packages
                        if all_packages_var.get(): # If showing all packages from device
                            if is_existing_on_device:
                                cb = ttk.Checkbutton(inner_frame, text=package, variable=selected, style="ExistingPackageCheckbutton.TCheckbutton")
                            else:
                                # This case shouldn't happen if all_packages_var is True and existing_packages is the source,
                                # but keeping the style for consistency or future use.
                                cb = ttk.Checkbutton(inner_frame, text=package, variable=selected, style="MissingPackageCheckbutton.TCheckbutton")
                        else: # If showing packages from loaded file or installed packages (non-all)
                             # Check if the package from the list is currently installed on the device
                            if package in existing_packages:
                                cb = ttk.Checkbutton(inner_frame, text=package, variable=selected, style="ExistingPackageCheckbutton.TCheckbutton")
                            else:
                                cb = ttk.Checkbutton(inner_frame, text=package, variable=selected, style="PackageCheckbutton.TCheckbutton") # Default style

                    cb.pack(anchor=tk.W, pady=2)
                    # Store checkbox, its variable, package name, and its existence status
                    checkboxes.append((cb, selected, package, package in existing_packages)) # is_existing here refers to presence on device

        inner_frame.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def toggle_select_all():
        """Function to handle select all checkbox"""
        # Iterate through currently displayed checkboxes and set their state
        for cb, selected, package, is_existing in checkboxes:
             selected.set(select_all_var.get())
        # No need to call update_package_listbox here, as the state is already toggled

    # "Select All" checkbox
    select_all_checkbox = ttk.Checkbutton(select_all_frame, text="Select All", variable=select_all_var, command=toggle_select_all, style="SelectAllCheckbutton.TCheckbutton")
    select_all_checkbox.pack(anchor=tk.W, pady=2)

    all_packages_var = tk.BooleanVar(value=False)  # Variable to track if "Get All Packages" was last clicked

    def handle_get_packages(get_all=False):
        """Gets the installed packages and updates the listbox."""
        global existing_packages
        global is_diff_view_active # Reset diff view
        is_diff_view_active = False

        existing_packages = get_installed_packages(log_textbox=window.log_textbox, all_packages=False) # Always get the non-all list for diff calculation
        all_packages_list = get_installed_packages(log_textbox=window.log_textbox, all_packages=True) # Always get the all list for diff calculation

        if get_all:
             # If "Get All Packages" was clicked, set the package list to all packages
             package_list_var.set(all_packages_list)
             all_packages_var.set(True) # Indicate that we are showing all packages
        else:
             # If "Get Packages" was clicked, set the package list to non-all packages
             package_list_var.set(existing_packages)
             all_packages_var.set(False) # Indicate that we are not showing all packages

        update_package_listbox()
        # Enable diff view if both files exist
        update_diff_button_state()


    def on_uninstall():
        """Handles the uninstall button click in a separate thread."""
        packages_to_uninstall = []
        for cb, selected, package, _ in checkboxes:
            if selected.get():
                packages_to_uninstall.append(package)
        if packages_to_uninstall:
            # Start uninstall in a new thread
            threading.Thread(target=uninstall_packages, args=(packages_to_uninstall, "adb", window.log_textbox)).start()
        else:
            window.log_textbox.insert(tk.END, "Select packages to uninstall.\n")
            window.log_textbox.see(tk.END)

    def on_install_existing():
        """Handles the install existing button click in a separate thread."""
        packages_to_install = []
        for cb, selected, package, _ in checkboxes:
            if selected.get():
                packages_to_install.append(package)
        if packages_to_install:
            # Start install in a new thread.
            threading.Thread(target=install_existing_packages, args=(packages_to_install, "adb", window.log_textbox)).start()
        else:
            window.log_textbox.insert(tk.END, "Select packages to install.\n")
            window.log_textbox.see(tk.END)

    def save_selection():
        """Saves the currently selected packages to a file."""
        selected_packages = []
        for cb, selected, package, _ in checkboxes:
            if selected.get():
                selected_packages.append(package)
        if selected_packages:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            save_file_path = os.path.join(script_dir, "saved_selection.txt")
            try:
                with open(save_file_path, "w") as f:
                    f.write("\n".join(selected_packages))
                window.log_textbox.insert(tk.END, f"Selection saved to {os.path.basename(save_file_path)}.\n")
                window.log_textbox.see(tk.END)
            except Exception as e:
                error_message = f"Error saving file: {e}"
                messagebox.showerror("Error", error_message)
                window.log_textbox.insert(tk.END, error_message + "\n")
                window.log_textbox.see(tk.END)
        else:
            window.log_textbox.insert(tk.END, "No packages selected to save.\n")
            window.log_textbox.see(tk.END)

    def load_selection():
        """Loads a selection of packages from a file and updates the checkboxes."""
        global is_diff_view_active # Reset diff view
        is_diff_view_active = False
        script_dir = os.path.dirname(os.path.abspath(__file__))
        load_file_path = os.path.join(script_dir, "saved_selection.txt")
        if os.path.exists(load_file_path):
            try:
                with open(load_file_path, "r") as f:
                    saved_packages = [line.strip() for line in f]

                # Ensure the current list displayed contains the saved packages
                # If not currently showing 'all' packages, load 'all' packages first
                if not all_packages_var.get():
                     handle_get_packages(get_all=True) # This will update package_list_var and checkboxes

                # Now iterate through the current checkboxes (which should include all packages if the above ran)
                found_count = 0
                for cb, selected, package, _ in checkboxes:
                    selected.set(False) # Deselect all first
                    if package in saved_packages:
                        selected.set(True)
                        found_count += 1

                window.log_textbox.insert(tk.END, f"Loaded selection from {os.path.basename(load_file_path)}. {found_count} packages selected.\n")
                window.log_textbox.see(tk.END)
            except Exception as e:
                error_message = f"Error loading file: {e}"
                messagebox.showerror("Error", error_message)
                window.log_textbox.insert(tk.END, error_message + "\n")
                window.log_textbox.see(tk.END)
        else:
            window.log_textbox.insert(tk.END, "No saved selection found.\n")
            window.log_textbox.see(tk.END)
        # Ensure diff button state is correct after loading selection
        update_diff_button_state()


    def clear_selection():
        """Clears the current selection of packages."""
        for cb, selected, _, _ in checkboxes:
            selected.set(False)
        # No need to call update_package_listbox, just the state changes
        window.log_textbox.insert(tk.END, "Selection cleared.\n")
        window.log_textbox.see(tk.END)


    def update_diff_button_state():
         """Enables or disables the diff button based on file existence."""
         if os.path.exists("installed_packages.txt") and os.path.exists("all_installed_packages.txt"):
             diff_button.config(state=tk.NORMAL)
         else:
             diff_button.config(state=tk.DISABLED)


    def show_diff():
        """Displays the difference between all packages and installed packages in the main list."""
        global is_diff_view_active
        global diff_list

        if is_diff_view_active:
            # If currently in diff view, exit diff view
            is_diff_view_active = False
            diff_button.config(text="Show Diff")
            update_package_listbox() # Revert to previous view (from package_list_var)
            window.log_textbox.insert(tk.END, "Exited diff view.\n")
            window.log_textbox.see(tk.END)
        else:
            # If not in diff view, calculate and show diff
            all_packages_list = []
            installed_packages_list = []
            try:
                if os.path.exists("all_installed_packages.txt"):
                    with open("all_installed_packages.txt", "r") as f:
                        all_packages_list = [line.strip() for line in f]
                else:
                     window.log_textbox.insert(tk.END, "Error: 'all_installed_packages.txt' not found. Please click 'Get All Packages'.\n")
                     window.log_textbox.see(tk.END)
                     return

                if os.path.exists("installed_packages.txt"):
                    with open("installed_packages.txt", "r") as f:
                        installed_packages_list = [line.strip() for line in f]
                else:
                     window.log_textbox.insert(tk.END, "Error: 'installed_packages.txt' not found. Please click 'Get Packages'.\n")
                     window.log_textbox.see(tk.END)
                     return

            except Exception as e:
                error_message = f"Error reading package lists for diff: {e}"
                messagebox.showerror("Error", error_message)
                window.log_textbox.insert(tk.END, error_message + "\n")
                window.log_textbox.see(tk.END)
                return

            diff_set = set(all_packages_list) - set(installed_packages_list)
            diff_list = sorted(list(diff_set))  # Store the sorted diff

            if diff_list:
                is_diff_view_active = True
                diff_button.config(text="Exit Diff View")
                update_package_listbox() # Display the diff list
                window.log_textbox.insert(tk.END, f"Showing {len(diff_list)} packages not currently installed (Diff View).\n")
                window.log_textbox.see(tk.END)
            else:
                messagebox.showinfo("Info", "All packages in 'all_installed_packages.txt' are installed.")
                window.log_textbox.insert(tk.END, "No packages found in diff.\n")
                window.log_textbox.see(tk.END)


    # Frame for buttons at the bottom (inside left_frame)
    bottom_button_frame = ttk.Frame(left_frame, style='TFrame')
    bottom_button_frame.pack(side=tk.BOTTOM, anchor="se", padx=10, pady=15, fill=tk.X)
    bottom_button_frame.configure(relief='groove', borderwidth=2)

    # Uninstall button
    uninstall_button = ttk.Button(bottom_button_frame, text="Uninstall", command=on_uninstall, style="TButton")
    uninstall_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)

    # Install Existing button.
    install_existing_button = ttk.Button(bottom_button_frame, text="Install Existing", command=on_install_existing, style="TButton")
    install_existing_button.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)

    # Save Selection button
    save_button = ttk.Button(bottom_button_frame, text="Save Selection", command=save_selection, style="TButton")
    save_button.pack(side=tk.RIGHT, padx=5, pady=5, expand=True, fill=tk.X)

    # Load Selection button
    load_button = ttk.Button(bottom_button_frame, text="Load Selection", command=load_selection, style="TButton")
    load_button.pack(side=tk.RIGHT, padx=5, pady=5, expand=True, fill=tk.X)

    # Clear Selection button
    clear_button = ttk.Button(bottom_button_frame, text="Clear Selection", command=clear_selection, style="TButton")
    clear_button.pack(side=tk.RIGHT, padx=5, pady=5, expand=True, fill=tk.X)

    # Diff Button
    diff_button = ttk.Button(bottom_button_frame, text="Show Diff", command=show_diff, style="TButton")
    diff_button.pack(side=tk.RIGHT, padx=5, pady=5, expand=True, fill=tk.X)
    diff_button.config(state=tk.DISABLED)  # Start disabled

    # Define styles for the checkboxes
    checkbox_style = ttk.Style()
    # Default style for packages (used when not showing all packages and not existing)
    checkbox_style.configure("PackageCheckbutton.TCheckbutton",
        font=("Arial", 11, "bold"),
        foreground="#2c3e50",
        background="#f0f0f0",
        borderwidth=0,
        relief="flat",
        indicatorcolor="#ffffff",
        highlightthickness=0,
        highlightcolor="#f0f0f0",
    )
    checkbox_style.map("PackageCheckbutton.TCheckbutton",
        background=[("active", "#f0f0f0"), ("selected", "#3498db")],
        foreground=[("active", "#2c3e50"), ("selected", "#ffffff")],
        indicatorcolor=[("selected", "#3498db")]
    )
    # Style for existing packages (used when showing any list and package is installed)
    checkbox_style.configure("ExistingPackageCheckbutton.TCheckbutton",
        font=("Arial", 11, "bold"),
        foreground="#2c3e50",  # Or any color you like, keeping it similar for 'installed' look
        background="#f0f0f0",
        borderwidth=0,
        relief="flat",
        indicatorcolor="#ffffff",
        highlightthickness=0,
        highlightcolor="#f0f0f0",
    )
    checkbox_style.map("ExistingPackageCheckbutton.TCheckbutton",
        background=[("active", "#f0f0f0"), ("selected", "#8e44ad")],  # Example color: purple when selected
        foreground=[("active", "#2c3e50"), ("selected", "#ffffff")], # Keep foreground consistent
        indicatorcolor=[("selected", "#8e44ad")]
    )

    # Style for missing packages (used in Diff View)
    checkbox_style.configure("MissingPackageCheckbutton.TCheckbutton",
        font=("Arial", 12, "bold"),
        foreground="#e74c3c", # Red color for missing
        background="#f0f0f0",
        borderwidth=0,
        relief="flat",
        indicatorcolor="#ffffff",
        highlightthickness=0,
        highlightcolor="#f0f0f0",
    )
    checkbox_style.map("MissingPackageCheckbutton.TCheckbutton",
        background=[("active", "#f0f0f0"), ("selected", "#e74c3c")], # Red when selected
        foreground=[("active", "#e74c3c"), ("selected", "#ffffff")], # Keep foreground consistent
        indicatorcolor=[("selected", "#e74c3c")]
    )

    # define style for select all checkbox
    checkbox_style.configure("SelectAllCheckbutton.TCheckbutton",
        font=("Arial", 12, "bold"),
        foreground="#555", # Neutral color
        background="#f0f0f0",
        borderwidth=0,
        relief="flat",
        indicatorcolor="#ffffff",
        highlightthickness=0,
        highlightcolor="#f0f0f0",
    )
    checkbox_style.map("SelectAllCheckbutton.TCheckbutton",
        background=[("active", "#f0f0f0"), ("selected", "#3498db")], # Blue when selected
        foreground=[("active", "#555"), ("selected", "#000000")], # Keep foreground consistent
        indicatorcolor=[("selected", "#3498db")]
    )


    # Create the log textbox in the right frame
    log_textbox = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Arial", 10),
        bg="#FFFFFF", fg="#000000", borderwidth=2, relief="solid")
    log_textbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    log_textbox.insert(tk.END, "Welcome to ADB Package Manager!\n")
    log_textbox.see(tk.END)

    # Store the log_textbox in a variable that can be accessed by the functions.
    window.log_textbox = log_textbox

    # Get initial installed packages and update the listbox
    # This also populates installed_packages.txt and all_installed_packages.txt
    # and updates the state of the diff button.
    handle_get_packages(get_all=True) # Start by showing all packages from the device

    # Load selection at start.
    # This will automatically call handle_get_packages(True) if saved_selection.txt exists,
    # ensuring the list is populated before trying to select.
    load_selection()

    window.mainloop()

if __name__ == "__main__":
    create_gui()
