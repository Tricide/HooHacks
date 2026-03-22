import pyzed.sl as sl
import math
import cv2
import numpy as np
import websocket
import time
from collections import deque
import requests
import json

# --- CONFIGURATION ---
SWAY_THRESHOLD = 180  # mm
BUZZ_COOLDOWN = 1.5   # Seconds the buzzer stays on once triggered
AWS_ENDPOINT = "http://3.223.106.18/presentationCoach/data/data_transmission.php"
# ---------------------


## Adding networking

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

def is_arms_crossed(kp_3d):
    return math.dist(kp_3d[16], kp_3d[15]) < 200 and math.dist(kp_3d[17], kp_3d[14]) < 200

def is_hands_in_pockets(kp_3d):
    return math.dist(kp_3d[16], kp_3d[18]) < 150 and math.dist(kp_3d[17], kp_3d[19]) < 150

def check_sway(history):
    if len(history) < 30: return False
    return (max(history) - min(history)) > SWAY_THRESHOLD

BODY_38_BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 10), (10, 12), (12, 14), (14, 16), (4, 11), (11, 13), (13, 15), (15, 17), (0, 18), (18, 20), (20, 22), (0, 19), (19, 21), (21, 23)]

def main():
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open ZED")
        return

    zed.enable_positional_tracking(sl.PositionalTrackingParameters())
    body_param = sl.BodyTrackingParameters()
    body_param.enable_body_fitting = True  
    body_param.body_format = sl.BODY_FORMAT.BODY_38
    zed.enable_body_tracking(body_param)

    bodies = sl.Bodies()
    image_zed = sl.Mat()
    
    sway_history = {}
    last_states = {}
    last_buzz_time = {}

    print("\n[RUNNING] Click on the ZED Video Window and press 'q' to quit.")

    try:
        while True:
            if zed.grab() == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image_zed, sl.VIEW.LEFT)
                zed.retrieve_bodies(bodies, sl.BodyTrackingRuntimeParameters())
                image_ocv = image_zed.get_data()

                current_bad_posture = False
                current_time = time.time()

                for body in bodies.body_list:
                    if body.keypoint.size > 0 and body.tracking_state == sl.OBJECT_TRACKING_STATE.OK:
                        kp_3d = body.keypoint
                        kp_2d = body.keypoint_2d
                        
                        # 1. Update Sway History
                        if body.id not in sway_history:
                            sway_history[body.id] = deque(maxlen=45)
                        sway_history[body.id].append(kp_3d[3][0])

                        # 2. Setup tracking for this specific person's last state
                        if body.id not in last_states: last_states[body.id] = "idle"
                        if body.id not in last_buzz_time:
                            last_buzz_time[body.id] = 0

                        # 3. Posture Logic
                        crossed = is_arms_crossed(kp_3d)
                        pockets = is_hands_in_pockets(kp_3d)
                        swaying = check_sway(sway_history[body.id])
                        
                        body_bad = crossed or pockets or swaying
                        
                        # Determine state for THIS body
                        this_state = "buzz" if body_bad else "idle"
                        if not body_bad and (current_time - last_buzz_time[body.id]) < BUZZ_COOLDOWN:
                            this_state = "buzz"
                        if body_bad: last_buzz_time = current_time

                        # 4. SEND TO CORRECT ESP32 (Using your custom send function)
                        if this_state != last_states[body.id]:
                            if body.id == 0:
                                send(ws1, ip1, this_state)
                            elif body.id == 1:
                                send(ws2, ip2, this_state)

                            # --- CLOUD LOGGING ---
                            try:
                                payload = {
                                    "event": this_state,
                                    "body_id": body.id,
                                    "timestamp": time.time(),
                                    "swayval": float(kp_3d[3][0])
                                }
                                requests.post(AWS_ENDPOINT, json=payload, timeout=0.05)
                            except:
                                pass # Keep frame rate high if AWS fails
                            
                            last_states[body.id] = this_state


                    # --- RENDER & EXIT ---
                    cv2.imshow("ZED Monitor", image_ocv)
                
                # Fix: Check for 'q' OR the window 'X' button being clicked
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or cv2.getWindowProperty("ZED Monitor", cv2.WND_PROP_VISIBLE) < 1:
                    break

    except KeyboardInterrupt:
        print("\nInterrupted by user in terminal.")
    finally:
        print("Closing resources...")
        if ws1: ws1.close()
        if ws2: ws2.close()
        zed.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()