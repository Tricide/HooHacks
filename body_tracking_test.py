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
WS_URL = "ws://172.27.153.139:81"
SWAY_THRESHOLD = 180  # mm
BUZZ_COOLDOWN = 1.5   # Seconds the buzzer stays on once triggered
AWS_ENDPOINT = "http://3.223.106.18/presentationCoach/data/data_transmission.php"
# ---------------------

try:
    ws = websocket.WebSocket()
    ws.connect(WS_URL)
    print(f"Connected to ESP32 at {WS_URL}")
except Exception as e:
    print(f"Could not connect to WebSocket: {e}")
    # We'll continue so you can still test the ZED logic without the ESP
    ws = None

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
    last_sent_state = "stop"
    last_buzz_time = 0 

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
                        
                        # Sway update
                        if body.id not in sway_history:
                            sway_history[body.id] = deque(maxlen=45)
                        sway_history[body.id].append(kp_3d[3][0])

                        # Logic check
                        # --- SKELETON RENDERING ---
                        # Get 2D keypoints for drawing
                        kp_2d = body.keypoint_2d

                        # Draw Bones
                        for part in BODY_38_BONES:
                            kp_a = kp_2d[part[0]]
                            kp_b = kp_2d[part[1]]
                            color = (255,255,255)
                            # Check if keypoints are valid/visible before drawing
                            if np.isfinite(kp_a).all() and np.isfinite(kp_b).all():
                                pt1 = (int(kp_a[0]), int(kp_a[1]))
                                pt2 = (int(kp_b[0]), int(kp_b[1]))
                                cv2.line(image_ocv, pt1, pt2, color, 2)

                        # Draw Joints (optional but helpful)
                        for kp in kp_2d:
                            if np.isfinite(kp).all():
                                cv2.circle(image_ocv, (int(kp[0]), int(kp[1])), 3, (255, 255, 255), -1)
                        crossed = is_arms_crossed(kp_3d)
                        pockets = is_hands_in_pockets(kp_3d)
                        swaying = check_sway(sway_history[body.id])

                        if crossed or pockets or swaying:
                            current_bad_posture = True
                        
                        # Drawing (Optional: keep for debugging)
                        color = (0, 0, 255) if current_bad_posture else (0, 255, 0)
                        cv2.putText(image_ocv, f"ID {body.id}: {'BAD' if current_bad_posture else 'OK'}", 
                                    (int(body.bounding_box_2d[0][0]), int(body.bounding_box_2d[0][1]) - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                # --- COOLDOWN & WEBSOCKET LOGIC ---
                desired_state = "stop"
                
                # If we detect bad posture, we want to buzz
                if current_bad_posture:
                    desired_state = "buzz"
                    last_buzz_time = current_time
                
                # If we are in the cooldown period, force the state to stay "buzz"
                elif (current_time - last_buzz_time) < BUZZ_COOLDOWN:
                    desired_state = "buzz"

                # Send only on change
                if desired_state != last_sent_state:
                    if ws:
                        try:
                            ws.send(desired_state)
                            print(f"Action: {desired_state.upper()}")
                        except:
                            print(f"ESP32 Connection Lost: {e}")
                    try:
                        payload = {
                            "event": desired_state,
                            "timestamp": time.time(),
                            "swayval": float(kp_3d[3][0]) if len (kp_3d) > 3 else 0
                        }
                        print("Sending data")
                        requests.post(AWS_ENDPOINT, json=payload, timeout=0.1)
                        print("Data sent")
                    except requests.exceptions.RequestException:
                        print("Cloud logging failed")
                    last_sent_state = desired_state


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
        if ws: ws.close()
        zed.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()