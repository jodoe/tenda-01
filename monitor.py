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
            # Polling only the essential files
            s.sendall(b"cat /proc/wlan0/sta_info /proc/wlan0/mib_all\n")
            
            # 1.0 Second Polling - Very stable for the hardware
            time.sleep(1.0) 
            
            s.setblocking(False)
            try:
                data = s.recv(32768).decode('ascii', errors='ignore').lower()
            except:
                continue
            
            # Parsing logic
            rssi_m  = re.search(r'rssi:\s*(\d+)', data)
            tx_m    = re.search(r'current_tx_rate:\s*([^\n\r]+)', data)
            nse_m   = re.search(r'noise:\s*([-\d]+)', data)
            temp_m  = re.search(r'thermal:\s*(\d+)', data)
            
            if rssi_m:
                rssi = int(rssi_m.group(1))
                tx_s = tx_m.group(1).strip().upper() if tx_m else "N/A"
                nse  = nse_m.group(1) if nse_m else "-110" # Default floor if missing
                temp = temp_m.group(1) if temp_m else "?"
                
                # dBm Calculation: Noise Floor + RSSI
                try:
                    dbm = int(nse) + rssi
                except:
                    dbm = "?"
                
                if rssi > PEAK: 
                    PEAK = rssi
                
                # Proportional Bar (RSSI 50 = 100%)
                bar_size = min(max(0, int((rssi / 50) * 40)), 40)
                bar = "█" * bar_size
                
                # Updated Clean Display
                output = (
                    f"\rRSSI:{rssi:2} ({dbm:>4} dBm) | PEAK:{PEAK:2} | "
                    f"NOISE:{nse:>4} | TEMP:{temp:>2}C | "
                    f"TX:{tx_s:<10} | [{bar:<40}]"
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
    if sys.platform == "win32":
        os.system('')
    fast_root_monitor()
