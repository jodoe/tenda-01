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
SMOOTH_RETRY = 0.0  # Global tracker for the retry smoothing filter

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

def get_single_bar(val, total_width=30):
    """Generates an independent tracking bar for a single polarisation path."""
    scaled = min(max(0, val), 50) 
    done = int((scaled / 50) * total_width)
    bar = ""
    for i in range(total_width):
        if i < done:
            if i < (total_width * 0.33): bar += RED + "█" + RESET
            elif i < (total_width * 0.66): bar += YELLOW + "█" + RESET
            else: bar += GREEN + "█" + RESET
        else:
            bar += "░"
    return bar

def monitor_logic():
    global PEAK, SMOOTH_RETRY
    first_run = True
    
    while STATE["running"]:
        if STATE["ip"] is None:
            time.sleep(0.1)
            continue

        host = STATE["ip"]
        label = STATE["label"]
        PEAK = 0
        SMOOTH_RETRY = 0.0 # Reset smoothing factor when switching targets
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        
        try:
            sys.stdout.write(f"\r{YELLOW}[*] Connecting to {label} ({host})...{' '*60}{RESET}\n")
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
                
                # ADVANCED REGEX: Extracts average RSSI, Chain A (Vertical), and Chain B (Horizontal)
                rssi_m = re.search(r'rssi:\s*(\d+)\s*\(\s*(\d+)\s+(\d+)\s*\)', data)
                tx_m   = re.search(r'current_tx_rate:\s*([^\n\r]+)', data)
                rx_m   = re.search(r'current_rx_rate:\s*([^\n\r]+)', data)
                nse_m  = re.search(r'noise:\s*([-\d]+)', data)
                temp_m = re.search(r'thermal:\s*(\d+)', data) 
                chan_m = re.search(r'dot11channel:\s*(\d+)', data)
                sq_m   = re.search(r'sq:\s*(\d+)', data)
                cca_m  = re.search(r'cca:\s*(\d+)', data)
                retry_m = re.search(r'tx_retry_ratio:\s*(\d+)', data)
                
                if rssi_m:
                    avg_rssi = int(rssi_m.group(1))
                    chain_v  = int(rssi_m.group(2)) # Chain A = Vertical Polarisation
                    chain_h  = int(rssi_m.group(3)) # Chain B = Horizontal Polarisation
                    
                    tx_s_raw = tx_m.group(1).strip().upper() if tx_m else "N/A"
                    rx_s_raw = rx_m.group(1).strip().upper() if rx_m else "N/A"
                    nse  = nse_m.group(1) if nse_m else "-110"
                    temp = temp_m.group(1) if temp_m else "?"
                    chan = chan_m.group(1) if chan_m else "?"
                    sq   = sq_m.group(1) if sq_m else "0"
                    cca  = cca_m.group(1) if cca_m else "0"
                    raw_retry = int(retry_m.group(1)) if retry_m else 0
                    
                    # EXPONENTIAL MOVING AVERAGE (EMA) FILTER
                    if SMOOTH_RETRY == 0.0:
                        SMOOTH_RETRY = float(raw_retry)
                    else:
                        SMOOTH_RETRY = (SMOOTH_RETRY * 0.85) + (raw_retry * 0.15)
                    display_retry = int(SMOOTH_RETRY)
                    
                    try: dbm = int(nse) + avg_rssi
                    except: dbm = "?"
                    if avg_rssi > PEAK: PEAK = avg_rssi
                    
                    # DUAL STREAM (2T2R) DETECTION LOGIC
                    mimo_match = re.search(r'MCS(8|9|10|11|12|13|14|15)\b', tx_s_raw)
                    if mimo_match:
                        mimo_status = f"{GREEN}[2T2R Dual]{RESET}"
                    else:
                        mimo_status = f"{YELLOW}[1T1R Single]{RESET}"
                    
                    # Format rate data string components cleanly
                    tx_clean = tx_s_raw.split() if " " in tx_s_raw else tx_s_raw
                    rx_clean = rx_s_raw.split() if " " in rx_s_raw else rx_s_raw
                    
                    # Process coloring tags
                    cca_i = int(cca)
                    c_clr = RED if cca_i > 1500 else (YELLOW if cca_i > 800 else RESET)
                    t_clr = YELLOW if temp != "?" and int(temp) > 55 else RESET
                    r_clr = RED if display_retry > 40 else (YELLOW if display_retry > 15 else GREEN)

                    label_tag = f"{CYAN}[{label}]{RESET}"
                    
                    # Generate independent graphical meters
                    bar_v = get_single_bar(chain_v, total_width=30)
                    bar_h = get_single_bar(chain_h, total_width=30)
                    
                    if not first_run:
                        sys.stdout.write("\033[F\033[F\033[F\033[F")
                    first_run = False
                    
                    # Line 1: Primary Hardware Configurations
                    line1 = (f"{label_tag} {MAGENTA}CH:{chan}{RESET} | "
                             f"Avg_RSSI:{avg_rssi}({dbm}dBm) Peak:{PEAK} | Mode:{mimo_status}")
                    
                    # Line 2: Link Performance & Error Telemetry (Moved to its own line)
                    line2 = (f" └──> Performance | "
                             f"Retry:{r_clr}{display_retry}%{RESET} | CCA:{c_clr}{cca}{RESET} | "
                             f"TX:{tx_clean} RX:{rx_clean} | T:{t_clr}{temp}C{RESET}")
                    
                    # Line 3: Isolated Vertical Polarisation Gauges
                    line3 = f"      ├──> V_Polarisation : {bar_v} ({chain_v})"
                    
                    # Line 4: Isolated Horizontal Polarisation Gauges
                    line4 = f"      └──> H_Polarisation : {bar_h} ({chain_h})"
                    
                    # Output all lines cleanly to terminal streams
                    sys.stdout.write(line1 + "\033[K\n")
                    sys.stdout.write(line2 + "\033[K\n")
                    sys.stdout.write(line3 + "\033[K\n")
                    sys.stdout.write(line4 + "\033[K\n")
                    sys.stdout.flush()

        except Exception as e:
            first_run = True # Reset multi-line cursor tracking on error
            sys.stdout.write(f"\n{RED}[!] Error: {str(e)[:30]}. Reconnecting...{RESET}\n")
            time.sleep(2)
        finally:
            s.close()

def main():
    if sys.platform == "win32":
        os.system('') 
    
    print(f"{CYAN}--- Tenda 01 Alignment Dashboard ---{RESET}")
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

    thread = threading.Thread(target=monitor_logic, daemon=True)
    thread.start()

    print(f"\n{GREEN}[*] Real-Time Alignment Dashboard Initialised.{RESET}")
    print(f"Hotkeys: {YELLOW}1{RESET}=AP, {YELLOW}2{RESET}=Client, {RED}Ctrl+C{RESET}=Exit\n\n\n\n") # 4 lines padding for initial cursor frame wrap

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
        print("\n\nExiting Layout Engine...")

if __name__ == "__main__":
    main()

