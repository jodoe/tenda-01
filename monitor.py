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
    s.settimeout(3)
    
    try:
        print(f"[*] Connecting to {HOST}...")
        s.connect((HOST, 23))
        
        # Standard Telnet handshake
        s.sendall(b'\xff\xfd\x03\xff\xfb\x01') 
        time.sleep(0.3)
        s.sendall(f"{USER}\r\n".encode('ascii'))
        time.sleep(0.3)
        s.sendall(f"{PASS}\r\n".encode('ascii'))
        time.sleep(0.5) 
        
        print(f"[*] Monitor Active. Target: {HOST}")

        while True:
            s.sendall(b"cat /proc/wlan0/sta_info\n")
            time.sleep(0.2) 
            
            s.setblocking(False)
            try:
                data = s.recv(16384).decode('ascii', errors='ignore').lower()
            except:
                continue
            
            rssi_m = re.search(r'rssi:\s*(\d+)', data)
            tx_m   = re.search(r'current_tx_rate:\s*([^\n\r]+)', data)
            rx_m   = re.search(r'current_rx_rate:\s*([^\n\r]+)', data)
            
            if rssi_m:
                rssi = int(rssi_m.group(1))
                tx_s = tx_m.group(1).strip().upper() if tx_m else "N/A"
                rx_s = rx_m.group(1).strip().upper() if rx_m else "N/A"
                
                if rssi > PEAK: 
                    PEAK = rssi
                
                # Math for proportional display (RSSI 50 = 100%)
                max_signal = 50 
                bar_total_width = 80 
                percent = rssi / max_signal
                bar_filled = int(percent * bar_total_width)
                bar_size = min(max(0, bar_filled), bar_total_width)
                bar = "█" * bar_size
                
                output = (
                    f"\rSIG RSSI:{rssi:2} (PK:{PEAK:2}) | "
                    f"TX:{tx_s:<10} | "
                    f"RX:{rx_s:<10} | "
                    f"[{bar:<{bar_total_width}}] {int(percent*100):3}% "
                )
                
                sys.stdout.write(output)
                sys.stdout.flush()

    except KeyboardInterrupt:
        print(f"\n\n[*] Stopped. Final Peak: {PEAK}")
    except Exception as e:
        print(f"\n[!] Error: {e}")
        time.sleep(2)
        fast_root_monitor()
    finally:
        s.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        os.system('')
    fast_root_monitor()
