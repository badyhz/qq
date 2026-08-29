#!/usr/bin/env python3
"""Loopback-only read-only web UI for the ZECUSDT 4H strategy."""
from __future__ import annotations

import base64
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.zec_4h_admin import collect_admin_snapshot


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>ZEC 4H 交易后台</title>
<style>
:root{color-scheme:dark;--bg:#0b0d12;--panel:#141821;--muted:#8f98a8;--line:#252b37;--text:#f6f7fb;--ok:#35d07f;--bad:#ff5d6c;--warn:#ffc857;--blue:#6ea8fe}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#0b0d12,#10141c);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1280px;margin:auto;padding:18px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:16px}.title{font-size:22px;font-weight:750}.sub{color:var(--muted);font-size:12px;margin-top:4px}.btn{border:1px solid var(--line);background:#1a202b;color:var(--text);border-radius:10px;padding:9px 13px;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.card,.section{background:rgba(20,24,33,.96);border:1px solid var(--line);border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.18)}
.card{padding:15px}.label{font-size:12px;color:var(--muted)}.value{font-size:22px;font-weight:720;margin-top:7px}.tiny{font-size:11px;color:var(--muted);margin-top:5px}
.section{margin-top:12px;padding:16px}.section h2{font-size:15px;margin:0 0 12px}.row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.kv{padding:10px 0;border-bottom:1px solid var(--line)}.kv b{display:block;font-size:12px;color:var(--muted);font-weight:500}.kv span{display:block;margin-top:5px;font-size:14px;word-break:break-word}
.ok{color:var(--ok)}.bad{color:var(--bad)}.warn{color:var(--warn)}.blue{color:var(--blue)}.pill{display:inline-flex;align-items:center;border:1px solid var(--line);border-radius:999px;padding:4px 8px;font-size:11px;margin:2px 5px 2px 0}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:10px}table{width:100%;border-collapse:collapse;min-width:900px}th,td{padding:10px 9px;text-align:right;border-bottom:1px solid var(--line);font-size:12px;white-space:nowrap}th{color:var(--muted);font-weight:600;background:#111620;position:sticky;top:0}th:first-child,td:first-child{text-align:left}.empty{color:var(--muted);padding:18px;text-align:center}
.toolbar{display:flex;gap:8px;justify-content:space-between;align-items:center;margin-bottom:10px}.toolbar input,.toolbar select{background:#0f141c;border:1px solid var(--line);color:var(--text);border-radius:8px;padding:8px}
footer{color:var(--muted);font-size:11px;text-align:center;padding:18px}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}.row{grid-template-columns:repeat(2,1fr)}}
@media(max-width:560px){.wrap{padding:12px}.grid{grid-template-columns:1fr 1fr;gap:8px}.card{padding:12px}.value{font-size:18px}.row{grid-template-columns:1fr 1fr}.title{font-size:19px}.top{align-items:flex-start}.section{padding:12px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div><div class="title">ZECUSDT · 4H 交易后台</div><div class="sub" id="generated">读取中…</div></div>
    <button class="btn" onclick="loadData()">刷新</button>
  </div>

  <div class="grid">
    <div class="card"><div class="label">策略权益</div><div class="value" id="equity">—</div><div class="tiny">固定资金池 50 USDT</div></div>
    <div class="card"><div class="label">总盈亏</div><div class="value" id="totalPnl">—</div><div class="tiny" id="pnlSplit">—</div></div>
    <div class="card"><div class="label">当前持仓</div><div class="value" id="positionQty">—</div><div class="tiny" id="positionPnl">—</div></div>
    <div class="card"><div class="label">实盘状态</div><div class="value" id="liveState">—</div><div class="tiny" id="preflightState">—</div></div>
  </div>

  <div class="section"><h2>当前持仓明细</h2><div class="row" id="positionDetails"></div></div>
  <div class="section"><h2>简单盈亏统计</h2><div class="row" id="pnlDetails"></div></div>
  <div class="section"><h2>账户 / API 健康</h2><div id="health"></div></div>
  <div class="section"><h2>策略与信号</h2><div class="row" id="strategySignal"></div></div>

  <div class="section">
    <div class="toolbar"><h2 style="margin:0">历史交易记录</h2><div><input id="historySearch" placeholder="筛选订单/动作" oninput="renderHistory()"><select id="historyLimit" onchange="renderHistory()"><option>20</option><option>50</option><option>100</option><option>500</option></select></div></div>
    <div class="table-wrap"><table><thead><tr><th>时间</th><th>方向</th><th>动作</th><th>成交价</th><th>数量</th><th>名义价值</th><th>手续费</th><th>已实现盈亏</th><th>R</th><th>退出原因</th><th>订单ID</th></tr></thead><tbody id="historyBody"></tbody></table></div>
  </div>

  <div class="section"><h2>最近执行 / 日志</h2><div class="table-wrap"><table><thead><tr><th>时间</th><th>动作</th><th>状态</th><th>原因</th><th>成交数量</th><th>成交价</th><th>盈亏</th><th>手续费</th><th>订单ID</th></tr></thead><tbody id="eventsBody"></tbody></table></div></div>
  <footer>只读后台 · 不提供下单接口 · 管理服务仅监听本机回环地址</footer>
</div>
<script>
let DATA=null;
const $=id=>document.getElementById(id);
const num=(v,d=2)=>v===null||v===undefined||Number.isNaN(Number(v))?'—':Number(v).toFixed(d);
const money=v=>v===null||v===undefined?'—':`${Number(v)>=0?'+':''}${num(v,4)} USDT`;
const pct=v=>v===null||v===undefined?'—':`${num(Number(v)*100,1)}%`;
const pctRaw=v=>v===null||v===undefined?'—':`${num(v,2)}%`;
const cls=v=>Number(v)>0?'ok':Number(v)<0?'bad':'';
const safe=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const kv=(k,v,c='')=>`<div class="kv"><b>${safe(k)}</b><span class="${c}">${safe(v)}</span></div>`;
const boolPill=(name,v)=>`<span class="pill ${v?'ok':'bad'}">${safe(name)} · ${v?'PASS':'FAIL'}</span>`;
function render(){
  const d=DATA,p=d.pnl||{},pos=d.position||{},r=d.runtime||{},h=d.health||{},s=d.strategy||{},sig=d.signal||{};
  $('generated').textContent=`最后读取：${d.generated_at||'—'} · ${s.account_mode||'—'} / ${s.api_mode||'—'}`;
  $('equity').textContent=`${num(p.strategy_equity,4)} USDT`;
  $('totalPnl').textContent=money(p.total_pnl); $('totalPnl').className=`value ${cls(p.total_pnl)}`;
  $('pnlSplit').textContent=`已实现 ${money(p.realized_net_pnl)} · 浮动 ${money(p.unrealized_pnl)}`;
  $('positionQty').textContent=Number(pos.qty||0)===0?'空仓':`${num(pos.qty,6)} ZEC`;
  $('positionPnl').textContent=`Mark ${num(pos.mark_price,4)} · ${money(pos.unrealized_pnl)}`;
  $('liveState').textContent=r.real_order?'REAL ORDER ON':'LIVE OFF'; $('liveState').className=`value ${r.real_order?'bad':'ok'}`;
  $('preflightState').textContent=`只读 Preflight ${h.preflight_pass?'PASS':'未通过/运行中状态'}`;
  $('positionDetails').innerHTML=[kv('开仓价',num(pos.entry_price,4)),kv('Mark Price',num(pos.mark_price,4)),kv('名义价值',`${num(pos.notional,4)} USDT`),kv('浮动盈亏',money(pos.unrealized_pnl),cls(pos.unrealized_pnl)),kv('估算 ROE',pctRaw(pos.roe_pct_estimate),cls(pos.roe_pct_estimate)),kv('止损 SL',pos.stop_loss==null?'—':num(pos.stop_loss,4)),kv('止盈 TP',pos.take_profit==null?'—':num(pos.take_profit,4)),kv('距离 SL / TP',`${pctRaw(pos.distance_to_sl_pct)} / ${pctRaw(pos.distance_to_tp_pct)}`)].join('');
  $('pnlDetails').innerHTML=[kv('已平仓交易',String(p.closed_trades??0)),kv('胜率',pct(p.win_rate)),kv('平均盈利',money(p.avg_win),cls(p.avg_win)),kv('平均亏损',money(p.avg_loss),cls(p.avg_loss)),kv('Profit Factor',num(p.profit_factor,2)),kv('最大单笔盈利',money(p.max_win),cls(p.max_win)),kv('最大单笔亏损',money(p.max_loss),cls(p.max_loss)),kv('近 7 / 30 天',`${money(p.pnl_7d)} / ${money(p.pnl_30d)}`,cls(p.pnl_30d))].join('')+`<div class="tiny" style="grid-column:1/-1">${p.sample_status==='INSUFFICIENT_SAMPLE'?'样本不足 20 笔：统计仅供观察，不作为策略有效性结论。':'样本数量已达到基础统计门槛。'}</div>`;
  $('health').innerHTML=[boolPill('PAPI认证',h.api_authentication),boolPill('Portfolio Margin',h.portfolio_margin_access),boolPill('交易权限',h.trading_permission),`<span class="pill ${h.withdraw_permission==='OFF'?'ok':'bad'}">提现权限 · ${safe(h.withdraw_permission||'UNKNOWN')}</span>`,boolPill('IP限制',h.ip_restricted),boolPill('ZEC 50x',h.zecusdt_50x_allowed),`<span class="pill ${h.position_mode==='HEDGE'?'ok':'warn'}">持仓模式 · ${safe(h.position_mode||'UNKNOWN')}</span>`,`<span class="pill">账户杠杆 · ${safe(h.account_leverage??'—')}x</span>`,h.error?`<span class="pill bad">错误 · ${safe(h.error)}</span>`:''].join('');
  $('strategySignal').innerHTML=[kv('策略',`${s.symbol||'ZECUSDT'} ${s.timeframe||'4h'} ${s.direction||'LONG_ONLY'}`),kv('资金 / 单次 sizing',`${num(s.capital_pool_usdt,2)} / ${num(s.sizing_base_usdt,2)} USDT`),kv('杠杆 / 目标名义价值',`${s.leverage||50}x / ≈${num(s.target_initial_notional_usdt,2)} USDT`),kv('止盈模式',s.take_profit_mode||'FIXED_2R'),kv('当前阶段',sig.phase||'—'),kv('最近信号',sig.last_signal||'—'),kv('最近处理 4H K线',sig.last_processed_bar_close_time||'—'),kv('下个预期 4H 边界',sig.next_expected_bar_close_time||'—'),kv('待执行动作',sig.pending_action||'无'),kv('恢复状态',sig.recovery_status||'正常')].join('');
  renderHistory();
  const events=(d.recent_events||[]).slice(0,30);
  $('eventsBody').innerHTML=events.length?events.map(e=>`<tr><td>${safe(e.recorded_at||e.bar_close_time)}</td><td>${safe(e.action)}</td><td>${safe(e.status)}</td><td>${safe(e.reason)}</td><td>${num(e.filled_qty,6)}</td><td>${num(e.average_fill_price,4)}</td><td class="${cls(e.realized_pnl)}">${money(e.realized_pnl)}</td><td>${num(e.fee,6)}</td><td>${safe(e.exchange_order_id)}</td></tr>`).join(''):`<tr><td colspan="9" class="empty">暂无执行记录</td></tr>`;
}
function renderHistory(){if(!DATA)return;const q=($('historySearch').value||'').toLowerCase(),limit=Number($('historyLimit').value||20);let rows=(DATA.history||[]).filter(x=>!q||JSON.stringify([x.order_id,x.action,x.exit_reason,x.side]).toLowerCase().includes(q)).slice(0,limit);$('historyBody').innerHTML=rows.length?rows.map(x=>`<tr><td>${safe(x.time)}</td><td>${safe(x.side)}</td><td>${safe(x.action||'—')}</td><td>${num(x.price,4)}</td><td>${num(x.qty,6)}</td><td>${num(x.notional,4)}</td><td>${num(x.fee,6)} ${safe(x.fee_asset)}</td><td class="${cls(x.realized_pnl)}">${money(x.realized_pnl)}</td><td>${x.r_multiple==null?'—':num(x.r_multiple,2)+'R'}</td><td>${safe(x.exit_reason||'—')}</td><td>${safe(x.order_id)}</td></tr>`).join(''):`<tr><td colspan="11" class="empty">暂无历史成交</td></tr>`;}
async function loadData(){$('generated').textContent='读取中…';try{const res=await fetch('/api/snapshot',{cache:'no-store'});if(!res.ok)throw new Error(`HTTP ${res.status}`);DATA=await res.json();render();}catch(e){$('generated').textContent=`读取失败：${e.message}`;}}
loadData();
</script>
</body></html>
"""


class AdminHandler(BaseHTTPRequestHandler):
    server_version = "Zec4hAdmin/1.0"

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
        return hmac.compare_digest(supplied_user, expected_user) and hmac.compare_digest(supplied_password, expected_password)

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")

    def _require_auth(self) -> bool:
        if self._authenticated(): return True
        self.send_response(401); self.send_header("WWW-Authenticate", 'Basic realm="ZEC 4H Admin", charset="UTF-8"'); self._security_headers(); self.end_headers(); return False

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self._security_headers(); self.end_headers(); self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._require_auth(): return
        path = urlparse(self.path).path
        if path == "/":
            body = HTML.encode("utf-8"); self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self._security_headers(); self.end_headers(); self.wfile.write(body); return
        if path == "/api/snapshot": self._send_json(200, collect_admin_snapshot()); return
        if path == "/healthz": self._send_json(200, {"ok": True, "mode": "READ_ONLY"}); return
        self._send_json(404, {"error": "NOT_FOUND"})

    def do_POST(self) -> None:
        if not self._require_auth(): return
        self._send_json(405, {"error": "READ_ONLY_ADMIN_NO_WRITE_ENDPOINTS"})
    def do_PUT(self) -> None: self.do_POST()
    def do_DELETE(self) -> None: self.do_POST()
    def log_message(self, fmt: str, *args: object) -> None: sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    user = os.environ.get("ZEC_4H_ADMIN_USER", "").strip(); password = os.environ.get("ZEC_4H_ADMIN_PASSWORD", "")
    if not user or not password: print("ZEC_4H_ADMIN_CREDENTIALS_MISSING", file=sys.stderr); return 2
    bind = os.environ.get("ZEC_4H_ADMIN_BIND", "127.0.0.1").strip()
    if bind not in {"127.0.0.1", "::1", "localhost"}: print("ZEC_4H_ADMIN_BIND_MUST_BE_LOOPBACK", file=sys.stderr); return 2
    try: port = int(os.environ.get("ZEC_4H_ADMIN_PORT", "8765"))
    except ValueError: print("ZEC_4H_ADMIN_PORT_INVALID", file=sys.stderr); return 2
    if not 1 <= port <= 65535: print("ZEC_4H_ADMIN_PORT_INVALID", file=sys.stderr); return 2
    server = ThreadingHTTPServer((bind, port), AdminHandler); print(f"ZEC_4H_ADMIN_READ_ONLY listening on {bind}:{port}", flush=True)
    try: server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
