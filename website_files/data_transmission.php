<?php
$host = "localhost";
$user = "posture_user";
$pass = "chiapet1";
$db   = "posture_db";

// 1. Get the raw JSON data from Python
$json = file_get_contents('php://input');
$data = json_decode($json, true);

if ($data) {
    $conn = new mysqli($host, $user, $pass, $db);

    if ($conn->connect_error) {
        die("Connection failed: " . $conn->connect_error);
    }

    // 2. Prepare the data
    $event   = $data['event'] ?? 'unknown';
    $body_id = isset($data['body_id']) ? (int)$data['body_id'] : 0;
    $sway    = isset($data['swayval']) ? (float)$data['swayval'] : 0.0;

    // 3. Use a Prepared Statement for security and speed
    $stmt = $conn->prepare("INSERT INTO logs (event_type, body_id, sway_value) VALUES (?, ?, ?)");
    $stmt->bind_param("sid", $event, $body_id, $sway); // "sid" = string, integer, double

    if ($stmt->execute()) {
        echo json_encode(["status" => "success", "msg" => "Logged Body $body_id"]);
    } else {
        echo json_encode(["status" => "error", "msg" => $stmt->error]);
    }

    $stmt->close();
    $conn->close();
} else {
    echo json_encode(["status" => "error", "msg" => "No data received"]);
}
?>