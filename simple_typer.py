#!/usr/bin/env python3
import sys
import time
import random
import threading
import pyautogui
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QSlider, QSpinBox, QCheckBox,
    QProgressBar, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

# Dictionary of special characters that need special handling
# Some characters need to be pressed with shift key
SPECIAL_CHARS = {
    '#': ('shift', '3'),
    '!': ('shift', '1'),
    '@': ('shift', '2'),
    '$': ('shift', '4'),
    '%': ('shift', '5'),
    '^': ('shift', '6'),
    '&': ('shift', '7'),
    '*': ('shift', '8'),
    '(': ('shift', '9'),
    ')': ('shift', '0'),
    '_': ('shift', '-'),
    '+': ('shift', '='),
    '{': ('shift', '['),
    '}': ('shift', ']'),
    '|': ('shift', '\\'),
    ':': ('shift', ';'),
    '"': ('shift', "'"),
    '<': ('shift', ','),
    '>': ('shift', '.'),
    '?': ('shift', '/'),
    '~': ('shift', '`')
}


class SimpleTyper(QMainWindow):
    """Simplified Auto Typer with emergency stop feature"""

    # Signal for progress updates
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Auto Typer")
        self.setMinimumSize(600, 500)

        # Variables
        self.typing_active = False
        self.paused = False
        self.typing_thread = None
        self.emergency_timer = None
        self.emergency_time = 10  # Auto-stop after 10 seconds by default

        # Basic settings
        self.delay = 0.1
        self.natural_typing = True
        self.repeat_count = 1

        # Create UI
        self.init_ui()

        # Safety fallback - never let typing run for more than 30 seconds
        self.max_timer = QTimer(self)
        self.max_timer.timeout.connect(self.emergency_stop)
        self.max_timer.setSingleShot(True)

    def init_ui(self):
        """Create the user interface"""
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # Text input section
        text_group = QGroupBox("Text to Type")
        text_layout = QVBoxLayout(text_group)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(
            "Enter text to type automatically..."
        )
        text_layout.addWidget(self.text_input)

        # Character count
        self.char_count_label = QLabel("Characters: 0")
        text_layout.addWidget(self.char_count_label)

        main_layout.addWidget(text_group)

        # Controls section
        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)

        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(int(self.delay * 100))
        self.speed_slider.valueChanged.connect(self.update_speed)
        speed_layout.addWidget(self.speed_slider)

        self.speed_label = QLabel(f"{self.delay:.2f}s")
        speed_layout.addWidget(self.speed_label)

        controls_layout.addLayout(speed_layout)

        # Options layout
        options_layout = QHBoxLayout()

        # Repeat count
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel("Repeat:"))

        self.repeat_spinbox = QSpinBox()
        self.repeat_spinbox.setMinimum(1)
        self.repeat_spinbox.setMaximum(10)
        self.repeat_spinbox.setValue(self.repeat_count)
        self.repeat_spinbox.valueChanged.connect(self.update_repeat)
        repeat_layout.addWidget(self.repeat_spinbox)

        options_layout.addLayout(repeat_layout)

        # Natural typing checkbox
        self.natural_typing_checkbox = QCheckBox("Natural Typing")
        self.natural_typing_checkbox.setChecked(self.natural_typing)
        self.natural_typing_checkbox.stateChanged.connect(
            self.update_natural_typing
        )
        options_layout.addWidget(self.natural_typing_checkbox)

        # Emergency stop timer
        emergency_layout = QHBoxLayout()
        emergency_layout.addWidget(QLabel("Auto-stop after (seconds):"))

        self.emergency_spinbox = QSpinBox()
        self.emergency_spinbox.setMinimum(5)
        self.emergency_spinbox.setMaximum(60)
        self.emergency_spinbox.setValue(self.emergency_time)
        self.emergency_spinbox.valueChanged.connect(self.update_emergency_time)
        emergency_layout.addWidget(self.emergency_spinbox)

        options_layout.addLayout(emergency_layout)
        options_layout.addStretch()

        controls_layout.addLayout(options_layout)

        # Button layout
        button_layout = QHBoxLayout()

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(
            "background-color: #e0e0e0; padding: 5px; border-radius: 3px;"
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.status_label)

        # Start button
        self.start_button = QPushButton("Start Typing")
        self.start_button.clicked.connect(self.start_typing)
        self.start_button.setStyleSheet(
            "background-color: #4CAF50; color: white;"
        )
        button_layout.addWidget(self.start_button)

        # Stop button
        self.stop_button = QPushButton("STOP (ESC)")
        self.stop_button.clicked.connect(self.stop_typing)
        self.stop_button.setStyleSheet(
            "background-color: #f44336; color: white;"
        )
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        controls_layout.addLayout(button_layout)

        main_layout.addWidget(controls_group)

        # Test area
        test_group = QGroupBox("Test Area")
        test_layout = QVBoxLayout(test_group)

        self.test_area = QTextEdit()
        self.test_area.setPlaceholderText("Test your typing here...")
        test_layout.addWidget(self.test_area)

        main_layout.addWidget(test_group)

        # Progress bar
        self.progress_label = QLabel("Progress: 0%")
        main_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Connect text change to update character count
        self.text_input.textChanged.connect(self.update_char_count)

        # Connect progress signal
        self.progress_signal.connect(self.update_progress)

        # Set keyboard shortcut for emergency stop
        self.shortcut = None
        try:
            # Try to set keyboard shortcut for ESC key
            from PyQt6.QtGui import QShortcut, QKeySequence
            self.shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
            self.shortcut.activated.connect(self.emergency_stop)
        except Exception:
            print("Could not set keyboard shortcut for emergency stop")

    def update_char_count(self):
        """Update character count display"""
        text = self.text_input.toPlainText()
        self.char_count_label.setText(f"Characters: {len(text)}")

    def update_speed(self):
        """Update typing speed from slider"""
        self.delay = self.speed_slider.value() / 100.0
        self.speed_label.setText(f"{self.delay:.2f}s")

    def update_repeat(self):
        """Update repeat count"""
        self.repeat_count = self.repeat_spinbox.value()

    def update_natural_typing(self):
        """Update natural typing setting"""
        self.natural_typing = self.natural_typing_checkbox.isChecked()

    def update_emergency_time(self):
        """Update emergency stop timer value"""
        self.emergency_time = self.emergency_spinbox.value()

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"Progress: {value}%")

    def start_typing(self):
        """Start the typing process"""
        if self.typing_active:
            return

        # Get the text to type
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.information(
                self,
                "No Text",
                "Please enter some text to type"
            )
            return

        # Show countdown message
        msg_pt1 = "Click OK, then immediately click where you want to type.\n"
        msg_pt2 = "You have 3 seconds to position your cursor."
        ok_button = QMessageBox.StandardButton.Ok
        cancel_button = QMessageBox.StandardButton.Cancel
        buttons = ok_button | cancel_button
        result = QMessageBox.question(
            self, "Ready to Type",
            msg_pt1 + msg_pt2,
            buttons
        )

        if result != QMessageBox.StandardButton.Ok:
            return

        # Start emergency timer
        self.max_timer.start(self.emergency_time * 1000)

        # Start typing thread
        self.typing_active = True
        self.typing_thread = threading.Thread(
            target=self.typing_process,
            args=(text,)
        )
        self.typing_thread.daemon = True

        # Update UI
        self.status_label.setText("Typing")
        self.status_label.setStyleSheet(
            "background-color: #fff3cd; padding: 5px; border-radius: 3px;"
        )
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Give time to position cursor
        for i in range(3, 0, -1):
            self.status_label.setText(f"Starting in {i}...")
            QApplication.processEvents()
            time.sleep(1)

        self.status_label.setText("Typing")
        self.typing_thread.start()

    def typing_process(self, text):
        """The actual typing process in a separate thread"""
        try:
            # Calculate total characters to type
            total_chars = len(text) * self.repeat_count
            typed_chars = 0

            # Type the text the specified number of times
            for repeat in range(self.repeat_count):
                if not self.typing_active:
                    break

                # Type each character
                for char in text:
                    if not self.typing_active:
                        break

                    # Handle special characters differently
                    if char in SPECIAL_CHARS:
                        keys = SPECIAL_CHARS[char]
                        if len(keys) == 2:
                            # For characters that need shift key
                            pyautogui.hotkey(keys[0], keys[1])
                        else:
                            # For other special characters
                            pyautogui.press(keys[0])
                    else:
                        # Type normal character
                        pyautogui.write(char)

                    # Update progress
                    typed_chars += 1
                    progress = int((typed_chars / total_chars) * 100)
                    self.progress_signal.emit(progress)

                    # Add delay with natural variability if enabled
                    if self.natural_typing:
                        if char in ['.', ',', '!', '?', ';', ':']:
                            # Longer pause after punctuation
                            time.sleep(self.delay * 2)
                        elif char in [' ', '\n', '\t']:
                            # Pause after spaces or line breaks
                            time.sleep(self.delay * 1.5)
                        else:
                            # Normal typing with variability
                            variation = random.uniform(
                                -self.delay*0.3, self.delay*0.3
                            )
                            time.sleep(self.delay + variation)
                    else:
                        # Fixed delay
                        time.sleep(self.delay)

            # Typing completed
            if self.typing_active:
                QTimer.singleShot(0, self.typing_completed)

        except Exception as exception:
            error_msg = f"Error during typing: {str(exception)}"
            print(error_msg)
            QTimer.singleShot(
                0, lambda: self.show_error(error_msg)
            )
            QTimer.singleShot(0, self.stop_typing)

    def typing_completed(self):
        """Called when typing is completed successfully"""
        self.typing_active = False
        self.max_timer.stop()
        self.status_label.setText("Completed")
        self.status_label.setStyleSheet(
            "background-color: #d4edda; padding: 5px; border-radius: 3px;"
        )
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        QMessageBox.information(
            self, "Completed", "Typing completed successfully"
        )

    def stop_typing(self):
        """Stop the typing process"""
        if not self.typing_active:
            return

        self.typing_active = False
        self.max_timer.stop()

        self.status_label.setText("Stopped")
        self.status_label.setStyleSheet(
            "background-color: #f8d7da; padding: 5px; border-radius: 3px;"
        )
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def emergency_stop(self):
        """Emergency stop when maximum time is reached or Escape is pressed"""
        if self.typing_active:
            self.typing_active = False
            self.max_timer.stop()

            self.status_label.setText("EMERGENCY STOP")
            self.status_label.setStyleSheet(
                "background-color: #dc3545; color: white; "
                "padding: 5px; border-radius: 3px;"
            )
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

            msg = "Typing has been stopped by emergency timeout or ESC key"
            QMessageBox.warning(
                self, "Emergency Stop",
                msg
            )

    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)

    def closeEvent(self, event):
        """Handle window close event"""
        if self.typing_active:
            self.typing_active = False
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    window = SimpleTyper()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
