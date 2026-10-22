"""Serve this exported performance locally; no renderer or SoundFont required."""
import argparse
import functools
import http.server
import threading
import webbrowser
from pathlib import Path

def create_server(port=4192):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(Path(__file__).resolve().parent))
    try:
        return http.server.ThreadingHTTPServer(('127.0.0.1', port), handler)
    except OSError:
        if port == 0:
            raise
        return http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=4192)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    with create_server(args.port) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'演奏页：{url}\n保持此窗口打开；Ctrl+C 停止服务。', flush=True)
        print(f'需要键盘麦克风时，在本目录运行：node keyboard-audio-bridge.mjs --origin {url.rstrip(chr(47))}', flush=True)
        if not args.no_browser:
            threading.Timer(.3, webbrowser.open, args=(url,)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()
