import json
import os
import urllib.request
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

MENU = {
    "Butter Scotch Cake":          {"price": 850},
    "Chocolate Cake":              {"price": 850},
    "Chocolate Truffle with Gems": {"price": 1200},
    "Chocolate Truffle Cake":      {"price": 950},
    "Chocolate Pistachio Filling": {"price": 1200},
    "KitKat Cake":                 {"price": 1500},
    "Mango Cake (Seasonal)":       {"price": 900},
    "Pineapple Cake":              {"price": 800},
    "Rasmalai Cake":               {"price": 1000},
    "Red Velvet":                  {"price": 950},
    "Strawberry Cake":             {"price": 800},
    "Vanilla Cake":                {"price": 800},
    "White Forest Cake":           {"price": 900},
    "Brownie":                     {"price": 70},
}


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def format_message(data: dict) -> str:
    name    = data.get("customerName", "—")
    phone   = data.get("phone", "—")
    date    = data.get("deliveryDate", "—")
    address = data.get("address", "—")
    note    = data.get("customNote", "")
    order   = data.get("order", {})
    ts      = datetime.now().strftime("%d %b %Y, %I:%M %p")

    lines, total = [], 0
    for item, qty in order.items():
        price = MENU.get(item, {}).get("price", 0)
        sub   = price * float(qty)
        total += sub
        lines.append(f"  • {item} × {qty} — ₹{int(sub):,}")

    order_text = "\n".join(lines) if lines else "  (Custom cake only)"

    msg = (
        f"🎂 <b>NEW ORDER — Miriam Pastries</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> {name}\n"
        f"📞 <b>Phone:</b> {phone}\n"
        f"📅 <b>Delivery:</b> {date}\n"
        f"📍 <b>Address:</b> {address}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 <b>Order:</b>\n{order_text}\n"
    )
    if total > 0:
        msg += f"\n💰 <b>Total: ₹{int(total):,}</b>\n"
    if note:
        msg += f"\n🎨 <b>Custom note:</b> {note}\n"
    msg += f"\n⏰ <i>{ts}</i>"
    return msg


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception:
            self._json(400, {"success": False, "error": "Invalid JSON"})
            return

        required = ["customerName", "phone", "deliveryDate", "address"]
        missing  = [f for f in required if not data.get(f)]
        if missing:
            self._json(400, {"success": False, "error": f"Missing: {missing}"})
            return

        if not data.get("order") and not data.get("customNote"):
            self._json(400, {"success": False, "error": "Empty order"})
            return

        try:
            result = send_telegram(format_message(data))
            if result.get("ok"):
                self._json(200, {"success": True})
            else:
                self._json(500, {"success": False, "error": result.get("description")})
        except Exception as e:
            self._json(500, {"success": False, "error": str(e)})

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
