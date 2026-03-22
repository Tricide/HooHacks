### THIS DOES NOT WORK

import time
import websocket
from zeroconf import ServiceBrowser, Zeroconf

# --- Discovery ---
discovered = {}

class HapticListener:
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info:
            ip = ".".join(str(b) for b in info.addresses[0])
            discovered[name] = f"ws://{ip}:81"
            print(f"  Found: {name} @ {ip}")

    def remove_service(self, zeroconf, type, name):
        discovered.pop(name, None)
        print(f"  Lost: {name}")

    def update_service(self, zeroconf, type, name):
        pass

def discover_esps(timeout=5):
    print(f"Scanning for ESPs ({timeout}s)...")
    zeroconf = Zeroconf()
    ServiceBrowser(zeroconf, "_haptic._tcp.local.", HapticListener())
    time.sleep(timeout)
    zeroconf.close()
    return dict(discovered)

# --- Connections ---
connections = {}

def connect_all():
    esps = discover_esps()
    if not esps:
        print("No ESPs found!")
        return
    for name, url in esps.items():
        try:
            ws = websocket.WebSocket()
            ws.connect(url, timeout=3)
            connections[name] = ws
            print(f"Connected: {name}")
        except Exception as e:
            print(f"Failed to connect {name}: {e}")

def disconnect_all():
    for name, ws in connections.items():
        try:
            ws.close()
        except:
            pass
    print("All disconnected")

# --- Send ---
def send(name, command):
    if name in connections:
        try:
            connections[name].send(command)
            print(f"  [{name}] -> {command}")
        except Exception as e:
            print(f"  Send failed {name}: {e}")
    else:
        print(f"  No connection: {name}")

def send_all(command):
    print(f"Sending '{command}' to all ({len(connections)} ESP(s))")
    for name in connections:
        send(name, command)

def send_index(index, command):
    """Send to a specific ESP by index (0, 1, 2...)"""
    names = list(connections.keys())
    if index < len(names):
        send(names[index], command)
    else:
        print(f"No ESP at index {index}")

# -------------------------------------------------------

if __name__ == "__main__":
    connect_all()

    if not connections:
        print("No ESPs connected. Exiting.")
        exit()

    print(f"\n{len(connections)} ESP(s) online: {list(connections.keys())}\n")

    try:
        # Example sequence — edit this to your needs
        send_all("buzz")
        time.sleep(3)

        send_all("pulse")
        time.sleep(3)

        send_all("long")
        time.sleep(4)

        send_all("continuous")
        time.sleep(3)

        send_all("idle")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        send_all("idle")
        disconnect_all()