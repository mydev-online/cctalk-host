# ccTalk Host - Bill & Coin Validator Interface

An interactive command-line interface for communicating with ccTalk-compatible bill validators and coin acceptors via serial port. Support for both CRC and checksum validation modes.

A polling option will periodically poll the device and display interpreted event data (bill events or coin credits/errors) only when new events occur. During polling the user will have a normal prompt to 'inject' commands. Raw output and interpretation of the response is displayed. 

![ccTalk Host Interface](screenshot.jpeg)

### Features

- **Universal Support**: Works with Bill Validators (address 40) and Coin Acceptors (address 2).
- **Keyboard History**: Use Up/Down arrows to navigate previous commands.
- **Persistent History**: Commands are saved to `~/.cctalk_host_history`.
- **Colored Output**: Rich ANSI color support for improved readability.
- **Protocol Flexibility**: Supports both 2-byte CRC (XModem) and 1-byte Checksum modes.
- **Improved Serial Handling**: Correct handling of echoed packets and binary data.

## Requirements

- Python 3.6 or higher
- `pyserial` library
- `readline` support (standard on macOS/Linux; Windows users may need `pyreadline3`)
- A ccTalk-compatible device connected via serial port

## Installation

### macOS / Linux

1. Create a virtual environment (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install pyserial
   ```
3. Run the script:
   ```bash
   python3 cctalk-host.py
   ```
   Or make it executable and run directly:
   ```bash
   chmod +x cctalk-host.py
   ./cctalk-host.py
   ```

### Windows

1. Create a virtual environment (recommended):
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. Install dependencies:
   ```cmd
   pip install pyserial
   ```
3. Run the script:
   ```cmd
   python cctalk-host.py
   ```

**Windows-specific notes:**
- Serial ports are typically named `COM1`, `COM2`, etc. (e.g., `COM3` instead of `/dev/ttyUSB0`)
- Use Command Prompt or PowerShell (Windows Terminal recommended for better color support)
- If colors don't display correctly, the script will automatically disable them for non-terminal output

## Usage

### Command-Line Options

```bash
# Interactive mode (prompts for type, port, mode, etc.)
python cctalk-host.py

# Full command line example
python cctalk-host.py --port /dev/ttyUSB0 --type bill --mode crc --address 40

# Options:
#  -p, --port      Serial port device path or index number
#  -t, --type      Device type: 'bill' or 'coin'
#  -m, --mode      Checksum mode: 'crc' or 'checksum'
#  -a, --address   Custom device address (default: 40 for bill, 2 for coin)
#  --color         Force colored output
#  --no-color      Disable colored output
```

### Interactive Commands

Once connected, you can use the following commands:

#### Basic Commands

- `help` - Show available commands
- `list` - List all header codes and their function names
- `quit` / `exit` - Exit the program

#### Sending Commands

- `<header> [data]` - Send command directly (e.g., `159` or `154 1`)
- `cmd <header> [data]` - Alternative syntax (e.g., `cmd 231 255 255`)

**Examples:**
```
> 4                    # Request comms revision
> 159                  # Read buffered bill events
> 154 1                # Route bill with data
> cmd 231 255 255      # Modify inhibit status
```

#### Polling

- `poll [period]` - Start polling events every `period` milliseconds (default: 1000ms).
  - Bill mode: Polls header **159** (Read buffered bill events)
  - Coin mode: Polls header **229** (Read buffered credit or error codes)
- `stop` - Stop polling

**Examples:**
```
> poll                 # Start polling with default 1000ms period
> poll 500             # Start polling with 500ms period
> stop                 # Stop polling
```

While polling is active, the prompt changes to `(polling) >` and bill events are automatically displayed when they change.

## Note
This script is designed to be compatible with a wide range of ccTalk devices. It has been specifically optimized for robustness (timing, echo handling) and user experience (history, colors).

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

