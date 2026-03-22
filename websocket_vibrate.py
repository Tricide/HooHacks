import websocket
import time

ws = websocket.WebSocket()
ws.connect("ws://172.27.131.171:81")
#ws.connect("ws://172.27.153.139:81")  # ESP32's IP

#ws2 = websocket.WebSocket()
#ws2.connect("ws://172.27.131.171:81")

# Send a trigger
while (1):
    ws.send("buzz")
    print("buzz")
    #ws2.send("pulse")
    print("pulse")
    time.sleep(3)
    
    ws.send("pulse")
    print("pulse")
    #ws2.send("long")
    print("long")
    time.sleep(3)
    
    ws.send("long")
    print("long")
    #ws2.send("idle")
    print("idle")
    time.sleep(3)
    
    ws.send("idle")
    print("idle")
    #ws2.send("buzz")
    print("buzz")
    time.sleep(3)

ws.close()
