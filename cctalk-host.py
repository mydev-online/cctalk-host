#!/usr/bin/env python3
"""ccTalk Host - Interactive command-line interface for Bill Validator communication"""

import sys
import os
import glob
import threading

# Add venv to path if it exists
script_dir = os.path.dirname(os.path.abspath(__file__))
venv_lib = os.path.join(script_dir, '.venv', 'lib')
if os.path.exists(venv_lib):
    # Find the python version directory (e.g., python3.13)
    python_dirs = glob.glob(os.path.join(venv_lib, 'python*'))
    if python_dirs:
        venv_site_packages = os.path.join(python_dirs[0], 'site-packages')
        if os.path.exists(venv_site_packages):
            sys.path.insert(0, venv_site_packages)

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial is not installed.")
    print("Please run: .venv/bin/python -m pip install pyserial")
    print("Or activate the virtual environment and run the script:")
    print("  source .venv/bin/activate")
    print("  python cctalk-host.py")
    print("Or run directly with venv python:")
    print("  .venv/bin/python cctalk-host.py")
    sys.exit(1)


class BillValidator:
    """Bill Validator class for ccTalk protocol communication"""
    
    # CRC lookup table for XModem CRC calculation
    CRC_TABLE = [0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7, 
        0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF, 
        0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6, 
        0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE, 
        0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485, 
        0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D, 
        0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4, 
        0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC, 
        0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823, 
        0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B, 
        0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12, 
        0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A, 
        0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41, 
        0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49, 
        0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70, 
        0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78, 
        0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F, 
        0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067, 
        0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E, 
        0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256, 
        0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D, 
        0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405, 
        0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C, 
        0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634, 
        0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB, 
        0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3, 
        0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A, 
        0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92, 
        0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9, 
        0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1, 
        0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8, 
        0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0]
    
    # Header codes and their function names (from Alberici BillyOne documentation)
    HEADER_CODES = {
        1: "Reset Device",
        4: "Request comms revision",
        152: "Request inhibit status",
        154: "Route bill",
        156: "Request country scaling factor",
        159: "Read buffered bill events",
        192: "Request build code",
        194: "Request database version",
        197: "Calculate ROM checksum",
        213: "Request option flags",
        225: "Request accept counter",
        226: "Request insertion counter",
        227: "Request master inhibit status",
        228: "Modify master inhibit status",
        230: "Request inhibit status",
        231: "Modify inhibit status",
        232: "Perform self-check",
        241: "Request software revision",
        242: "Request serial number",
        244: "Request product code",
        245: "Request equipment category id",
        246: "Request manufacturer id",
        249: "Request polling priority",
        254: "Simple poll"
    }
    
    def __init__(self, baudrate=9600, timeout=0.02):
        """Initialize BillValidator instance"""
        self.ser = None
        self.baudrate = baudrate
        self.timeout = timeout
        self.port = None
    
    def _crc_calculate_xmodem(self, message):
        """Calculate XModem CRC for a message"""
        crc = 0x0000
        for byte in message:
            crc = ((crc << 8) ^ self.CRC_TABLE[(crc >> 8) ^ byte]) & 0xFFFF
        crc = '%04x' % crc
        msb = int(crc[:-2], 16)
        lsb = int(crc[-2:], 16)
        return msb, lsb
    
    def _add_crc(self, l):
        """Add CRC to message (LSB at position 2, MSB at end)"""
        msb, lsb = self._crc_calculate_xmodem(l)
        l.insert(2, lsb)
        l.append(msb)
        return l
    
    def _remove_crc(self, data):
        """Remove CRC from response and verify it
        
        CRC structure in ccTalk:
        - CRC LSB overwrites position 2 (source address field)
        - CRC MSB is at the end of the message
        - CRC is calculated on: [dest, len, header, data...] (after removing both CRC bytes)
        
        Example: [1, 2, 116, 0, 31, 0, 84]
        - Position 2 (116) = CRC LSB
        - Position 6 (84) = CRC MSB
        - CRC calculated on: [1, 2, 0, 31, 0]
        
        Returns:
            tuple: (data_without_crc, crc_valid) where crc_valid is True if CRC matches
        """
        # Convert bytes to list of integers if needed
        if isinstance(data, bytes):
            l = list(data)
        else:
            l = list(data)
        
        if len(l) < 5:
            return (l, False)  # Too short to have CRC (need at least dest + len + crc_lsb + header + crc_msb)
        
        # Extract CRC bytes: MSB from end, LSB from position 2
        msb = l.pop(-1)  # Remove CRC MSB from end
        lsb = l.pop(2)   # Remove CRC LSB from position 2 (overwrites source address)
        
        # Verify CRC: calculate on remaining bytes [dest, len, header, data...]
        calculated_crc = self._crc_calculate_xmodem(l)
        crc_valid = (calculated_crc == (msb, lsb))
        
        if not crc_valid:
            print(f"CRC error for {data}: calculated {calculated_crc}, got ({msb}, {lsb})")
            print(f"  Raw input (hex): {' '.join([f'{x:02X}' for x in data])}")
            print(f"  Data being CRC-checked: {l}")
            print(f"  Data being CRC-checked (hex): {' '.join([f'{x:02X}' for x in l])}")
            print(f"  Calculated CRC: MSB={calculated_crc[0]} (0x{calculated_crc[0]:02X}), LSB={calculated_crc[1]} (0x{calculated_crc[1]:02X})")
            print(f"  Received CRC: MSB={msb} (0x{msb:02X}), LSB={lsb} (0x{lsb:02X})")
        
        # Return message without CRC bytes and verification status: [dest, len, header, data...]
        return (l, crc_valid)
    
    def _ints_to_ascii(self, int_list):
        """Convert list of integers to ASCII string if all are printable ASCII"""
        if not int_list:
            return None
        if all(i == 0 or (32 <= i <= 126) for i in int_list):
            return ''.join(chr(i) for i in int_list)
        return None
    
    def h(self, bytes_list):
        """Return hex string representation"""
        l = list(bytes_list)
        return " ".join([f"{x:02X}" for x in l])
    
    def d(self, bytes_list):
        """Return decimal string representation"""
        if type(bytes_list) == int:
            return bytes_list
        l = list(bytes_list)
        return " ".join([f"{x}" for x in l])
    
    def _l(self, req, resp):
        """Print request and (separated) response"""
        print(f'{self.d(req)} | {self.d(resp[len(req):])}')
    
    @staticmethod
    def list_ports():
        """List all available serial ports"""
        print("Scanning for available serial ports...")
        print("-" * 50)
        
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            print("No serial ports found.")
            return []
        
        port_list = []
        for idx, port_info in enumerate(ports):
            print(f"  [{idx}] {port_info.device}")
            if port_info.description:
                print(f"      {port_info.description}")
            port_list.append(port_info.device)
        
        print("-" * 50)
        return port_list
    
    @staticmethod
    def list_headers():
        """List all header codes and their function names"""
        print("Header Codes:")
        print("-" * 50)
        for code in sorted(BillValidator.HEADER_CODES.keys()):
            name = BillValidator.HEADER_CODES[code]
            print(f"  {code:3d} (0x{code:02X}): {name}")
        print("-" * 50)
        return BillValidator.HEADER_CODES
    
    def connect(self, port):
        """Connect to a given serial port by name"""
        if port is None:
            print("Error: port name is required. Use list_ports() to see available ports.")
            return False
        
        try:
            self.ser = serial.Serial(port=port, baudrate=self.baudrate, timeout=self.timeout)
            self.port = port
            print(f"Connected to {port}")
            return True
        except Exception as e:
            print(f"Error connecting to {port}: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Disconnected from {self.port}")
            self.port = None
    
    def cmd(self, header, data=[], to_print=True, raw=False):
        """Create and send message, print request and response"""
        if self.ser is None or not self.ser.is_open:
            print("Not connected. Call connect() first.")
            return None
        
        if not isinstance(data, list):
            data = [data]
        
        length = len(data)
        msg = [40, length, header] + data
        req = self._add_crc(msg.copy())
        
        self.ser.readline()  # Clear any pending data
        self.ser.write(bytes(req))
        resp = self.ser.readline()
        
        resp_header = None
        resp_data = []
        
        # Check if response is long enough: msg + 5 bytes minimum (dest + len + crc_lsb + header + crc_msb)
        if len(resp) >= len(msg) + 5:
            # Response may include echoed request, skip it
            resp_part = resp[len(req):]
            
            # Response structure: [dest, len, crc_lsb, header, crc_msb, data...]
            # After removing CRC: [dest, len, header, data...]
            if len(resp_part) >= 5:
                try:
                    resp_trunc, crc_valid = self._remove_crc(resp_part)
                    if len(resp_trunc) >= 3:
                        resp_header = resp_trunc[2]  # Header is at position 2 after CRC removal
                        resp_data = resp_trunc[3:] if len(resp_trunc) > 3 else []
                except (IndexError, ValueError) as e:
                    # If CRC removal fails, try to parse anyway
                    resp_list = list(resp_part)
                    if len(resp_list) >= 4:
                        resp_header = resp_list[3]
                        resp_data = resp_list[5:] if len(resp_list) > 5 else []
            
            if to_print:
                print(f'Req: {header} {data}, Resp: {resp_header} [{resp_data}]', end="")
                
                # Special handling for header 159 responses (check request header, not response header)
                if header == 159:
                    counter, events = parse_header159_response(resp_data)
                    print()
                    print(f"Counter: {counter}")
                    for event in events:
                        print(f"  {event}")
                else:
                    print("  ", end="")
                    str_ = self._ints_to_ascii(resp_data)
                    if str_:
                        print(str_, end="  ")
        
        if raw:
            print("   Raw:")
            self._l(req, resp)
        
        if to_print:
            print()
        
        if len(resp) <= len(msg):
            return None
        else:
            try:
                return {'header': resp_header, 'data': resp_data}
            except:
                return {'header': -1, 'data': []}
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def parse_header159_response(resp_data):
    """Parse header 159 response and return human-readable descriptions"""
    if not resp_data or len(resp_data) < 1:
        return 0, []
    
    counter = resp_data[0]
    events = []
    
    # Parse 5 A/B pairs (10 bytes after counter)
    for i in range(5):
        idx = 1 + (i * 2)
        if idx + 1 < len(resp_data):
            result_a = resp_data[idx]
            result_b = resp_data[idx + 1]
        else:
            # Not enough data, use default (0, 0)
            result_a = 0
            result_b = 0
        
        # Determine event description
        if result_a == 0:
            # Status/Error/Fraud events
            event_map = {
                0: "Master inhibit active",
                1: "Bill returned from escrow",
                2: "Invalid bill (due to validation fail)",
                3: "Invalid bill (due to transport problem)",
                4: "Inhibited bill (on serial)",
                5: "Inhibited bill (on DIP switches)",
                6: "Bill jammed in transport (unsafe mode)",
                7: "Bill jammed in stacker",
                8: "Bill pulled backwards",
                9: "Bill tamper",
                10: "Stacker OK",
                11: "Stacker removed",
                12: "Stacker inserted",
                13: "Stacker faulty",
                14: "Stacker full",
                15: "Stacker jammed",
                16: "Bill jammed in transport (safe mode)",
                17: "Opto fraud detected",
                18: "String fraud detected",
                19: "Anti-string mechanism faulty",
                20: "Barcode detected",
                21: "Unknown bill type stacked"
            }
            event_type = event_map.get(result_b, f"Unknown event (A={result_a}, B={result_b})")
            event_category = "Status" if result_b in [0, 1, 4, 5, 10, 11, 12, 14, 20, 21] else \
                            "Reject" if result_b in [2, 3] else \
                            "Fatal Error" if result_b in [6, 7, 13, 15, 16, 19] else \
                            "Fraud Attempt"
            events.append(f"{event_category}: {event_type}")
        elif result_a >= 1 and result_a <= 255:
            if result_b == 0:
                events.append(f"Credit: Bill type {result_a} validated correctly and sent to cashbox/stacker")
            elif result_b == 1:
                events.append(f"Pending Credit: Bill type {result_a} validated correctly and held in escrow")
            else:
                events.append(f"Unknown: A={result_a}, B={result_b}")
        else:
            events.append(f"Unknown: A={result_a}, B={result_b}")
    
    return counter, events


def print_help():
    """Print help message"""
    print("Available commands:")
    print("  help              - Show this help message")
    print("  list              - List all header codes and their function names")
    print("  <header> [data]   - Send command (cmd keyword optional)")
    print("                        Header and data values are decimal, space-separated")
    print("                        Example: 254")
    print("                        Example: 154 1")
    print("                        Example: cmd 231 255 255")
    print("  test              - Show available tests")
    print("  test <name>       - Run a test")
    print("  poll [period]     - Start polling command 159 every period ms (default: 1000ms)")
    print("  stop              - Stop polling")
    print("  quit, exit        - Exit the program")
    print()


def parse_test(line, bv):
    """Parse and execute test command"""
    parts = line.split()
    if len(parts) < 2:
        print("Available tests:")
        print("  add_crc    - Test CRC calculation by adding CRC to [1, 2, 0, 31, 0]")
        print("  remove_crc - Test CRC removal from [1, 2, 116, 0, 31, 0, 84]")
        return
    
    subcommand = parts[1].lower()
    
    if subcommand == 'add_crc':
        test_data = [1, 2, 0, 31, 0]
        result = bv._add_crc(test_data.copy())
        print(f"Input: {test_data}")
        print(f"Output: {result}")
    elif subcommand == 'remove_crc':
        test_data = [1, 2, 116, 0, 31, 0, 84]
        result, crc_valid = bv._remove_crc(test_data.copy())
        received_msb, received_lsb = test_data[-1], test_data[2]
        calc_msb, calc_lsb = bv._crc_calculate_xmodem(result)
        print(f"Input: {test_data}")
        print(f"Output: {result}")
        print(f"CRC: Calculated ({calc_msb}, {calc_lsb}) = Received ({received_msb}, {received_lsb}): {'✓' if crc_valid else '✗'}")
    else:
        print(f"Unknown test: {subcommand}")
        print("Available tests: add_crc, remove_crc")


def poll_worker(bv, period, stop_event, last_response_lock, last_response):
    """Worker thread for polling command 159"""
    while not stop_event.is_set():
        try:
            # Send command 159 silently
            result = bv.cmd(159, [], to_print=False)
            
            if result and result.get('data'):
                current_data = result['data']
                
                # Compare with last response
                with last_response_lock:
                    if last_response[0] is None or last_response[0] != current_data:
                        # Response changed or first response
                        # Print the response
                        print()  # New line before printing
                        print(f'Req: 159 [], Resp: {result.get("header", 0)} [{current_data}]', end="")
                        counter, events = parse_header159_response(current_data)
                        print()
                        print(f"Counter: {counter}")
                        for event in events:
                            print(f"  {event}")
                        print()  # New line after printing
                        print("(polling) > ", end="", flush=True)  # Restore prompt (main loop is blocked on input())
                        
                        # Update last response
                        last_response[0] = current_data.copy()
        except Exception as e:
            # On error, print and continue
            if not stop_event.is_set():
                print(f"\nPolling error: {e}")
                print("(polling) > ", end="", flush=True)  # Restore prompt
        
        # Wait for period milliseconds
        if stop_event.wait(period / 1000.0):
            break  # Stop event was set


def parse_cmd(line, bv):
    """Parse and execute cmd command"""
    parts = line.split()
    
    # Handle both "cmd <header> [data]" and "<header> [data]" formats
    if len(parts) < 1:
        print("Error: requires at least a header code")
        print("Usage: <header> [data...] or cmd <header> [data...]")
        return
    
    # Check if first part is "cmd" keyword
    if parts[0].lower() == 'cmd':
        if len(parts) < 2:
            print("Error: cmd requires at least a header code")
            print("Usage: cmd <header> [data...]")
            return
        header_idx = 1
        data_start_idx = 2
    else:
        # Direct integer input (without "cmd" keyword)
        header_idx = 0
        data_start_idx = 1
    
    try:
        header = int(parts[header_idx])
        data = []
        if len(parts) > data_start_idx:
            data = [int(x) for x in parts[data_start_idx:]]
        
        bv.cmd(header, data)
    except ValueError:
        # Check if it's a known command word that was mistakenly used with "cmd"
        if parts[header_idx].lower() in ['test', 'help', 'list', 'quit', 'exit']:
            print(f"Error: '{parts[header_idx]}' is a command, not a header code")
            print(f"Did you mean: {parts[header_idx].lower()} (without 'cmd')?")
        else:
            print(f"Error: Invalid header code '{parts[header_idx]}'. Header must be a decimal number.")
            print("Usage: <header> [data...] or cmd <header> [data...]")
    except Exception as e:
        print(f"Error executing command: {e}")


def main():
    """Main function"""
    # List ports and connect at startup
    print("ccTalk Host - Bill Validator Interface")
    print("=" * 50)
    
    port_list = BillValidator.list_ports()
    
    if not port_list:
        print("No serial ports available. Exiting.")
        sys.exit(1)
    
    # Prompt for port selection
    while True:
        try:
            selection = input("Select port number: ").strip()
            if not selection:
                continue
            idx = int(selection)
            if 0 <= idx < len(port_list):
                selected_port = port_list[idx]
                break
            else:
                print(f"Invalid selection. Please enter a number between 0 and {len(port_list)-1}")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)
    
    # Create validator instance and connect
    bv = BillValidator()
    if not bv.connect(selected_port):
        print("Failed to connect. Exiting.")
        sys.exit(1)
    
    print("\nConnected! Type 'help' for available commands.\n")
    
    # Polling state
    polling_thread = None
    polling_stop_event = threading.Event()
    last_response_lock = threading.Lock()
    last_response = [None]  # Use list to allow modification from thread
    
    # Main command loop
    while True:
        try:
            # Determine prompt based on polling status
            is_polling = polling_thread and polling_thread.is_alive()
            prompt = "(polling) > " if is_polling else "> "
            
            line = input(prompt).strip()
            
            if not line:
                continue
            
            parts = line.split()
            command = parts[0].lower()
            
            # Check if first token is a number (allow direct integer input as cmd)
            try:
                int(command)
                # It's a number, treat as cmd command
                parse_cmd(line, bv)
            except ValueError:
                # Not a number, check for text commands
                if command in ['quit', 'exit', 'q']:
                    # Stop polling if active
                    if polling_thread and polling_thread.is_alive():
                        polling_stop_event.set()
                        polling_thread.join(timeout=1.0)
                    bv.disconnect()
                    print("Goodbye!")
                    break
                elif command == 'help':
                    print_help()
                elif command == 'list':
                    BillValidator.list_headers()
                elif command == 'cmd':
                    parse_cmd(line, bv)
                elif command == 'test':
                    parse_test(line, bv)
                elif command == 'poll':
                    # Start polling
                    if polling_thread and polling_thread.is_alive():
                        print("Polling is already active. Use 'stop' to stop it first.")
                        continue
                    
                    # Parse period (default 1000ms)
                    period = 1000
                    if len(parts) > 1:
                        try:
                            period = int(parts[1])
                            if period < 100:
                                print("Warning: Period too short, using minimum 100ms")
                                period = 100
                        except ValueError:
                            print(f"Error: Invalid period '{parts[1]}'. Using default 1000ms.")
                    
                    # Reset state
                    polling_stop_event.clear()
                    with last_response_lock:
                        last_response[0] = None
                    
                    # Start polling thread
                    polling_thread = threading.Thread(
                        target=poll_worker,
                        args=(bv, period, polling_stop_event, last_response_lock, last_response),
                        daemon=True
                    )
                    polling_thread.start()
                    print(f"Polling started (period: {period}ms). Type 'stop' to stop.")
                elif command == 'stop':
                    # Stop polling
                    if polling_thread and polling_thread.is_alive():
                        polling_stop_event.set()
                        polling_thread.join(timeout=1.0)
                        print("Polling stopped.")
                    else:
                        print("No active polling to stop.")
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands.")
        
        except KeyboardInterrupt:
            print("\nUse 'quit' or 'exit' to exit.")
        except EOFError:
            print("\nGoodbye!")
            bv.disconnect()
            break
        except Exception as e:
            print(f"Error: {e}")
            # Restore prompt if polling is active
            if polling_thread and polling_thread.is_alive():
                print("(polling) > ", end="", flush=True)


def test_add_crc():
    """Test routine: Add CRC to [1, 2, 0, 31, 0]"""
    bv = BillValidator()
    test_data = [1, 2, 0, 31, 0]
    print("Test CRC routine")
    print("=" * 50)
    print("Input data:", test_data)
    print()
    
    result = bv._add_crc(test_data.copy())
    print("After adding CRC:", result)
    print()
    
    # Display in different formats
    print("Decimal:", " ".join([str(x) for x in result]))
    print("Hex:", " ".join([f"0x{x:02X}" for x in result]))
    print("Hex (no prefix):", " ".join([f"{x:02X}" for x in result]))
    print("=" * 50)


if __name__ == "__main__":
    # Run test if --test argument is provided
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_add_crc()
    else:
        main()

