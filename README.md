# Simple Auto Typer

A reliable, safety-focused automatic typing tool built with PyQt6 and PyAutoGUI that helps automate repetitive typing tasks.

## Features

- **Text Automation**: Type text automatically at a controlled speed
- **Safety First**: Built-in emergency stop timer and ESC key shortcut
- **Natural Typing**: Option to simulate natural typing patterns with varied pauses
- **Customizable Speed**: Adjust typing speed with a simple slider
- **Repeat Functionality**: Automatically repeat the typing sequence
- **Progress Tracking**: Visual progress bar to track typing completion
- **Clean Interface**: Simple, high-contrast UI that's easy to use

## Safety Features

- **Automatic Emergency Stop**: Typing automatically stops after a configurable time period (default: 10 seconds)
- **ESC Key Emergency Stop**: Press ESC at any time to immediately stop typing
- **Countdown Timer**: Clear countdown before typing begins
- **Status Indicators**: Clear visual indicators of current status

## Requirements

- Python 3.6+
- PyQt6
- PyAutoGUI

## Installation

1. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install required dependencies:

```bash
pip install PyQt6 pyautogui
```

3. Run the application:

```bash
python simple_typer.py
```

## Usage Instructions

1. **Enter Text**: Type or paste the text you want to auto-type in the "Text to Type" box
2. **Configure Settings**:
   - **Speed**: Adjust typing speed using the slider
   - **Repeat**: Set how many times to repeat the typing sequence
   - **Natural Typing**: Toggle to simulate more natural typing patterns
   - **Auto-stop**: Set the emergency timeout (5-60 seconds)
3. **Start Typing**:
   - Click "Start Typing"
   - A countdown will begin, giving you 3 seconds to position your cursor where you want to type
   - The text will begin typing automatically after the countdown
4. **Stop Typing**:
   - Click "STOP" at any time to stop typing
   - Press ESC for emergency stop
   - Typing will automatically stop after the auto-stop time elapses

## Common Use Cases

- Filling forms with repetitive information
- Testing input fields with the same text multiple times
- Automating repetitive typing tasks
- Simulating keyboard input for demos or testing

## Troubleshooting

- **Text Not Typing**: Make sure you've positioned your cursor in the right location during the countdown
- **Cannot Stop Typing**: Press ESC or wait for the emergency timer to stop typing
- **Application Won't Start**: Ensure you have all required dependencies installed

## License

This project is licensed under the MIT License - see the LICENSE file for details. 