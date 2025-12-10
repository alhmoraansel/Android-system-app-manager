import subprocess
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from datetime import datetime
from tkinter import scrolledtext
import threading
import sys
import shutil
import re
import concurrent.futures
import time

# --- FIX: Prevent "No Console" Crashes ---
class NullWriter:
    def write(self, arg): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

# Global variables
is_diff_view_active = False
diff_list = []
existing_packages = [] 
all_packages_cache = [] 
installed_packages_cache = [] 

# --- PATH FIX: Determine correct base path for logs ---
# If frozen (exe), use the folder of the exe. If script, use __file__.
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Device Environment Globals
current_device_name = "Unknown_Device"
# Logs will now be created next to the .exe instead of inside the temporary temp folder
device_folder = os.path.join(application_path, "Unknown_Device") 
adb_executable = None 

# --- ROBUST PROCESS RUNNER ---
def run_with_timeout(cmd, timeout_sec):
    """
    Runs a command with a GUARANTEED timeout kill switch.
    """
    try:
        # If we are forced to use the system "adb" command (not a path), 
        # we generally need shell=True on Windows to resolve it correctly.
        use_shell = (cmd[0] == "adb")
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            shell=use_shell
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_sec)
            return proc.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            proc.kill() 
            proc.wait() 
            raise 
    except Exception as e:
        raise e

# --- TOOL RESOLUTION LOGIC ---
def get_bundled_path(filename):
    # This logic remains the same because we WANT internal resources 
    # to be pulled from the temp bundle (_MEIPASS)
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "bin", filename)

def resolve_initial_adb():
    """
    Finds ADB using the user's strict fallback order:
    1. System Path (REAL binaries only, ignores Shim).
    2. Chocolatey Lib paths (The real binaries hidden in lib).
    3. Local Bin subfolder.
    4. Return None (triggers User Prompt).
    """
    
    # --- 1. System Path (If it's REAL) ---
    system_adb = shutil.which("adb")
    if system_adb:
        # Filter out the "Bad" Chocolatey Shim (usually in .../chocolatey/bin/adb.exe)
        # If it's in "chocolatey" AND "bin", it's the shim -> SKIP IT.
        if "chocolatey" in system_adb.lower() and "bin" in system_adb.lower():
            pass 
        else:
            return system_adb # It's a real system ADB (e.g. C:\platform-tools\adb.exe), use it.

    # --- 2. Chocolatey "Real" Paths (Deep Search) ---
    # These bypass the shim by looking directly where the tools are installed.
    choco_paths = [
        r"C:\ProgramData\chocolatey\lib\adb\tools\platform-tools\adb.exe",
        r"C:\ProgramData\chocolatey\lib\scrcpy\tools\adb.exe",
        # Dynamic check using environment variable just in case
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"chocolatey\lib\adb\tools\platform-tools\adb.exe"),
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"chocolatey\lib\scrcpy\tools\adb.exe")
    ]
    
    for path in choco_paths:
        if os.path.exists(path):
            return path

    # --- 3. Local Bin Subfolder ---
    bundled = get_bundled_path("adb.exe")
    if os.path.exists(bundled):
        return bundled
    
    # --- 4. Fallback: Ask User ---
    return None

def force_kill_all_adb():
    """Nuclear option to clear all ADB processes."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", "adb.exe"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW
        )
    except: pass

def get_device_name_with_tool(adb_path):
    try:
        # 1. Sanity Check
        try:
            run_with_timeout([adb_path, "--version"], 5)
        except:
            return None, "Binary Unresponsive"

        # 2. Run 'devices'
        try:
            code, output, err = run_with_timeout([adb_path, "devices"], 15)
        except subprocess.TimeoutExpired:
            return None, "Daemon Start Timeout"

        if "device" not in output.replace("List of devices attached", ""):
            return None, "No device found"

        # 3. Get Model Name
        try:
            code, name, err = run_with_timeout([adb_path, "shell", "getprop", "ro.product.model"], 5)
            if code == 0:
                name = name.strip()
                name = re.sub(r'[^\w\-_]', '_', name)
                return (name if name else "Unknown_Device"), None
        except:
            return None, "Read Error"
            
    except Exception as e:
        return None, str(e)
        
    return None, "Unknown Error"

class Logger:
    def __init__(self, textbox=None):
        self.textbox = textbox
        self.log_file = os.path.join(device_folder, "operation_log.txt")
        self.setup_tags()

    def setup_tags(self):
        if self.textbox:
            self.textbox.tag_config("INFO", foreground="#212121") 
            self.textbox.tag_config("SUCCESS", foreground="#2e7d32", font=("Consolas", 13, "bold")) 
            self.textbox.tag_config("ERROR", foreground="#c62828", font=("Consolas", 13, "bold")) 
            self.textbox.tag_config("WARNING", foreground="#ef6c00", font=("Consolas", 12, "bold")) 
            self.textbox.tag_config("HEADER", foreground="#1565c0", font=("Consolas", 10, "bold")) 

    def update_log_path(self, new_folder):
        self.log_file = os.path.join(new_folder, "operation_log.txt")

    def log(self, message, level=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        if level is None:
            msg_lower = message.lower()
            if any(x in msg_lower for x in ["error", "failed", "failure", "exception", "no device", "timed out", "unresponsive", "switching"]):
                level = "ERROR"
            elif any(x in msg_lower for x in ["success", "installed successfully"]):
                level = "SUCCESS"
            elif any(x in msg_lower for x in ["warning", "no selection"]):
                level = "WARNING"
            elif any(x in msg_lower for x in ["starting", "launching", "fetching", "connecting", "attempting"]):
                level = "HEADER"
            else:
                level = "INFO"

        if self.textbox:
            def _gui_log():
                self.textbox.insert(tk.END, formatted_msg + "\n", level)
                self.textbox.see(tk.END)
            self.textbox.after(0, _gui_log)

        try:
            folder = os.path.dirname(self.log_file)
            if not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)
                
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().strftime('%Y-%m-%d')} [{level}] {message}\n")
        except Exception:
            pass

logger = None

def uninstall_packages(package_list):
    task_log_file = os.path.join(device_folder, "uninstall_log.txt")
    logger.log(f"Starting uninstall for {len(package_list)} packages...", level="HEADER")
    try:
        with open(task_log_file, "w") as f: f.write(f"Start: {datetime.now()}\n")
    except: pass

    for package_name in package_list:
        logger.log(f"Uninstalling: {package_name}", level="INFO")
        try:
            code, out, err = run_with_timeout(
                [adb_executable, "shell", "pm", "uninstall", "--user", "0", package_name], 
                15
            )
            if code == 0:
                logger.log(f"SUCCESS: {package_name}", level="SUCCESS")
                with open(task_log_file, "a") as f: f.write(f"SUCCESS: {package_name}\n")
            else:
                logger.log(f"FAILED: {package_name} (ADB Error: {err.strip()})", level="ERROR")
        except Exception as e:
            logger.log(f"ERROR: {package_name} ({str(e)})", level="ERROR")
    logger.log("Uninstallation process finished.", level="HEADER")

def install_existing_packages(package_list):
    task_log_file = os.path.join(device_folder, "install_existing_log.txt")
    logger.log(f"Starting install for {len(package_list)} packages...", level="HEADER")
    try:
        with open(task_log_file, "w") as f: f.write(f"Start: {datetime.now()}\n")
    except: pass

    for package_name in package_list:
        logger.log(f"Installing: {package_name}", level="INFO")
        try:
            code, out, err = run_with_timeout(
                [adb_executable, "shell", "pm", "install-existing", package_name], 
                15
            )
            if code == 0:
                logger.log(f"SUCCESS: {package_name}", level="SUCCESS")
                with open(task_log_file, "a") as f: f.write(f"SUCCESS: {package_name}\n")
            else:
                logger.log(f"FAILED: {package_name} (ADB Error: {err.strip()})", level="ERROR")
        except Exception as e:
            logger.log(f"ERROR: {package_name} ({str(e)})", level="ERROR")
    logger.log("Installation process finished.", level="HEADER")

def load_package_list(file_path):
    package_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                package_name = line.strip()
                if package_name and not package_name.startswith("#"):
                    package_list.append(package_name)
    except Exception as e:
        logger.log(f"Error reading file: {e}", level="ERROR")
        messagebox.showerror("Error", str(e))
        return []
    logger.log(f"Loaded {len(package_list)} packages from {os.path.basename(file_path)}.", level="HEADER")
    return package_list

def get_installed_packages_worker(all_packages):
    cmd = [adb_executable, "shell", "pm", "list", "packages"]
    if all_packages:
        cmd.append("-a")
    try:
        code, out, err = run_with_timeout(cmd, 10)
        if code == 0:
            packages = out.strip().split('\n')
            return [p.replace("package:", "").strip() for p in packages if p.strip()]
        return []
    except Exception:
        return []

def save_packages_to_file(packages, filename):
    full_path = os.path.join(device_folder, filename)
    try:
        if not os.path.exists(device_folder):
            os.makedirs(device_folder, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write("\n".join(packages))
    except Exception: pass

def run_scrcpy(flags):
    scrcpy_exe = shutil.which("scrcpy")
    if not scrcpy_exe:
        bundled = get_bundled_path("scrcpy.exe")
        if os.path.exists(bundled):
            scrcpy_exe = bundled

    if not scrcpy_exe:
        logger.log("Error: 'scrcpy' not found.", level="ERROR")
        messagebox.showerror("Error", "Scrcpy not found in PATH or bin folder.")
        return

    env = os.environ.copy()
    if os.path.isabs(adb_executable):
        env["ADB"] = adb_executable

    cmd = [scrcpy_exe] + flags
    logger.log(f"Launching Scrcpy via {adb_executable}...", level="HEADER")
    try:
        cwd_path = os.path.dirname(scrcpy_exe) if os.path.isabs(scrcpy_exe) else None
        subprocess.Popen(
            cmd, creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            env=env, cwd=cwd_path
        )
    except Exception as e:
        logger.log(f"Failed to launch scrcpy: {e}", level="ERROR")

def create_gui():
    global logger, adb_executable
    
    # 1. Initialize Root Window First (needed for dialogs)
    window = tk.Tk()
    
    # 2. Resolve ADB using new logic
    adb_executable = resolve_initial_adb()
    
    # 3. If NOT found (or only Shim found), Ask User
    if not adb_executable:
        messagebox.showinfo("ADB Missing", "A valid ADB binary was not found (or the system version is a Chocolatey Shim).\n\nPlease select your 'adb.exe' manually.")
        file_path = filedialog.askopenfilename(title="Select adb.exe", filetypes=[("Executable", "adb.exe")])
        
        if file_path and os.path.exists(file_path):
            adb_executable = file_path
        else:
            # If user cancels, we fall back to "adb" as a hail mary
            adb_executable = "adb" 

    window.title(f"ADB Manager - Starting...") 
    window.geometry("950x750")
    window.minsize(800, 600)
    window.state("zoomed")
    window.configure(bg="#f5f5f5")

    style = ttk.Style()
    style.theme_use('clam')
    bold_font = ("Segoe UI", 13, "bold")

    style.configure("Uninstall.TButton", background="#ef5350", foreground="white", font=bold_font)
    style.map("Uninstall.TButton", background=[("active", "#e53935")])
    style.configure("Install.TButton", background="#66bb6a", foreground="white", font=bold_font)
    style.map("Install.TButton", background=[("active", "#43a047")])
    style.configure("Action.TButton", background="#42a5f5", foreground="white", font=bold_font)
    style.map("Action.TButton", background=[("active", "#1e88e5")])
    style.configure("Clear.TButton", background="#ffa726", foreground="white", font=bold_font)
    style.map("Clear.TButton", background=[("active", "#fb8c00")])
    style.configure("Scrcpy.TButton", background="#26c6da", foreground="white", font=bold_font)
    style.map("Scrcpy.TButton", background=[("active", "#00acc1")])

    style.configure("PackageCheckbutton.TCheckbutton", font=("Segoe UI", 11), background="#f5f5f5", anchor="w")
    style.map("PackageCheckbutton.TCheckbutton", background=[("selected", "#e3f2fd")])
    style.configure("ExistingPackageCheckbutton.TCheckbutton", font=("Segoe UI", 11, "bold"), foreground="#2e7d32", background="#f5f5f5", anchor="w")
    style.map("ExistingPackageCheckbutton.TCheckbutton", background=[("selected", "#e8f5e9")])
    style.configure("MissingPackageCheckbutton.TCheckbutton", font=("Segoe UI", 11, "bold"), foreground="#c62828", background="#f5f5f5", anchor="w")
    style.map("MissingPackageCheckbutton.TCheckbutton", background=[("selected", "#ffebee")])

    paned_window = ttk.Panedwindow(window, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    left_frame = ttk.Frame(paned_window)
    paned_window.add(left_frame, weight=3)
    controls_frame = ttk.Frame(left_frame, padding=10)
    controls_frame.pack(anchor="nw", fill=tk.X)

    package_list_var = tk.Variable(value=[])
    
    def select_file():
        global is_diff_view_active
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            targets = load_package_list(file_path)
            if not targets: return
            for _, var, _, _ in checkboxes: var.set(False)
            
            match_count = 0
            first_match_widget = None
            for cb, var, pkg, _ in checkboxes:
                if pkg in targets:
                    var.set(True)
                    match_count += 1
                    if first_match_widget is None: first_match_widget = cb
            
            file_label.config(text=f"Selected: {os.path.basename(file_path)}", foreground="#1565c0")
            logger.log(f"Auto-selected {match_count} packages from file.", level="SUCCESS")

            if first_match_widget:
                window.update_idletasks()
                try:
                    widget_y = first_match_widget.winfo_y()
                    frame_h = scrollable_frame.winfo_height()
                    if frame_h > 0: canvas.yview_moveto(max(0, (widget_y - 30) / frame_h))
                except: pass
        update_diff_btn()

    ttk.Button(controls_frame, text="Load List File", command=select_file, style="Action.TButton").pack(side="left", padx=(0, 10))
    file_label = ttk.Label(controls_frame, text="No file loaded", font=("Segoe UI", 9))
    file_label.pack(side="left", padx=(0, 10))

    filter_frame = ttk.Frame(controls_frame)
    filter_frame.pack(side="left", fill="x", expand=True, padx=10)
    ttk.Label(filter_frame, text="Filter:").pack(side="left")
    filter_entry = tk.Entry(filter_frame, font=("Segoe UI", 12))
    filter_entry.pack(side="left", fill="x", expand=True, padx=5)

    refresh_frame = ttk.Frame(controls_frame)
    refresh_frame.pack(side="right")
    
    refresh_btn = ttk.Button(refresh_frame, text="Refresh", command=lambda: fetch_packages_thread(True), style="Action.TButton")
    refresh_btn.pack(side="left", padx=2)

    list_container = ttk.Frame(left_frame, padding=(10,0,10,0))
    list_container.pack(fill=tk.BOTH, expand=True)
    
    select_all_var = tk.BooleanVar(value=False)
    checkboxes = []

    def toggle_select_all():
        val = select_all_var.get()
        for _, var, _, _ in checkboxes: var.set(val)

    ttk.Checkbutton(list_container, text="Select All Displayed", variable=select_all_var, command=toggle_select_all).pack(anchor="w", pady=(0,5))

    canvas = tk.Canvas(list_container, bg="white", highlightthickness=1, highlightbackground="#e0e0e0")
    scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas, style="TFrame")
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    def _bind_to_mousewheel(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    def _unbind_from_mousewheel(event):
        canvas.unbind_all("<MouseWheel>")
    list_container.bind('<Enter>', _bind_to_mousewheel)
    list_container.bind('<Leave>', _unbind_from_mousewheel)
    filter_entry.bind("<KeyRelease>", lambda e: update_package_listbox())

    right_frame = ttk.Frame(paned_window, padding=10)
    paned_window.add(right_frame, weight=2)

    scrcpy_frame = ttk.LabelFrame(right_frame, text="Scrcpy Tools", padding=10)
    scrcpy_frame.pack(fill=tk.X, pady=(0, 10))
    ttk.Button(scrcpy_frame, text="Project Screen", command=lambda: run_scrcpy([]), style="Scrcpy.TButton").pack(fill=tk.X, pady=2)
    ttk.Button(scrcpy_frame, text="Mouse Only (Stealth)", command=lambda: run_scrcpy(["--no-video-playback", "--no-audio", "-K", "-M"]), style="Scrcpy.TButton").pack(fill=tk.X, pady=2)
    ttk.Button(scrcpy_frame, text="Audio Cast Only", command=lambda: run_scrcpy(["--no-video-playback", "--audio-output-buffer=20"]), style="Scrcpy.TButton").pack(fill=tk.X, pady=2)

    ttk.Label(right_frame, text="System Log:").pack(anchor="w")
    log_textbox = scrolledtext.ScrolledText(right_frame, font=("Consolas", 9), height=15, state='normal')
    log_textbox.pack(fill=tk.BOTH, expand=True)
    
    logger = Logger(log_textbox)
    logger.log(f"GUI Started. Initial ADB: {adb_executable}", level="HEADER")

    def update_package_listbox():
        nonlocal checkboxes
        for cb, _, _, _ in checkboxes: cb.destroy()
        checkboxes = []
        filter_txt = filter_entry.get().lower()
        source = diff_list if is_diff_view_active else package_list_var.get()
        
        for pkg in source:
            if filter_txt in pkg.lower():
                var = tk.BooleanVar(value=select_all_var.get())
                is_inst = pkg in existing_packages
                style_n = "MissingPackageCheckbutton.TCheckbutton" if is_diff_view_active else ("ExistingPackageCheckbutton.TCheckbutton" if is_inst else "PackageCheckbutton.TCheckbutton")
                cb = ttk.Checkbutton(scrollable_frame, text=pkg, variable=var, style=style_n)
                cb.pack(anchor="w", fill="x", pady=1)
                checkboxes.append((cb, var, pkg, is_inst))

    def fetch_packages_thread(get_all=False):
        logger.log("Initiating ADB connection...", level="HEADER")
        refresh_btn.config(state="disabled")

        def task():
            global existing_packages, installed_packages_cache, all_packages_cache, current_device_name, device_folder, adb_executable
            
            logger.log("Scanning for active ADB connection...", level="INFO")
            # FIX: Kill command removed.
            
            # PHASE 1: Try System ADB (with safety net)
            logger.log(f"Attempting connection with: {adb_executable}", level="INFO")
            new_device_name, error_reason = get_device_name_with_tool(adb_executable)
            
            # PHASE 2: Fallback to Bundled
            if not new_device_name:
                logger.log(f"Connection failed ({error_reason}).", level="WARNING")
                
                bundled_adb = get_bundled_path("adb.exe")
                if adb_executable != bundled_adb and os.path.exists(bundled_adb):
                    logger.log("Switching to Bundled ADB...", level="WARNING")
                    
                    # We only force kill if the FIRST attempt failed, just in case the shim is truly broken.
                    force_kill_all_adb() 
                    adb_executable = bundled_adb
                    
                    new_device_name, error_reason = get_device_name_with_tool(adb_executable)

            if new_device_name is None:
                msg = f"Failed to connect. Error: {error_reason}. Check cable/drivers."
                window.after(0, lambda: logger.log(msg, level="ERROR"))
                window.after(0, lambda: refresh_btn.config(state="normal"))
                window.after(0, lambda: window.title("ADB Manager - No Device"))
                return

            if new_device_name != current_device_name or "Unknown" in device_folder:
                current_device_name = new_device_name
                
                # --- UPDATE FIX: Use correct path for new folder creation ---
                if getattr(sys, 'frozen', False):
                    app_path = os.path.dirname(sys.executable)
                else:
                    app_path = os.path.dirname(os.path.abspath(__file__))
                    
                device_folder = os.path.join(app_path, current_device_name)
                
                if not os.path.exists(device_folder):
                    try: os.makedirs(device_folder)
                    except: pass

                logger.update_log_path(device_folder)
                window.after(0, lambda: window.title(f"ADB Manager - {current_device_name}"))

            logger.log("Fetching packages...", level="HEADER")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as exc:
                f1 = exc.submit(get_installed_packages_worker, False)
                f2 = exc.submit(get_installed_packages_worker, True)
                try:
                    res1, res2 = f1.result(), f2.result()
                    existing_packages = res1
                    installed_packages_cache[:] = res1
                    all_packages_cache[:] = res2
                    save_packages_to_file(res1, "installed_packages.txt")
                    save_packages_to_file(res2, "all_installed_packages.txt")
                    
                    def update_ui():
                        package_list_var.set(all_packages_cache if get_all else existing_packages)
                        logger.log(f"Fetched {len(all_packages_cache if get_all else existing_packages)} packages.", level="SUCCESS")
                        update_package_listbox()
                        update_diff_btn()
                        refresh_btn.config(state="normal")
                    window.after(0, update_ui)
                except Exception as e:
                    window.after(0, lambda: logger.log(f"Fetch Error: {e}", level="ERROR"))
                    window.after(0, lambda: refresh_btn.config(state="normal"))
        
        threading.Thread(target=task, daemon=True).start()

    def perform(action):
        sel = [pkg for _, var, pkg, _ in checkboxes if var.get()]
        if not sel: 
            logger.log("No selection made.", level="WARNING")
            return

        if action == "uninstall":
            threading.Thread(target=uninstall_packages, args=(sel,)).start()
        elif action == "install":
            threading.Thread(target=install_existing_packages, args=(sel,)).start()
        elif action == "save":
            path = filedialog.asksaveasfilename(initialdir=device_folder, defaultextension=".txt", initialfile=f"{current_device_name}_selection.txt")
            if path:
                try:
                    with open(path, "w") as f: f.write("\n".join(sel))
                    logger.log(f"Saved to {os.path.basename(path)}", level="SUCCESS")
                except Exception as e: messagebox.showerror("Error", str(e))

    actions_frame = ttk.Frame(left_frame, padding=10, relief="groove")
    actions_frame.pack(side="bottom", fill="x", padx=10, pady=10)
    
    def clear_sel():
        for _, var, _, _ in checkboxes: var.set(False)
        logger.log("Selection cleared.", level="INFO")
    
    ttk.Button(actions_frame, text="Clear Selection", command=clear_sel, style="Clear.TButton").pack(side="left", padx=(0, 10))
    ttk.Button(actions_frame, text="Uninstall Selected", command=lambda: perform("uninstall"), style="Uninstall.TButton").pack(side="left", fill="x", expand=True, padx=2)
    ttk.Button(actions_frame, text="Install Selected", command=lambda: perform("install"), style="Install.TButton").pack(side="left", fill="x", expand=True, padx=2)

    extra_frame = ttk.Frame(left_frame, padding=(10, 0))
    extra_frame.pack(side="bottom", fill="x")

    diff_btn = ttk.Button(extra_frame, text="Show Diff", command=lambda: toggle_diff(), state="disabled", style="Action.TButton")
    diff_btn.pack(side="right")
    
    ttk.Button(extra_frame, text="Save Selection", command=lambda: perform("save"), style="Action.TButton").pack(side="right", padx=5)

    def update_diff_btn():
        state = "normal" if installed_packages_cache and all_packages_cache else "disabled"
        diff_btn.config(state=state)

    def toggle_diff():
        global is_diff_view_active, diff_list
        is_diff_view_active = not is_diff_view_active
        if is_diff_view_active:
            diff_list = sorted(list(set(all_packages_cache) - set(installed_packages_cache)))
            diff_btn.config(text="Exit Diff View", style="Clear.TButton")
            logger.log(f"Diff View: {len(diff_list)} missing packages.", level="WARNING")
        else:
            diff_btn.config(text="Show Diff", style="Action.TButton")
            logger.log("Exited Diff View.", level="INFO")
        update_package_listbox()

    def on_closing():
        logger.log("Stopping ADB server and closing...", level="HEADER")
        try:
            force_kill_all_adb()
        except: pass
        window.destroy()
        sys.exit(0)

    window.protocol("WM_DELETE_WINDOW", on_closing)

    fetch_packages_thread(True)
    window.mainloop()

if __name__ == "__main__":
    create_gui()