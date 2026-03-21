import websocket
import time

ws = websocket.WebSocket()
ws.connect("ws://192.168.4.1:81")  # ESP32's IP

# Send a trigger
while (1):
    ws.send("buzz")
    print("yes")
    time.sleep(2)
    ws.send("stop")
    print("no")
    time.sleep(2)

ws.close()
