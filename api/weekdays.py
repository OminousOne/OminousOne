import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _render import render_card


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        svg, cache = render_card("weekdays")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", f"public, s-maxage={cache}, stale-while-revalidate=86400")
        self.end_headers()
        self.wfile.write(svg.encode())
