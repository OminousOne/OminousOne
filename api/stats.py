from http.server import BaseHTTPRequestHandler

from _render import render_card


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        svg, cache = render_card("stats")
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", f"public, s-maxage={cache}, stale-while-revalidate=3600")
        self.end_headers()
        self.wfile.write(svg.encode())
