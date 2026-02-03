import socket
import time
import re
import sys
import os
import threading

# --- Configuration ---
USER = "root"      
PASS = "Fireitup"
PEAK = 0
STATE = {
    "ip": None,
    "label": None,
    "running": True
}

# ANSI Color Codes
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
RESET = "\033[0m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"

def get_simple_bar(size, total_width=30):
    """Generates a reliable tricolor bar."""
    done = int(size)
    bar = ""
    for i in range(total_width):
        if i < done:
            if i < 10: bar += RED + "█" + RESET
            elif i < 20: bar += YELLOW + "█" + RESET
            else: bar += GREEN + "█" + RESET
        else:
            bar += "░" # Background character for visibility
    return bar

def monitor_logic():
    global PEAK
    while STATE["running"]:
        if STATE["ip"] is None:
            time.sleep(0.1)
            continue

        host = STATE["ip"]
        label = STATE["label"]
        PEAK = 0
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        
        try:
            sys.stdout.write(f"\r{YELLOW}[*] Connecting to {label} ({host})...{' '*40}{RESET}\r")
            sys.stdout.flush()
            s.connect((host, 23))
            
            s.sendall(b'\xff\xfd\x03\xff\xfb\x01') 
            time.sleep(0.5)
            s.sendall(f"{USER}\r\n".encode('ascii'))
            time.sleep(0.2)
            s.sendall(f"{PASS}\r\n".encode('ascii'))
            time.sleep(0.5)

            while STATE["running"] and STATE["ip"] == host:
                s.sendall(b"cat /proc/wlan0/sta_info /proc/wlan0/mib_all\n")
                time.sleep(0.8) 
                
                s.setblocking(False)
                try:
                    data = s.recv(65536).decode('ascii', errors='ignore').lower()
                except: continue
                
                rssi_m = re.search(r'rssi:\s*(\d+)', data)
                tx_m   = re.search(r'current_tx_rate:\s*([^\n\r]+)', data)
                nse_m  = re.search(r'noise:\s*([-\d]+)', data)
                temp_m = re.search(r'thermal:\s*(\d+)', data) 
                chan_m = re.search(r'dot11channel:\s*(\d+)', data)
                sq_m   = re.search(r'sq:\s*(\d+)', data)
                cca_m  = re.search(r'cca:\s*(\d+)', data)
                
                if rssi_m:
                    rssi = int(rssi_m.group(1))
                    tx_s = tx_m.group(1).strip().upper() if tx_m else "N/A"
                    nse  = nse_m.group(1) if nse_m else "-110"
                    temp = temp_m.group(1) if temp_m else "?"
                    chan = chan_m.group(1) if chan_m else "?"
                    sq   = sq_m.group(1) if sq_m else "0"
                    cca  = cca_m.group(1) if cca_m else "0"
                    
                    try: dbm = int(nse) + rssi
                    except: dbm = "?"
                    if rssi > PEAK: PEAK = rssi
                    
                    # Bar Logic (Scaled for 2.4GHz typical values)
                    bar_max = 30
                    scaled_rssi = min(max(0, rssi), 50) 
                    bar_len = int((scaled_rssi / 50) * bar_max)
                    colored_bar = get_simple_bar(bar_len, bar_max)
                    
                    cca_i = int(cca)
                    c_clr = RED if cca_i > 500 else (YELLOW if cca_i > 200 else RESET)
                    t_clr = YELLOW if temp != "?" and int(temp) > 55 else RESET

                    label_tag = f"{CYAN}[{label}]{RESET}"
                    output = (f"\r{label_tag} {MAGENTA}CH:{chan}{RESET} | "
                              f"RSSI:{rssi}({dbm}dBm) | Peak:{PEAK} | "
                              f"SQ:{sq}% | CCA:{c_clr}{cca}{RESET} | "
                              f"T:{t_clr}{temp}C{RESET} | "
                              f"TX:{tx_s[:8]} | {colored_bar}")
                    
                    sys.stdout.write(output)
                    sys.stdout.write("\033[K") 
                    sys.stdout.flush()

        except Exception:
            sys.stdout.write(f"\r{RED}[!] Connection error. Waiting for target...{' '*20}{RESET}\r")
            time.sleep(2)
        finally:
            s.close()

def main():
    if sys.platform == "win32":
        os.system('') 
    
    # Initial menu before thread starts
    print(f"{CYAN}--- Tenda Diagnostic Monitor ---{RESET}")
    print("Select starting device:")
    print("1) Access Point (192.168.2.1)")
    print("2) Client       (192.168.2.2)")
    
    while True:
        choice = input(f"\nChoice: ").strip()
        if choice == '1':
            STATE["ip"], STATE["label"] = "192.168.2.1", "AP"
            break
        elif choice == '2':
            STATE["ip"], STATE["label"] = "192.168.2.2", "CLIENT"
            break
        else:
            print(f"{RED}Invalid. Press 1 or 2.{RESET}")

    # Start the monitor thread now that target is selected
    thread = threading.Thread(target=monitor_logic, daemon=True)
    thread.start()

    print(f"\n{GREEN}[*] Monitor Started.{RESET}")
    print(f"Hotkeys: {YELLOW}1{RESET}=AP, {YELLOW}2{RESET}=Client, {RED}Ctrl+C{RESET}=Exit\n")

    try:
        if os.name == 'nt':
            import msvcrt
            while True:
                if msvcrt.kbhit():
                    k = msvcrt.getch().decode('utf-8')
                    if k == '1': STATE["ip"], STATE["label"] = "192.168.2.1", "AP"
                    if k == '2': STATE["ip"], STATE["label"] = "192.168.2.2", "CLIENT"
                time.sleep(0.1)
        else:
            import tty, termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                while True:
                    k = sys.stdin.read(1)
                    if k == '1': STATE["ip"], STATE["label"] = "192.168.2.1", "AP"
                    if k == '2': STATE["ip"], STATE["label"] = "192.168.2.2", "CLIENT"
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except KeyboardInterrupt:
        STATE["running"] = False
        print("\n\nExiting...")

if __name__ == "__main__":
    main()
