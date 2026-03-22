import pyzed.sl as sl
import math
import cv2
import numpy as np
import websocket
import time
from collections import deque
import requests

# --- CONFIGURATION ---
SWAY_THRESHOLD = 180 
BUZZ_COOLDOWN = 1.5   
AWS_ENDPOINT = "http://3.223.106.18/presentationCoach/data/data_transmission.php"

ip1, ip2 = "172.27.153.139", "172.27.145.98"

# --- CONNECTIONS ---
def connect(ip):
    try:
        ws = websocket.WebSocket()
        ws.connect(f"ws://{ip}:81", timeout=3)
        print(f"Connected: {ip}")
        return ws
    except Exception as e:
        print(f"Failed {ip}: {e}"); return None

def send(ws, ip, command):
    if ws:
        try: ws.send(command)
        except: print(f"Lost connection to {ip}")

ws1, ws2 = connect(ip1), connect(ip2)

# --- TRACKING HELPERS ---
BODY_38_BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 10), (10, 12), (12, 14), (14, 16), 
                 (4, 11), (11, 13), (13, 15), (15, 17), (0, 18), (18, 20), (20, 22), 
                 (0, 19), (19, 21), (21, 23)]

def is_arms_crossed(kp): return math.dist(kp[16], kp[15]) < 200 and math.dist(kp[17], kp[14]) < 200
def is_hands_in_pockets(kp): return math.dist(kp[16], kp[18]) < 150 and math.dist(kp[17], kp[19]) < 150
def check_sway(hist): return (max(hist) - min(hist)) > SWAY_THRESHOLD if len(hist) >= 30 else False

def main():
    zed = sl.Camera()
    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.HD720
    init.coordinate_units = sl.UNIT.MILLIMETER
    if zed.open(init) != sl.ERROR_CODE.SUCCESS: return

    zed.enable_positional_tracking(sl.PositionalTrackingParameters())
    body_p = sl.BodyTrackingParameters()
    body_p.enable_body_fitting = True
    body_p.body_format = sl.BODY_FORMAT.BODY_38
    zed.enable_body_tracking(body_p)

    bodies, image_zed = sl.Bodies(), sl.Mat()
    sway_history, last_states, last_buzz_times = {}, {}, {}

    while True:
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            zed.retrieve_bodies(bodies, sl.BodyTrackingRuntimeParameters())
            frame = image_zed.get_data()
            curr_t = time.time()

            for body in bodies.body_list:
                if body.tracking_state == sl.OBJECT_TRACKING_STATE.OK:
                    kp3, kp2 = body.keypoint, body.keypoint_2d
                    
                    # 1. Init user data
                    bid = body.id
                    if bid not in sway_history:
                        sway_history[bid] = deque(maxlen=45)
                        last_states[bid], last_buzz_times[bid] = "stop", 0

                    # 2. Logic
                    sway_history[bid].append(kp3[3][0])
                    is_bad = is_arms_crossed(kp3) or is_hands_in_pockets(kp3) or check_sway(sway_history[bid])
                    
                    state = "buzz" if is_bad or (curr_t - last_buzz_times[bid] < BUZZ_COOLDOWN) else "idle"
                    if is_bad: last_buzz_times[bid] = curr_t

                    # 3. Draw Skeleton (DEBUG)
                    # Red if Buzzing, Green if Idle
                    color = (0, 0, 255) if state == "buzz" else (0, 255, 0)
                    
                    for bone in BODY_38_BONES:
                        p1, p2 = kp2[bone[0]], kp2[bone[1]]
                        if np.isfinite(p1).all() and np.isfinite(p2).all():
                            cv2.line(frame, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), color, 2)

                    # 4. Networking
                    if state != last_states[bid]:
                        send(ws1 if bid == 0 else ws2, ip1 if bid == 0 else ip2, state)
                        try:
                            requests.post(AWS_ENDPOINT, json={"event": state, "body_id": bid, "swayval": float(kp3[3][0])}, timeout=0.05)
                        except: pass
                        last_states[bid] = state

            cv2.imshow("ZED Debug Monitor", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

    zed.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()