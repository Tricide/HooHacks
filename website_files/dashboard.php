<?php
// Database Connection
$host = "localhost";
$user = "posture_user";
$pass = "chiapet1";
$db   = "posture_db";

$conn = new mysqli($host, $user, $pass, $db);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Fetch total "buzz" events for today
$result = $conn->query("SELECT COUNT(*) as buzz_count FROM logs WHERE event_type = 'buzz' AND DATE(created_at) = CURDATE()");
$buzz_data = $result->fetch_assoc();
$buzz_count = $buzz_data['buzz_count'] ?? 0;

$conn->close();
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Posture Coach</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --panel-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --danger: #ef4444;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 2rem;
            display: flex;
            justify-content: center;
        }
        .container {
            max-width: 900px;
            width: 100%;
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 2rem;
        }
        .card {
            background: var(--panel-bg);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        }
        h1, h2, h3 { margin-top: 0; }
        .stat-box {
            text-align: center;
            padding: 2rem 0;
        }
        .stat-number {
            font-size: 4rem;
            font-weight: bold;
            color: var(--danger);
            margin: 0;
        }
        .chat-box {
            display: flex;
            flex-direction: column;
            height: 500px;
        }
        .messages {
            flex-grow: 1;
            overflow-y: auto;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            background: #0b1120;
        }
        .msg { margin-bottom: 1rem; line-height: 1.5; }
        .msg.ai { color: #60a5fa; }
        .msg.user { color: #34d399; text-align: right; }
        .input-group {
            display: flex;
            gap: 0.5rem;
        }
        input[type="text"] {
            flex-grow: 1;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid #334155;
            background: #0f172a;
            color: white;
        }
        button {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.2s;
        }
        button:hover { background: var(--accent-hover); }
    </style>
</head>
<body>

    <div class="container">
        <div class="sidebar">
            <div class="card stat-box">
                <h3>Today's Alerts</h3>
                <p class="stat-number"><?php echo $buzz_count; ?></p>
                <p class="text-muted">Posture corrections</p>
            </div>
        </div>

        <div class="card chat-box">
            <h2>Gemini Insights</h2>
            <div class="messages" id="chatWindow">
                <div class="msg ai">
                    <strong>Gemini:</strong> Hello! I am analyzing your posture logs. Once your backend script saves my report, it will appear right here. What would you like to know about your stance?
                </div>
            </div>
            
            <div class="input-group">
                <input type="text" id="userInput" placeholder="Ask Gemini to explain your sway patterns...">
                <button onclick="sendMessage()">Ask</button>
            </div>
        </div>
    </div>

    <script>
        async function sendMessage() {
    const input = document.getElementById('userInput');
    const chat = document.getElementById('chatWindow');
    const message = input.value.trim();
    
    if(!message) return;

    // Add user message to UI
    chat.innerHTML += `<div class="msg user"><strong>You:</strong> ${message}</div>`;
    input.value = '';
    chat.scrollTop = chat.scrollHeight;

    // Show a loading state
    const loadingId = "loading-" + Date.now();
    chat.innerHTML += `<div class="msg ai" id="${loadingId}"><strong>Gemini:</strong> Thinking...</div>`;

    try {
        const response = await fetch('gemini_chat.php', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        
        // Replace "Thinking..." with real response
        document.getElementById(loadingId).innerHTML = `<strong>Gemini:</strong> ${data.reply}`;
    } catch (error) {
        document.getElementById(loadingId).innerHTML = `<strong>Error:</strong> Could not reach the coach.`;
    }
    
    chat.scrollTop = chat.scrollHeight;
}
    </script>
</body>
</html>