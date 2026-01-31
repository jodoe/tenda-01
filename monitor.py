import socket
import time
import re
import sys
import os

# --- Configuration ---
# Initial values; HOST will be set by user input
USER = "root"      
PASS = "Fireitup"
PEAK = 0

# ANSI Color Codes
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"
CYAN = "\033[36m"

def get_colored_bar(size, total_width=40):
    """Generates a tri-color signal bar based on width."""
    bar_chars = ""
    for i in range(1, total_width + 1):
        if i <= size:
            if i <= 13:
                bar_chars += f"{RED}█{RESET}"
            elif i <= 26:
                bar_chars += f"{YELLOW}█{RESET}"
            else:
                bar_chars += f"{GREEN}█{RESET}"
        else:
            bar_chars += " "
    return bar_chars

def select_target():
    """Menu to select target device."""
    while True:
        print(f"\n{CYAN}--- Tenda O1 v1 Wireless Monitor Setup ---{RESET}")
        print("1) Access Point (192.168.2.1)")
        print("2) Client       (192.168.2.2)")
        choice = input(f"\nSelect target (1 or 2): ").strip()
        
        if choice == '1':
            return "192.168.2.1", "AP"
        elif choice == '2':
            return "192.168.2.2", "CLIENT"
        else:
            print(f"{RED}[!] Invalid choice. Please pick 1 or 2.{RESET}")

def fast_root_monitor(host, label):
    global PEAK
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5) 
    
    try:
        print(f"[*] Connecting to {label} at {host}...")
        s.connect((host, 23))
        
        s.sendall(b'\xff\xfd\x03\xff\xfb\x01') 
        time.sleep(0.5)
        s.sendall(f"{USER}\r\n".encode('ascii'))
        time.sleep(0.5)
        s.sendall(f"{PASS}\r\n".encode('ascii'))
        time.sleep(1.0) 
        
        print(f"[*] {label} Dashboard Active. Polling: 1.0s.")

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
                
                bar_len = min(max(0, int((rssi / 50) * 40)), 40)
                colored_bar = get_colored_bar(bar_len)
                
                output = (
                    f"\r{label} | RSSI:{rssi:2} ({dbm:>4} dBm) | PEAK:{PEAK:2} | "
                    f"TEMP:{temp:>2}C | TX:{tx_s:<10} | [{colored_bar}]"
                )
                
                sys.stdout.write(output)
                sys.stdout.flush()

    except (socket.error, ConnectionResetError):
        sys.stdout.write(f"\n{RED}[!] Connection lost. Retrying {host}...{RESET}")
        sys.stdout.flush()
        time.sleep(2)
        fast_root_monitor(host, label)
    except KeyboardInterrupt:
        print(f"\n\n[*] Stopped. Final Peak for {label}: {PEAK}")
    finally:
        s.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        os.system('')
    
    target_ip, target_label = select_target()
    fast_root_monitor(target_ip, target_label)
