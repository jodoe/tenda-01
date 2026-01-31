import socket
import time
import re
import sys
import os

# --- Configuration ---
HOST = "192.168.2.1"
USER = "root"      
PASS = "Fireitup"
PEAK = 0

# ANSI Color Codes
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"

def get_colored_bar(size, total_width=40):
    """Generates a tri-color signal bar based on width."""
    bar_chars = ""
    for i in range(1, total_width + 1):
        if i <= size:
            # Determine color based on position in the bar
            if i <= 13:
                bar_chars += f"{RED}█{RESET}"
            elif i <= 26:
                bar_chars += f"{YELLOW}█{RESET}"
            else:
                bar_chars += f"{GREEN}█{RESET}"
        else:
            bar_chars += " "  # Empty space for the rest of the bar
    return bar_chars

def fast_root_monitor():
    global PEAK
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5) 
    
    try:
        print(f"[*] Connecting to {HOST}...")
        s.connect((HOST, 23))
        
        s.sendall(b'\xff\xfd\x03\xff\xfb\x01') 
        time.sleep(0.5)
        s.sendall(f"{USER}\r\n".encode('ascii'))
        time.sleep(0.5)
        s.sendall(f"{PASS}\r\n".encode('ascii'))
        time.sleep(1.0) 
        
        print(f"[*] Dashboard Active. Polling: 1.0s. Mode: dBm Precision.")

        while True:
            s.sendall(b"cat /proc/wlan0/sta_info /proc/wlan0/mib_all\n")
            time.sleep(1.0) 
            
            s.setblocking(False)
            try:
                data = s.recv(32768).decode('ascii', errors='ignore').lower()
            except:
                continue
            
            rssi_m  = re.search(r'rssi:\s*(\d+)', data)
            tx_m    = re.search(r'current_tx_rate:\s*([^\n\r]+)', data)
            nse_m   = re.search(r'noise:\s*([-\d]+)', data)
            temp_m  = re.search(r'thermal:\s*(\d+)', data)
            
            if rssi_m:
                rssi = int(rssi_m.group(1))
                tx_s = tx_m.group(1).strip().upper() if tx_m else "N/A"
                nse  = nse_m.group(1) if nse_m else "-110"
                temp = temp_m.group(1) if temp_m else "?"
                
                try:
                    dbm = int(nse) + rssi
                except:
                    dbm = "?"
                
                if rssi > PEAK: 
                    PEAK = rssi
                
                # Proportional Bar calculation
                bar_len = min(max(0, int((rssi / 50) * 40)), 40)
                colored_bar = get_colored_bar(bar_len)
                
                # Output formatting
                # Note: We don't use :<40 padding on {colored_bar} because 
                # the ANSI codes mess up Pythons string length calculation.
                output = (
                    f"\rRSSI:{rssi:2} ({dbm:>4} dBm) | PEAK:{PEAK:2} | "
                    f"NOISE:{nse:>4} | TEMP:{temp:>2}C | "
                    f"TX:{tx_s:<10} | [{colored_bar}]"
                )
                
                sys.stdout.write(output)
                sys.stdout.flush()

    except (socket.error, ConnectionResetError):
        sys.stdout.write("\n[!] Connection lost. Retrying...")
        sys.stdout.flush()
        time.sleep(2)
        fast_root_monitor()
    except KeyboardInterrupt:
        print(f"\n\n[*] Stopped. Final Peak: {PEAK}")
    finally:
        s.close()

if __name__ == "__main__":
    # os.system('') enables ANSI support on Windows 10+ terminals
    if sys.platform == "win32":
        os.system('')
    fast_root_monitor()
