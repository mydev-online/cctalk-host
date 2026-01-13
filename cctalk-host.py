#!/usr/bin/env python3
"""ccTalk Host - Interactive command-line interface for Bill Validator communication"""

import sys
import os
import glob
import threading
import argparse

try:
    import readline
    import atexit
    # Enable persistent history
    history_file = os.path.join(os.path.expanduser("~"), ".cctalk_host_history")
    try:
        if os.path.exists(history_file):
            readline.read_history_file(history_file)
        readline.set_history_length(1000)
        
        # macOS libedit support
        if 'libedit' in getattr(readline, '__doc__', ''):
            readline.parse_and_bind("bind ^[[A ed-prev-history")
            readline.parse_and_bind("bind ^[[B ed-next-history")
        
        # Disable default word delimiters for better history handling of spaces
        readline.set_completer_delims('')
    except Exception:
        pass
    atexit.register(readline.write_history_file, history_file)
except ImportError:
    # Readline not available (e.g. on Windows without pyreadline)
    pass

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""
    _ENABLED = True
    
    _CODES = {
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
        'DIM': '\033[2m',
        'BLACK': '\033[30m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'YELLOW': '\033[33m',
        'BLUE': '\033[34m',
        'MAGENTA': '\033[35m',
        'CYAN': '\033[36m',
        'WHITE': '\033[37m',
        'BRIGHT_BLACK': '\033[90m',
        'BRIGHT_RED': '\033[91m',
        'BRIGHT_GREEN': '\033[92m',
        'BRIGHT_YELLOW': '\033[93m',
        'BRIGHT_BLUE': '\033[94m',
        'BRIGHT_MAGENTA': '\033[95m',
        'BRIGHT_CYAN': '\033[96m',
        'BRIGHT_WHITE': '\033[97m',
    }

    @classmethod
    def enable(cls):
        cls._ENABLED = True
        for name, code in cls._CODES.items():
            setattr(cls, name, code)

    @classmethod
    def disable(cls):
        cls._ENABLED = False
        for name in cls._CODES.keys():
            setattr(cls, name, '')

# Initialize attributes
Colors.enable()

# Determine if colors should be enabled
def should_enable_colors():
    if os.environ.get('FORCE_COLOR'):
        return True
    if os.environ.get('NO_COLOR'):
        return False
    return sys.stdout.isatty()

if not should_enable_colors():
    Colors.disable()

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
        152: "[BILL] Request inhibit status",
        154: "[BILL] Route bill",
        155: "[BILL] Request bill position",
        156: "[BILL] Request country scaling factor",
        157: "[BILL] Request bill ID",
        158: "[BILL] Modify bill ID",
        159: "[BILL] Read buffered bill events",
        192: "Request build code",
        194: "Request database version",
        197: "Calculate ROM checksum",
        209: "[COIN] Request sorter paths",
        210: "[COIN] Modify sorter paths",
        213: "Request option flags",
        225: "Request accept counter",
        226: "Request insertion counter",
        227: "Request master inhibit status",
        228: "Modify master inhibit status",
        229: "[COIN] Read buffered credit or error codes",
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
    
    def __init__(self, baudrate=9600, timeout=0.2, checksum_mode='crc', address=40):
        """Initialize BillValidator instance
        
        Args:
            baudrate: Serial baud rate (default: 9600)
            timeout: Serial timeout in seconds (default: 0.2)
            checksum_mode: 'crc' for 2-byte CRC (XModem) or 'checksum' for 1-byte checksum (default: 'crc')
            address: Device address (default: 40)
        """
        self.ser = None
        self.baudrate = baudrate
        self.timeout = timeout
        self.port = None
        self.address = address
        self.checksum_mode = checksum_mode.lower()
        if self.checksum_mode not in ['crc', 'checksum']:
            raise ValueError("checksum_mode must be 'crc' or 'checksum'")
    
    def _crc_calculate_xmodem(self, message):
        """Calculate XModem CRC for a message"""
        crc = 0x0000
        for byte in message:
            crc = ((crc << 8) ^ self.CRC_TABLE[(crc >> 8) ^ byte]) & 0xFFFF
        crc = '%04x' % crc
        msb = int(crc[:-2], 16)
        lsb = int(crc[-2:], 16)
        return msb, lsb
    
    def _checksum_calculate(self, message):
        """Calculate 8-bit checksum for a message
        
        The checksum byte is chosen such that the sum of all bytes (including checksum) is 0 mod 256.
        Returns the checksum byte value to append.
        """
        total_sum = sum(message) & 0xFF
        checksum = (256 - total_sum) & 0xFF
        return checksum
    
    def _add_crc(self, l):
        """Add CRC or checksum to message
        
        CRC mode: LSB at position 2 (overwrites source address), MSB at end
        Checksum mode: Single byte appended at end
        """
        if self.checksum_mode == 'crc':
            msb, lsb = self._crc_calculate_xmodem(l)
            l.insert(2, lsb)  # LSB overwrites position 2 (source address field)
            l.append(msb)      # MSB at end
        else:  # checksum mode
            checksum = self._checksum_calculate(l)
            l.append(checksum)  # Single byte at end
        return l
    
    def _remove_crc(self, data):
        """Remove CRC or checksum from response and verify it
        
        CRC structure in ccTalk:
        - CRC LSB overwrites position 2 (source address field)
        - CRC MSB is at the end of the message
        - CRC is calculated on: [dest, len, header, data...] (after removing both CRC bytes)
        
        Checksum structure:
        - Single checksum byte appended at the end
        - Checksum is calculated on: [dest, len, header, data...] (after removing checksum byte)
        
        Returns:
            tuple: (data_without_crc, crc_valid) where crc_valid is True if CRC/checksum matches
        """
        # Convert bytes to list of integers if needed
        if isinstance(data, bytes):
            l = list(data)
        else:
            l = list(data)
        
        if self.checksum_mode == 'crc':
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
        else:  # checksum mode
            if len(l) < 2:
                return (l, False)  # Too short to have checksum (need at least dest + len + checksum)
            
            # Extract checksum byte from end
            received_checksum = l.pop(-1)  # Remove checksum from end
            
            # Verify checksum: 
            # Method 1: Calculate expected checksum and compare
            calculated_checksum = self._checksum_calculate(l)
            # Method 2: Verify sum of all bytes (including checksum) is 0 mod 256
            total_sum = (sum(l) + received_checksum) & 0xFF
            
            # In checksum mode, ccTalk responses include Source at position 2.
            # We pop it here to keep the return format consistent: [dest, len, header, data...]
            if len(l) >= 3:
                l.pop(2)
                
            crc_valid = (calculated_checksum == received_checksum) and (total_sum == 0)
            
            if not crc_valid:
                print(f"Checksum error for {data}: calculated {calculated_checksum} (0x{calculated_checksum:02X}), got {received_checksum} (0x{received_checksum:02X})")
                print(f"  Total sum (including checksum): {total_sum} (should be 0)")
                print(f"  Raw input (hex): {' '.join([f'{x:02X}' for x in data])}")
                print(f"  Data being checksum-checked: {l}")
                print(f"  Data being checksum-checked (hex): {' '.join([f'{x:02X}' for x in l])}")
        
        # Return message without CRC/checksum bytes and verification status: [dest, len, header, data...]
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
        """List all available serial ports in 80's terminal box style"""
        box_width = 90
        
        header_text = "SERIAL PORTS"
        header_len = len(header_text) + 4  # "╔═ " + text + " ═" = 3 + text + 2
        print(f"{Colors.BOLD}{Colors.BLUE}╔═ {header_text} ═{'═' * (box_width - header_len)}{Colors.RESET}")
        print(f"{Colors.BLUE}║{Colors.RESET} {Colors.DIM}Scanning for available serial ports...{Colors.RESET}")
        
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            print(f"{Colors.BLUE}║{Colors.RESET} {Colors.RED}No serial ports found.{Colors.RESET}")
            print(f"{Colors.BLUE}╚{'═' * box_width}{Colors.RESET}")
            return []
        
        print(f"{Colors.BLUE}╠{'═' * box_width}{Colors.RESET}")
        port_list = []
        for idx, port_info in enumerate(ports):
            print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}[{idx}]{Colors.RESET} {Colors.BRIGHT_BLUE}{port_info.device}{Colors.RESET}")
            if port_info.description:
                print(f"{Colors.BLUE}║{Colors.RESET} {'':6s}{Colors.DIM}{port_info.description}{Colors.RESET}")
            port_list.append(port_info.device)
        
        print(f"{Colors.BLUE}╚{'═' * box_width}{Colors.RESET}")
        return port_list
    
    @staticmethod
    def list_headers():
        """List all header codes and their function names in 80's terminal box style"""
        box_width = 90
        
        header_text = "HEADER CODES"
        header_len = len(header_text) + 4  # "╔═ " + text + " ═" = 3 + text + 2
        print(f"{Colors.BOLD}{Colors.BLUE}╔═ {header_text} ═{'═' * (box_width - header_len)}{Colors.RESET}")
        
        codes = sorted(BillValidator.HEADER_CODES.keys())
        if codes:
            print(f"{Colors.BLUE}╠{'═' * box_width}{Colors.RESET}")
            for code in codes:
                name = BillValidator.HEADER_CODES[code]
                if "[BILL]" in name:
                    name = name.replace("[BILL]", f"{Colors.BRIGHT_BLUE}[BILL]{Colors.RESET}")
                elif "[COIN]" in name:
                    name = name.replace("[COIN]", f"{Colors.BRIGHT_MAGENTA}[COIN]{Colors.RESET}")
                
                print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}{code:3d}{Colors.RESET} ({Colors.DIM}0x{code:02X}{Colors.RESET}) {Colors.BRIGHT_WHITE}{name}{Colors.RESET}")
        
        print(f"{Colors.BLUE}╚{'═' * box_width}{Colors.RESET}")
        return BillValidator.HEADER_CODES
    
    def scan(self):
        """Scan for devices on all addresses with both CRC and Checksum modes"""
        if self.ser is None or not self.ser.is_open:
            print("Not connected. Call connect() first.")
            return
        
        box_width = 90
        header_text = "DEVICE SCAN"
        header_len = len(header_text) + 4
        print(f"\n{Colors.BOLD}{Colors.YELLOW}╔═ {header_text} ═{'═' * (box_width - header_len)}{Colors.RESET}")
        print(f"{Colors.YELLOW}║{Colors.RESET} Scanning addresses... Press Ctrl+C to abort.")
        
        # Priority addresses to check first
        priority_addresses = [40, 2, 1]
        other_addresses = [a for a in range(1, 256) if a not in priority_addresses]
        all_addresses = priority_addresses + other_addresses
        
        found_devices = []
        original_address = self.address
        original_mode = self.checksum_mode
        
        try:
            for addr in all_addresses:
                self.address = addr
                for mode in ['crc', 'checksum']:
                    self.checksum_mode = mode
                    # Use a very short timeout for scanning to speed up
                    self.ser.timeout = 0.05
                    
                    # Send Simple Poll (header 254)
                    res = self.cmd(254, to_print=False)
                    
                    if res is not None:
                        # Found something!
                        # Get manufacturer name (header 246)
                        man_res = self.cmd(246, to_print=False)
                        man_name = self._ints_to_ascii(man_res['data']) if (man_res and man_res.get('data')) else "Unknown"
                        
                        device_info = {
                            'address': addr,
                            'mode': mode,
                            'manufacturer': man_name.strip()
                        }
                        found_devices.append(device_info)
                        print(f"{Colors.YELLOW}║{Colors.RESET} {Colors.BRIGHT_GREEN}FOUND!{Colors.RESET} Addr: {Colors.BOLD}{addr:3d}{Colors.RESET}, Mode: {Colors.CYAN}{mode:8s}{Colors.RESET}, Mfg: {Colors.BRIGHT_WHITE}{man_name}{Colors.RESET}")
                
                # Show progress occasionally
                if addr % 20 == 0:
                    print(f"{Colors.YELLOW}║{Colors.RESET}   Progress: {addr/255*100:.1f}%...")
                    
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}║{Colors.RESET} Scan aborted by user.")
        
        # Restore original settings
        self.address = original_address
        self.checksum_mode = original_mode
        self.ser.timeout = self.timeout
        
        if not found_devices:
            print(f"{Colors.YELLOW}║{Colors.RESET} {Colors.BRIGHT_RED}No devices responded.{Colors.RESET}")
            print(f"{Colors.YELLOW}║{Colors.RESET} Check connection and power.")
        
        print(f"{Colors.YELLOW}╚{'═' * box_width}{Colors.RESET}\n")
        return found_devices

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
        
        if self.checksum_mode == 'crc':
            msg = [self.address, length, header] + data
        else:
            msg = [self.address, length, 1, header] + data
            
        req = self._add_crc(msg.copy())
        
        # Clear buffer
        self.ser.reset_input_buffer()
        self.ser.write(bytes(req))
        
        # ccTalk often echoes the request back
        # Read the echo (if any) and then look for response
        echo = self.ser.read(len(req))
        
        # Connection check: If we don't even hear our own echo, RX/TX might be disconnected
        if len(echo) == 0 and to_print:
            print(f"{Colors.BRIGHT_RED}Hardware Alert:{Colors.RESET} No loopback detected. Check RX/TX wiring and power.")
        
        # Read response: [dest, len, src/crc_lsb, header, data..., checksum/crc_msb]
        # We read first 2 bytes to get the data length
        dest_len = self.ser.read(2)
        resp = b""
        
        if len(dest_len) == 2:
            resp_data_len = dest_len[1]
            # Total remaining in packet: source(1) + header(1) + data(N) + checksum(1)
            # Both CRC and Checksum modes have 3 bytes overhead after [dest, len] + data
            remaining = self.ser.read(resp_data_len + 3)
            resp = dest_len + remaining
        
        resp_header = None
        resp_data = []
        
        # Check if response is long enough: 5 bytes minimum
        if len(resp) >= 5:
            try:
                # _remove_crc returns [dest, len, header, data...]
                resp_trunc, crc_valid = self._remove_crc(resp)
                if len(resp_trunc) >= 3:
                    resp_header = resp_trunc[2]  # Header is at position 2
                    resp_data = resp_trunc[3:] if len(resp_trunc) > 3 else []
            except (IndexError, ValueError) as e:
                # Fallback parsing
                resp_list = list(resp)
                if len(resp_list) >= 4:
                    # In checksum mode: [1, len, 40, header, ...]
                    # In CRC mode: [1, len, lsb, header, ...]
                    resp_header = resp_list[3]
                    resp_data = resp_list[4:-1]
            
            if to_print:
                # Format request
                header_name = BillValidator.HEADER_CODES.get(header, "Unknown")
                req_str = f"{Colors.BLUE}→{Colors.RESET} {Colors.BOLD}Header{Colors.RESET} {Colors.BRIGHT_BLUE}{header}{Colors.RESET} ({Colors.DIM}0x{header:02X}{Colors.RESET}) - {Colors.DIM}{header_name}{Colors.RESET}"
                if data:
                    data_hex = " ".join([f"0x{x:02X}" for x in data])
                    data_dec = " ".join([str(x) for x in data])
                    req_str += f"\n  {Colors.DIM}Data:{Colors.RESET} [{Colors.BRIGHT_WHITE}{data_dec}{Colors.RESET}] ({Colors.DIM}{data_hex}{Colors.RESET})"
                else:
                    req_str += f"\n  {Colors.DIM}Data:{Colors.RESET} {Colors.DIM}[empty]{Colors.RESET}"
                
                # Format response
                if resp_header is not None:
                    resp_str = f"{Colors.BLUE}←{Colors.RESET} {Colors.BOLD}Response{Colors.RESET} {Colors.BRIGHT_BLUE}{resp_header}{Colors.RESET}"
                    if resp_data:
                        resp_hex = " ".join([f"0x{x:02X}" for x in resp_data])
                        resp_dec = " ".join([str(x) for x in resp_data])
                        resp_str += f"\n  {Colors.DIM}Data:{Colors.RESET} [{Colors.BRIGHT_WHITE}{resp_dec}{Colors.RESET}] ({Colors.DIM}{resp_hex}{Colors.RESET})"
                    else:
                        resp_str += f"\n  {Colors.DIM}Data:{Colors.RESET} {Colors.DIM}[empty]{Colors.RESET}"
                else:
                    resp_str = f"{Colors.RED}←{Colors.RESET} {Colors.BOLD}Response{Colors.RESET} {Colors.RED}None{Colors.RESET} {Colors.DIM}(no response received){Colors.RESET}"
                
                # Special handling for event headers
                if header == 159:
                    counter, events = parse_header159_response(resp_data)
                    print(req_str)
                    print(resp_str)
                    print_header159_formatted(counter, events)
                elif header == 229:
                    counter, events = parse_header229_response(resp_data)
                    print(req_str)
                    print(resp_str)
                    print_header229_formatted(counter, events)
                else:
                    print(req_str)
                    print(resp_str)
                    # Show ASCII representation if available
                    str_ = self._ints_to_ascii(resp_data)
                    if str_:
                        print(f"  {Colors.DIM}ASCII:{Colors.RESET} {Colors.BRIGHT_WHITE}{str_}{Colors.RESET}")
        
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


def parse_header229_response(resp_data):
    """Parse header 229 response (Coin Acceptor) and return structured event data"""
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
            result_a = 0
            result_b = 0
        
        if result_a == 0:
            # Error/Status codes
            event_map = {
                0: "Null event",
                1: "Reject coin",
                2: "Invalid coin",
                3: "Abandon coin",
                4: "Inhibited coin",
                5: "Full post-insertion inhibit",
                6: "Sorter wall",
                7: "Sorter path",
                8: "Coin jam",
                9: "Sorter jam",
                10: "Sorter sensor",
                11: "Sorter not ready",
                12: "Sorter path error",
                13: "Pay out jam",
                14: "Pay out sensor",
                15: "Pay out empty",
                16: "Base sensor error",
                17: "Year sensor error",
                18: "Token teach error",
                19: "Power fail",
                20: "Authentication fail",
                21: "Coin feeder jam",
                22: "Coin feeder sensor error",
                23: "Coin feeder empty",
                24: "Coin feeder faulty",
                255: "Unknown error"
            }
            event_type = event_map.get(result_b, f"Unknown coin event (B={result_b})")
            event_category = "Status" if result_b in [0, 1, 4, 11] else \
                            "Reject" if result_b in [2, 3] else "Error"
            events.append({
                'category': event_category,
                'type': event_type,
                'a': result_a,
                'b': result_b,
                'pair': i + 1
            })
        else:
            # Result A > 0 means credit
            events.append({
                'category': 'Credit',
                'type': f'Coin type {result_a} accepted (Sorter path {result_b})',
                'coin_type': result_a,
                'sorter_path': result_b,
                'a': result_a,
                'b': result_b,
                'pair': i + 1
            })
    
    return counter, events


def print_header229_formatted(counter, events):
    """Print header 229 response in 80's terminal box style"""
    box_width = 90
    header_text = "COIN EVENTS"
    header_len = len(header_text) + 4
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}╔═ {header_text} ═{'═' * (box_width - header_len)}{Colors.RESET}")
    print(f"{Colors.MAGENTA}║{Colors.RESET} {Colors.BOLD}Counter:{Colors.RESET} {Colors.BRIGHT_MAGENTA}{counter:3d}{Colors.RESET} {Colors.DIM}(0x{counter:02X}){Colors.RESET}")
    
    if not events:
        print(f"{Colors.MAGENTA}║{Colors.RESET} {Colors.DIM}No events{Colors.RESET}")
    else:
        print(f"{Colors.MAGENTA}╠{'═' * box_width}{Colors.RESET}")
        for ev in events:
            color = Colors.BRIGHT_GREEN if ev['category'] == 'Credit' else \
                    Colors.BRIGHT_YELLOW if ev['category'] == 'Status' else Colors.BRIGHT_RED
            print(f"{Colors.MAGENTA}║{Colors.RESET} {ev['pair']}. {color}{ev['category']:14s}{Colors.RESET} {ev['type']}")
    
    print(f"{Colors.MAGENTA}╚{'═' * box_width}{Colors.RESET}\n")


def parse_header159_response(resp_data):
    """Parse header 159 response and return structured event data"""
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
            events.append({
                'category': event_category,
                'type': event_type,
                'a': result_a,
                'b': result_b,
                'pair': i + 1
            })
        elif result_a >= 1 and result_a <= 255:
            if result_b == 0:
                events.append({
                    'category': 'Credit',
                    'type': f'Bill type {result_a} validated correctly and sent to cashbox/stacker',
                    'bill_type': result_a,
                    'a': result_a,
                    'b': result_b,
                    'pair': i + 1
                })
            elif result_b == 1:
                events.append({
                    'category': 'Pending Credit',
                    'type': f'Bill type {result_a} validated correctly and held in escrow',
                    'bill_type': result_a,
                    'a': result_a,
                    'b': result_b,
                    'pair': i + 1
                })
            else:
                events.append({
                    'category': 'Unknown',
                    'type': f'A={result_a}, B={result_b}',
                    'a': result_a,
                    'b': result_b,
                    'pair': i + 1
                })
        else:
            events.append({
                'category': 'Unknown',
                'type': f'A={result_a}, B={result_b}',
                'a': result_a,
                'b': result_b,
                'pair': i + 1
            })
    
    return counter, events


def print_header159_formatted(counter, events):
    """Print header 159 response in 80's terminal box style"""
    box_width = 90
    
    # Box header
    header_text = "BILL EVENTS"
    header_len = len(header_text) + 4  # "╔═ " + text + " ═" = 3 + text + 2
    print(f"\n{Colors.BOLD}{Colors.BLUE}╔═ {header_text} ═{'═' * (box_width - header_len)}{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}Counter:{Colors.RESET} {Colors.BRIGHT_BLUE}{counter:3d}{Colors.RESET} {Colors.DIM}(0x{counter:02X}){Colors.RESET}")
    
    if not events:
        print(f"{Colors.BLUE}║{Colors.RESET} {Colors.DIM}No events{Colors.RESET}")
    else:
        # Print separator line
        print(f"{Colors.BLUE}╠{'═' * box_width}{Colors.RESET}")
        
        # Group events by category for better display
        for event in events:
            category = event['category']
            event_type = event['type']
            pair_num = event['pair']
            
            # Choose color based on category (no icons)
            if category == 'Credit':
                cat_color = Colors.GREEN
            elif category == 'Pending Credit':
                cat_color = Colors.YELLOW
            elif category == 'Status':
                cat_color = Colors.BLUE
            elif category == 'Reject':
                cat_color = Colors.YELLOW
            elif category == 'Fatal Error':
                cat_color = Colors.RED
            elif category == 'Fraud Attempt':
                cat_color = Colors.RED
            else:
                cat_color = Colors.DIM
            
            # Format the event line
            pair_str = f"{Colors.DIM}Pair {pair_num}:{Colors.RESET}"
            cat_str = f"{cat_color}{Colors.BOLD}{category:15s}{Colors.RESET}"
            type_str = f"{Colors.BRIGHT_WHITE}{event_type}{Colors.RESET}"
            
            print(f"{Colors.BLUE}║{Colors.RESET} {pair_str} {cat_str} {type_str}")
    
    print(f"{Colors.BLUE}╚{'═' * box_width}{Colors.RESET}")


def print_help():
    """Print help message in 80's terminal box style"""
    box_width = 90
    cmd_width = 18  # Width for command names
    
    header_text = "COMMANDS"
    header_len = len(header_text) + 5  # "╔═ " + text + " ═" = 3 + text + 2
    print(f"{Colors.BOLD}{Colors.BLUE}╔═ {header_text} ═{'═' * (box_width - header_len)}{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}help{Colors.RESET}{' ' * (cmd_width - 4)} - Show this help message")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}list{Colors.RESET}{' ' * (cmd_width - 4)} - List all header codes and their function names")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}scan{Colors.RESET}{' ' * (cmd_width - 4)} - Scan for devices (addresses 1-255, modes CRC/Checksum)")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}<header> [data]{Colors.RESET}{' ' * (cmd_width - 15)} - Send command (cmd keyword optional)")
    print(f"{Colors.BLUE}║{Colors.RESET} {' ' * (cmd_width + 1)}   Header and data values are decimal, space-separated")
    print(f"{Colors.BLUE}║{Colors.RESET} {' ' * (cmd_width + 1)}   Example: {Colors.BRIGHT_WHITE}254{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET} {' ' * (cmd_width + 1)}   Example: {Colors.BRIGHT_WHITE}154 1{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET} {' ' * (cmd_width + 1)}   Example: {Colors.BRIGHT_WHITE}cmd 231 255 255{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}poll [period]{Colors.RESET}{' ' * (cmd_width - 13)} - Start polling command 159 every period ms")
    print(f"{Colors.BLUE}║{Colors.RESET} {' ' * (cmd_width + 1)}   (default: 1000ms)")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}stop{Colors.RESET}{' ' * (cmd_width - 4)} - Stop polling")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}quit, exit{Colors.RESET}{' ' * (cmd_width - 10)} - Exit the program")
    print(f"{Colors.BLUE}╚{'═' * box_width}{Colors.RESET}")
    print()


def parse_test(line, bv):
    """Parse and execute test command"""
    parts = line.split()
    if len(parts) < 2:
        print("Available tests:")
        print("  add_crc       - Test CRC calculation by adding CRC to [1, 2, 0, 31, 0]")
        print("  remove_crc    - Test CRC removal from [1, 2, 116, 0, 31, 0, 84]")
        print("  add_checksum  - Test checksum calculation by adding checksum to [40, 0, 1, 159]")
        print("  remove_checksum - Test checksum removal from [40, 0, 1, 159, 56]")
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
    elif subcommand == 'add_checksum':
        # Create temporary validator in checksum mode for this test
        test_bv = BillValidator(checksum_mode='checksum')
        test_data = [40, 0, 1, 159]
        result = test_bv._add_crc(test_data.copy())
        calculated_checksum = test_bv._checksum_calculate(test_data)
        print(f"Input: {test_data}")
        print(f"Output: {result}")
        print(f"Checksum: Calculated {calculated_checksum} (0x{calculated_checksum:02X}), Added {result[-1]} (0x{result[-1]:02X}): {'✓' if calculated_checksum == result[-1] else '✗'}")
    elif subcommand == 'remove_checksum':
        # Create temporary validator in checksum mode for this test
        test_bv = BillValidator(checksum_mode='checksum')
        test_data = [40, 0, 1, 159, 56]
        result, checksum_valid = test_bv._remove_crc(test_data.copy())
        received_checksum = test_data[-1]
        calculated_checksum = test_bv._checksum_calculate(result)
        print(f"Input: {test_data}")
        print(f"Output: {result}")
        print(f"Checksum: Calculated {calculated_checksum} (0x{calculated_checksum:02X}) = Received {received_checksum} (0x{received_checksum:02X}): {'✓' if checksum_valid else '✗'}")
    else:
        print(f"Unknown test: {subcommand}")
        print("Available tests: add_crc, remove_crc, add_checksum, remove_checksum")


def poll_worker(bv, period, stop_event, last_response_lock, last_response, event_header=159):
    """Worker thread for polling device events (159 for bill, 229 for coin)"""
    while not stop_event.is_set():
        try:
            # Send command silently
            result = bv.cmd(event_header, [], to_print=False)
            
            if result and result.get('data'):
                current_data = result['data']
                
                # Compare with last response
                with last_response_lock:
                    if last_response[0] is None or last_response[0] != current_data:
                        # Response changed or first response
                        # Format and print the response
                        print()  # New line before printing
                        header_name = BillValidator.HEADER_CODES.get(event_header, f"Header {event_header}")
                        req_str = f"{Colors.BLUE}→{Colors.RESET} {Colors.BOLD}Header{Colors.RESET} {Colors.BRIGHT_BLUE}{event_header}{Colors.RESET} ({Colors.DIM}0x{event_header:02X}{Colors.RESET}) - {Colors.DIM}{header_name}{Colors.RESET}"
                        req_str += f"\n  {Colors.DIM}Data:{Colors.RESET} {Colors.DIM}[empty]{Colors.RESET}"
                        
                        resp_header = result.get("header", 0)
                        resp_hex = " ".join([f"0x{x:02X}" for x in current_data])
                        resp_dec = " ".join([str(x) for x in current_data])
                        resp_str = f"{Colors.BLUE}←{Colors.RESET} {Colors.BOLD}Response{Colors.RESET} {Colors.BRIGHT_BLUE}{resp_header}{Colors.RESET}"
                        resp_str += f"\n  {Colors.DIM}Data:{Colors.RESET} [{Colors.BRIGHT_WHITE}{resp_dec}{Colors.RESET}] ({Colors.DIM}{resp_hex}{Colors.RESET})"
                        
                        print(req_str)
                        print(resp_str)
                        
                        if event_header == 159:
                            counter, events = parse_header159_response(current_data)
                            print_header159_formatted(counter, events)
                        elif event_header == 229:
                            counter, events = parse_header229_response(current_data)
                            print_header229_formatted(counter, events)
                            
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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='ccTalk Host - Interactive command-line interface for Bill Validator communication',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Interactive mode (prompts for port and checksum mode)
  %(prog)s --port /dev/ttyUSB0      # Use specific port, prompt for checksum mode
  %(prog)s --port 3 --mode crc      # Use port index 3, use CRC mode
  %(prog)s --port /dev/ttyUSB0 --mode checksum  # Use specific port, checksum mode
        """
    )
    parser.add_argument(
        '--port', '-p',
        type=str,
        help='Serial port (device path like /dev/ttyUSB0 or port index number)'
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['crc', 'checksum'],
        help='Checksum mode: "crc" for 2-byte CRC (XModem) or "checksum" for 1-byte checksum'
    )
    parser.add_argument(
        '--type', '-t',
        choices=['bill', 'coin'],
        help='Device type: "bill" for bill validator or "coin" for coin acceptor'
    )
    parser.add_argument(
        '--address', '-a',
        type=int,
        default=40,
        help='ccTalk device address (default: 40)'
    )
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    parser.add_argument(
        '--force-color', '--color',
        action='store_true',
        help='Force colored output even if not in a terminal'
    )
    
    args = parser.parse_args()

    # Update color status based on arguments
    if args.no_color:
        Colors.disable()
    elif args.force_color:
        Colors.enable()
    
    # List ports and connect at startup
    box_width = 90
    print(f"\n{Colors.BOLD}{Colors.BLUE}╔{'═' * box_width}{Colors.RESET}")
    print(f"{Colors.BLUE}║{Colors.RESET} {Colors.BOLD}{Colors.BRIGHT_BLUE}ccTalk Host - Bill Validator Interface{Colors.RESET}")
    print(f"{Colors.BLUE}╚{'═' * box_width}{Colors.RESET}\n")
    
    port_list = BillValidator.list_ports()
    
    if not port_list:
        print("No serial ports available. Exiting.")
        sys.exit(1)
    
    # Determine port selection
    selected_port = None
    if args.port:
        # Try to parse as port index first
        try:
            idx = int(args.port)
            if 0 <= idx < len(port_list):
                selected_port = port_list[idx]
            else:
                print(f"Invalid port index {idx}. Please use a number between 0 and {len(port_list)-1}")
                sys.exit(1)
        except ValueError:
            # Not a number, treat as device path
            if args.port in port_list:
                selected_port = args.port
            else:
                print(f"Port '{args.port}' not found in available ports.")
                sys.exit(1)
    else:
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
    
    # Determine device type
    device_type = args.type
    if not device_type:
        print(f"\n{Colors.BOLD}{Colors.BLUE}Device Type Selection:{Colors.RESET}")
        print("  [0] Bill Validator (default address: 40, event header: 159)")
        print("  [1] Coin Acceptor  (default address: 2, event header: 229)")
        while True:
            try:
                type_selection = input("Select device type [0/1]: ").strip()
                if type_selection == '0':
                    device_type = 'bill'
                    break
                elif type_selection == '1':
                    device_type = 'coin'
                    break
                else:
                    print("Invalid selection. Please enter 0 or 1.")
            except KeyboardInterrupt:
                print("\nExiting.")
                sys.exit(0)
    
    # Set default address if not provided
    address = args.address
    if address == 40 and device_type == 'coin':
        # Default changed if user didn't specify and selected coin
        address = 2
    
    event_header = 159 if device_type == 'bill' else 229

    # Determine checksum mode
    checksum_mode = args.mode
    if not checksum_mode:
        # Prompt for checksum mode
        print(f"\n{Colors.BOLD}{Colors.BLUE}Checksum Mode Selection:{Colors.RESET}")
        print("  [0] CRC (2-byte XModem CRC - LSB overwrites address field, MSB at end)")
        print("  [1] Checksum (1-byte checksum - appended at end)")
        while True:
            try:
                mode_selection = input("Select checksum mode [0/1]: ").strip()
                if mode_selection == '0':
                    checksum_mode = 'crc'
                    break
                elif mode_selection == '1':
                    checksum_mode = 'checksum'
                    break
                else:
                    print("Invalid selection. Please enter 0 for CRC or 1 for Checksum.")
            except KeyboardInterrupt:
                print("\nExiting.")
                sys.exit(0)
    
    # Create validator instance and connect
    bv = BillValidator(checksum_mode=checksum_mode, address=address)
    if not bv.connect(selected_port):
        print("Failed to connect. Exiting.")
        sys.exit(1)
    
    # Display selected mode
    mode_display = "CRC (2-byte XModem)" if checksum_mode == 'crc' else "Checksum (1-byte)"
    print(f"{Colors.DIM}Using {mode_display} mode{Colors.RESET}")
    
    box_width = 90
    print(f"\n{Colors.GREEN}╔{'═' * box_width}{Colors.RESET}")
    print(f"{Colors.GREEN}║{Colors.RESET} {Colors.BOLD}{Colors.BRIGHT_GREEN}Connected!{Colors.RESET} Type '{Colors.BRIGHT_BLUE}help{Colors.RESET}' for available commands.")
    print(f"{Colors.GREEN}╚{'═' * box_width}{Colors.RESET}\n")
    
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
            prompt = f"{Colors.BRIGHT_MAGENTA}(polling){Colors.RESET} > " if is_polling else f"{Colors.BRIGHT_GREEN}> {Colors.RESET}"
            
            line = input(prompt).strip()
            
            if not line:
                continue
            
            # Add to history if readline is available and it's not a duplicate of the last entry
            # Note: We don't need manual add_history if readline is working correctly, 
            # but we keep it for environments where it's not automatic.
            if 'readline' in sys.modules:
                try:
                    import readline
                    # On some systems, input() adds to history automatically. 
                    # To avoid duplicates, we check the last item.
                    last_idx = readline.get_current_history_length()
                    last_item = readline.get_history_item(last_idx) if last_idx > 0 else None
                    if last_item != line:
                        readline.add_history(line)
                except Exception:
                    pass
            
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
                elif command == 'scan':
                    bv.scan()
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
                        args=(bv, period, polling_stop_event, last_response_lock, last_response, event_header),
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

