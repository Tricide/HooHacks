<?php
header('Content-Type: application/json');

// 1. DATABASE CONFIG
$db_host = "localhost";
$db_user = "posture_user";
$db_pass = "chiapet1";
$db_name = "posture_db";

// 2. GEMINI CONFIG (Update with your 2026 Model & Key)
$api_key = "AIzaSyAZvJJRZnSZCHwGBAseet7BqJwj979p1Gs";
$model   = "gemini-3-flash-preview"; 
$api_url = "https://generativelanguage.googleapis.com/v1beta/models/{$model}:generateContent?key={$api_key}";

// 3. GET DATA FROM USER & DATABASE
$input = json_decode(file_get_contents('php://input'), true);
$user_query = $input['message'] ?? 'Analyze my recent posture.';

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name);
$result = $conn->query("SELECT event_type, sway_value, created_at FROM logs ORDER BY created_at DESC LIMIT 30");
$logs = [];
while($row = $result->fetch_assoc()) { $logs[] = $row; }
$conn->close();

// 4. PREPARE THE PROMPT
$context = "You are an AI Posture Coach. Here are the user's recent logs:\n" . json_encode($logs) . "\n\n" .
           "Context: 'sway_value' is horizontal movement (mm). >180mm triggers a 'buzz'.\n" .
           "User asks: " . $user_query;

$payload = [
    "contents" => [
        ["parts" => [["text" => $context]]]
    ]
];

// 5. CALL GEMINI
$ch = curl_init($api_url);
curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); // For local testing only

$response = curl_exec($ch);
$err = curl_error($ch);
curl_close($ch);

if ($err) {
    echo json_encode(["error" => "cURL Error: " . $err]);
} else {
    $data = json_decode($response, true);
    $text = $data['candidates'][0]['content']['parts'][0]['text'] ?? "I couldn't generate a response.";
    echo json_encode(["reply" => $text]);
}
?>