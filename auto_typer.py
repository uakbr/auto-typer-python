import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, colorchooser, filedialog, simpledialog
import pyautogui
import random
import time
import threading
import json
import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw
import math

# Only import keyboard on non-macOS platforms
MACOS = sys.platform == 'darwin'
if not MACOS:
    try:
        import keyboard
    except ImportError:
        keyboard = None
else:
    keyboard = None

# Only import pystray for system tray support
try:
    import pystray
except ImportError:
    pystray = None

class AdvancedTyperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Auto Typer")
        self.root.geometry("700x650")
        self.root.minsize(600, 550)
        
        # Set app icon
        try:
            self.icon_path = self._create_default_icon()
            self.root.iconphoto(True, tk.PhotoImage(file=self.icon_path))
        except:
            pass
            
        # Variables
        self.typing_active = False
        self.paused = False
        self.typing_thread = None
        self.config_file = os.path.join(self._get_app_dir(), "typer_config.json")
        self.snippets_file = os.path.join(self._get_app_dir(), "snippets.json")
        self.char_count = 0
        self.total_chars = 0
        self.current_text = ""
        self.minimized_to_tray = False
        self.keyboard_available = keyboard is not None and not MACOS
        
        # Default settings
        self.default_settings = {
            "base_delay": 0.1,  # Base delay between keystrokes in seconds
            "delay_variability": 0.05,  # Random variability to add to base delay
            "word_delay": 0.3,  # Extra delay between words
            "typing_mode": "character",  # 'character' or 'word'
            "pause_key": "f10",  # Hotkey to pause/resume typing (was ctrl+shift+p)
            "emergency_stop_key": "f11",  # Emergency stop hotkey (was ctrl+shift+x)
            "repeat_count": 1,  # Number of times to repeat typing
            "countdown_seconds": 3,  # Seconds to countdown before typing
            "natural_typing": True,  # Simulate more natural typing patterns
            "theme": "light",  # UI theme (previously "dark")
            "minimize_to_tray": not MACOS,  # Minimize to system tray (disabled on macOS)
            "confirm_emergency_stop": True,  # Require confirmation for emergency stop
        }
        
        # Load settings
        self.settings = self.load_settings()
        self.snippets = self.load_snippets()
        
        # Create style
        self.style = ttk.Style()
        self.apply_theme()
        
        # Create GUI
        self.create_menu()
        self.create_widgets()
        
        # Register global hotkeys
        self.register_hotkeys()
        
        # Set up protocol for window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create system tray icon if supported
        if self.settings["minimize_to_tray"]:
            self.setup_system_tray()
    
    def _get_app_dir(self):
        """Get or create application directory for storing config files"""
        app_dir = os.path.join(os.path.expanduser("~"), ".advanced_typer")
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
        return app_dir
    
    def _create_default_icon(self):
        """Create a default icon for the application"""
        icon_path = os.path.join(self._get_app_dir(), "icon.png")
        if not os.path.exists(icon_path):
            # Create a simple icon
            img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse((4, 4, 60, 60), fill=(52, 152, 219))
            d.rectangle((20, 20, 44, 44), fill=(255, 255, 255))
            img.save(icon_path)
        return icon_path
    
    def setup_system_tray(self):
        """Set up system tray icon if supported"""
        # Skip system tray on macOS which has issues with pystray
        if MACOS:
            print("System tray support disabled on macOS")
            self.settings["minimize_to_tray"] = False
            self.save_settings()
            return
        
        if not pystray:
            print("Pystray module not available, system tray disabled")
            self.settings["minimize_to_tray"] = False
            self.save_settings()
            return
            
        try:
            self.tray_icon = pystray.Icon("Advanced Typer")
            self.tray_icon.icon = Image.open(self.icon_path)
            
            # Create tray menu
            menu = (
                pystray.MenuItem("Show", self.show_window),
                pystray.MenuItem("Start Typing", self.start_typing),
                pystray.MenuItem("Stop Typing", self.stop_typing),
                pystray.MenuItem("Exit", self.exit_app)
            )
            self.tray_icon.menu = pystray.Menu(*menu)
            
            # Start tray icon in a separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Failed to set up system tray: {e}")
            self.settings["minimize_to_tray"] = False
            self.save_settings()
    
    def show_window(self, icon=None, item=None):
        """Show the main window when clicked in system tray"""
        self.minimized_to_tray = False
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def exit_app(self, icon=None, item=None):
        """Exit the application from system tray"""
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.root.destroy()
    
    def on_close(self):
        """Handle window close event"""
        if self.settings["minimize_to_tray"] and hasattr(self, 'tray_icon'):
            self.root.withdraw()
            self.minimized_to_tray = True
        else:
            if hasattr(self, 'tray_icon'):
                self.tray_icon.stop()
            self.root.destroy()
    
    def register_hotkeys(self):
        """Register global hotkeys with improved macOS support"""
        # Skip hotkey registration on macOS
        if MACOS:
            self.keyboard_available = False
            print("Global hotkeys disabled on macOS")
            return
        
        # Skip if keyboard module not available
        if not keyboard:
            self.keyboard_available = False
            print("Keyboard module not available")
            return
        
        try:
            # Try to unhook any existing hotkeys
            try:
                keyboard.unhook_all()
            except:
                pass
            
            # Register the hotkeys
            keyboard.add_hotkey(self.settings["emergency_stop_key"], self.emergency_stop)
            keyboard.add_hotkey(self.settings["pause_key"], self.toggle_pause)
            keyboard.add_hotkey('f9', self.start_typing)
            keyboard.add_hotkey('f10', self.toggle_pause)
            keyboard.add_hotkey('f11', self.stop_typing)
            
            # Mark keyboard as available
            self.keyboard_available = True
            print("Global hotkeys registered successfully")
        except Exception as e:
            # Any error during hotkey registration
            self.keyboard_available = False
            messagebox.showwarning(
                "Hotkey Warning", 
                f"Failed to register hotkeys: {str(e)}\n\n"
                "The application will still work, but global hotkeys may not function."
            )
        
        # Update the UI to show keyboard status
        if not self.keyboard_available:
            self.update_ui_for_limited_mode()
    
    def update_ui_for_limited_mode(self):
        """Update UI to indicate limited mode without global hotkeys"""
        # We'll implement this later when creating the UI
        pass
    
    def apply_theme(self):
        """Apply the selected theme to the application"""
        if self.settings["theme"] == "dark":
            self.style.theme_use("clam")
            self.bg_color = "#2d2d2d"
            self.fg_color = "#ffffff"
            self.accent_color = "#3498db"
            self.input_bg_color = "#383838"  # Slightly lighter than background for input areas
            self.root.configure(bg=self.bg_color)
            self.style.configure("TButton", background=self.accent_color, foreground="white")
            self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("TFrame", background=self.bg_color)
            self.style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("Horizontal.TProgressbar", background=self.accent_color)
        else:
            self.style.theme_use("clam")
            self.bg_color = "#f5f5f5"
            self.fg_color = "#000000"
            self.accent_color = "#3498db"
            self.input_bg_color = "#ffffff"  # White background for input areas
            self.root.configure(bg=self.bg_color)
            self.style.configure("TButton", background=self.accent_color, foreground="black")
            self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("TFrame", background=self.bg_color)
            self.style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("Horizontal.TProgressbar", background=self.accent_color)
    
    def create_menu(self):
        """Create the application menu"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Text", command=self.save_text)
        file_menu.add_command(label="Load Text", command=self.load_text)
        file_menu.add_separator()
        file_menu.add_command(label="Save as Snippet", command=self.save_as_snippet)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Options menu
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="Settings", command=self.show_settings)
        
        # Theme submenu
        theme_menu = tk.Menu(options_menu, tearoff=0)
        theme_menu.add_command(label="Light", command=lambda: self.change_theme("light"))
        theme_menu.add_command(label="Dark", command=lambda: self.change_theme("dark"))
        options_menu.add_cascade(label="Theme", menu=theme_menu)
        
        options_menu.add_separator()
        options_menu.add_command(label="Manage Snippets", command=self.manage_snippets)
        menubar.add_cascade(label="Options", menu=options_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Instructions", command=self.show_instructions)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def change_theme(self, theme):
        """Change the application theme"""
        self.settings["theme"] = theme
        self.save_settings()
        self.apply_theme()
        
        # Update all frames' backgrounds
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame) or isinstance(widget, ttk.Frame):
                widget.configure(bg=self.bg_color)
            
        # Need to recreate widgets with new theme
        for widget in self.root.winfo_children():
            if widget != self.root.nametowidget('.!menu'):
                widget.destroy()
        
        self.create_widgets()
    
    def show_about(self):
        """Show the about dialog"""
        about_text = "Advanced Auto Typer\n\nVersion 2.0\n\n" \
                     "A powerful tool for automating keyboard input with advanced features.\n\n" \
                     "Created using Python, Tkinter, and PyAutoGUI."
        messagebox.showinfo("About", about_text)
    
    def show_instructions(self):
        """Show the instructions dialog"""
        instructions = (
            "Instructions:\n\n"
            "1. Enter or paste the text you want to type automatically.\n"
            "2. Configure typing settings as needed.\n"
            "3. Position your cursor where you want the text to appear.\n"
            "4. Click 'Start Typing' or press F9.\n"
            "5. Wait for the countdown to complete.\n"
            "6. The application will type your text automatically.\n\n"
            "Controls:\n"
            f"- Start Typing: 'Start' button or F9\n"
            f"- Pause/Resume: 'Pause' button, F10, or {self.settings['pause_key']}\n"
            f"- Stop: 'Stop' button, F11\n"
            f"- Emergency Stop: {self.settings['emergency_stop_key']} (works globally)\n\n"
            "Features:\n"
            "- Save and load text\n"
            "- Save and manage frequently used snippets\n"
            "- Configure typing speed and variability\n"
            "- Type character-by-character or word-by-word\n"
            "- Natural typing patterns simulation\n"
            "- Progress tracking\n"
            "- System tray support"
        )
        
        # Create a custom dialog for instructions
        dialog = tk.Toplevel(self.root)
        dialog.title("Instructions")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.bg_color)
        
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, height=20, width=60)
        text.insert(tk.END, instructions)
        text.configure(state=tk.DISABLED, bg=self.input_bg_color, fg=self.fg_color)
        text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Button(frame, text="Close", command=dialog.destroy).pack(pady=10)
    
    def show_settings(self):
        """Show settings dialog"""
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("Settings")
        settings_dialog.geometry("500x500")
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        settings_dialog.configure(bg=self.bg_color)
        
        # Create tabbed interface
        notebook = ttk.Notebook(settings_dialog)
        
        # Typing settings tab
        typing_frame = ttk.Frame(notebook, padding=10)
        notebook.add(typing_frame, text="Typing")
        
        # Timing settings
        ttk.Label(typing_frame, text="Typing Speed Settings:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5))
        
        timing_frame = ttk.Frame(typing_frame)
        timing_frame.grid(row=1, column=0, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(timing_frame, text="Base Delay (seconds):").grid(row=0, column=0, sticky=tk.W, padx=5)
        base_delay_var = tk.StringVar(value=str(self.settings["base_delay"]))
        ttk.Entry(timing_frame, textvariable=base_delay_var, width=6).grid(row=0, column=1, padx=5)
        
        ttk.Label(timing_frame, text="Variability:").grid(row=0, column=2, sticky=tk.W, padx=5)
        variability_var = tk.StringVar(value=str(self.settings["delay_variability"]))
        ttk.Entry(timing_frame, textvariable=variability_var, width=6).grid(row=0, column=3, padx=5)
        
        ttk.Label(timing_frame, text="Word Delay:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        word_delay_var = tk.StringVar(value=str(self.settings["word_delay"]))
        ttk.Entry(timing_frame, textvariable=word_delay_var, width=6).grid(row=1, column=1, padx=5, pady=(5, 0))
        
        # Typing mode
        ttk.Label(typing_frame, text="Typing Mode:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        mode_frame = ttk.Frame(typing_frame)
        mode_frame.grid(row=3, column=0, sticky=tk.W, pady=5)
        
        mode_var = tk.StringVar(value=self.settings["typing_mode"])
        ttk.Radiobutton(mode_frame, text="Character by Character", 
                        variable=mode_var, value="character").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Radiobutton(mode_frame, text="Word by Word", 
                        variable=mode_var, value="word").grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Natural typing option
        natural_typing_var = tk.BooleanVar(value=self.settings["natural_typing"])
        ttk.Checkbutton(typing_frame, text="Simulate Natural Typing Patterns", 
                       variable=natural_typing_var).grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        
        # Repeat count
        repeat_frame = ttk.Frame(typing_frame)
        repeat_frame.grid(row=5, column=0, sticky=tk.W, pady=5)
        
        ttk.Label(repeat_frame, text="Repeat Count:").grid(row=0, column=0, sticky=tk.W, padx=5)
        repeat_var = tk.IntVar(value=self.settings["repeat_count"])
        ttk.Spinbox(repeat_frame, from_=1, to=100, textvariable=repeat_var, width=5).grid(row=0, column=1, padx=5)
        
        # Countdown seconds
        countdown_frame = ttk.Frame(typing_frame)
        countdown_frame.grid(row=6, column=0, sticky=tk.W, pady=5)
        
        ttk.Label(countdown_frame, text="Countdown Seconds:").grid(row=0, column=0, sticky=tk.W, padx=5)
        countdown_var = tk.IntVar(value=self.settings["countdown_seconds"])
        ttk.Spinbox(countdown_frame, from_=0, to=10, textvariable=countdown_var, width=5).grid(row=0, column=1, padx=5)
        
        # Controls tab
        controls_frame = ttk.Frame(notebook, padding=10)
        notebook.add(controls_frame, text="Controls")
        
        # Hotkey settings
        ttk.Label(controls_frame, text="Hotkey Settings:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5))
        
        hotkey_frame = ttk.Frame(controls_frame)
        hotkey_frame.grid(row=1, column=0, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(hotkey_frame, text="Pause Key:").grid(row=0, column=0, sticky=tk.W, padx=5)
        pause_key_var = tk.StringVar(value=self.settings["pause_key"])
        pause_key_entry = ttk.Entry(hotkey_frame, textvariable=pause_key_var, width=15)
        pause_key_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(hotkey_frame, text="Emergency Stop Key:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=(5, 0))
        stop_key_var = tk.StringVar(value=self.settings["emergency_stop_key"])
        stop_key_entry = ttk.Entry(hotkey_frame, textvariable=stop_key_var, width=15)
        stop_key_entry.grid(row=1, column=1, padx=5, pady=(5, 0))
        
        # Record hotkeys
        ttk.Button(hotkey_frame, text="Record Pause Key", 
                  command=lambda: self.record_hotkey(pause_key_entry)).grid(row=0, column=2, padx=5)
        ttk.Button(hotkey_frame, text="Record Stop Key", 
                  command=lambda: self.record_hotkey(stop_key_entry)).grid(row=1, column=2, padx=5, pady=(5, 0))
        
        # Emergency stop confirmation
        confirm_stop_var = tk.BooleanVar(value=self.settings["confirm_emergency_stop"])
        ttk.Checkbutton(controls_frame, text="Require Confirmation for Emergency Stop", 
                       variable=confirm_stop_var).grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        # Interface tab
        interface_frame = ttk.Frame(notebook, padding=10)
        notebook.add(interface_frame, text="Interface")
        
        # Theme selection
        ttk.Label(interface_frame, text="Theme:").grid(row=0, column=0, sticky=tk.W, pady=(10, 5))
        
        theme_frame = ttk.Frame(interface_frame)
        theme_frame.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        theme_var = tk.StringVar(value=self.settings["theme"])
        ttk.Radiobutton(theme_frame, text="Light", 
                        variable=theme_var, value="light").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Radiobutton(theme_frame, text="Dark", 
                        variable=theme_var, value="dark").grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # System tray option
        tray_var = tk.BooleanVar(value=self.settings["minimize_to_tray"])
        ttk.Checkbutton(interface_frame, text="Minimize to System Tray", 
                       variable=tray_var).grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Buttons
        button_frame = ttk.Frame(settings_dialog, padding=10)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_settings_dialog(
            base_delay_var.get(), variability_var.get(), word_delay_var.get(), 
            mode_var.get(), natural_typing_var.get(), repeat_var.get(), countdown_var.get(),
            pause_key_var.get(), stop_key_var.get(), confirm_stop_var.get(),
            theme_var.get(), tray_var.get(), settings_dialog
        )).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=settings_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=lambda: self.reset_settings(settings_dialog)).pack(side=tk.LEFT, padx=5)
    
    def record_hotkey(self, entry_widget):
        """Record a hotkey combination from user input"""
        # Create a small dialog to record the hotkey
        dialog = tk.Toplevel(self.root)
        dialog.title("Record Hotkey")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.bg_color)
        
        ttk.Label(dialog, text="Press the key combination you want to use\n"
                "and then click 'Save'").pack(pady=(20, 10))
        
        key_var = tk.StringVar(value="")
        ttk.Label(dialog, textvariable=key_var, font=("Arial", 12, "bold")).pack(pady=10)
        
        def on_key_press(e):
            key = []
            if e.state & 0x4:  # Control
                key.append("ctrl")
            if e.state & 0x1:  # Shift
                key.append("shift")
            if e.state & 0x8:  # Alt
                key.append("alt")
            
            # Add the actual key pressed
            if e.keysym == "Control_L" or e.keysym == "Control_R":
                pass  # Skip control keys themselves
            elif e.keysym == "Alt_L" or e.keysym == "Alt_R":
                pass  # Skip alt keys themselves
            elif e.keysym == "Shift_L" or e.keysym == "Shift_R":
                pass  # Skip shift keys themselves
            else:
                key.append(e.keysym.lower())
            
            key_var.set("+".join(key))
        
        dialog.bind("<KeyPress>", on_key_press)
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, pady=10)
        
        ttk.Button(button_frame, text="Save", command=lambda: [
            entry_widget.delete(0, tk.END),
            entry_widget.insert(0, key_var.get()),
            dialog.destroy()
        ]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def save_settings_dialog(self, base_delay, variability, word_delay, mode, natural_typing, 
                           repeat_count, countdown, pause_key, stop_key, confirm_stop,
                           theme, tray, dialog):
        """Save settings from the settings dialog"""
        try:
            # Validate numeric inputs
            base_delay = float(base_delay)
            variability = float(variability)
            word_delay = float(word_delay)
            repeat_count = int(repeat_count)
            countdown = int(countdown)
            
            # Update settings
            self.settings["base_delay"] = base_delay
            self.settings["delay_variability"] = variability
            self.settings["word_delay"] = word_delay
            self.settings["typing_mode"] = mode
            self.settings["natural_typing"] = natural_typing
            self.settings["repeat_count"] = repeat_count
            self.settings["countdown_seconds"] = countdown
            self.settings["confirm_emergency_stop"] = confirm_stop
            
            # Check if theme changed
            theme_changed = self.settings["theme"] != theme
            self.settings["theme"] = theme
            
            # Check if tray setting changed
            tray_changed = self.settings["minimize_to_tray"] != tray
            self.settings["minimize_to_tray"] = tray
            
            # Check if hotkeys need updating
            hotkeys_changed = (
                self.settings["pause_key"] != pause_key or
                self.settings["emergency_stop_key"] != stop_key
            )
            
            self.settings["pause_key"] = pause_key
            self.settings["emergency_stop_key"] = stop_key
            
            # Save settings
            self.save_settings()
            
            # Re-register hotkeys if changed
            if hotkeys_changed:
                self.register_hotkeys()
            
            # Update system tray if changed
            if tray_changed:
                if tray:
                    self.setup_system_tray()
                else:
                    if hasattr(self, 'tray_icon'):
                        self.tray_icon.stop()
                        delattr(self, 'tray_icon')
            
            # Apply theme if changed
            if theme_changed:
                self.apply_theme()
                # Need to recreate widgets with new theme
                for widget in self.root.winfo_children():
                    if widget != self.root.nametowidget('.!menu'):
                        widget.destroy()
                self.create_widgets()
            
            dialog.destroy()
            messagebox.showinfo("Settings", "Settings updated successfully")
            
        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {str(e)}\n\nPlease check numeric values.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update settings: {str(e)}")
    
    def reset_settings(self, dialog=None):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            # Make a copy of the theme to check if it changed
            old_theme = self.settings["theme"] if "theme" in self.settings else "light"
            
            # Reset settings
            self.settings = self.default_settings.copy()
            self.save_settings()
            
            # Check if theme changed
            if old_theme != self.settings["theme"]:
                self.apply_theme()
                # Need to recreate widgets with new theme
                for widget in self.root.winfo_children():
                    if widget != self.root.nametowidget('.!menu'):
                        widget.destroy()
                self.create_widgets()
            
            # Re-register hotkeys
            self.register_hotkeys()
            
            # Close dialog if provided
            if dialog:
                dialog.destroy()
            
            messagebox.showinfo("Settings", "Settings reset to defaults")
    
    def load_settings(self):
        """Load settings from config file or use defaults if file doesn't exist"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    settings = json.load(f)
                    
                    # Ensure all settings exist (add defaults for new settings)
                    for key, value in self.default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    
                    return settings
            except Exception as e:
                print(f"Failed to load config: {str(e)}")
                return self.default_settings.copy()
        else:
            return self.default_settings.copy()
    
    def save_settings(self):
        """Save current settings to config file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {str(e)}")
    
    def load_snippets(self):
        """Load saved text snippets"""
        if os.path.exists(self.snippets_file):
            try:
                with open(self.snippets_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load snippets: {str(e)}")
                return {}
        else:
            return {}
    
    def save_snippets(self):
        """Save text snippets"""
        try:
            with open(self.snippets_file, 'w') as f:
                json.dump(self.snippets, f, indent=2)
        except Exception as e:
            print(f"Failed to save snippets: {str(e)}")
    
    def save_as_snippet(self):
        """Save current text as a snippet"""
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Info", "Please enter some text to save as a snippet")
            return
        
        # Get snippet name
        name = simpledialog.askstring("Save Snippet", "Enter a name for this snippet:")
        if not name:
            return
        
        self.snippets[name] = text
        self.save_snippets()
        
        # Update snippets menu if it exists
        if hasattr(self, 'snippets_menu'):
            self.update_snippets_menu()
        
        messagebox.showinfo("Snippet Saved", f"Snippet '{name}' saved successfully")
    
    def manage_snippets(self):
        """Manage saved snippets"""
        if not self.snippets:
            messagebox.showinfo("No Snippets", "You don't have any saved snippets yet.")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Snippets")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.bg_color)
        
        # Snippets list
        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Select a snippet:").pack(anchor=tk.W, pady=(0, 5))
        
        # Create listbox with scrollbar
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        snippet_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                 bg=self.bg_color, fg=self.fg_color, 
                                 selectbackground=self.accent_color)
        snippet_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=snippet_list.yview)
        
        # Populate listbox
        for name in sorted(self.snippets.keys()):
            snippet_list.insert(tk.END, name)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        preview_text = scrolledtext.ScrolledText(preview_frame, height=5, wrap=tk.WORD,
                                               bg=self.input_bg_color, fg=self.fg_color)
        preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Function to update preview
        def update_preview(event=None):
            selection = snippet_list.curselection()
            if selection:
                name = snippet_list.get(selection[0])
                preview_text.delete("1.0", tk.END)
                preview_text.insert(tk.END, self.snippets[name])
        
        snippet_list.bind("<<ListboxSelect>>", update_preview)
        
        # Buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Use Selected", command=lambda: [
            self.use_snippet(snippet_list.get(snippet_list.curselection()[0]) if snippet_list.curselection() else None),
            dialog.destroy()
        ]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Rename", command=lambda: [
            self.rename_snippet(snippet_list.get(snippet_list.curselection()[0]) if snippet_list.curselection() else None,
                             snippet_list)
        ]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Delete", command=lambda: [
            self.delete_snippet(snippet_list.get(snippet_list.curselection()[0]) if snippet_list.curselection() else None,
                             snippet_list)
        ]).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def use_snippet(self, name):
        """Use the selected snippet"""
        if not name:
            return
        
        # Get confirmation
        if messagebox.askyesno("Use Snippet", f"Replace current text with snippet '{name}'?"):
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, self.snippets[name])
            self.update_char_count()
    
    def rename_snippet(self, name, listbox):
        """Rename a snippet"""
        if not name:
            messagebox.showinfo("Select Snippet", "Please select a snippet to rename")
            return
        
        # Get new name
        new_name = simpledialog.askstring("Rename Snippet", "Enter new name:", initialvalue=name)
        if not new_name or new_name == name:
            return
        
        # Check if name already exists
        if new_name in self.snippets:
            messagebox.showerror("Error", f"A snippet named '{new_name}' already exists")
            return
        
        # Rename snippet
        self.snippets[new_name] = self.snippets[name]
        del self.snippets[name]
        self.save_snippets()
        
        # Update listbox
        selection = listbox.curselection()[0]
        listbox.delete(0, tk.END)
        for n in sorted(self.snippets.keys()):
            listbox.insert(tk.END, n)
        
        # Try to select the renamed item
        for i, n in enumerate(sorted(self.snippets.keys())):
            if n == new_name:
                listbox.selection_set(i)
                listbox.see(i)
                break
        
        # Update snippets menu if it exists
        if hasattr(self, 'snippets_menu'):
            self.update_snippets_menu()
    
    def delete_snippet(self, name, listbox):
        """Delete a snippet"""
        if not name:
            messagebox.showinfo("Select Snippet", "Please select a snippet to delete")
            return
        
        # Get confirmation
        if not messagebox.askyesno("Delete Snippet", f"Are you sure you want to delete snippet '{name}'?"):
            return
        
        # Delete snippet
        del self.snippets[name]
        self.save_snippets()
        
        # Update listbox
        listbox.delete(0, tk.END)
        for n in sorted(self.snippets.keys()):
            listbox.insert(tk.END, n)
        
        # Update snippets menu if it exists
        if hasattr(self, 'snippets_menu'):
            self.update_snippets_menu()
    
    def save_text(self):
        """Save current text to a file"""
        text = self.text_input.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Info", "There is no text to save")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Text"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Success", "Text saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def load_text(self):
        """Load text from a file"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Load Text"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, text)
            self.update_char_count()
            messagebox.showinfo("Success", "Text loaded successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {str(e)}")
    
    def create_widgets(self):
        """Create GUI widgets"""
        # Main container frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a message for limited mode if keyboard module isn't available
        if not self.keyboard_available:
            limited_frame = ttk.Frame(main_frame)
            limited_frame.pack(fill=tk.X, pady=(0, 10))
            
            limited_label = ttk.Label(
                limited_frame, 
                text="Running in limited mode: Global hotkeys unavailable",
                foreground="#cc3300",
                font=("Arial", 10, "bold")
            )
            limited_label.pack(side=tk.LEFT)
            
            help_button = ttk.Button(
                limited_frame, 
                text="Fix This",
                command=self.show_hotkey_help
            )
            help_button.pack(side=tk.RIGHT)
        
        # Text input section
        input_frame = ttk.LabelFrame(main_frame, text="Text to Type", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Text area toolbar
        toolbar_frame = ttk.Frame(input_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Text area
        self.text_input = scrolledtext.ScrolledText(
            input_frame, height=10, wrap=tk.WORD, 
            bg=self.input_bg_color, fg=self.fg_color,
            insertbackground=self.fg_color  # Cursor color
        )
        self.text_input.pack(fill=tk.BOTH, expand=True)
        
        # Bind event to update character count
        self.text_input.bind("<KeyRelease>", self.update_char_count)
        
        # Character count
        count_frame = ttk.Frame(input_frame)
        count_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.char_count_var = tk.StringVar(value="Characters: 0")
        ttk.Label(count_frame, textvariable=self.char_count_var).pack(side=tk.LEFT)
        
        self.word_count_var = tk.StringVar(value="Words: 0")
        ttk.Label(count_frame, textvariable=self.word_count_var).pack(side=tk.LEFT, padx=(20, 0))
        
        # Snippets menu
        if self.snippets:
            snippets_button = ttk.Menubutton(toolbar_frame, text="Snippets ▼")
            snippets_button.pack(side=tk.LEFT)
            
            self.snippets_menu = tk.Menu(snippets_button, tearoff=0)
            snippets_button.configure(menu=self.snippets_menu)
            
            self.update_snippets_menu()
        
        # Control section
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Settings quick-access frame
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Speed control
        speed_frame = ttk.Frame(settings_frame)
        speed_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)
        
        self.speed_var = tk.DoubleVar(value=self.settings["base_delay"])
        speed_scale = ttk.Scale(
            speed_frame, from_=0.01, to=0.5, 
            variable=self.speed_var, 
            orient=tk.HORIZONTAL, length=120,
            command=self.update_speed
        )
        speed_scale.pack(side=tk.LEFT, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text=f"{self.settings['base_delay']:.2f}s")
        self.speed_label.pack(side=tk.LEFT)
        
        # Repeat count
        repeat_frame = ttk.Frame(settings_frame)
        repeat_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(repeat_frame, text="Repeat:").pack(side=tk.LEFT)
        
        self.repeat_var = tk.IntVar(value=self.settings["repeat_count"])
        repeat_spinbox = ttk.Spinbox(
            repeat_frame, from_=1, to=100, 
            textvariable=self.repeat_var, width=3,
            command=self.update_repeat
        )
        repeat_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Natural typing checkbox
        self.natural_typing_var = tk.BooleanVar(value=self.settings["natural_typing"])
        natural_check = ttk.Checkbutton(
            settings_frame, text="Natural Typing", 
            variable=self.natural_typing_var,
            command=self.update_natural_typing
        )
        natural_check.pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Status indicator
        status_frame = ttk.Frame(button_frame)
        status_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                               width=12, anchor=tk.CENTER, 
                               relief=tk.SUNKEN, padding=5)
        status_label.pack(side=tk.TOP)
        
        # Status lights (using canvas for colored indicators)
        self.status_canvas = tk.Canvas(status_frame, width=80, height=10, 
                                     bg=self.bg_color, highlightthickness=0)
        self.status_canvas.pack(side=tk.BOTTOM, pady=(2, 0))
        
        # Draw status indicators
        self.status_indicators = {}
        colors = {"ready": "#00cc00", "typing": "#0066cc", "paused": "#ffcc00", "stopped": "#cc0000"}
        pos_x = 10
        for status, color in colors.items():
            self.status_indicators[status] = self.status_canvas.create_oval(
                pos_x, 2, pos_x+8, 10, fill="#555555", outline="")
            pos_x += 20
        
        # Highlight ready status initially
        self.status_canvas.itemconfig(self.status_indicators["ready"], fill=colors["ready"])
        
        # Start button
        self.start_button = ttk.Button(
            button_frame, text="Start Typing (F9)", 
            command=self.start_typing
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Pause button
        self.pause_button = ttk.Button(
            button_frame, text="Pause (F10)", 
            command=self.toggle_pause, state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_button = ttk.Button(
            button_frame, text="Stop (F11)", 
            command=self.stop_typing, state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Settings button
        settings_button = ttk.Button(
            button_frame, text="Settings", 
            command=self.show_settings
        )
        settings_button.pack(side=tk.RIGHT, padx=5)
        
        # Test area
        test_frame = ttk.LabelFrame(main_frame, text="Test Area (Practice typing here)", padding=10)
        test_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.test_area = scrolledtext.ScrolledText(
            test_frame, height=5, wrap=tk.WORD,
            bg=self.input_bg_color, fg=self.fg_color,
            insertbackground=self.fg_color
        )
        self.test_area.pack(fill=tk.BOTH, expand=True)
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, orient=tk.HORIZONTAL, 
            length=100, mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        # Progress percentage
        self.progress_percent = ttk.Label(progress_frame, text="0%", width=5)
        self.progress_percent.pack(side=tk.LEFT, padx=(5, 0))
        
        # Update initial character count
        self.update_char_count()
    
    def update_snippets_menu(self):
        """Update the snippets dropdown menu"""
        if not hasattr(self, 'snippets_menu'):
            return
            
        # Clear menu
        self.snippets_menu.delete(0, tk.END)
        
        # Add snippets
        for name in sorted(self.snippets.keys()):
            self.snippets_menu.add_command(
                label=name, 
                command=lambda n=name: self.use_snippet(n)
            )
        
        # Add manage option
        if self.snippets:
            self.snippets_menu.add_separator()
        self.snippets_menu.add_command(label="Manage Snippets...", command=self.manage_snippets)
    
    def update_speed(self, value=None):
        """Update typing speed from slider"""
        value = self.speed_var.get()
        self.settings["base_delay"] = value
        self.speed_label.config(text=f"{value:.2f}s")
        self.save_settings()
    
    def update_repeat(self):
        """Update repeat count from spinbox"""
        value = self.repeat_var.get()
        self.settings["repeat_count"] = value
        self.save_settings()
    
    def update_natural_typing(self):
        """Update natural typing setting"""
        value = self.natural_typing_var.get()
        self.settings["natural_typing"] = value
        self.save_settings()
    
    def update_char_count(self, event=None):
        """Update character and word count display"""
        text = self.text_input.get("1.0", tk.END).rstrip('\n')
        chars = len(text)
        words = len(text.split()) if text else 0
        
        self.char_count_var.set(f"Characters: {chars}")
        self.word_count_var.set(f"Words: {words}")
    
    def update_progress(self, current, total):
        """Update progress bar and percentage"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.progress_percent.config(text=f"{int(progress)}%")
        else:
            self.progress_var.set(0)
            self.progress_percent.config(text="0%")
    
    def set_status(self, status):
        """Update status display and indicator lights"""
        self.status_var.set(status.capitalize())
        
        # Reset all indicators
        colors = {"ready": "#00cc00", "typing": "#0066cc", "paused": "#ffcc00", "stopped": "#cc0000"}
        for s in self.status_indicators:
            self.status_canvas.itemconfig(self.status_indicators[s], fill="#555555")
        
        # Highlight current status
        if status.lower() in self.status_indicators:
            self.status_canvas.itemconfig(
                self.status_indicators[status.lower()], 
                fill=colors[status.lower()]
            )
    
    def countdown(self, seconds):
        """Display countdown before typing starts"""
        if seconds <= 0:
            return
        
        # Create countdown overlay
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        overlay.attributes('-alpha', 0.8)
        overlay.configure(bg='black')
        
        # Position at center of screen
        width = 200
        height = 200
        x = self.root.winfo_screenwidth() // 2 - width // 2
        y = self.root.winfo_screenheight() // 2 - height // 2
        overlay.geometry(f"{width}x{height}+{x}+{y}")
        
        # Countdown label
        count_var = tk.StringVar()
        label = tk.Label(
            overlay, textvariable=count_var, 
            font=("Arial", 72, "bold"), 
            bg='black', fg='white'
        )
        label.pack(expand=True, fill=tk.BOTH)
        
        # Update function for countdown
        def update_countdown(remaining):
            if remaining <= 0:
                overlay.destroy()
                return
            
            count_var.set(str(remaining))
            overlay.update()
            self.root.after(1000, update_countdown, remaining - 1)
        
        # Start countdown
        update_countdown(seconds)
        
        # Wait for countdown to complete
        self.root.wait_window(overlay)
    
    def start_typing(self):
        """Start the typing process"""
        if self.typing_active:
            return
        
        self.current_text = self.text_input.get("1.0", tk.END).strip()
        if not self.current_text:
            messagebox.showinfo("Info", "Please enter some text to type")
            return
        
        # Calculate total characters for progress tracking
        self.total_chars = len(self.current_text) * self.settings["repeat_count"]
        self.char_count = 0
        self.update_progress(0, self.total_chars)
        
        # Show countdown if enabled
        if self.settings["countdown_seconds"] > 0:
            self.countdown(self.settings["countdown_seconds"])
        
        # Start typing in a separate thread
        self.typing_active = True
        self.paused = False
        self.typing_thread = threading.Thread(target=self.typing_process)
        self.typing_thread.daemon = True
        self.typing_thread.start()
        
        # Update UI
        self.set_status("typing")
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
    
    def typing_process(self):
        """Simulate typing the text"""
        try:
            for repeat in range(self.settings["repeat_count"]):
                if not self.typing_active:
                    break
                
                if self.settings["typing_mode"] == "character":
                    # Type character by character
                    self.type_by_char()
                else:
                    # Type word by word
                    self.type_by_word()
                
                # Add extra delay between repeats
                if repeat < self.settings["repeat_count"] - 1 and self.typing_active:
                    time.sleep(self.settings["word_delay"] * 3)
            
            # Typing finished normally
            if self.typing_active:
                self.root.after(0, self.typing_completed)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Typing error: {str(e)}"))
            self.root.after(0, self.stop_typing)
    
    def type_by_char(self):
        """Type text character by character"""
        for char in self.current_text:
            if not self.typing_active:
                break
                
            # Check if paused
            while self.paused and self.typing_active:
                time.sleep(0.1)
                
            if not self.typing_active:
                break
                
            # Type the character
            pyautogui.write(char)
            
            # Update progress
            self.char_count += 1
            self.root.after(0, lambda c=self.char_count, t=self.total_chars: 
                          self.update_progress(c, t))
            
            # Add delay with variability
            if self.settings["natural_typing"]:
                # More realistic typing pattern
                if char in ['.', ',', '!', '?', ';', ':']:
                    # Longer pause after punctuation
                    delay = self.settings["base_delay"] * 2
                elif char in [' ', '\n', '\t']:
                    # Pause between words
                    delay = self.settings["word_delay"]
                else:
                    # Normal typing with variability
                    delay = self.settings["base_delay"] + random.normalvariate(
                        0, self.settings["delay_variability"])
            else:
                # Simple variability
                delay = self.settings["base_delay"] + random.uniform(
                    -self.settings["delay_variability"], 
                    self.settings["delay_variability"])
                
            delay = max(0.01, delay)  # Ensure delay is at least 10ms
            time.sleep(delay)
    
    def type_by_word(self):
        """Type text word by word"""
        words = self.current_text.split()
        
        for i, word in enumerate(words):
            if not self.typing_active:
                break
                
            # Check if paused
            while self.paused and self.typing_active:
                time.sleep(0.1)
                
            if not self.typing_active:
                break
                
            # Type the word
            pyautogui.write(word)
            
            # Add space after word (except for the last word)
            if i < len(words) - 1:
                pyautogui.write(' ')
                
            # Update progress (count word + space)
            self.char_count += len(word) + (1 if i < len(words) - 1 else 0)
            self.root.after(0, lambda c=self.char_count, t=self.total_chars: 
                          self.update_progress(c, t))
                
            # Delay between words
            if i < len(words) - 1:
                # Natural variation in typing speed between words
                if self.settings["natural_typing"]:
                    # Check for punctuation at the end of the word
                    if word[-1] in ['.', '!', '?']:
                        # Longer pause after sentences
                        delay = self.settings["word_delay"] * 2
                    elif word[-1] in [',', ';', ':']:
                        # Medium pause after clauses
                        delay = self.settings["word_delay"] * 1.5
                    else:
                        # Normal word delay with variability
                        delay = self.settings["word_delay"] + random.normalvariate(
                            0, self.settings["delay_variability"])
                else:
                    # Simple variability
                    delay = self.settings["word_delay"] + random.uniform(
                        -self.settings["delay_variability"],
                        self.settings["delay_variability"])
                
                delay = max(0.01, delay)  # Ensure delay is at least 10ms
                time.sleep(delay)
    
    def typing_completed(self):
        """Called when typing is completed"""
        self.typing_active = False
        self.set_status("ready")
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.update_progress(self.total_chars, self.total_chars)
        
        # Show completion message
        messagebox.showinfo("Completed", "Typing completed successfully")
    
    def toggle_pause(self):
        """Toggle pause state"""
        if not self.typing_active:
            return
            
        self.paused = not self.paused
        if self.paused:
            self.set_status("paused")
            self.pause_button.config(text="Resume (F10)")
        else:
            self.set_status("typing")
            self.pause_button.config(text="Pause (F10)")
    
    def stop_typing(self):
        """Stop the typing process"""
        if not self.typing_active:
            return
            
        self.typing_active = False
        if self.typing_thread and self.typing_thread.is_alive():
            self.typing_thread.join(0.5)
            
        self.set_status("stopped")
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
    
    def emergency_stop(self):
        """Emergency stop that works regardless of focus"""
        if not self.typing_active:
            return
            
        # Check if confirmation is required
        if self.settings["confirm_emergency_stop"] and not self.minimized_to_tray:
            if not messagebox.askyesno("Emergency Stop", 
                                     "Emergency stop activated. Stop typing?",
                                     parent=self.root):
                return
                
        self.typing_active = False
        self.root.after(0, lambda: self.set_status("stopped"))
        self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.pause_button.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
        
        # Show window if minimized to tray
        if self.minimized_to_tray:
            self.show_window()
            messagebox.showinfo("Emergency Stop", "Typing has been stopped", parent=self.root)
    
    def show_hotkey_help(self):
        """Show help about fixing hotkey permissions"""
        if MACOS:
            message = (
                "Global hotkeys are not supported on macOS in this application.\n\n"
                "This is due to macOS security restrictions that require special permissions.\n\n"
                "Please use the buttons in the application interface instead of hotkeys.\n\n"
                "You can also use the function keys (F9, F10, F11) if your app has focus."
            )
        else:
            message = (
                "To enable global hotkeys:\n\n"
                "1. Ensure the keyboard module is properly installed\n"
                "2. Try running the application with administrator privileges\n"
                "3. Check if any other application is intercepting keyboard shortcuts"
            )
        
        messagebox.showinfo("Global Hotkey Help", message)

def main():
    # Check for macOS and display a message about limitations
    if MACOS:
        print("Running on macOS. Note that global hotkeys are disabled for compatibility.")
        print("Please use the buttons in the application interface instead.")
    
    # Check for required modules
    missing_modules = []
    
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError:
        missing_modules.append("tkinter")
    
    # Safely try to import pyautogui which is essential
    try:
        import pyautogui
    except ImportError:
        missing_modules.append("pyautogui")
    
    # Import keyboard only on non-macOS platforms
    if not MACOS:
        try:
            import keyboard
        except ImportError:
            missing_modules.append("keyboard")
    
    # Try to import PIL for image handling
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        missing_modules.append("pillow")
    
    # Try to import pystray for system tray support (optional)
    if not MACOS:  # Skip on macOS
        try:
            import pystray
        except ImportError:
            print("Pystray module not available, system tray functionality will be disabled")
    
    if missing_modules:
        print(f"Missing required modules: {', '.join(missing_modules)}")
        print("Please install them using pip:")
        print(f"pip install {' '.join(missing_modules)}")
        
        # Show error message if tkinter is available
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Missing Modules",
                f"The following required modules are missing:\n{', '.join(missing_modules)}\n\n"
                f"Please install them using pip:\npip install {' '.join(missing_modules)}"
            )
        except:
            pass
            
        return
    
    # Create and run the application
    root = tk.Tk()
    app = AdvancedTyperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()