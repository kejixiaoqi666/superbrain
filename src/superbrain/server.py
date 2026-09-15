"""超脑 SuperBrain MCP/服务层 —— 把超脑暴露成可被其它 agent 调用的服务。

零依赖实现（标准库 http.server）：
- HTTP REST API：任何 agent 用 curl/requests 就能调
- JSON-RPC 2.0 端点：兼容 MCP 风格的消息协议

启动：
    python -m src.superbrain.server  --port 8090 --db ~/.superbrain/brain.db

或 python 内：
    from superbrain.server import start
    start(port=8090)

其它 agent 接入示例（curl）：
    curl -X POST http://localhost:8090/chat -H "Content-Type: application/json" -d '{"message":"你好"}'
    curl -X POST http://localhost:8090/remember -d '{"content":"用户喜欢茶"}'
    curl http://localhost:8090/state
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlparse

from .facade import SuperBrain


class _BrainHandler(BaseHTTPRequestHandler):
    brain: Optional[SuperBrain] = None  # 类级共享

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError:
            return {}

    def _handle(self) -> None:
        b = self.brain
        if b is None:
            self._send(500, {"error": "brain 未初始化"})
            return
        path = urlparse(self.path).path
        data = self._read_json()
        try:
            if path == "/chat":
                self._send(200, {"reply": b.chat(data.get("message", ""),
                                                 person_id=data.get("person_id"))})
            elif path == "/orientations":
                self._send(200, b.orientations())
            elif path == "/remember":
                node_id = b.remember(data.get("content", ""),
                                     scope=data.get("scope", "user"))
                self._send(200, {"node_id": node_id})
            elif path == "/recall":
                hits = b.recall(data.get("query", ""), k=int(data.get("k", 5)))
                self._send(200, {"hits": hits})
            elif path == "/state":
                self._send(200, b.state())
            elif path == "/save":
                p = b.save(data.get("path"))
                self._send(200, {"saved": p})
            elif path == "/load":
                ok = b.load(data.get("path"))
                self._send(200, {"loaded": ok})
            elif path == "/thoughts":
                th = b.generate_thoughts()
                self._send(200, {"thoughts": [
                    {"type": t.type, "content": t.content, "urgency": t.urgency,
                     "reason": t.reason, "person_id": t.person_id} for t in th]})
            elif path == "/drain_thoughts":
                th = b.drain_thoughts()
                self._send(200, {"thoughts": [
                    {"type": t.type, "content": t.content, "urgency": t.urgency,
                     "reason": t.reason, "person_id": t.person_id} for t in th]})
            elif path == "/humanize":
                self._send(200, {"text": b.humanize(
                    data.get("text", ""), person_id=data.get("person_id"))})
            elif path == "/meme":
                try:
                    limit = int(data.get("limit", 5))
                except (TypeError, ValueError):
                    limit = 5
                self._send(200, {"memes": b.search_meme(
                    data.get("query", ""), limit=max(1, min(limit, 20)))})
            elif path == "/health":
                self._send(200, {"status": "ok"})
            elif path == "/tools":
                self._send(200, {"tools": ["chat", "remember", "recall",
                                           "state", "save", "load",
                                           "thoughts", "drain_thoughts",
                                           "humanize", "meme", "orientations"]})
            else:
                self._send(404, {"error": f"未知端点 {path}"})
        except Exception as e:
            self._send(500, {"error": str(e)})

    def do_POST(self) -> None:
        self._handle()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, {"status": "ok"})
        elif path == "/state":
            if self.brain:
                self._send(200, self.brain.state())
            else:
                self._send(500, {"error": "brain 未初始化"})
        else:
            self._send(404, {"error": f"未知端点 {path}"})

    def log_message(self, fmt, *args) -> None:  # 静默日志
        pass


def start(brain: Optional[SuperBrain] = None, port: int = 8090,
          host: str = "127.0.0.1", db: Optional[str] = None) -> ThreadingHTTPServer:
    """启动超脑服务。brain 缺省时 from_env 装配。"""
    if brain is None:
        import os
        os.environ.setdefault("SUPERBRAIN_DB", db or "~/.superbrain/brain.db")
        brain = SuperBrain.from_env()
    _BrainHandler.brain = brain
    server = ThreadingHTTPServer((host, port), _BrainHandler)
    return server


def run(brain: Optional[SuperBrain] = None, port: int = 8090,
        host: str = "127.0.0.1", db: Optional[str] = None) -> None:
    """启动并阻塞运行。"""
    srv = start(brain=brain, port=port, host=host, db=db)
    print(f"超脑服务已启动: http://{host}:{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8090"))
    host = os.environ.get("HOST", "127.0.0.1")
    run(port=port, host=host)