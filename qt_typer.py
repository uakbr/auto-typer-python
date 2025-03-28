#!/usr/bin/env python3
import sys
import os
import json
import time
import random
import threading
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QSlider, QSpinBox, QCheckBox, QRadioButton,
    QTabWidget, QGroupBox, QProgressBar, QFileDialog, QMessageBox,
    QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSettings
from PyQt6.QtGui import QFont, QColor, QIcon
import pyautogui

class QTyperApp(QMainWindow):
    """PyQt6 version of the Advanced Auto Typer"""
    
    # Signal to update progress safely from a thread
    update_progress_signal = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Auto Typer")
        self.setMinimumSize(700, 600)
        
        # Variables
        self.typing_active = False
        self.paused = False
        self.typing_thread = None
        self.config_file = os.path.join(self._get_app_dir(), "qt_typer_config.json")
        self.snippets_file = os.path.join(self._get_app_dir(), "qt_snippets.json")
        self.char_count = 0
        self.total_chars = 0
        
        # Default settings
        self.default_settings = {
            "base_delay": 0.1,  # Base delay between keystrokes in seconds
            "delay_variability": 0.05,  # Random variability to add to base delay
            "word_delay": 0.3,  # Extra delay between words
            "typing_mode": "character",  # 'character' or 'word'
            "repeat_count": 1,  # Number of times to repeat typing
            "countdown_seconds": 3,  # Seconds to countdown before typing
            "natural_typing": True,  # Simulate more natural typing patterns
        }
        
        # Load settings and snippets
        self.settings = self.load_settings()
        self.snippets = self.load_snippets()
        
        # Connect the progress signal
        self.update_progress_signal.connect(self.update_progress_slot)
        
        # Create UI
        self.init_ui()
    
    def _get_app_dir(self):
        """Get or create application directory for storing config files"""
        app_dir = os.path.join(os.path.expanduser("~"), ".qt_auto_typer")
        if not os.path.exists(app_dir):
            os.makedirs(app_dir)
        return app_dir
    
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
    
    def init_ui(self):
        """Initialize the user interface"""
        # Main widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        
        # Text input area
        text_group = QGroupBox("Text to Type")
        text_layout = QVBoxLayout(text_group)
        
        self.text_input = QTextEdit()
        self.text_input.setMinimumHeight(150)
        self.text_input.setPlaceholderText("Enter text to type automatically...")
        self.text_input.textChanged.connect(self.update_char_count)
        text_layout.addWidget(self.text_input)
        
        # Character count display
        char_layout = QHBoxLayout()
        self.char_count_label = QLabel("Characters: 0")
        self.word_count_label = QLabel("Words: 0")
        char_layout.addWidget(self.char_count_label)
        char_layout.addWidget(self.word_count_label)
        char_layout.addStretch()
        text_layout.addLayout(char_layout)
        
        main_layout.addWidget(text_group)
        
        # Controls group
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        # Speed and repeat settings
        settings_layout = QHBoxLayout()
        
        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(int(self.settings["base_delay"] * 100))
        self.speed_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.speed_slider.setTickInterval(10)
        self.speed_slider.valueChanged.connect(self.update_speed)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel(f"{self.settings['base_delay']:.2f}s")
        speed_layout.addWidget(self.speed_label)
        settings_layout.addLayout(speed_layout)
        
        # Repeat count
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("Repeat:"))
        
        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setMinimum(1)
        self.repeat_spinbox.setMaximum(100)
        self.repeat_spinbox.setValue(self.settings["repeat_count"])
        self.repeat_spinbox.valueChanged.connect(self.update_repeat)
        repeat_layout.addWidget(self.repeat_spinbox)
        settings_layout.addLayout(repeat_layout)
        
        # Natural typing checkbox
        self.natural_typing_checkbox = QCheckBox("Natural Typing")
        self.natural_typing_checkbox.setChecked(self.settings["natural_typing"])
        self.natural_typing_checkbox.stateChanged.connect(self.update_natural_typing)
        settings_layout.addWidget(self.natural_typing_checkbox)
        
        settings_layout.addStretch()
        controls_layout.addLayout(settings_layout)
        
        # Typing mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Typing Mode:"))
        
        self.char_mode_radio = QRadioButton("Character by Character")
        self.word_mode_radio = QRadioButton("Word by Word")
        
        if self.settings["typing_mode"] == "character":
            self.char_mode_radio.setChecked(True)
        else:
            self.word_mode_radio.setChecked(True)
            
        self.char_mode_radio.toggled.connect(self.update_typing_mode)
        
        mode_layout.addWidget(self.char_mode_radio)
        mode_layout.addWidget(self.word_mode_radio)
        mode_layout.addStretch()
        controls_layout.addLayout(mode_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        # Status indicator
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        status_layout.addWidget(self.status_label)
        button_layout.addLayout(status_layout)
        
        # Buttons
        self.start_button = QPushButton("Start Typing (F9)")
        self.start_button.clicked.connect(self.start_typing)
        button_layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("Pause (F10)")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        self.stop_button = QPushButton("Stop (F11)")
        self.stop_button.clicked.connect(self.stop_typing)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        controls_layout.addLayout(button_layout)
        
        main_layout.addWidget(controls_group)
        
        # Test area
        test_group = QGroupBox("Test Area (Practice typing here)")
        test_layout = QVBoxLayout(test_group)
        
        self.test_area = QTextEdit()
        self.test_area.setMinimumHeight(100)
        test_layout.addWidget(self.test_area)
        
        main_layout.addWidget(test_group)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("0%")
        self.progress_label.setMinimumWidth(40)
        progress_layout.addWidget(self.progress_label)
        
        main_layout.addLayout(progress_layout)
        
        # Create menu bar
        self.create_menu()
        
        # Set central widget
        self.setCentralWidget(central_widget)
        
        # Set keyboard shortcuts for buttons
        self.start_button.setShortcut("F9")
        self.pause_button.setShortcut("F10")
        self.stop_button.setShortcut("F11")
        
        # Show window
        self.show()
    
    def create_menu(self):
        """Create the application menu"""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("File")
        
        save_action = file_menu.addAction("Save Text")
        save_action.triggered.connect(self.save_text)
        
        load_action = file_menu.addAction("Load Text")
        load_action.triggered.connect(self.load_text)
        
        file_menu.addSeparator()
        
        save_snippet_action = file_menu.addAction("Save as Snippet")
        save_snippet_action.triggered.connect(self.save_as_snippet)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Snippets menu
        if self.snippets:
            snippets_menu = menu_bar.addMenu("Snippets")
            
            for name in sorted(self.snippets.keys()):
                snippet_action = snippets_menu.addAction(name)
                snippet_action.triggered.connect(lambda checked, n=name: self.use_snippet(n))
                
            snippets_menu.addSeparator()
            
            manage_action = snippets_menu.addAction("Manage Snippets")
            manage_action.triggered.connect(self.manage_snippets)
        
        # Help menu
        help_menu = menu_bar.addMenu("Help")
        
        instructions_action = help_menu.addAction("Instructions")
        instructions_action.triggered.connect(self.show_instructions)
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
    
    def update_speed(self):
        """Update typing speed from slider"""
        value = self.speed_slider.value() / 100.0
        self.settings["base_delay"] = value
        self.speed_label.setText(f"{value:.2f}s")
        self.save_settings()
    
    def update_repeat(self):
        """Update repeat count from spinbox"""
        value = self.repeat_spinbox.value()
        self.settings["repeat_count"] = value
        self.save_settings()
    
    def update_natural_typing(self):
        """Update natural typing setting"""
        value = self.natural_typing_checkbox.isChecked()
        self.settings["natural_typing"] = value
        self.save_settings()
    
    def update_typing_mode(self):
        """Update typing mode based on radio button selection"""
        if self.char_mode_radio.isChecked():
            self.settings["typing_mode"] = "character"
        else:
            self.settings["typing_mode"] = "word"
        self.save_settings()
    
    def update_char_count(self):
        """Update character and word count display"""
        text = self.text_input.toPlainText()
        chars = len(text)
        words = len(text.split()) if text else 0
        
        self.char_count_label.setText(f"Characters: {chars}")
        self.word_count_label.setText(f"Words: {words}")
    
    def update_progress_slot(self, current, total):
        """Update progress bar and percentage (slot for signal)"""
        if total > 0:
            progress = (current / total) * 100
            self.progress_bar.setValue(int(progress))
            self.progress_label.setText(f"{int(progress)}%")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("0%")
    
    def set_status(self, status):
        """Update status display"""
        status_text = status.capitalize()
        self.status_label.setText(status_text)
        
        if status.lower() == "ready":
            self.status_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        elif status.lower() == "typing":
            self.status_label.setStyleSheet("background-color: #d4edda; padding: 5px; border: 1px solid #c3e6cb;")
        elif status.lower() == "paused":
            self.status_label.setStyleSheet("background-color: #fff3cd; padding: 5px; border: 1px solid #ffeeba;")
        elif status.lower() == "stopped":
            self.status_label.setStyleSheet("background-color: #f8d7da; padding: 5px; border: 1px solid #f5c6cb;")
    
    def countdown(self, seconds):
        """Display countdown before typing starts"""
        if seconds <= 0:
            return
        
        # Create countdown dialog
        countdown_dialog = QMessageBox(self)
        countdown_dialog.setWindowTitle("Countdown")
        countdown_dialog.setStyleSheet("QLabel { font-size: 48pt; }")
        countdown_dialog.setStandardButtons(QMessageBox.StandardButton.NoButton)
        countdown_dialog.setModal(True)
        countdown_dialog.show()
        
        # Update countdown
        for i in range(seconds, 0, -1):
            countdown_dialog.setText(str(i))
            QApplication.processEvents()
            time.sleep(1)
        
        countdown_dialog.close()
    
    def start_typing(self):
        """Start the typing process"""
        if self.typing_active:
            return
        
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Info", "Please enter some text to type")
            return
        
        # Calculate total characters for progress tracking
        self.total_chars = len(text) * self.settings["repeat_count"]
        self.char_count = 0
        self.update_progress_signal.emit(0, self.total_chars)
        
        # Show countdown if enabled
        if self.settings["countdown_seconds"] > 0:
            self.countdown(self.settings["countdown_seconds"])
        
        # Start typing in a separate thread
        self.typing_active = True
        self.paused = False
        self.typing_thread = threading.Thread(target=self.typing_process, args=(text,))
        self.typing_thread.daemon = True
        self.typing_thread.start()
        
        # Update UI
        self.set_status("typing")
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
    
    def typing_process(self, text):
        """Simulate typing the text"""
        try:
            for repeat in range(self.settings["repeat_count"]):
                if not self.typing_active:
                    break
                
                if self.settings["typing_mode"] == "character":
                    # Type character by character
                    self.type_by_char(text)
                else:
                    # Type word by word
                    self.type_by_word(text)
                
                # Add extra delay between repeats
                if repeat < self.settings["repeat_count"] - 1 and self.typing_active:
                    time.sleep(self.settings["word_delay"] * 3)
            
            # Typing finished normally
            if self.typing_active:
                # Use QTimer to call typing_completed from the main thread
                QTimer.singleShot(0, self.typing_completed)
        except Exception as e:
            # Use QTimer to show error from the main thread
            QTimer.singleShot(0, lambda: self.show_error(f"Typing error: {str(e)}"))
            QTimer.singleShot(0, self.stop_typing)
    
    def type_by_char(self, text):
        """Type text character by character"""
        for char in text:
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
            self.update_progress_signal.emit(self.char_count, self.total_chars)
            
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
    
    def type_by_word(self, text):
        """Type text word by word"""
        words = text.split()
        
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
            self.update_progress_signal.emit(self.char_count, self.total_chars)
                
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
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.update_progress_signal.emit(self.total_chars, self.total_chars)
        
        # Show completion message
        QMessageBox.information(self, "Completed", "Typing completed successfully")
    
    def toggle_pause(self):
        """Toggle pause state"""
        if not self.typing_active:
            return
            
        self.paused = not self.paused
        if self.paused:
            self.set_status("paused")
            self.pause_button.setText("Resume (F10)")
        else:
            self.set_status("typing")
            self.pause_button.setText("Pause (F10)")
    
    def stop_typing(self):
        """Stop the typing process"""
        if not self.typing_active:
            return
            
        self.typing_active = False
        if self.typing_thread and self.typing_thread.is_alive():
            self.typing_thread.join(0.5)
            
        self.set_status("stopped")
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
    
    def save_text(self):
        """Save current text to a file"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Info", "There is no text to save")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Text", "", "Text files (*.txt);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, "Success", "Text saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    def load_text(self):
        """Load text from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Text", "", "Text files (*.txt);;All files (*.*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            self.text_input.setPlainText(text)
            QMessageBox.information(self, "Success", "Text loaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    def save_as_snippet(self):
        """Save current text as a snippet"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Info", "Please enter some text to save as a snippet")
            return
        
        # Get snippet name
        name, ok = QInputDialog.getText(
            self, "Save Snippet", "Enter a name for this snippet:"
        )
        
        if not ok or not name:
            return
        
        self.snippets[name] = text
        self.save_snippets()
        
        # Recreate menu to include new snippet
        self.create_menu()
        
        QMessageBox.information(self, "Snippet Saved", f"Snippet '{name}' saved successfully")
    
    def use_snippet(self, name):
        """Use the selected snippet"""
        if name not in self.snippets:
            return
            
        # Get confirmation
        result = QMessageBox.question(
            self, "Use Snippet", 
            f"Replace current text with snippet '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if result == QMessageBox.StandardButton.Yes:
            self.text_input.setPlainText(self.snippets[name])
            self.update_char_count()
    
    def manage_snippets(self):
        """Manage saved snippets"""
        if not self.snippets:
            QMessageBox.information(self, "No Snippets", "You don't have any saved snippets yet.")
            return
            
        # Create dialog to manage snippets
        # In a real implementation, we would create a custom dialog
        # For simplicity, just show the first snippet
        snippet_names = sorted(self.snippets.keys())
        name, ok = QInputDialog.getItem(
            self, "Select Snippet", "Choose a snippet to use:", 
            snippet_names, 0, False
        )
        
        if ok and name:
            self.use_snippet(name)
    
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
            "- Start Typing: 'Start' button or F9\n"
            "- Pause/Resume: 'Pause' button or F10\n"
            "- Stop: 'Stop' button or F11\n\n"
            "Features:\n"
            "- Save and load text\n"
            "- Save and manage frequently used snippets\n"
            "- Configure typing speed and variability\n"
            "- Type character-by-character or word-by-word\n"
            "- Natural typing patterns simulation\n"
            "- Progress tracking"
        )
        
        QMessageBox.information(self, "Instructions", instructions)
    
    def show_about(self):
        """Show the about dialog"""
        about_text = (
            "Advanced Auto Typer (Qt Version)\n\n"
            "Version 1.0\n\n"
            "A powerful tool for automating keyboard input with advanced features.\n\n"
            "Created using Python, PyQt6, and PyAutoGUI."
        )
        
        QMessageBox.about(self, "About", about_text)

def main():
    # Create the application
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show the main window
    window = QTyperApp()
    
    # Start the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 