import subprocess
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime

def uninstall_packages(package_list, adb_command="adb"):
    """
    Uninstalls APK packages from a list using ADB and saves logs.

    Args:
        package_list (list): A list of package names to uninstall.
        adb_command (str, optional): The ADB command. Defaults to "adb".
    """
    log_file = "uninstall_log.txt"

    # Create the log file
    with open(log_file, "w") as f:
        now = datetime.now()
        f.write(f"Script started at {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Uninstalling packages using adb shell pm uninstall --user 0...\n\n")

    # Uninstall each package in the list
    for package_name in package_list:
        print(f"Uninstalling package: {package_name}")
        with open(log_file, "a") as lf:
            lf.write(f"Uninstalling package: {package_name}\n")

        # Use adb shell pm uninstall --user 0
        try:
            process = subprocess.run(
                [adb_command, "shell", "pm", "uninstall", "--user", "0", package_name],
                capture_output=True,
                text=True,
                check=True  # Raise an exception for non-zero exit codes
            )
            # Log success
            with open(log_file, "a") as lf:
                lf.write(f"Package '{package_name}' uninstalled successfully.\n")
            print(f"Package '{package_name}' uninstalled successfully.")

        except subprocess.CalledProcessError as e:
            # Log failure
            with open(log_file, "a") as lf:
                lf.write(f"Failed to uninstall package: {package_name}\n")
                lf.write(f"Error: {e.stderr}\n")
            print(f"Failed to uninstall package: {package_name}")
            print(f"Error: {e.stderr}")
    
    # Log Completion
    with open(log_file, "a") as f:
        now = datetime.now()
        f.write(f"\nUninstallation process complete.\n")
        f.write(f"Script ended at {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"\nUninstallation process complete. Log file: {log_file}")
    messagebox.showinfo("Uninstallation Complete", f"Uninstallation process complete. Log file: {log_file}")



def load_package_list(file_path, package_list_var):
    """Loads package names from a text file and updates the list variable.

    Args:
        file_path (str): Path to the text file.
        package_list_var (tk.Variable): Tkinter variable to store the package list.
    """
    package_list = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                package_name = line.strip()
                if package_name and not package_name.startswith("#"):
                    package_list.append(package_name)
    except Exception as e:
        messagebox.showerror("Error", f"Error reading file: {e}")
        return
    package_list_var.set(package_list)  # Update the Tkinter variable
    return package_list # Return package list for further processing

def get_installed_packages(adb_command="adb"):
    """Gets the list of installed packages from the Android device using ADB.
    Saves the list to a text file (installed_packages.txt) and returns the list.
    """
    try:
        process = subprocess.run(
            [adb_command, "shell", "pm", "list", "packages"],
            capture_output=True,
            text=True,
            check=True
        )
        packages = process.stdout.strip().split('\n')
        # Remove "package:" prefix
        packages = [p.replace("package:", "").strip() for p in packages]
        
        # Save to file
        with open("installed_packages.txt", "w") as f:
            f.write("\n".join(packages))
        
        return packages
    
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Error getting package list: {e.stderr}")
        return []

def create_gui():
    """Creates the main GUI window."""
    window = tk.Tk()
    window.title("ADB Package Uninstaller")
    window.geometry("600x400")
    window.minsize(640, 480)  # Set minimum size here
    window.configure(bg="#f0f0f0")  # Light gray background

    # Style for buttons
    button_style = ttk.Style()
    button_style.configure("TButton",
        padding=5,
        relief="flat",
        borderwidth=0,
        font=("Arial", 9),
        background="#f0f0f0",
        foreground="#555",
        highlightthickness=0,
        highlightcolor="#f0f0f0",
        highlightbackground="#f0f0f0"
    )
    button_style.map("TButton",
        background=[("active", "#e0e0e0"), ("disabled", "#f0f0f0")],
        foreground=[("active", "#212121"), ("disabled", "#B8B8B8")],
        relief=[("active", "raised")],
        borderwidth=[("active", 1)]
    )
    # Style for labels
    label_style = ttk.Style()
    label_style.configure("TLabel",
        font=("Arial", 10),
        foreground="#555",
        background="#f0f0f0"
    )

    # Package list variable
    package_list_var = tk.Variable(value=[])

    # Frame for buttons and file selection
    controls_frame = ttk.Frame(window,  style='TFrame')
    controls_frame.pack(anchor="nw", padx=10, pady=10, fill=tk.X)

    # Label and button for file selection
    file_label = ttk.Label(controls_frame, text="Package List:", style="TLabel")
    file_label.pack(side="left", padx=(0, 5))

    def select_file():
        """Opens a file dialog to select the package list file."""
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            global loaded_packages
            loaded_packages = load_package_list(file_path, package_list_var)
            file_path_label.config(text=os.path.basename(file_path), foreground="#2196F3")
            update_package_listbox()
        else:
            file_path_label.config(text="No file", foreground="#555")

    file_button = ttk.Button(controls_frame, text="Choose File", command=select_file, style="TButton")
    file_button.pack(side="left", padx=(0, 10))

    file_path_label = ttk.Label(controls_frame, text="No file",  style="TLabel")
    file_path_label.pack(side="left", padx=(0, 10))

    # Entry for filtering packages
    filter_entry = tk.Entry(controls_frame, font=("Arial", 9), relief="solid", borderwidth=1)
    filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    filter_entry.bind("<KeyRelease>", lambda event: update_package_listbox())  # Update on key release
    filter_entry.configure(highlightcolor="#707070")

    # Button to get installed packages
    get_packages_button = ttk.Button(controls_frame, text="Get Packages", command=lambda: handle_get_packages(), style="TButton")
    get_packages_button.pack(side="left", padx=(0, 0))

    # Checkbox Frame and Scrollbar
    checkbox_frame = ttk.Frame(window)
    checkbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

    canvas = tk.Canvas(checkbox_frame, bg="#f0f0f0", highlightthickness=0)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(checkbox_frame, orient=tk.VERTICAL, command=canvas.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    canvas.configure(yscrollcommand=scrollbar.set, scrollregion=canvas.bbox("all"))
    canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    inner_frame = ttk.Frame(canvas,  style='TFrame')
    canvas.create_window((0, 0), window=inner_frame, anchor='nw')

    def on_mousewheel(event):
        """Handle mousewheel scrolling."""
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    checkboxes = []
    def update_package_listbox():
        """Updates the listbox with checkboxes based on the package list."""
        nonlocal checkboxes
        for cb, _, _ in checkboxes: # Fix: Iterate and destroy the Checkbutton widget.
            cb.destroy()
        checkboxes = []

        package_list = package_list_var.get()
        filter_text = filter_entry.get().lower()  # Get text from entry and convert to lowercase

        if package_list:
            for package in package_list:
                if filter_text in package.lower(): # Perform case-insensitive filtering
                    selected = tk.BooleanVar(value=False)
                    cb = tk.Checkbutton(inner_frame, text=package, variable=selected, bg="#f0f0f0", font=("Arial", 9))
                    cb.pack(anchor=tk.W, pady=1)
                    checkboxes.append((cb, selected, package))
            inner_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))

    def handle_get_packages():
        """Gets the installed packages and updates the listbox."""
        packages = get_installed_packages()
        if packages:
            package_list_var.set(packages)
            update_package_listbox()
            messagebox.showinfo("Packages Loaded", "Installed packages loaded.")

    def on_uninstall():
        """Handles the uninstall button click."""
        packages_to_uninstall = []
        for cb, selected, package in checkboxes:
            if selected.get():
                packages_to_uninstall.append(package)
        if packages_to_uninstall:
            uninstall_packages(packages_to_uninstall)
        else:
            messagebox.showinfo("No Packages Selected", "Select packages to uninstall.")

    # Uninstall button
    uninstall_button = ttk.Button(window, text="Uninstall", command=on_uninstall, style="TButton")
    uninstall_button.pack(pady=15, anchor="w", padx=20)

    window.mainloop()

if __name__ == "__main__":
    create_gui()
