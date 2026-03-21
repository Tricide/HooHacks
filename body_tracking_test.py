import pyzed.sl as sl
import math
import cv2
import numpy as np

# Updated indices for BODY_38
# Wrist: L=16, R=17 | Elbow: L=14, R=15 | Hip: L=18, R=19
def is_arms_crossed(left_hand, right_hand, left_elbow, right_elbow):
    dist_l_wrist_r_elbow = math.dist(left_hand, right_elbow)
    dist_r_wrist_l_elbow = math.dist(right_hand, left_elbow)
    return dist_l_wrist_r_elbow < 200 and dist_r_wrist_l_elbow < 200

def is_hands_in_pockets(left_hand, right_hand, left_hip, right_hip):
    dist_l_pocket = math.dist(left_hand, left_hip)
    dist_r_pocket = math.dist(right_hand, right_hip)
    return dist_l_pocket < 150 and dist_r_pocket < 150

# Skeletal map for BODY_38
BODY_38_BONES = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # Spine
    (4, 5), (5, 6), (5, 7), (6, 8), (7, 9),  # Head/Face
    (4, 10), (10, 12), (12, 14), (14, 16),   # Left Arm
    (4, 11), (11, 13), (13, 15), (15, 17),   # Right Arm
    (0, 18), (18, 20), (20, 22),             # Left Leg
    (0, 19), (19, 21), (21, 23),             # Right Leg
    (22, 24), (22, 26), (22, 28),            # Left Foot
    (23, 25), (23, 27), (23, 29),            # Right Foot
    (16, 30), (16, 32), (16, 34), (16, 36),  # Left Hand Fingers
    (17, 31), (17, 33), (17, 35), (17, 37)   # Right Hand Fingers
]

def main():
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD720
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open camera")
        exit(1)

    zed.enable_positional_tracking(sl.PositionalTrackingParameters())

    body_param = sl.BodyTrackingParameters()
    body_param.enable_body_fitting = True  
    body_param.detection_model = sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
    body_param.body_format = sl.BODY_FORMAT.BODY_38  # Using 38 keypoints
    zed.enable_body_tracking(body_param)

    body_runtime_param = sl.BodyTrackingRuntimeParameters()
    bodies = sl.Bodies()
    image_zed = sl.Mat()

    print("Tracking BODY_38... Press 'q' to quit.")

    while True:
        if zed.grab() == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            zed.retrieve_bodies(bodies, body_runtime_param)
            image_ocv = image_zed.get_data()

            for body in bodies.body_list:
                if body.keypoint.size > 0 and body.tracking_state == sl.OBJECT_TRACKING_STATE.OK:
                    
                    # --- Updated Indices for Logic ---
                    kp_3d = body.keypoint
                    l_wrist_3d = kp_3d[16]
                    r_wrist_3d = kp_3d[17]
                    l_elbow_3d = kp_3d[14]
                    r_elbow_3d = kp_3d[15]
                    l_hip_3d = kp_3d[18]
                    r_hip_3d = kp_3d[19]

                    gesture_text = "Idle"
                    color = (0, 255, 0)

                    if is_arms_crossed(l_wrist_3d, r_wrist_3d, l_elbow_3d, r_elbow_3d):
                        gesture_text = "Arms Crossed!"
                        color = (0, 0, 255)
                    elif is_hands_in_pockets(l_wrist_3d, r_wrist_3d, l_hip_3d, r_hip_3d):
                        gesture_text = "Hands in Pockets!"
                        color = (255, 0, 0)

                    # --- Rendering 38 Keypoints & Bones ---
                    kp_2d = body.keypoint_2d

                    # 1. Draw Bones (Lines)
                    for bone in BODY_38_BONES:
                        pt1 = kp_2d[bone[0]]
                        pt2 = kp_2d[bone[1]]
                        if not (math.isnan(pt1[0]) or math.isnan(pt2[0])):
                            cv2.line(image_ocv, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (255, 255, 255), 2)

                    # 2. Draw Joints (Dots)
                    for pt in kp_2d:
                        if not math.isnan(pt[0]):
                            cv2.circle(image_ocv, (int(pt[0]), int(pt[1])), 3, (0, 255, 255), -1)

                    # 3. Labeling
                    if not math.isnan(body.bounding_box_2d[0][0]):
                        top_left = (int(body.bounding_box_2d[0][0]), int(body.bounding_box_2d[0][1]))
                        cv2.putText(image_ocv, f"ID {body.id}: {gesture_text}", (top_left[0], top_left[1] - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            cv2.imshow("ZED BODY_38 Tracking", image_ocv)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()
    zed.close()

if __name__ == "__main__":
    main()