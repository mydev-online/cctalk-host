# ccTalk Host - Bill Validator Interface

An interactive command-line interface for communicating with ccTalk-compatible bill validators via serial port. Features a retro 80's terminal-style UI with support for both CRC and checksum validation modes.

## Features

- **Interactive CLI** with 80's terminal box-style formatting
- **Dual checksum modes**: Support for both 2-byte CRC (XModem) and 1-byte checksum
- **Command-line options** for port and checksum mode selection
- **Background polling** of bill events with real-time updates
- **Header 159 parsing** with human-readable event descriptions
- **Color-coded output** for better readability
- **Direct command input** - type header codes directly without `cmd` keyword

## Requirements

- Python 3.6 or higher
- pyserial library
- A ccTalk-compatible bill validator connected via serial port

## Installation

### macOS / Linux

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install pyserial
   ```
4. Run the script:
   ```bash
   python3 cctalk-host.py
   ```
   Or make it executable and run directly:
   ```bash
   chmod +x cctalk-host.py
   ./cctalk-host.py
   ```

### Windows

1. Clone or download this repository
2. Create a virtual environment (recommended):
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```cmd
   pip install pyserial
   ```
4. Run the script:
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
# Interactive mode (prompts for port and checksum mode)
python cctalk-host.py

# Specify port only
python cctalk-host.py --port COM3                    # Windows
python cctalk-host.py --port /dev/ttyUSB0            # Linux/Mac
python cctalk-host.py --port 0                       # Use port index

# Specify both port and checksum mode
python cctalk-host.py --port COM3 --mode crc         # Windows with CRC
python cctalk-host.py --port /dev/ttyUSB0 --mode checksum  # Linux/Mac with checksum

# Short options
python cctalk-host.py -p COM3 -m crc
```

**Options:**
- `--port`, `-p`: Serial port (device path like `COM3` or `/dev/ttyUSB0`, or port index number)
- `--mode`, `-m`: Checksum mode - `crc` for 2-byte CRC (XModem) or `checksum` for 1-byte checksum

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

- `poll [period]` - Start polling command 159 every `period` milliseconds (default: 1000ms)
- `stop` - Stop polling

**Examples:**
```
> poll                 # Start polling with default 1000ms period
> poll 500             # Start polling with 500ms period
> stop                 # Stop polling
```

While polling is active, the prompt changes to `(polling) >` and bill events are automatically displayed when they change.

#### Testing

- `test` - Show available tests
- `test <name>` - Run a specific test

**Available tests:**
- `test add_crc` - Test CRC calculation
- `test remove_crc` - Test CRC removal
- `test add_checksum` - Test checksum calculation
- `test remove_checksum` - Test checksum removal

## Checksum Modes

### CRC Mode (2-byte XModem CRC)
- Uses XModem CRC-16 algorithm
- CRC LSB overwrites position 2 (source address field)
- CRC MSB is appended at the end
- More robust error detection

### Checksum Mode (1-byte checksum)
- Simple 8-bit checksum
- Checksum byte appended at the end
- Checksum value chosen such that total sum is 0 mod 256
- Simpler but less robust than CRC

## Header 159 Response Format

When sending command 159 (Read buffered bill events), the response is automatically parsed and displayed with human-readable descriptions:

- **Counter**: Event counter (first byte)
- **5 A/B pairs**: Each pair represents an event
  - Credit events: Bill validated and sent to cashbox
  - Pending Credit: Bill validated and held in escrow
  - Status events: Various status messages
  - Reject events: Invalid bills
  - Fatal Errors: Critical errors requiring attention
  - Fraud Attempts: Fraud detection events

## Example Session

```
$ python cctalk-host.py --port COM3 --mode crc

╔══════════════════════════════════════════════════════════════════════════════
║ ccTalk Host - Bill Validator Interface
╚══════════════════════════════════════════════════════════════════════════════

╔═ SERIAL PORTS ═══════════════════════════════════════════════════════════════
║ Scanning for available serial ports...
╠══════════════════════════════════════════════════════════════════════════════
║ [0] COM1
║ [1] COM2
║ [2] COM3
╚══════════════════════════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════════════════════════
║ Connected! Type 'help' for available commands.
╚══════════════════════════════════════════════════════════════════════════════

Using CRC (2-byte XModem) mode
> 159

→ Header 159 (0x9F) - Read buffered bill events
  Data: [empty]
← Response 0
  Data: [20 0 0 0 0 0 1 2 1 0 1] (0x14 0x00 0x00 0x00 0x00 0x00 0x01 0x02 0x01 0x00 0x01)

╔═ BILL EVENTS ════════════════════════════════════════════════════════════════
║ Counter:  20 (0x14)
╠══════════════════════════════════════════════════════════════════════════════
║ Pair 1: Status          Master inhibit active
║ Pair 2: Status          Master inhibit active
║ Pair 3: Status          Bill returned from escrow
║ Pair 4: Pending Credit Bill type 2 validated correctly and held in escrow
║ Pair 5: Status          Bill returned from escrow
╚══════════════════════════════════════════════════════════════════════════════

> poll
Polling started (period: 1000ms). Type 'stop' to stop.
(polling) > 
```

## Troubleshooting

### Port Not Found
- **Windows**: Check Device Manager for COM port numbers
- **Linux/Mac**: Check `/dev/tty*` or use `ls /dev/tty*` to list available ports
- Ensure the device is connected and drivers are installed

### Permission Denied (Linux/Mac)
- Add your user to the `dialout` group: `sudo usermod -a -G dialout $USER`
- Log out and log back in for changes to take effect
- Or run with `sudo` (not recommended)

### Colors Not Displaying
- The script automatically disables colors for non-terminal output
- On Windows, use Windows Terminal or PowerShell for best color support
- Colors are disabled when output is piped or redirected

### CRC/Checksum Errors
- Verify you're using the correct checksum mode for your device
- Some devices use CRC, others use checksum
- Check device documentation or try both modes

## Development

This project was developed on macOS. For Windows users:
- Serial port paths use `COM` prefix instead of `/dev/`
- Terminal colors work in Windows Terminal and PowerShell
- Path separators are handled automatically by Python's `os.path`

## License

[Add your license here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

