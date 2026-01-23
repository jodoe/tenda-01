import telnetlib
import time
import os

# Configuration
HOST = "192.168.2.1"  # Your O1 IP
USER = "root"        # Or root
PASSWORD = "Fireitup"
COMMAND = "cat /proc/wlan0/sta_info"

def get_stats():
    try:
        # Connect to Tenda O1
        tn = telnetlib.Telnet(HOST, timeout=5)
        
        # Handle Login
        tn.read_until(b"login: ", timeout=2)
        tn.write(USER.encode('ascii') + b"\n")
        
        tn.read_until(b"Password: ", timeout=2)
        tn.write(PASSWORD.encode('ascii') + b"\n")
        
        # Run the command
        tn.write(COMMAND.encode('ascii') + b"\n")
        tn.write(b"exit\n") # Close session after command

        output = tn.read_all().decode('ascii')
        return output
    except Exception as e:
        return f"Error: {e}"

def parse_and_display(raw_data):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("="*40)
    print(f" TENDA O1 LIVE MONITOR - {HOST}")
    print("="*40)
    
    # Filter for the lines you found
    for line in raw_data.split('\n'):
        if any(key in line.lower() for key in ["rssi", "sq", "noise"]):
            print(f" [>] {line.strip()}")
    
    print("="*40)
    print(" Press Ctrl+C to stop")

while True:
    data = get_stats()
    parse_and_display(data)
    time.sleep(1) # Refresh rate
