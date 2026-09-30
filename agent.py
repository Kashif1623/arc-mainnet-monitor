import time
import os
import threading
import sqlite3
import json
import socket
import urllib.request
import urllib.error
from flask import Flask, jsonify

socket.setdefaulttimeout(3)

PRIMARY_RPC_ENDPOINT = "https://lb.drpc.live/arc/AkLbXOc8IkXki1HqEPdmcWxt_NlEsigR8b3uEl_NDNxu"
TELEGRAM_BOT_TOKEN = "8996901688:AAHEpEeYGzcMDqMkLBcBwUSou6-ojjoKkgY"
DB_FILE = "arc_mainnet_sla.db"
global_node_data = {}
logs_list = []

app = Flask(__name__)

def log_msg(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"{timestamp} | {message}"
    print(formatted)
    logs_list.append(formatted)
    if len(logs_list) > 100:
        logs_list.pop(0)

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS uptime_logs
                     (timestamp TEXT, node_url TEXT, status TEXT, latency_ms INTEGER, block_height INTEGER)''')
        conn.commit()
        conn.close()
    except Exception:
        pass

init_db()

def send_telegram_message(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=3)
    except Exception as e:
        log_msg(f"[!] Telegram Error: {e}")

def get_status_report():
    report = "⚡ *ARC Mainnet Node Status Report*\n\n"
    if not global_node_data:
        return report + "Initializing nodes data, please wait..."
    for url, data in global_node_data.items():
        status = data.get("status", "UNKNOWN")
        block = data.get("block", 0)
        latency = data.get("latency", 0)
        emoji = "🟢" if status == "ONLINE" else "🔴"
        report += f"{emoji} `ARC Mainnet Node`\n   • Status: *{status}*\n   • Block: `{block}`\n   • Latency: `{latency}ms`\n\n"
    return report

def monitor_worker():
    log_msg("Monitor worker started successfully (Mainnet)!")
    while True:
        log_msg("Attempting fetch...")
        start_time = time.time()
        try:
            rpc_payload = json.dumps({
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }).encode('utf-8')
            
            req = urllib.request.Request(
                PRIMARY_RPC_ENDPOINT, 
                data=rpc_payload, 
                headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            )
            
            try:
                with urllib.request.urlopen(req, timeout=3) as response:
                    latency = int((time.time() - start_time) * 1000)
                    if response.status == 200:
                        res_data = json.loads(response.read().decode('utf-8'))
                        if "result" in res_data:
                            block_height = int(res_data["result"], 16)
                            log_msg(f"🟢 [ONLINE] Block: {block_height} | Ping: {latency}ms")
                            global_node_data[PRIMARY_RPC_ENDPOINT] = {"status": "ONLINE", "latency": latency, "block": block_height}
                        else:
                            global_node_data[PRIMARY_RPC_ENDPOINT] = {"status": "OFFLINE", "latency": latency, "block": 0}
                    else:
                        global_node_data[PRIMARY_RPC_ENDPOINT] = {"status": "OFFLINE", "latency": latency, "block": 0}
            except Exception as inner_e:
                latency = int((time.time() - start_time) * 1000)
                log_msg(f"🔴 [TIMEOUT/CONNECTION FAIL]: {inner_e}")
                global_node_data[PRIMARY_RPC_ENDPOINT] = {"status": "OFFLINE", "latency": latency, "block": 0}
        except Exception as e:
            log_msg(f"🔴 [ERROR]: {e}")
            global_node_data[PRIMARY_RPC_ENDPOINT] = {"status": "OFFLINE", "latency": 0, "block": 0}
        
        time.sleep(10)

def telegram_listener():
    log_msg("Telegram listener started successfully (Mainnet)!")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
        urllib.request.urlopen(url, timeout=3)
    except Exception:
        pass

    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=3"
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    for result in data.get("result", []):
                        offset = result["update_id"] + 1
                        message = result.get("message", {})
                        text = message.get("text", "").strip()
                        chat_id = message.get("chat", {}).get("id")
                        
                        if chat_id and text:
                            log_msg(f"[TG] Command received: {text}")
                            if text.startswith("/start") or text.lower() == "start":
                                send_telegram_message(chat_id, "⚡ *ARC Mainnet Monitoring Sentinel is Online!*\n\nSend /status to check node statuses.")
                            elif text.startswith("/status"):
                                send_telegram_message(chat_id, get_status_report())
        except Exception:
            pass
        time.sleep(1)

threading.Thread(target=monitor_worker, daemon=True).start()
threading.Thread(target=telegram_listener, daemon=True).start()
log_msg("Background threads spawned successfully.")

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ARC Mainnet Sentinel</title>
        <style>
            body { background-color: #0d0d0d; color: #00ff66; font-family: monospace; padding: 20px; }
            h2 { color: #ffcc00; border-bottom: 1px dashed #ffcc00; padding-bottom: 10px; }
            pre { white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.5; background: #111; padding: 15px; border-radius: 5px; }
            .node-box { background: #161616; padding: 10px; margin-bottom: 10px; border-left: 4px solid #00ff66; }
        </style>
    </head>
    <body>
        <h2>⚡ ARC MAINNET SENTINEL INFRASTRUCTURE</h2>
        <div id="status">Loading node statuses...</div>
        <h3>Live Activity Logs:</h3>
        <pre id="logs">Loading logs...</pre>
        <script>
            function fetchData() {
                fetch('/api/data')
                    .then(res => res.json())
                    .then(data => {
                        let statusHtml = "<h4>Node Statuses:</h4>";
                        if (Object.keys(data.nodes).length === 0) {
                            statusHtml += "<p>Initializing nodes connection...</p>";
                        } else {
                            for (let [url, info] of Object.entries(data.nodes)) {
                                let color = info.status === 'ONLINE' ? '#00ff66' : '#ff3333';
                                statusHtml += `<div class="node-box" style="border-left-color: ${color}">` +
                                              `${info.status === 'ONLINE' ? '🟢' : '🔴'} <b>ARC Mainnet Node</b><br>` +
                                              `• Status: <b>${info.status}</b> | Block: <code>${info.block}</code> | Latency: <code>${info.latency}ms</code>` +
                                              `</div>`;
                            }
                        }
                        document.getElementById('status').innerHTML = statusHtml;
                        document.getElementById('logs').textContent = data.logs.join('\\n');
                    })
                    .catch(err => console.log(err));
            }
            fetchData();
            setInterval(fetchData, 4000);
        </script>
    </body>
    </html>
    """

@app.route("/api/data")
def api_data():
    return jsonify({
        "nodes": global_node_data,
        "logs": list(logs_list)
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
