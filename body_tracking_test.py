import pyzed.sl as sl
import math
import cv2
import numpy as np
import websocket
from collections import deque

## define connection esp
ws = websocket.WebSocket()
ws.connect("ws://192.168.4.1:81")

# --- Detection Logic ---

def is_arms_crossed(kp_3d):
    l_wrist, r_wrist = kp_3d[16], kp_3d[17]
    l_elbow, r_elbow = kp_3d[14], kp_3d[15]
    return math.dist(l_wrist, r_elbow) < 200 and math.dist(r_wrist, l_elbow) < 200

def is_hands_in_pockets(kp_3d):
    l_wrist, r_wrist = kp_3d[16], kp_3d[17]
    l_hip, r_hip = kp_3d[18], kp_3d[19]
    return math.dist(l_wrist, l_hip) < 150 and math.dist(r_wrist, r_hip) < 150

def check_sway(history, threshold=180):
    if len(history) < 30: return False
    return (max(history) - min(history)) > threshold

BODY_38_BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 10), (10, 12), (12, 14), (14, 16), (4, 11), (11, 13), (13, 15), (15, 17), (0, 18), (18, 20), (20, 22), (0, 19), (19, 21), (21, 23)]

def main():
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS: exit(1)

    zed.enable_positional_tracking(sl.PositionalTrackingParameters())
    body_param = sl.BodyTrackingParameters()
    body_param.enable_body_fitting = True  
    body_param.body_format = sl.BODY_FORMAT.BODY_38
    zed.enable_body_tracking(body_param)

    body_runtime_param = sl.BodyTrackingRuntimeParameters()
    bodies = sl.Bodies()
    image_zed = sl.Mat()

    sway_history = {}
    
    # --- NEW: State Tracking ---
    # Stores the last message sent for each person: {id: "stop" or "buzz"}
    last_sent_state = {} 

    print("Optimized Tracking Active...")

    while True:
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            zed.retrieve_bodies(bodies, body_runtime_param)
            image_ocv = image_zed.get_data()

            current_ids = [b.id for b in bodies.body_list]
            # Cleanup old IDs
            sway_history = {id: h for id, h in sway_history.items() if id in current_ids}
            last_sent_state = {id: s for id, s in last_sent_state.items() if id in current_ids}

            for body in bodies.body_list:
                if body.keypoint.size > 0 and body.tracking_state == sl.OBJECT_TRACKING_STATE.OK:
                    kp_3d = body.keypoint
                    
                    # 1. Update Sway History
                    if body.id not in sway_history:
                        sway_history[body.id] = deque(maxlen=45)
                    sway_history[body.id].append(kp_3d[3][0])

                    # 2. Determine Current Condition
                    bad_posture = is_arms_crossed(kp_3d) or is_hands_in_pockets(kp_3d) or check_sway(sway_history[body.id])
                    current_msg = "buzz" if bad_posture else "stop"

                    # 3. ONLY Send if the state has changed
                    if body.id not in last_sent_state or last_sent_state[body.id] != current_msg:
                        try:
                            ws.send(current_msg)
                            last_sent_state[body.id] = current_msg
                            print(f"Sent {current_msg} for Person {body.id}")
                        except Exception as e:
                            print(f"WS Error: {e}")

                    # --- Rendering ---
                    gesture_text = "ALERT" if bad_posture else "OK"
                    color = (0, 0, 255) if bad_posture else (0, 255, 0)
                    
                    kp_2d = body.keypoint_2d
                    for bone in BODY_38_BONES:
                        pt1, pt2 = kp_2d[bone[0]], kp_2d[bone[1]]
                        if not (math.isnan(pt1[0]) or math.isnan(pt2[0])):
                            cv2.line(image_ocv, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (255, 255, 255), 2)

                    if not math.isnan(body.bounding_box_2d[0][0]):
                        box = body.bounding_box_2d
                        cv2.putText(image_ocv, f"ID {body.id}: {gesture_text}", (int(box[0][0]), int(box[0][1]) - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            cv2.imshow("ZED Feedback", image_ocv)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

    zed.close()

if __name__ == "__main__":
    main()