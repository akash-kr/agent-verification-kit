"""The demo shop: a cart page at / and the total at /total?prices=20,20&coupon=10. Port from $PORT."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cart import total

PAGE = Path(__file__).with_name("cart.html")


class Shop(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            return self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if url.path == "/total":
            query = parse_qs(url.query)
            try:
                prices = [float(p) for p in query.get("prices", [""])[0].split(",") if p]
                coupon = float(query.get("coupon", ["0"])[0])
            except ValueError:
                return self.reply(400, b'{"error": "prices and coupon must be numbers"}', "application/json")
            return self.reply(200, json.dumps({"total": total(prices, coupon)}).encode(), "application/json")
        self.reply(404, b"not found", "text/plain")

    def reply(self, status, body, kind):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8000"))), Shop).serve_forever()
