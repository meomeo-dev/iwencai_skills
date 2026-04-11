#!/usr/bin/env python3
"""
同花顺问财(iWencai)统一 CLI 运行时。

当前阶段提供 family-first 的 query2data/search/trade CLI，以及内置 skillbook 输出。
"""

from __future__ import annotations

import argparse
import html
import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable, MutableMapping
from pathlib import Path
from typing import Any

DEFAULT_API_URL = "https://openapi.iwencai.com/v1/query2data"
DEFAULT_SEARCH_API_URL = "https://openapi.iwencai.com/v1/comprehensive/search"
DEFAULT_SEARCH_APP_ID = "AIME_SKILL"
DEFAULT_SIMTRADE_BASE_URL = "http://trade.10jqka.com.cn:8088"
CANONICAL_PROGRAM_NAME = "iwencai"
DEVELOPMENT_ENTRYPOINT = "python iwencai_cli.py"
SKILLBOOK_FILE_NAME = "SKILL.md"
SKILLBOOK_INSTALL_DIR = "iwencai-official-cli"
DEFAULT_SKILLBOOK_FORMAT = "markdown"
DEFAULT_SIMTRADE_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_DEPARTMENT_ID = "997376"
DEFAULT_ACCOUNT_PATH = Path(__file__).resolve().parent / ".iwencai" / "default_account.json"
DEFAULT_DOTENV_PATHS = (
    Path.cwd() / ".env",
    Path(__file__).resolve().parent / ".env",
)
DEFAULT_PAGE = "1"
DEFAULT_LIMIT = "10"
DEFAULT_IS_CACHE = "1"
DEFAULT_EXPAND_INDEX = "true"
DEFAULT_API_KEY_SETUP_TIMEOUT_SECONDS = 600
SEARCH_CHANNELS = ("announcement", "investor", "news", "report")
SEARCH_CHANNEL_HELP = ", ".join(SEARCH_CHANNELS)
DEFAULT_NO_PROXY_HOSTS = tuple(
    dict.fromkeys(
        filter(
            None,
            (
                urllib.parse.urlparse(DEFAULT_API_URL).hostname,
                urllib.parse.urlparse(DEFAULT_SEARCH_API_URL).hostname,
                urllib.parse.urlparse(DEFAULT_SIMTRADE_BASE_URL).hostname,
            ),
        )
    )
)


class CLIHelpFormatter(argparse.RawTextHelpFormatter):
    """统一 CLI help formatter。"""

    def __init__(self, prog: str):
        super().__init__(prog, max_help_position=30, width=100)


ROOT_DESCRIPTION = (
    "官方 iWencai family-first CLI。\n"
    f"省略 family 时，默认按 query2data 执行；安装后命令名为 {CANONICAL_PROGRAM_NAME}。"
)
ROOT_EPILOG = (
    "快速开始:\n"
    f'  {CANONICAL_PROGRAM_NAME} -q "2连板股票"\n'
    f'  {CANONICAL_PROGRAM_NAME} search -q "最近的分红公告" --channel announcement\n'
    f"  {CANONICAL_PROGRAM_NAME} trade positions --format table\n"
    f"  {CANONICAL_PROGRAM_NAME} skillbook\n\n"
    "family 说明:\n"
    "  query2data  通用自然语言查询、选股、排行、指标筛选\n"
    "  search      公告/新闻/研报/投关活动搜索，可按 channel 收窄\n"
    "  trade       模拟炒股开户、下单、持仓、资金、成交查询\n"
    "  skillbook   输出内置 SKILL.md，帮助无状态 LLM 快速上手\n\n"
    "认证 UX:\n"
    "  query2data/search 未配置密钥时，交互式终端会自动拉起本地配置页\n"
    "  页面支持粘贴 API key，并可选择保存到当前目录 .env\n"
    "  默认等待 10 分钟，页面会显示倒计时；未完成时本次命令不会继续执行\n\n"
    "Query 写法:\n"
    "  query2data  主体 + 指标/事件；筛选时写 范围 + 条件/排序 + 时间窗\n"
    "  search      实体/主题 + 内容类型 + 时间词，如 公告/新闻/研究报告/投关活动\n"
    "  trade       显式子命令 + 参数，如 "
    "trade buy --stock-code 600519 --quantity 100 --price 1500\n"
    "  skillbook   直接读取内置技能书，适合给无状态 LLM 建立认知框架\n"
    "  避免        只写公司名、只写 好/强/便宜、把多个 family 混成一条"
)
QUERY2DATA_DESCRIPTION = (
    "直接调用官方 query2data family。\n"
    "问财更像弱 DSL，不是闲聊句子。\n"
    "适合自然语言条件查询、选股、排行、指标筛选；不需要指定 skill。\n"
    "若未配置 IWENCAI_API_KEY，交互式终端会自动打开本地配置页并显示倒计时。"
)
QUERY2DATA_EPILOG = (
    "推荐 query 写法:\n"
    "  检索类: 主体 + 指标/事件，如 宁德时代业绩预告 / 2024年中国GDP\n"
    "  筛选类: 范围 + 条件/排序 + 时间窗，如 近一年收益排名前十的基金经理\n"
    "  避免: 帮我选好基金 / 查一下公告并顺便筛股\n\n"
    "示例:\n"
    f'  {CANONICAL_PROGRAM_NAME} -q "2连板股票"\n'
    f'  {CANONICAL_PROGRAM_NAME} query2data -q "近5日主力资金净流入前10" --limit 10\n'
    f'  {CANONICAL_PROGRAM_NAME} query2data -q "市盈率最低的A股" --all-pages --format jsonl'
)
SEARCH_DESCRIPTION = (
    "直接调用官方 comprehensive/search family。\n"
    "适合搜索公告、新闻、研报、投资者关系活动；不指定 --channel 时会搜索全部官方频道。\n"
    "若未配置 IWENCAI_API_KEY，交互式终端会自动打开本地配置页并显示倒计时。"
)
SEARCH_EPILOG = (
    "推荐 query 写法:\n"
    "  实体/主题 + 内容类型 + 时间词，如 贵州茅台 公告 / 人工智能行业研究报告\n"
    "  不要只写公司名或主题名；最好写明 公告/新闻/研究报告/投资者关系活动\n"
    "  多主体时拆分查询，如 贵州茅台 公告 和 五粮液 公告\n\n"
    f"可用 channel: {SEARCH_CHANNEL_HELP}\n\n"
    "示例:\n"
    f'  {CANONICAL_PROGRAM_NAME} search -q "最近的分红公告"\n'
    f'  {CANONICAL_PROGRAM_NAME} search -q "近期业绩说明会" --channel investor\n'
    f'  {CANONICAL_PROGRAM_NAME} search -q "机器人行业深度报告" --channel report --limit 20'
)
TRADE_DESCRIPTION = (
    "官方模拟炒股 family。\n首次使用建议先执行 bootstrap-account；买卖仅支持 6 位 A 股代码。"
)
TRADE_EPILOG = (
    "示例:\n"
    f"  {CANONICAL_PROGRAM_NAME} trade bootstrap-account\n"
    f"  {CANONICAL_PROGRAM_NAME} trade positions --format table\n"
    f"  {CANONICAL_PROGRAM_NAME} trade buy --stock-code 600519 --price 1500 --quantity 100"
)
SKILLBOOK_DESCRIPTION = (
    "输出内置技能书 SKILL.md。\n"
    "默认直接输出原始 Markdown，适合无状态 LLM 直接读取并建立 iwencai 使用框架。"
)
SKILLBOOK_EPILOG = (
    "示例:\n"
    f"  {CANONICAL_PROGRAM_NAME} skillbook\n"
    f"  {CANONICAL_PROGRAM_NAME} skillbook --format json\n"
    f"  {CANONICAL_PROGRAM_NAME} skillbook --output ./iwencai-skillbook.md"
)
BUY_DESCRIPTION = "提交模拟买入委托。\n仅支持 6 位 A 股代码；数量必须为 100 股整数倍。"
SELL_DESCRIPTION = "提交模拟卖出委托。\n仅支持 6 位 A 股代码；数量必须为 100 股整数倍。"
ORDER_EPILOG_TEMPLATE = (
    f"示例:\n  {CANONICAL_PROGRAM_NAME} trade {{action}} "
    "--stock-code 600519 --price 1500 --quantity 100"
)
ACCOUNT_QUERY_DESCRIPTION = "查询当前模拟账户状态。\n如果本地不存在账户文件，会先自动开户后再查询。"
HISTORY_TRADES_DESCRIPTION = "查询历史成交记录。\n日期支持 YYYYMMDD 或 YYYY-MM-DD。"
HISTORY_TRADES_EPILOG = (
    f"示例:\n  {CANONICAL_PROGRAM_NAME} trade history-trades "
    "--start-date 20260101 --end-date 20260331"
)


class IWenCaiAPIError(Exception):
    """问财 API 通用错误异常。"""

    def __init__(self, message: str, status_code: int | None = None, response: str | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class SimTradeAPIError(Exception):
    """模拟炒股运行时异常。"""


class InteractiveSetupExit(Exception):
    """交互式配置未完成，但不属于系统异常。"""

    def __init__(self, status: str, message: str, exit_code: int = 2):
        super().__init__(message)
        self.status = status
        self.message = message
        self.exit_code = exit_code


def should_auto_launch_api_key_setup(
    env: MutableMapping[str, str] | None = None,
    *,
    interactive: bool | None = None,
) -> bool:
    """判断是否应在缺少 API key 时自动拉起本地配置页。"""
    if interactive is not None:
        return interactive

    target_env = os.environ if env is None else env
    disable_flag = target_env.get("IWENCAI_DISABLE_API_KEY_WEB_BOOTSTRAP", "").strip().casefold()
    if disable_flag in {"1", "true", "yes", "on"}:
        return False
    if target_env.get("CI", "").strip():
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def _format_dotenv_assignment(key: str, value: str) -> str:
    escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'{key}="{escaped_value}"'


def upsert_dotenv_variable(dotenv_path: Path, key: str, value: str) -> Path:
    """更新或新增 .env 变量，不破坏其他配置。"""
    resolved_path = dotenv_path.resolve()
    lines = resolved_path.read_text(encoding="utf-8").splitlines() if resolved_path.exists() else []
    target_prefixes = (f"{key}=", f"export {key}=")
    updated_lines: list[str] = []
    replacement = _format_dotenv_assignment(key, value)
    replaced = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(target_prefixes):
            if not replaced:
                updated_lines.append(replacement)
                replaced = True
            continue
        updated_lines.append(line)

    if not replaced:
        if updated_lines and updated_lines[-1] != "":
            updated_lines.append("")
        updated_lines.append(replacement)

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    return resolved_path


def _format_duration_label(timeout_seconds: float) -> str:
    whole_seconds = max(1, int(timeout_seconds))
    if whole_seconds % 60 == 0:
        minutes = whole_seconds // 60
        return f"{minutes} 分钟"
    return f"{whole_seconds} 秒"


def _render_api_key_setup_form(
    dotenv_path: Path,
    *,
    timeout_seconds: float,
    error_message: str | None = None,
) -> str:
    safe_error = html.escape(error_message or "")
    safe_path = html.escape(str(dotenv_path))
    error_block = ""
    if safe_error:
        error_block = (
            '<div class="notice notice-error">'
            '<span class="eyebrow">需要修正</span>'
            f"<strong>{safe_error}</strong>"
            "</div>"
        )
    timeout_label = html.escape(_format_duration_label(timeout_seconds))
    timeout_value = max(1, int(timeout_seconds))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>配置 IWENCAI_API_KEY</title>
  <style>
    :root {{
      --bg: #f5efe2;
      --panel: rgba(255, 251, 243, 0.92);
      --ink: #1c1917;
      --muted: #6b6257;
      --line: rgba(28, 25, 23, 0.14);
      --accent: #c2410c;
      --accent-strong: #9a3412;
      --shadow: 0 24px 80px rgba(28, 25, 23, 0.12);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(194, 65, 12, 0.16), transparent 32%),
        radial-gradient(circle at bottom right, rgba(120, 53, 15, 0.12), transparent 28%),
        linear-gradient(135deg, #f8f2e8 0%, #efe4d2 100%);
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      display: grid;
      place-items: center;
      padding: 24px;
    }}
    .shell {{
      width: min(720px, 100%);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      overflow: hidden;
      backdrop-filter: blur(14px);
    }}
    .hero {{
      padding: 28px 28px 18px;
      border-bottom: 1px solid var(--line);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.55), rgba(255,255,255,0.15)),
        repeating-linear-gradient(
          135deg,
          rgba(28,25,23,0.02) 0,
          rgba(28,25,23,0.02) 10px,
          transparent 10px,
          transparent 20px
        );
    }}
    .eyebrow {{
      display: inline-block;
      margin-bottom: 10px;
      color: var(--accent-strong);
      font: 600 12px/1.2 "Menlo", "SFMono-Regular", "Cascadia Mono", monospace;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(28px, 5vw, 42px);
      line-height: 1;
    }}
    p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
      font-size: 16px;
    }}
    .body {{
      padding: 24px 28px 28px;
      display: grid;
      gap: 18px;
    }}
    .notice {{
      border-radius: 18px;
      padding: 14px 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.7);
    }}
    .notice strong {{
      display: block;
      margin-top: 6px;
      font-size: 15px;
    }}
    .countdown {{
      display: grid;
      gap: 8px;
      padding: 18px;
      border-radius: 18px;
      border: 1px solid rgba(154, 52, 18, 0.16);
      background: rgba(255, 247, 237, 0.88);
    }}
    .countdown strong {{
      font-size: clamp(20px, 4vw, 28px);
      letter-spacing: 0.04em;
    }}
    .notice-error {{
      border-color: rgba(194, 65, 12, 0.22);
      background: rgba(255, 237, 213, 0.8);
    }}
    .grid {{
      display: grid;
      gap: 14px;
    }}
    label {{
      display: grid;
      gap: 8px;
      font: 600 14px/1.4 "Menlo", "SFMono-Regular", "Cascadia Mono", monospace;
      letter-spacing: 0.02em;
    }}
    input[type="password"] {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px 16px;
      background: rgba(255,255,255,0.82);
      color: var(--ink);
      font: 500 15px/1.4 "Menlo", "SFMono-Regular", "Cascadia Mono", monospace;
    }}
    input[type="password"]:focus {{
      outline: 2px solid rgba(194, 65, 12, 0.28);
      border-color: rgba(194, 65, 12, 0.36);
    }}
    .check {{
      display: grid;
      grid-template-columns: 20px 1fr;
      gap: 12px;
      align-items: start;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.68);
    }}
    .check input {{
      margin-top: 3px;
      accent-color: var(--accent);
    }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.6;
    }}
    code {{
      font-family: "Menlo", "SFMono-Regular", "Cascadia Mono", monospace;
      font-size: 13px;
      color: var(--accent-strong);
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 14px 22px;
      color: #fff7ed;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
      font: 700 14px/1 "Menlo", "SFMono-Regular", "Cascadia Mono", monospace;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      cursor: pointer;
      justify-self: start;
      box-shadow: 0 16px 32px rgba(154, 52, 18, 0.24);
    }}
    button:hover {{
      transform: translateY(-1px);
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <span class="eyebrow">IWENCAI API</span>
      <h1>配置访问密钥</h1>
      <p>当前命令缺少 <code>IWENCAI_API_KEY</code>。在这里粘贴密钥后，命令会继续执行。</p>
    </section>
    <section class="body">
      {error_block}
      <div class="notice">
        <span class="eyebrow">持久化选项</span>
        <strong>勾选后会写入当前目录的 <code>{safe_path}</code>，下次运行可自动复用。</strong>
      </div>
      <div class="countdown">
        <span class="eyebrow">倒计时</span>
        <strong id="countdown">--:--</strong>
        <span class="meta">
          当前页面默认保留 {timeout_label}。超时后，本次命令会结束但不会报系统错误。
        </span>
      </div>
      <form method="post" class="grid">
        <label>
          API Key
          <input type="password" name="api_key" autocomplete="off" autofocus required>
        </label>
        <label class="check">
          <input type="checkbox" name="persist_dotenv" checked>
          <span class="meta">
            保存到当前目录 <code>.env</code>。如果不勾选，本次只在当前进程内生效。
          </span>
        </label>
        <button type="submit">保存并继续</button>
      </form>
    </section>
  </main>
  <script>
    (function () {{
      var remaining = {timeout_value};
      var node = document.getElementById("countdown");
      function render() {{
        var minutes = String(Math.floor(remaining / 60)).padStart(2, "0");
        var seconds = String(remaining % 60).padStart(2, "0");
        node.textContent = minutes + ":" + seconds;
      }}
      render();
      window.setInterval(function () {{
        remaining = Math.max(0, remaining - 1);
        render();
      }}, 1000);
    }})();
  </script>
</body>
</html>
"""


def _render_api_key_setup_success(dotenv_path: Path, *, persisted: bool) -> str:
    saved_hint = (
        f"已写入 <code>{html.escape(str(dotenv_path))}</code>，后续运行会自动加载。"
        if persisted
        else "仅对当前命令进程生效，未写入磁盘。"
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>配置完成</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f5efe2;
      color: #1c1917;
      font-family: "Iowan Old Style", "Palatino Linotype", Georgia, serif;
      padding: 24px;
    }}
    .card {{
      width: min(560px, 100%);
      padding: 28px;
      border-radius: 24px;
      border: 1px solid rgba(28, 25, 23, 0.14);
      background: rgba(255, 251, 243, 0.94);
      box-shadow: 0 24px 80px rgba(28, 25, 23, 0.12);
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: clamp(26px, 4vw, 36px);
    }}
    p {{
      margin: 0;
      color: #6b6257;
      line-height: 1.6;
      font-size: 16px;
    }}
    code {{
      font-family: "Menlo", "SFMono-Regular", "Cascadia Mono", monospace;
      color: #9a3412;
    }}
  </style>
</head>
<body>
  <main class="card">
    <h1>密钥已接收，命令继续执行</h1>
    <p>{saved_hint}</p>
  </main>
  <script>
    window.setTimeout(function () {{
      window.close();
    }}, 1200);
  </script>
</body>
</html>
"""


def launch_api_key_setup_page(
    *,
    dotenv_path: Path,
    env: MutableMapping[str, str] | None = None,
    open_browser: bool = True,
    timeout_seconds: int = DEFAULT_API_KEY_SETUP_TIMEOUT_SECONDS,
    ready_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """启动本地 HTML 配置页，收集 API key 并可选择写入 .env。"""
    target_env = os.environ if env is None else env
    resolved_dotenv_path = dotenv_path.resolve()
    completed = threading.Event()
    setup_result: dict[str, Any] = {
        "success": False,
        "persisted": False,
        "dotenv_path": str(resolved_dotenv_path),
    }

    class APIKeySetupHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _write_html(self, status_code: int, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            self._write_html(
                200,
                _render_api_key_setup_form(
                    resolved_dotenv_path,
                    timeout_seconds=timeout_seconds,
                ),
            )

        def do_POST(self) -> None:  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            form = urllib.parse.parse_qs(raw_body, keep_blank_values=True)
            api_key_value = form.get("api_key", [""])[0].strip()
            persist_dotenv = form.get("persist_dotenv", [""])[0] in {"on", "1", "true", "yes"}

            if not api_key_value:
                self._write_html(
                    400,
                    _render_api_key_setup_form(
                        resolved_dotenv_path,
                        timeout_seconds=timeout_seconds,
                        error_message="API key 不能为空，请粘贴从问财技能页复制的密钥。",
                    ),
                )
                return

            target_env["IWENCAI_API_KEY"] = api_key_value
            setup_result["api_key"] = api_key_value
            setup_result["persisted"] = persist_dotenv
            setup_result["success"] = True

            if persist_dotenv:
                written_path = upsert_dotenv_variable(
                    resolved_dotenv_path,
                    "IWENCAI_API_KEY",
                    api_key_value,
                )
                setup_result["dotenv_path"] = str(written_path)

            self._write_html(
                200,
                _render_api_key_setup_success(
                    resolved_dotenv_path,
                    persisted=persist_dotenv,
                ),
            )
            completed.set()

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), APIKeySetupHandler)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        url = f"http://127.0.0.1:{server.server_port}/"
        setup_result["url"] = url
        timeout_label = _format_duration_label(timeout_seconds)
        print(
            f"未检测到 IWENCAI_API_KEY，正在启动本地配置页: {url}，等待最多 {timeout_label}",
            file=sys.stderr,
        )

        if ready_callback is not None:
            ready_callback(url)
            browser_opened = False
        else:
            browser_opened = webbrowser.open(url) if open_browser else False
            if not browser_opened:
                print(f"浏览器未自动打开，请手动访问: {url}", file=sys.stderr)
        setup_result["browser_opened"] = browser_opened

        try:
            if not completed.wait(timeout_seconds):
                raise InteractiveSetupExit(
                    status="timed_out",
                    message=(
                        f"等待 API 密钥配置已超时（{timeout_label}）。"
                        "当前命令未执行；重新运行会再次打开本地配置页，"
                        "也可提前写入当前目录 .env 或设置环境变量 IWENCAI_API_KEY。"
                    ),
                )
        except KeyboardInterrupt as err:
            raise InteractiveSetupExit(
                status="cancelled",
                message=("已取消本地 API 密钥配置，当前命令未执行。重新运行会再次打开本地配置页。"),
                exit_code=130,
            ) from err
        return setup_result
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1)


def ensure_no_proxy_hosts(
    hosts: tuple[str, ...] = DEFAULT_NO_PROXY_HOSTS,
    *,
    env: MutableMapping[str, str] | None = None,
) -> tuple[str, ...]:
    """把运行时官方域名合并进 NO_PROXY/no_proxy，避免本地 HTTP 代理劫持。"""
    target_env = os.environ if env is None else env
    merged_hosts: list[str] = []
    seen: set[str] = set()

    for key in ("NO_PROXY", "no_proxy"):
        for raw_part in target_env.get(key, "").split(","):
            part = raw_part.strip()
            normalized = part.casefold()
            if not part or normalized in seen:
                continue
            seen.add(normalized)
            merged_hosts.append(part)

    for host in hosts:
        normalized = host.strip().casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged_hosts.append(host)

    value = ",".join(merged_hosts)
    target_env["NO_PROXY"] = value
    target_env["no_proxy"] = value
    return tuple(merged_hosts)


ensure_no_proxy_hosts()


def load_local_env(
    dotenv_paths: tuple[Path, ...] = DEFAULT_DOTENV_PATHS,
    env: MutableMapping[str, str] | None = None,
) -> list[Path]:
    """从本地 .env 加载缺失的环境变量，不覆盖现有值。"""
    target_env = os.environ if env is None else env
    loaded_paths: list[Path] = []
    seen_paths: set[Path] = set()

    for raw_path in dotenv_paths:
        path = raw_path.resolve()
        if path in seen_paths or not path.exists():
            continue
        seen_paths.add(path)

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or key in target_env:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                value = value[1:-1]
            target_env[key] = value

        loaded_paths.append(path)

    return loaded_paths


def get_api_key(
    api_key: str | None = None,
    *,
    env: MutableMapping[str, str] | None = None,
    dotenv_paths: tuple[Path, ...] = DEFAULT_DOTENV_PATHS,
    interactive_bootstrap: bool | None = None,
    bootstrapper: Callable[..., dict[str, Any]] | None = None,
) -> str:
    """优先使用显式参数，否则从环境变量或本地 .env 获取 API key。"""
    if api_key:
        return api_key

    target_env = os.environ if env is None else env
    load_local_env(dotenv_paths=dotenv_paths, env=target_env)
    resolved_key = target_env.get("IWENCAI_API_KEY", "")
    should_bootstrap = should_auto_launch_api_key_setup(
        env=target_env,
        interactive=interactive_bootstrap,
    )

    if not resolved_key and should_bootstrap:
        setup = (bootstrapper or launch_api_key_setup_page)(
            dotenv_path=dotenv_paths[0],
            env=target_env,
        )
        resolved_key = str(setup.get("api_key", "")).strip()

    if not resolved_key:
        raise IWenCaiAPIError(
            "API密钥未设置，请通过环境变量 IWENCAI_API_KEY 或当前目录 .env 指定；"
            "交互式终端会自动拉起本地配置页"
        )
    return resolved_key


def list_search_channels() -> list[str]:
    return list(SEARCH_CHANNELS)


def _coerce_positive_int(raw_value: str, field_name: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as err:
        raise ValueError(f"{field_name} 必须是正整数: {raw_value}") from err
    if value <= 0:
        raise ValueError(f"{field_name} 必须大于 0: {raw_value}")
    return value


def _normalize_search_channels(channels: list[str] | None) -> list[str]:
    if not channels:
        return list_search_channels()

    normalized_channels: list[str] = []
    seen: set[str] = set()
    valid_channels = set(SEARCH_CHANNELS)

    for raw_value in channels:
        for part in raw_value.split(","):
            channel = part.strip().casefold()
            if not channel:
                continue
            if channel not in valid_channels:
                available = ", ".join(SEARCH_CHANNELS)
                raise ValueError(f"无效 channel: {channel}，可选值: {available}")
            if channel in seen:
                continue
            seen.add(channel)
            normalized_channels.append(channel)

    if not normalized_channels:
        raise ValueError("至少需要一个有效 channel")
    return normalized_channels


def _ensure_account_directory(account_path: Path = DEFAULT_ACCOUNT_PATH) -> None:
    account_path.parent.mkdir(parents=True, exist_ok=True)


def generate_simtrade_username() -> str:
    return f"iwencai_{int(time.time() * 1000)}"


def load_account_state(account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict | None:
    if not account_path.exists():
        return None
    return json.loads(account_path.read_text(encoding="utf-8"))


def save_account_state(account: dict, account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict:
    _ensure_account_directory(account_path)
    account_path.write_text(json.dumps(account, ensure_ascii=False, indent=2), encoding="utf-8")
    return account


def _simtrade_request(endpoint: str, params: dict[str, str]) -> dict:
    ensure_no_proxy_hosts()
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{DEFAULT_SIMTRADE_BASE_URL}{endpoint}?{query}",
        headers={"User-Agent": DEFAULT_SIMTRADE_USER_AGENT},
        method="GET",
    )
    opener = urllib.request.build_opener()
    try:
        with opener.open(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        response = err.read().decode("utf-8") if err.fp else ""
        raise SimTradeAPIError(f"HTTP错误 {err.code}: {err.reason}; {response}") from err
    except urllib.error.URLError as err:
        raise SimTradeAPIError(f"网络错误: {err.reason}") from err
    except json.JSONDecodeError as err:
        raise SimTradeAPIError(f"响应解析失败: {err}") from err


def _raise_simtrade_error(payload: dict, action_name: str) -> None:
    if "ret" in payload and isinstance(payload["ret"], dict):
        code = str(payload["ret"].get("code", "0"))
        if code != "0":
            raise SimTradeAPIError(f"{action_name}失败: {payload['ret'].get('msg', '未知错误')}")
        return
    if "error_no" in payload:
        code = str(payload.get("error_no", "0"))
        if code != "0":
            raise SimTradeAPIError(f"{action_name}失败: {payload.get('error_info', '未知错误')}")
        return
    if "errorcode" in payload:
        code = str(payload.get("errorcode", "0"))
        if code != "0":
            raise SimTradeAPIError(f"{action_name}失败: {payload.get('errormsg', '未知错误')}")
        return
    if "code" in payload:
        code = str(payload.get("code", "0"))
        if code != "0":
            raise SimTradeAPIError(f"{action_name}失败: {payload.get('msg', '未知错误')}")


def create_simtrade_capital_account(
    username: str,
    department_id: str = DEFAULT_DEPARTMENT_ID,
) -> dict:
    payload = _simtrade_request(
        "/pt_add_user",
        {"usrname": username, "yybid": department_id, "datatype": "json"},
    )
    _raise_simtrade_error(payload, "开户")
    capital_account = payload.get("errormsg", "")
    if not capital_account:
        raise SimTradeAPIError("开户成功但未返回资金账号")
    return {
        "username": username,
        "capital_account": capital_account,
        "department_id": department_id,
    }


def query_simtrade_shareholder_accounts(
    capital_account: str,
    department_id: str = DEFAULT_DEPARTMENT_ID,
) -> dict:
    payload = _simtrade_request(
        "/pt_qry_stkaccount_dklc",
        {"usrid": capital_account, "yybid": department_id, "datatype": "json"},
    )
    _raise_simtrade_error(payload, "查询股东账号")
    items = payload.get("result", []) or payload.get("list", [])
    shareholder_accounts: dict[str, str] = {}
    market_codes: dict[str, str] = {}
    for item in items:
        market_code = item.get("scdm")
        shareholder_account = item.get("gddm") or item.get("gdzh")
        if not shareholder_account:
            continue
        if market_code == "1":
            shareholder_accounts["sz"] = shareholder_account
            market_codes["sz"] = "1"
        elif market_code == "2":
            shareholder_accounts["sh"] = shareholder_account
            market_codes["sh"] = "2"
    if not shareholder_accounts:
        raise SimTradeAPIError("未查询到有效股东账号")
    return {"shareholder_accounts": shareholder_accounts, "market_codes": market_codes}


def bootstrap_simtrade_account(
    account_path: Path = DEFAULT_ACCOUNT_PATH,
    *,
    force: bool = False,
) -> dict:
    existing = load_account_state(account_path)
    if existing and not force:
        return existing

    username = generate_simtrade_username()
    account = create_simtrade_capital_account(username=username)
    account.update(
        query_simtrade_shareholder_accounts(account["capital_account"], account["department_id"])
    )
    save_account_state(account, account_path)
    return account


def infer_market_from_stock_code(stock_code: str) -> str:
    if not re.fullmatch(r"\d{6}", stock_code):
        raise ValueError(f"仅支持 6 位 A 股代码: {stock_code}")
    if stock_code.startswith(("60", "68", "90")):
        return "sh"
    return "sz"


def validate_trade_order(price: float, quantity: int) -> None:
    if price <= 0:
        raise ValueError(f"价格必须大于 0: {price}")
    if quantity <= 0:
        raise ValueError(f"数量必须大于 0: {quantity}")
    if quantity % 100 != 0:
        raise ValueError(f"数量必须是 100 的整数倍: {quantity}")


def _add_output_options(container: Any) -> None:
    container.add_argument(
        "--format",
        choices=["json", "jsonl", "table"],
        default="json",
        help="输出格式；json 适合程序消费，table 适合终端查看",
    )
    container.add_argument(
        "--output", type=str, default=None, help="输出文件路径；默认直接打印到终端"
    )


def _add_api_key_option(container: Any) -> None:
    container.add_argument(
        "--api-key",
        type=str,
        default=None,
        help=(
            "问财 API 密钥；未提供时会先读 IWENCAI_API_KEY/.env，交互式终端缺失时自动打开本地配置页"
        ),
    )


def _add_skillbook_output_options(container: Any) -> None:
    container.add_argument(
        "--format",
        choices=["markdown", "json"],
        default=DEFAULT_SKILLBOOK_FORMAT,
        help="输出格式；markdown 默认输出原始技能书，json 适合程序消费",
    )
    container.add_argument(
        "--output", type=str, default=None, help="输出文件路径；默认直接打印到终端"
    )


def get_skillbook_candidate_paths() -> list[Path]:
    module_dir = Path(__file__).resolve().parent
    return [
        module_dir / SKILLBOOK_FILE_NAME,
        Path(sys.prefix) / "share" / SKILLBOOK_INSTALL_DIR / SKILLBOOK_FILE_NAME,
    ]


def resolve_skillbook_path() -> Path:
    for candidate in get_skillbook_candidate_paths():
        if candidate.is_file():
            return candidate
    searched_paths = "、".join(str(path) for path in get_skillbook_candidate_paths())
    raise ValueError(f"未找到内置技能书 {SKILLBOOK_FILE_NAME}。已检查路径: {searched_paths}")


def load_skillbook_content() -> tuple[Path, str]:
    skillbook_path = resolve_skillbook_path()
    try:
        return skillbook_path, skillbook_path.read_text(encoding="utf-8")
    except OSError as err:
        raise ValueError(f"读取内置技能书失败: {skillbook_path} ({err})") from err


def build_parser(prog: str = CANONICAL_PROGRAM_NAME) -> argparse.ArgumentParser:
    """构建统一 CLI parser。"""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=ROOT_DESCRIPTION,
        epilog=ROOT_EPILOG,
        formatter_class=CLIHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", title="family 子命令")

    query_parser = subparsers.add_parser(
        "query2data",
        help="通用自然语言查询、选股、排行、指标筛选",
        description=QUERY2DATA_DESCRIPTION,
        epilog=QUERY2DATA_EPILOG,
        formatter_class=CLIHelpFormatter,
    )
    query_input_group = query_parser.add_argument_group("查询输入")
    query_input_group.add_argument(
        "--query",
        "-q",
        type=str,
        required=True,
        help="查询语句；建议写成 主体 + 指标/事件，或 范围 + 条件/排序 + 时间窗",
    )
    query_paging_group = query_parser.add_argument_group("分页控制")
    query_paging_group.add_argument(
        "--page",
        type=str,
        default=DEFAULT_PAGE,
        help=f"起始页码；默认 {DEFAULT_PAGE}",
    )
    query_paging_group.add_argument(
        "--limit",
        type=str,
        default=DEFAULT_LIMIT,
        help=f"每页返回条数上限；默认 {DEFAULT_LIMIT}",
    )
    query_paging_group.add_argument(
        "--all-pages",
        action="store_true",
        help="从起始页继续翻页，直到当前查询结果拉取完毕",
    )
    query_runtime_group = query_parser.add_argument_group("请求控制")
    query_runtime_group.add_argument(
        "--is-cache",
        type=str,
        default=DEFAULT_IS_CACHE,
        help=f"问财缓存参数；默认 {DEFAULT_IS_CACHE}",
    )
    query_auth_group = query_parser.add_argument_group("身份认证")
    _add_api_key_option(query_auth_group)
    query_output_group = query_parser.add_argument_group("输出控制")
    _add_output_options(query_output_group)

    search_parser = subparsers.add_parser(
        "search",
        help="公告、新闻、研报、投关活动搜索",
        description=SEARCH_DESCRIPTION,
        epilog=SEARCH_EPILOG,
        formatter_class=CLIHelpFormatter,
    )
    search_input_group = search_parser.add_argument_group("查询输入")
    search_input_group.add_argument(
        "--query",
        "-q",
        type=str,
        required=True,
        help="搜索语句；建议写成 实体/主题 + 内容类型 + 时间词",
    )
    search_scope_group = search_parser.add_argument_group("搜索范围")
    search_scope_group.add_argument(
        "--channel",
        action="append",
        default=None,
        help="搜索频道；可重复指定或用逗号分隔。不指定时覆盖全部官方频道",
    )
    search_scope_group.add_argument(
        "--limit",
        type=str,
        default=DEFAULT_LIMIT,
        help=f"最终输出条数上限；默认 {DEFAULT_LIMIT}",
    )
    search_auth_group = search_parser.add_argument_group("身份认证")
    _add_api_key_option(search_auth_group)
    search_output_group = search_parser.add_argument_group("输出控制")
    _add_output_options(search_output_group)

    skillbook_parser = subparsers.add_parser(
        "skillbook",
        help="输出内置技能书，帮助无状态 LLM 快速上手",
        description=SKILLBOOK_DESCRIPTION,
        epilog=SKILLBOOK_EPILOG,
        formatter_class=CLIHelpFormatter,
    )
    skillbook_output_group = skillbook_parser.add_argument_group("输出控制")
    _add_skillbook_output_options(skillbook_output_group)

    trade_parser = subparsers.add_parser(
        "trade",
        help="模拟炒股开户、下单、持仓、资金、成交查询",
        description=TRADE_DESCRIPTION,
        epilog=TRADE_EPILOG,
        formatter_class=CLIHelpFormatter,
    )
    trade_subparsers = trade_parser.add_subparsers(dest="trade_command", title="交易动作")
    trade_subparsers.required = True

    bootstrap_parser = trade_subparsers.add_parser(
        "bootstrap-account",
        help="初始化或复用模拟账户",
        description="初始化本地默认模拟账户；若已存在则直接复用。",
        epilog=f"示例:\n  {CANONICAL_PROGRAM_NAME} trade bootstrap-account",
        formatter_class=CLIHelpFormatter,
    )
    bootstrap_output_group = bootstrap_parser.add_argument_group("输出控制")
    _add_output_options(bootstrap_output_group)

    show_account_parser = trade_subparsers.add_parser(
        "show-account",
        help="显示当前模拟账户",
        description=ACCOUNT_QUERY_DESCRIPTION,
        epilog=f"示例:\n  {CANONICAL_PROGRAM_NAME} trade show-account",
        formatter_class=CLIHelpFormatter,
    )
    show_account_output_group = show_account_parser.add_argument_group("输出控制")
    _add_output_options(show_account_output_group)

    for command_name in ("buy", "sell"):
        action_label = "买入" if command_name == "buy" else "卖出"
        description = BUY_DESCRIPTION if command_name == "buy" else SELL_DESCRIPTION
        order_parser = trade_subparsers.add_parser(
            command_name,
            help=f"{action_label} A 股委托",
            description=description,
            epilog=ORDER_EPILOG_TEMPLATE.format(action=command_name),
            formatter_class=CLIHelpFormatter,
        )
        order_input_group = order_parser.add_argument_group("交易参数")
        order_input_group.add_argument("--stock-code", required=True, help="6 位 A 股代码")
        order_input_group.add_argument(
            "--price", type=float, required=True, help="委托价格；必须大于 0"
        )
        order_input_group.add_argument(
            "--quantity",
            type=int,
            required=True,
            help="委托数量；必须为 100 股整数倍",
        )
        order_output_group = order_parser.add_argument_group("输出控制")
        _add_output_options(order_output_group)

    for command_name, help_text in (
        ("positions", "查询持仓"),
        ("profit", "查询盈利情况"),
        ("fund", "查询资金"),
        ("today-trades", "查询当日成交"),
        ("gain-30d", "查询近30天收益"),
    ):
        parser_description = f"{help_text}。\n如果本地不存在账户文件，会先自动开户后再查询。"
        trade_query_parser = trade_subparsers.add_parser(
            command_name,
            help=help_text,
            description=parser_description,
            epilog=f"示例:\n  {CANONICAL_PROGRAM_NAME} trade {command_name}",
            formatter_class=CLIHelpFormatter,
        )
        trade_query_output_group = trade_query_parser.add_argument_group("输出控制")
        _add_output_options(trade_query_output_group)

    history_parser = trade_subparsers.add_parser(
        "history-trades",
        help="查询历史成交",
        description=HISTORY_TRADES_DESCRIPTION,
        epilog=HISTORY_TRADES_EPILOG,
        formatter_class=CLIHelpFormatter,
    )
    history_range_group = history_parser.add_argument_group("时间范围")
    history_range_group.add_argument(
        "--start-date",
        required=True,
        help="开始日期；支持 YYYYMMDD 或 YYYY-MM-DD",
    )
    history_range_group.add_argument(
        "--end-date",
        required=True,
        help="结束日期；支持 YYYYMMDD 或 YYYY-MM-DD",
    )
    history_output_group = history_parser.add_argument_group("输出控制")
    _add_output_options(history_output_group)

    return parser


def _normalize_argv(argv: list[str]) -> list[str]:
    if not argv:
        return []
    if argv[0] in {"-h", "--help"}:
        return argv
    if argv[0] not in {"query2data", "search", "skillbook", "trade"}:
        return ["query2data", *argv]
    return argv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = build_parser()
    incoming = list(sys.argv[1:] if argv is None else argv)
    normalized = _normalize_argv(incoming)
    if not normalized:
        parser.print_help()
        raise SystemExit(0)
    return parser.parse_args(normalized)


def query_iwencai(query: str, page: str, limit: str, is_cache: str, api_key: str) -> dict:
    """调用问财通用 query2data 接口。"""
    api_key = get_api_key(api_key)
    ensure_no_proxy_hosts()

    payload = {
        "query": query,
        "page": page,
        "limit": limit,
        "is_cache": is_cache,
        "expand_index": DEFAULT_EXPAND_INDEX,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    request = urllib.request.Request(
        DEFAULT_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    opener = urllib.request.build_opener()

    try:
        with opener.open(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            result = json.loads(response_body)

        if isinstance(result, dict):
            if result.get("status_code", 0) != 0:
                message = result.get("status_msg", "未知错误")
                raise IWenCaiAPIError(f"API返回错误: {message}")

            return {
                "datas": result.get("datas", []),
                "total_count": result.get("code_count", 0),
                "chunks_info": result.get("chunks_info", {}),
            }
        return {"datas": [], "total_count": 0, "chunks_info": {}}
    except urllib.error.HTTPError as err:
        error_body = err.read().decode("utf-8") if err.fp else ""
        raise IWenCaiAPIError(
            f"HTTP错误 {err.code}: {err.reason}",
            status_code=err.code,
            response=error_body,
        ) from err
    except urllib.error.URLError as err:
        raise IWenCaiAPIError(f"网络错误: {err.reason}") from err
    except json.JSONDecodeError as err:
        raise IWenCaiAPIError(f"响应解析失败: {err}") from err


def query_search_channels(
    channels: list[str],
    query: str,
    api_key: str | None = None,
) -> list[dict]:
    """调用问财 comprehensive/search 接口。"""
    effective_api_key = get_api_key(api_key)
    ensure_no_proxy_hosts()

    payload = {
        "channels": channels,
        "app_id": DEFAULT_SEARCH_APP_ID,
        "query": query,
    }
    headers = {
        "Authorization": f"Bearer {effective_api_key}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        DEFAULT_SEARCH_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    opener = urllib.request.build_opener()

    try:
        with opener.open(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            result = json.loads(response_body)

        if not isinstance(result, dict):
            return []
        if "error" in result:
            raise IWenCaiAPIError(f"API返回错误: {result['error']}")
        data = result.get("data", [])
        return data if isinstance(data, list) else []
    except urllib.error.HTTPError as err:
        error_body = err.read().decode("utf-8") if err.fp else ""
        raise IWenCaiAPIError(
            f"HTTP错误 {err.code}: {err.reason}",
            status_code=err.code,
            response=error_body,
        ) from err
    except urllib.error.URLError as err:
        raise IWenCaiAPIError(f"网络错误: {err.reason}") from err
    except json.JSONDecodeError as err:
        raise IWenCaiAPIError(f"响应解析失败: {err}") from err


def execute_query2data_family(
    query: str,
    page: str = DEFAULT_PAGE,
    limit: str = DEFAULT_LIMIT,
    is_cache: str = DEFAULT_IS_CACHE,
    api_key: str | None = None,
    *,
    all_pages: bool = False,
) -> dict:
    """执行 query2data family 并返回统一 envelope。"""

    start_page = _coerce_positive_int(page, "page")
    page_size = _coerce_positive_int(limit, "limit")
    current_page = start_page
    aggregated_items: list[dict] = []
    chunks_info: dict = {}
    total_count = 0
    pages_fetched: list[int] = []

    while True:
        page_result = query_iwencai(
            query=query,
            page=str(current_page),
            limit=str(page_size),
            is_cache=is_cache,
            api_key=api_key or "",
        )
        page_items = page_result.get("datas", [])
        aggregated_items.extend(page_items)
        pages_fetched.append(current_page)
        chunks_info = page_result.get("chunks_info", {})
        total_count = max(total_count, int(page_result.get("total_count", 0)))

        if not all_pages:
            break
        if not page_items:
            break
        if total_count and len(aggregated_items) >= total_count:
            break
        if len(page_items) < page_size:
            break
        current_page += 1

    has_more = total_count > len(aggregated_items)
    output = {
        "success": True,
        "family": "query2data",
        "query": query,
        "page": start_page,
        "limit": page_size,
        "all_pages": all_pages,
        "pages_fetched": pages_fetched,
        "returned_count": len(aggregated_items),
        "total_count": total_count,
        "has_more": has_more,
        "source": {
            "provider": "同花顺问财",
            "endpoint": DEFAULT_API_URL,
        },
        "chunks_info": chunks_info,
        "items": aggregated_items,
        "datas": aggregated_items,
    }
    if has_more:
        output["pagination_tip"] = (
            f"共查到 {total_count} 条数据，当前累计返回 {len(aggregated_items)} 条。"
            "如需更多数据，请使用 --all-pages 或调整分页参数。"
        )
    return output


def execute_search_family(
    query: str,
    channels: list[str] | None = None,
    limit: str = DEFAULT_LIMIT,
    api_key: str | None = None,
) -> dict:
    """执行 comprehensive_search family 并返回统一 envelope。"""
    normalized_channels = _normalize_search_channels(channels)

    max_items = _coerce_positive_int(limit, "limit")
    articles = query_search_channels(normalized_channels, query=query, api_key=api_key)
    trimmed_articles = articles[:max_items]

    source = {
        "provider": "同花顺问财",
        "endpoint": DEFAULT_SEARCH_API_URL,
        "channels": normalized_channels,
        "app_id": DEFAULT_SEARCH_APP_ID,
    }
    if len(normalized_channels) == 1:
        source["channel"] = normalized_channels[0]

    return {
        "success": True,
        "family": "comprehensive_search",
        "query": query,
        "limit": max_items,
        "returned_count": len(trimmed_articles),
        "total_count": len(articles),
        "has_more": len(articles) > len(trimmed_articles),
        "source": source,
        "items": trimmed_articles,
        "data": trimmed_articles,
    }


def place_simtrade_order(
    action: str,
    stock_code: str,
    price: float,
    quantity: int,
    account_path: Path = DEFAULT_ACCOUNT_PATH,
) -> dict:
    account = bootstrap_simtrade_account(account_path)
    validate_trade_order(price, quantity)

    normalized_action = action.lower()
    if normalized_action not in {"buy", "sell"}:
        raise ValueError(f"仅支持 buy/sell: {action}")

    market = infer_market_from_stock_code(stock_code)
    direction = "B" if normalized_action == "buy" else "S"
    payload = _simtrade_request(
        "/pt_stk_weituo_dklc",
        {
            "usrid": account["capital_account"],
            "zqdm": stock_code,
            "gddh": account["shareholder_accounts"][market],
            "scdm": account["market_codes"][market],
            "yybd": account["department_id"],
            "wtjg": str(price),
            "wtsl": str(quantity),
            "mmlb": direction,
            "datatype": "json",
        },
    )
    _raise_simtrade_error(payload, "委托下单")
    result = payload.get("result", [])
    if isinstance(result, list):
        order_data = result[0] if result else {}
    else:
        order_data = result
    return {
        "success": True,
        "action": normalized_action,
        "stock_code": stock_code,
        "price": price,
        "quantity": quantity,
        "account_id": account["capital_account"],
        "entrust_no": order_data.get("entrust_no"),
        "raw": payload,
    }


def query_simtrade_positions(account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict:
    account = bootstrap_simtrade_account(account_path)
    payload = _simtrade_request(
        "/pt_web_qry_stock",
        {
            "name": account["capital_account"],
            "yybid": account["department_id"],
            "type": "1",
            "datatype": "json",
        },
    )
    _raise_simtrade_error(payload, "查询持仓")
    items = payload.get("result", []) or payload.get("list", []) or payload.get("data", [])
    return {"items": items, "total_count": len(items), "account_id": account["capital_account"]}


def query_simtrade_profit(account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict:
    account = bootstrap_simtrade_account(account_path)
    payload = _simtrade_request(
        "/pt_qry_userinfo_v1",
        {
            "usrname": account["username"],
            "yybid": account["department_id"],
            "type": "",
            "datatype": "json",
        },
    )
    _raise_simtrade_error(payload, "查询盈利情况")
    items = payload.get("list", [])
    return {"item": items[0] if items else {}, "account_id": account["capital_account"]}


def query_simtrade_fund(account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict:
    account = bootstrap_simtrade_account(account_path)
    payload = _simtrade_request(
        "/pt_qry_fund_t",
        {"usrid": account["capital_account"], "datatype": "json"},
    )
    _raise_simtrade_error(payload, "查询资金")
    items = payload.get("list", []) or payload.get("result", {}).get("list", [])
    return {"item": items[0] if items else {}, "account_id": account["capital_account"]}


def query_simtrade_today_trades(account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict:
    account = bootstrap_simtrade_account(account_path)
    payload = _simtrade_request(
        "/pt_qry_busin_nocache",
        {"usrname": account["capital_account"], "kind": "1", "datatype": "json"},
    )
    _raise_simtrade_error(payload, "查询当日成交")
    items = payload.get("result", []) or payload.get("list", [])
    if not items and isinstance(payload.get("ret"), dict):
        items = payload["ret"].get("item", [])
    return {"items": items, "total_count": len(items), "account_id": account["capital_account"]}


def query_simtrade_history_trades(
    start_date: str,
    end_date: str,
    account_path: Path = DEFAULT_ACCOUNT_PATH,
) -> dict:
    account = bootstrap_simtrade_account(account_path)
    payload = _simtrade_request(
        "/pt_qry_busin1",
        {
            "usrname": account["capital_account"],
            "start": start_date,
            "end": end_date,
            "yhbId": account["department_id"],
            "kind": "1",
            "datatype": "json",
        },
    )
    _raise_simtrade_error(payload, "查询历史成交")
    items = payload.get("list", [])
    return {"items": items, "total_count": len(items), "account_id": account["capital_account"]}


def query_simtrade_gain_30d(account_path: Path = DEFAULT_ACCOUNT_PATH) -> dict:
    account = bootstrap_simtrade_account(account_path)
    payload = _simtrade_request("/pt_qry_gainstat", {"usrid": account["capital_account"]})
    _raise_simtrade_error(payload, "查询近30天收益")
    return {"item": payload.get("data", {}), "account_id": account["capital_account"]}


def execute_skillbook_command() -> dict:
    skillbook_path, content = load_skillbook_content()
    return {
        "success": True,
        "command": "skillbook",
        "source_path": str(skillbook_path),
        "content": content,
    }


def _normalize_trade_date(raw_value: str) -> str:
    compact = raw_value.replace("-", "")
    if not re.fullmatch(r"\d{8}", compact):
        raise ValueError(f"日期格式无效，需为 YYYYMMDD 或 YYYY-MM-DD: {raw_value}")
    return compact


def _extract_output_items(payload: object) -> list[dict] | None:
    if isinstance(payload, list):
        return payload if all(isinstance(item, dict) for item in payload) else None
    if isinstance(payload, dict):
        for key in ("items", "datas", "data"):
            value = payload.get(key)
            if isinstance(value, list) and all(isinstance(item, dict) for item in value):
                return value
        item = payload.get("item")
        if isinstance(item, dict):
            return [item]
    return None


def _render_table_rows(rows: list[dict]) -> str:
    if not rows:
        return "(empty)"
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)

    widths = {column: len(column) for column in columns}
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized_row: dict[str, str] = {}
        for column in columns:
            value = row.get(column, "")
            cell = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            normalized_row[column] = cell
            widths[column] = max(widths[column], len(cell))
        normalized_rows.append(normalized_row)

    header = " | ".join(column.ljust(widths[column]) for column in columns)
    divider = "-+-".join("-" * widths[column] for column in columns)
    body = [
        " | ".join(row[column].ljust(widths[column]) for column in columns)
        for row in normalized_rows
    ]
    return "\n".join([header, divider, *body])


def render_output(payload: object, output_format: str) -> str:
    if output_format == "markdown":
        if isinstance(payload, dict) and isinstance(payload.get("content"), str):
            return payload["content"]
        if isinstance(payload, str):
            return payload
        raise ValueError("markdown 输出仅支持字符串或带 content 字段的对象")
    if output_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2)
    if output_format == "jsonl":
        items = _extract_output_items(payload)
        if items is None:
            return json.dumps(payload, ensure_ascii=False)
        return "\n".join(json.dumps(item, ensure_ascii=False) for item in items)
    if output_format == "table":
        items = _extract_output_items(payload)
        if items is not None:
            return _render_table_rows(items)
        if isinstance(payload, dict):
            return _render_table_rows(
                [{"field": key, "value": value} for key, value in payload.items()]
            )
        return str(payload)
    raise ValueError(f"不支持的输出格式: {output_format}")


def emit_output(payload: object, output_format: str, output_path: str | None) -> None:
    rendered = render_output(payload, output_format)
    if output_path:
        Path(output_path).write_text(
            rendered + ("\n" if not rendered.endswith("\n") else ""), encoding="utf-8"
        )
        return
    print(rendered)


def handle_query2data_command(args: argparse.Namespace) -> dict:
    return execute_query2data_family(
        query=args.query,
        page=args.page,
        limit=args.limit,
        is_cache=args.is_cache,
        api_key=args.api_key,
        all_pages=args.all_pages,
    )


def handle_search_command(args: argparse.Namespace) -> dict:
    return execute_search_family(
        query=args.query,
        channels=args.channel,
        limit=args.limit,
        api_key=args.api_key,
    )


def handle_skillbook_command(args: argparse.Namespace) -> dict:
    del args
    return execute_skillbook_command()


def handle_trade_command(args: argparse.Namespace) -> dict:
    if args.trade_command == "bootstrap-account":
        return bootstrap_simtrade_account()
    if args.trade_command == "show-account":
        return load_account_state() or bootstrap_simtrade_account()
    if args.trade_command == "buy":
        return place_simtrade_order(
            action="buy",
            stock_code=args.stock_code,
            price=args.price,
            quantity=args.quantity,
        )
    if args.trade_command == "sell":
        return place_simtrade_order(
            action="sell",
            stock_code=args.stock_code,
            price=args.price,
            quantity=args.quantity,
        )
    if args.trade_command == "positions":
        return query_simtrade_positions()
    if args.trade_command == "profit":
        return query_simtrade_profit()
    if args.trade_command == "fund":
        return query_simtrade_fund()
    if args.trade_command == "today-trades":
        return query_simtrade_today_trades()
    if args.trade_command == "history-trades":
        return query_simtrade_history_trades(
            start_date=_normalize_trade_date(args.start_date),
            end_date=_normalize_trade_date(args.end_date),
        )
    if args.trade_command == "gain-30d":
        return query_simtrade_gain_30d()
    raise ValueError("trade 子命令不能为空")


def main() -> None:
    """CLI 入口。"""
    args = parse_args()

    try:
        if args.command == "query2data":
            payload = handle_query2data_command(args)
        elif args.command == "search":
            payload = handle_search_command(args)
        elif args.command == "skillbook":
            payload = handle_skillbook_command(args)
        elif args.command == "trade":
            payload = handle_trade_command(args)
        else:
            raise ValueError(f"未知命令: {args.command}")

        emit_output(payload, getattr(args, "format", "json"), getattr(args, "output", None))
    except ValueError as err:
        print(json.dumps({"success": False, "error": str(err)}, ensure_ascii=False, indent=2))
        sys.exit(2)
    except IWenCaiAPIError as err:
        print(json.dumps({"success": False, "error": err.message}, ensure_ascii=False, indent=2))
        sys.exit(1)
    except SimTradeAPIError as err:
        print(json.dumps({"success": False, "error": str(err)}, ensure_ascii=False, indent=2))
        sys.exit(1)
    except InteractiveSetupExit as event:
        print(
            json.dumps(
                {
                    "success": False,
                    "status": event.status,
                    "message": event.message,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(event.exit_code)
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "success": False,
                    "status": "cancelled",
                    "message": "用户已取消当前命令。",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(130)
    except Exception as err:
        print(
            json.dumps(
                {"success": False, "error": f"发生系统错误: {str(err)}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
