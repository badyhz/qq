#!/usr/bin/env python3
import json
import os
import ssl
import time
import http.server
import urllib.request
import urllib.error

HOST = "0.0.0.0"
PORT = 4457
UPSTREAM = "https://api.deepseek.com/anthropic/v1/messages"

def log(msg: str) -> None:
    print(msg, flush=True)

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log("[http] " + fmt % args)

    def do_GET(self):
        self._json(200, {"ok": True, "service": "deepseek_anthropic_shim"})

    def do_POST(self):
        started = time.time()
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            self._json(500, {"error": {"type": "missing_api_key", "message": "DEEPSEEK_API_KEY is empty"}})
            return

        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))

            model = payload.get("model", "deepseek-v4-flash")
            stream_requested = bool(payload.get("stream", False))
            log(f"[shim] path={self.path} model={model} stream_requested={stream_requested}")

            if "count_tokens" in self.path:
                approx = len(json.dumps(payload, ensure_ascii=False)) // 4 + 1
                self._json(200, {"input_tokens": approx})
                log(f"[shim] count_tokens approx={approx}")
                return

            if int(payload.get("max_tokens", 0) or 0) < 128:
                payload["max_tokens"] = 128

            req = urllib.request.Request(
                UPSTREAM,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": self.headers.get("anthropic-version", "2023-06-01"),
                },
                method="POST",
            )

            if stream_requested:
                self._stream_passthrough(req, started)
            else:
                self._nonstream(req, started)

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            log(f"[shim] upstream_http_error status={e.code} body={body[:500]}")
            self._json(e.code, {"error": {"type": "upstream_http_error", "message": body[:1000]}})
        except Exception as e:
            log(f"[shim] error={type(e).__name__}: {e}")
            self._json(502, {"error": {"type": type(e).__name__, "message": str(e)}})

    def _nonstream(self, req, started):
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            result = json.loads(body.decode("utf-8"))

        content = result.get("content", [])
        content_types = [c.get("type") for c in content if isinstance(c, dict)]
        text = "".join(
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        )

        result["content"] = [{"type": "text", "text": text}]
        result["stop_reason"] = result.get("stop_reason") or "end_turn"

        elapsed = time.time() - started
        log(f"[shim] nonstream_ok content_types={content_types} text_len={len(text)} elapsed={elapsed:.2f}s")
        self._json(200, result)

    def _stream_passthrough(self, req, started):
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.send_header("cache-control", "no-cache")
        self.send_header("connection", "close")
        self.end_headers()

        events_forwarded = 0
        events_dropped = 0
        got_message_stop = False
        dropped_indexes = set()
        index_map = {}
        next_index = 0

        def emit_event(event_name, data_json):
            nonlocal events_forwarded
            payload = (
                "event: " + event_name + "\n" +
                "data: " + json.dumps(data_json, ensure_ascii=False, separators=(",", ":")) + "\n\n"
            ).encode("utf-8")
            self.wfile.write(payload)
            self.wfile.flush()
            events_forwarded += 1

        with urllib.request.urlopen(req, timeout=120) as resp:
            buffer = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break

                buffer += chunk.replace(b"\r\n", b"\n")

                while b"\n\n" in buffer:
                    event_raw, buffer = buffer.split(b"\n\n", 1)
                    event_str = event_raw.decode("utf-8", errors="replace")

                    event_name = None
                    event_data = None

                    for line in event_str.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("event:"):
                            event_name = line[len("event:"):].strip()
                        elif line.startswith("data:"):
                            event_data = line[len("data:"):].strip()

                    if not event_name or not event_data:
                        events_dropped += 1
                        continue

                    if event_data == "[DONE]":
                        continue

                    try:
                        data_json = json.loads(event_data)
                    except json.JSONDecodeError:
                        events_dropped += 1
                        continue

                    idx = data_json.get("index")

                    if event_name == "content_block_start":
                        cb = data_json.get("content_block", {})
                        if isinstance(cb, dict) and cb.get("type") == "thinking":
                            if isinstance(idx, int):
                                dropped_indexes.add(idx)
                            events_dropped += 1
                            continue

                        if isinstance(idx, int):
                            if idx not in index_map:
                                index_map[idx] = next_index
                                next_index += 1
                            data_json["index"] = index_map[idx]

                    elif event_name in {"content_block_delta", "content_block_stop"}:
                        if isinstance(idx, int) and idx in dropped_indexes:
                            events_dropped += 1
                            continue

                        delta = data_json.get("delta", {})
                        if isinstance(delta, dict) and delta.get("type") in {"thinking_delta", "signature_delta"}:
                            events_dropped += 1
                            continue

                        if isinstance(idx, int):
                            if idx not in index_map:
                                events_dropped += 1
                                continue
                            data_json["index"] = index_map[idx]

                    elif event_name == "message_stop":
                        got_message_stop = True

                    emit_event(event_name, data_json)

        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        self.close_connection = True

        elapsed = time.time() - started
        log(f"[shim] stream_done forwarded={events_forwarded} dropped={events_dropped} got_message_stop={got_message_stop} index_map={index_map} dropped_indexes={sorted(dropped_indexes)} elapsed={elapsed:.2f}s")

    def _json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.send_header("connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

if __name__ == "__main__":
    log(f"DeepSeek Anthropic shim listening on https://{HOST}:{PORT}")
    httpd = http.server.HTTPServer((HOST, PORT), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("certs/deepseek-shim.crt", "certs/deepseek-shim.key")
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()
