import websocket
import time

def connect(ip):
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{ip}:81", timeout=3)
        print(f"Connected: {ip}")
        return ws
    except Exception as e:
        print(f"Failed to connect {ip}: {e}")
        return None

def send(ws, ip, command):
    if ws is None:
        print(f"  Skipping {ip} — not connected")
        return
    try:
        ws.send(command)
        print(f"  [{ip}] -> {command}")
    except Exception as e:
        print(f"  [{ip}] send failed: {e}")
        
ip1 = "172.27.153.139"
ip2 = "172.27.145.98"

ws1 = connect(ip1)
ws2 = connect(ip2)

try:
    while True:
        send(ws1, ip1, "buzz");  send(ws2, ip2, "pulse")
        time.sleep(3)

        send(ws1, ip1, "pulse"); send(ws2, ip2, "long")
        time.sleep(3)

        send(ws1, ip1, "long");  send(ws2, ip2, "idle")
        time.sleep(3)

        send(ws1, ip1, "idle");  send(ws2, ip2, "buzz")
        time.sleep(3)

finally:
    send(ws1, ip1, "idle")
    send(ws2, ip2, "idle")
    if ws1: ws1.close()
    if ws2: ws2.close()
    print("Done")
