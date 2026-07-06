import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _render import render_card


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        svg, cache = render_card("visitors")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        if cache:
            self.send_header("Cache-Control", f"public, s-maxage={cache}, stale-while-revalidate=86400")
        else:
            self.send_header("Cache-Control", "max-age=0, no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(svg.encode())
