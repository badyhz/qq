#!/usr/bin/env python3
"""Loopback-only authenticated ZEC strategy control dashboard.

The web app can mutate governed local runtime configuration only.  It never
constructs a live-enabled exchange adapter and exposes no manual order endpoint.
"""
from __future__ import annotations

import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import threading
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.zec_4h_admin import (
    apply_control_change,
    collect_admin_snapshot,
    collect_control_snapshot,
)
from core.zec_4h_live_execution import BinanceUsdMExecutionAdapter
from core.zec_control import ControlConflictError, UnsafeConfigurationChange


CONTROL_LOCK = threading.Lock()

HTML = r"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>ZEC 自动交易后台</title>
<style>
:root{color-scheme:dark;--bg:#0b0e14;--panel:#151a23;--line:#293140;--text:#f4f7fb;--muted:#94a0b2;--ok:#38d382;--bad:#ff6374;--warn:#ffc85c;--blue:#70a9ff}*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0a0d12,#111722);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}.wrap{max-width:1280px;margin:auto;padding:16px}.top,.toolbar{display:flex;gap:10px;justify-content:space-between;align-items:center}.title{font-size:22px;font-weight:760}.sub,.tiny{color:var(--muted);font-size:12px}.grid,.row,.control{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.card,.section{background:rgba(21,26,35,.97);border:1px solid var(--line);border-radius:14px}.card{padding:14px}.section{padding:15px;margin-top:12px}.label,.kv b{font-size:12px;color:var(--muted);font-weight:500}.value{font-size:21px;font-weight:720;margin-top:6px}.kv{padding:8px 0;border-bottom:1px solid var(--line)}.kv span{display:block;margin-top:5px}.btn,input,select{background:#111721;border:1px solid var(--line);color:var(--text);border-radius:9px;padding:9px}.btn{cursor:pointer}.primary{border-color:#315f9c}.danger{border-color:#8b303b;color:#ffadb5}.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:11px}.table{overflow:auto;border:1px solid var(--line);border-radius:10px}table{width:100%;border-collapse:collapse;min-width:850px}th,td{padding:9px;border-bottom:1px solid var(--line);text-align:right;font-size:12px;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{color:var(--muted)}@media(max-width:760px){.grid,.row,.control{grid-template-columns:1fr 1fr}.wrap{padding:10px}.title{font-size:19px}}
</style></head><body><div class="wrap">
<div class="top"><div><div class="title">自动交易控制中心</div><div class="sub" id="generated">读取中…</div></div><button class="btn" onclick="loadAll()">刷新</button></div>
<div class="grid" style="margin-top:12px">
<div class="card"><div class="label">交易引擎</div><div class="value" id="engine">—</div></div>
<div class="card"><div class="label">实盘主权限</div><div class="value" id="armed">—</div></div>
<div class="card"><div class="label">策略</div><div class="value" id="strategyState">—</div></div>
<div class="card"><div class="label">当前持仓</div><div class="value" id="position">—</div><div class="tiny" id="positionPnl"></div></div>
</div>
<div class="section"><div class="toolbar"><h3 style="margin:0">策略设置</h3><span class="pill" id="revision">—</span></div>
<div class="control" style="margin-top:10px">
<label class="kv"><b>策略</b><select id="strategy"></select></label>
<label class="kv"><b>管理标的</b><select id="symbol"></select></label>
<label class="kv"><b>交易周期</b><select id="timeframe"></select></label>
<label class="kv"><b>单次仓位基数 USDT</b><input id="sizing" type="number" min="0.01" max="50" step="0.01"></label>
</div>
<div class="row" style="margin-top:8px"><div class="kv"><b>资金硬上限</b><span>50 USDT</span></div><div class="kv"><b>固定杠杆</b><span>50x</span></div><div class="kv"><b>预计名义仓位</b><span id="notional">—</span></div><div class="kv"><b>执行版本</b><span id="execRevision">—</span></div></div>
<div class="toolbar" style="margin-top:12px"><button class="btn primary" onclick="saveSettings()">保存设置</button><div><button class="btn danger" onclick="toggleStrategy(false)">关闭策略</button> <button class="btn primary" onclick="toggleStrategy(true)">开启策略</button></div></div>
<div class="tiny" id="message" style="margin-top:8px">关闭策略只阻止新的 OPEN / ADD；已有持仓的止损、止盈、硬止损与恢复继续运行。</div></div>
<div class="section"><h3>盈亏概览</h3><div class="row" id="pnl"></div></div>
<div class="section"><h3>当前持仓明细</h3><div class="row" id="positionDetails"></div></div>
<div class="section"><h3>最近交易记录</h3><div class="table"><table><thead><tr><th>时间</th><th>方向</th><th>动作</th><th>成交价</th><th>数量</th><th>名义价值</th><th>手续费</th><th>已实现盈亏</th><th>退出原因</th></tr></thead><tbody id="history"></tbody></table></div></div>
<div class="tiny" style="text-align:center;padding:16px">控制面只管理策略开关与运行参数 · 不提供人工买入/卖出/平仓接口</div>
</div><script>
let DATA=null,CTL=null;const $=x=>document.getElementById(x);const n=(v,d=2)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toFixed(d);const m=v=>v===null||v===undefined?'—':`${Number(v)>=0?'+':''}${n(v,4)} USDT`;const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));const kv=(a,b,c='')=>`<div class="kv"><b>${esc(a)}</b><span class="${c}">${esc(b)}</span></div>`;const cls=v=>Number(v)>0?'ok':Number(v)<0?'bad':'';
function render(){if(!DATA||!CTL)return;const r=DATA.runtime||{},p=DATA.pnl||{},pos=DATA.position||{};$('generated').textContent=`最后读取 ${DATA.generated_at||'—'} · ${DATA.strategy?.account_mode||'—'} / ${DATA.strategy?.api_mode||'—'}`;$('engine').textContent=r.engine_running?'RUNNING':'STALE/OFFLINE';$('engine').className=`value ${r.engine_running?'ok':'warn'}`;$('armed').textContent=r.live_enabled?'ARMED':'OFF';$('armed').className=`value ${r.live_enabled?'ok':'warn'}`;$('strategyState').textContent=CTL.strategy_enabled?'ON':'OFF';$('strategyState').className=`value ${CTL.strategy_enabled?'ok':'warn'}`;$('position').textContent=Number(pos.qty||0)===0?'空仓':`${n(pos.qty,6)} ${CTL.symbol.replace('USDT','')}`;$('positionPnl').textContent=`浮动 ${m(pos.unrealized_pnl)}`;$('revision').textContent=`控制版本 ${CTL.revision}`;$('execRevision').textContent=CTL.execution_revision??'—';$('strategy').innerHTML=(CTL.registry||[]).map(x=>`<option value="${esc(x.strategy_id)}">${esc(x.name)}</option>`).join('');$('strategy').value=CTL.strategy_id;$('symbol').innerHTML=(CTL.available_symbols||[CTL.symbol]).map(x=>`<option>${esc(x)}</option>`).join('');$('symbol').value=CTL.symbol;const def=(CTL.registry||[]).find(x=>x.strategy_id===CTL.strategy_id);$('timeframe').innerHTML=((def&&def.allowed_timeframes)||['4h']).map(x=>`<option>${esc(x)}</option>`).join('');$('timeframe').value=CTL.timeframe;$('sizing').value=CTL.sizing_base_usdt;$('notional').textContent=`≈ ${n(Number(CTL.sizing_base_usdt)*Number(CTL.leverage),2)} USDT`;$('pnl').innerHTML=[kv('策略权益',`${n(p.strategy_equity,4)} USDT`),kv('总盈亏',m(p.total_pnl),cls(p.total_pnl)),kv('已实现',m(p.realized_net_pnl),cls(p.realized_net_pnl)),kv('浮动',m(p.unrealized_pnl),cls(p.unrealized_pnl)),kv('已平仓',String(p.closed_trades??0)),kv('胜率',p.win_rate==null?'—':`${n(p.win_rate*100,1)}%`),kv('Profit Factor',n(p.profit_factor,2)),kv('近30天',m(p.pnl_30d),cls(p.pnl_30d))].join('');$('positionDetails').innerHTML=[kv('标的',pos.symbol||CTL.symbol),kv('开仓价',n(pos.entry_price,4)),kv('Mark',n(pos.mark_price,4)),kv('名义价值',`${n(pos.notional,4)} USDT`),kv('止损',pos.stop_loss==null?'—':n(pos.stop_loss,4)),kv('止盈',pos.take_profit==null?'—':n(pos.take_profit,4)),kv('估算 ROE',pos.roe_pct_estimate==null?'—':`${n(pos.roe_pct_estimate,2)}%`),kv('持仓方向',pos.position_side||'—')].join('');const rows=(DATA.history||[]).slice(0,50);$('history').innerHTML=rows.length?rows.map(x=>`<tr><td>${esc(x.time)}</td><td>${esc(x.side)}</td><td>${esc(x.action||'—')}</td><td>${n(x.price,4)}</td><td>${n(x.qty,6)}</td><td>${n(x.notional,4)}</td><td>${n(x.fee,6)} ${esc(x.fee_asset||'')}</td><td class="${cls(x.realized_pnl)}">${m(x.realized_pnl)}</td><td>${esc(x.exit_reason||'—')}</td></tr>`).join(''):`<tr><td colspan="9">暂无历史成交</td></tr>`;}
async function loadAll(){try{const [a,c]=await Promise.all([fetch('api/snapshot',{cache:'no-store'}),fetch('api/control',{cache:'no-store'})]);if(!a.ok||!c.ok)throw new Error(`HTTP ${a.status}/${c.status}`);DATA=await a.json();CTL=await c.json();render()}catch(e){$('generated').textContent=`读取失败：${e.message}`}}
async function post(path,payload){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const b=await r.json().catch(()=>({error:`HTTP ${r.status}`}));if(!r.ok)throw new Error(b.error||`HTTP ${r.status}`);CTL=b;await loadAll()}
async function saveSettings(){if(!CTL)return;const sizing=Number($('sizing').value);if(!confirm(`保存设置？\n策略：${$('strategy').value}\n标的：${$('symbol').value}\n周期：${$('timeframe').value}\n仓位基数：${sizing.toFixed(2)} USDT\n预计名义仓位：${(sizing*50).toFixed(2)} USDT`))return;try{await post('api/control/settings',{expected_revision:CTL.revision,strategy_id:$('strategy').value,symbol:$('symbol').value,timeframe:$('timeframe').value,sizing_base_usdt:sizing});$('message').textContent='设置已保存。'}catch(e){$('message').textContent=`拒绝：${e.message}`}}
async function toggleStrategy(on){if(!CTL)return;const text=on?'开启策略后只从下一根有效 CLOSED BAR 开始，不补旧入场信号。':'关闭策略后停止新的开仓和加仓；已有持仓继续风控。';if(!confirm(`${text}\n\n确认${on?'开启':'关闭'}？`))return;try{await post(`api/control/strategy/${on?'enable':'disable'}`,{expected_revision:CTL.revision});$('message').textContent=`策略已${on?'开启':'关闭'}。`}catch(e){$('message').textContent=`拒绝：${e.message}`}}
loadAll();
</script></body></html>"""


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "ZecControlAdmin/2.0"

    def _authenticated(self) -> bool:
        expected_user = os.environ.get("ZEC_4H_ADMIN_USER", "")
        expected_password = os.environ.get("ZEC_4H_ADMIN_PASSWORD", "")
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
            supplied_user, supplied_password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(supplied_user, expected_user) and hmac.compare_digest(
            supplied_password, expected_password
        )

    def _authenticated_user(self) -> str:
        header = self.headers.get("Authorization", "")
        try:
            return base64.b64decode(header[6:], validate=True).decode("utf-8").split(":", 1)[0]
        except Exception:
            return "admin"

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )

    def _require_auth(self) -> bool:
        if self._authenticated():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="ZEC Control Admin", charset="UTF-8"')
        self._security_headers()
        self.end_headers()
        return False

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _same_origin(self) -> bool:
        host = self.headers.get("Host", "").strip().lower()
        origin = self.headers.get("Origin", "").strip()
        if not host or not origin:
            return False
        parsed = urlparse(origin)
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host

    def _read_json(self) -> dict:
        if self.headers.get_content_type() != "application/json":
            raise ValueError("JSON_CONTENT_TYPE_REQUIRED")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 16_384:
            raise ValueError("INVALID_JSON_BODY_LENGTH")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON_OBJECT_REQUIRED")
        return payload

    @staticmethod
    def _control_adapter() -> BinanceUsdMExecutionAdapter:
        api_key = os.environ.get("ZEC_4H_BINANCE_API_KEY", "")
        api_secret = os.environ.get("ZEC_4H_BINANCE_API_SECRET", "")
        if not api_key or not api_secret:
            raise RuntimeError("CONTROL_PREFLIGHT_CREDENTIALS_MISSING")
        return BinanceUsdMExecutionAdapter(
            api_key=api_key,
            api_secret=api_secret,
            live_enabled=False,
        )

    def _control_payload(self) -> dict:
        try:
            return collect_control_snapshot(adapter=self._control_adapter())
        except Exception:
            return collect_control_snapshot()

    def do_GET(self) -> None:
        if not self._require_auth():
            return
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/snapshot":
            self._send_json(200, collect_admin_snapshot())
            return
        if path == "/api/control":
            self._send_json(200, self._control_payload())
            return
        if path == "/healthz":
            self._send_json(200, {"ok": True, "mode": "GOVERNED_CONTROL_PLANE", "manual_orders": False})
            return
        self._send_json(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        if not self._require_auth():
            return
        path = urlparse(self.path).path
        allowed_paths = {
            "/api/control/settings",
            "/api/control/strategy/enable",
            "/api/control/strategy/disable",
        }
        if path not in allowed_paths:
            self._send_json(405, {"error": "NO_ORDER_OR_MANUAL_TRADE_ENDPOINT"})
            return
        if not self._same_origin():
            self._send_json(403, {"error": "SAME_ORIGIN_REQUIRED"})
            return
        try:
            payload = self._read_json()
            expected_revision = int(payload.pop("expected_revision"))
            if path == "/api/control/settings":
                expected_fields = {"strategy_id", "symbol", "timeframe", "sizing_base_usdt"}
                if set(payload) != expected_fields:
                    raise ValueError("EXACT_SETTINGS_FIELDS_REQUIRED")
                changes = payload
            else:
                if payload:
                    raise ValueError("UNEXPECTED_TOGGLE_FIELDS")
                changes = {"strategy_enabled": path.endswith("/enable")}
            with CONTROL_LOCK:
                apply_control_change(
                    changes,
                    expected_revision=expected_revision,
                    actor=self._authenticated_user(),
                    adapter=self._control_adapter(),
                )
                self._send_json(200, self._control_payload())
        except ControlConflictError:
            self._send_json(409, {"error": "CONFIG_REVISION_CONFLICT"})
        except UnsafeConfigurationChange as exc:
            self._send_json(409, {"error": f"CONFIG_CHANGE_BLOCKED_ACTIVE_POSITION:{exc}"})
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc) or exc.__class__.__name__})
        except Exception as exc:
            self._send_json(503, {"error": exc.__class__.__name__})

    def _reject_non_post_write(self) -> None:
        if not self._require_auth():
            return
        self._send_json(405, {"error": "CONTROL_CHANGES_REQUIRE_POST"})

    def do_PUT(self) -> None:
        self._reject_non_post_write()

    def do_DELETE(self) -> None:
        self._reject_non_post_write()

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    user = os.environ.get("ZEC_4H_ADMIN_USER", "").strip()
    password = os.environ.get("ZEC_4H_ADMIN_PASSWORD", "")
    if not user or not password:
        print("ZEC_4H_ADMIN_CREDENTIALS_MISSING", file=sys.stderr)
        return 2
    bind = os.environ.get("ZEC_4H_ADMIN_BIND", "127.0.0.1").strip()
    if bind not in {"127.0.0.1", "::1", "localhost"}:
        print("ZEC_4H_ADMIN_BIND_MUST_BE_LOOPBACK", file=sys.stderr)
        return 2
    try:
        port = int(os.environ.get("ZEC_4H_ADMIN_PORT", "8766"))
    except ValueError:
        print("ZEC_4H_ADMIN_PORT_INVALID", file=sys.stderr)
        return 2
    if not 1 <= port <= 65535:
        print("ZEC_4H_ADMIN_PORT_INVALID", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((bind, port), AdminHandler)
    print(f"ZEC_4H_ADMIN_CONTROL listening on {bind}:{port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
