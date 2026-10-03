#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║          🎓  EWT360 智能刷课助手 · 单文件完整版                        ║
║                       ewt_brush_optimized.py                          ║
╚══════════════════════════════════════════════════════════════════════╝

【这是什么】
  一个「开箱即用」的 EWT360（升学 e网通）自动刷课工具。
  引擎 + 引导界面全部打包在这一个文件里，无需其他任何脚本。

【怎么用】
  1) 安装依赖（只需一次）：
         pip install -r requirements.txt
     若没有 requirements.txt，也可直接：
         pip install httpx pycryptodome
  2) 直接运行本文件：
         python3 ewt_brush_optimized.py
  3) 按屏幕提示回答几个问题（账号密码、配置），全程自动完成。

【特色】
  · 单文件：不会再出现"找不到主脚本"的困扰
  · 智能引导：全程中文提示，小白也能用
  · 彩色界面：进度条、状态一目了然
  · 引擎能力：登录签名头降风控 / FM板报直写 / 过课检测对齐 /
              完成判定阈值 0.8 / 进度延迟复核 / token 自动续期
  · 快速复核：达标即停，实测 21 分钟视频约 41 秒刷完

【Windows 中文乱码修复】
  本脚本已内置 UTF-8 加固，一般无需设置。若仍报 UnicodeEncodeError：
    PowerShell:  $env:PYTHONUTF8="1" ; py ewt_brush_optimized.py
    CMD:         set PYTHONUTF8=1 && py ewt_brush_optimized.py

【合并说明】
  本文件由 ewt_brush_v3_test.py（引擎）+ ewt_brush_easy_v3_test.py（引导）
  合并优化而成，功能完全保留，并重做了操作界面。
"""

import argparse
import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
import re
import sys
import threading
import time
import urllib.parse
import uuid

# ======================================================================
# 【自动依赖安装】小白无需手动 pip，首次运行自动检测并安装
# ======================================================================
_REQUIRED_PKGS = [("httpx", "httpx"), ("Crypto", "pycryptodome")]


def _ensure_dependencies():
    """检测缺失依赖并自动安装（失败则给出清晰指引）。"""
    import importlib
    import subprocess

    missing = []
    for mod_name, pkg_name in _REQUIRED_PKGS:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            missing.append((mod_name, pkg_name))

    if not missing:
        return

    print()
    print("  " + "=" * 58)
    print("   📦 检测到缺少运行所需的组件，正在自动安装…")
    for mod_name, pkg_name in missing:
        print(f"      · {pkg_name}")
    print("  " + "=" * 58)
    print("   （只需安装一次，请稍候，约 10~60 秒）")
    print()

    ok_all = True
    for mod_name, pkg_name in missing:
        installed = False
        # 依次尝试多种 pip 调用方式（兼容 Windows / Linux / macOS / Termux）
        for cmd in (
            [sys.executable, "-m", "pip", "install", pkg_name],
            [sys.executable, "-m", "pip", "install", "--user", pkg_name],
            [sys.executable, "-m", "pip", "install",
             "--break-system-packages", pkg_name],
            ["pip3", "install", pkg_name],
            ["pip", "install", pkg_name],
        ):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if r.returncode == 0:
                    installed = True
                    break
            except Exception:
                continue
        if installed:
            print(f"   ✅ {pkg_name} 安装成功")
        else:
            ok_all = False
            print(f"   ❌ {pkg_name} 安装失败")

    print()
    if ok_all:
        print("  🎉 组件全部就绪，即将启动程序…")
        print()
        try:
            time.sleep(1)
        except Exception:
            pass
    else:
        print("  " + "=" * 58)
        print("   ⚠️  自动安装失败，请手动执行下面任意一条命令：")
        print()
        print(f"      {sys.executable} -m pip install httpx pycryptodome")
        print("      或：  pip install httpx pycryptodome")
        print()
        print("   💡 若提示权限不足，命令后面加 --user")
        print("   💡 若在手机上（Termux），可能需要先执行：")
        print("         pkg install python")
        print("  " + "=" * 58)
        sys.exit(1)


try:
    _ensure_dependencies()
except SystemExit:
    raise
except Exception:
    pass  # 检测本身异常时不阻断，交给后续 import 报错

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# ---- Windows/终端 UTF-8 加固：强制 stdout/stderr 用 UTF-8，避免中文 UnicodeEncodeError ----
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# ======================================================================
# [常量]
# ======================================================================
GATEWAY = "https://gateway.ewt360.com"
BFE = "https://bfe.ewt360.com"
VIDEO_BIZ_CODE = "1013"          # 普通视频
SCHOOL_VIDEO_BIZ_CODE = "1014"   # 校本视频
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76"
)
SPEED = 2                # 硬上限！speed=2.1 即触发 699001（实测验证）
BURST_SIZE = 12          # 单课时竞态爆发并发路数（--burst 可调）
BURST_WAIT = 10          # 爆发间隔（秒）— bucket refill 约需 ~12s
STAY_MS = 10000          # 单轮推进（毫秒）— 每次上报声称的播放时长（可调，越大越快）
FAST_MODE = True         # [默认] 快速复核循环：0.2s 高频爆发+每波查进度提前停（实测 9~32 倍速）
FAST_INTERVAL = 0.2      # [v3-test] 快速模式波间隔（秒），实测 48发/波 + 0.2s ≈ 9~32倍速

# ---- [进度面板] 全局渲染钩子：run_brush_all 会安装 ProgressDashboard ----
_PROGRESS_SINK = None   # 存在时接管刷课输出（原地刷新面板）


def _install_sink(dash) -> None:
    """安装/卸载进度面板（传入 None 则卸载并关闭旧面板）。"""
    global _PROGRESS_SINK
    old = _PROGRESS_SINK
    if old is not None and old is not dash:
        try:
            old.close()
        except Exception:
            pass
    _PROGRESS_SINK = dash if (dash is not None and getattr(dash, "enabled", False)) else None


def _p_log(msg: str) -> None:
    """刷课期间的日志输出：有面板交给面板，否则直接打印。"""
    if _PROGRESS_SINK is not None:
        try:
            _PROGRESS_SINK.show_log(msg)
            return
        except Exception:
            pass
    print(msg, flush=True)

FAST_MAX_ROUNDS = 400    # [v3-test] 快速模式单课时最大波数（防死循环兜底）
MAX_LOGIN_RETRY = 3      # token 自动续期上限
# WAF 风控缓解配置
WAF_BACKOFF_SECONDS = 120.0   # WAF 拦截后冷却秒数
WAF_RETRY_COUNT = 2           # 冷却重试上限（超过则失败）
# ⚠ 安全：无内置默认账号！账号密码必须由用户显式提供
# （--account/--password 参数，或终端下交互输入）
# token 文件路径：可用环境变量 EWT_TOKEN_FILE 覆盖（手机端 Termux 等无 /root 目录时必用）
TOKEN_FILE = os.environ.get("EWT_TOKEN_FILE", "/root/ewt_token.txt")

logger = logging.getLogger("ewt_brush")


# ======================================================================
# [异常]
# ======================================================================
class WafCaptchaBlocked(RuntimeError):
    """EWT 风控/WAF 拦截（JSON 429「安全威胁」或 HTML 滑块）。"""


class TokenInvalidError(RuntimeError):
    """Token 失效 / 被挤下线（2001106 等）。"""


def is_waf_blocked(data) -> bool:
    """识别 EWT 网关返回的 JSON 429「安全威胁」风控拦截。"""
    if not isinstance(data, dict):
        return False
    return data.get("code") == 429 and "安全威胁" in str(data.get("msg", ""))


def is_waf_captcha(response) -> bool:
    """检测阿里云 WAF 滑块验证（acw_tc 人机验证）。"""
    ct = response.headers.get("Content-Type", "")
    if "text/html" in ct:
        return True
    text = response.text[:200] if hasattr(response, "text") else ""
    if not text:
        return False
    return not text.startswith("{")


_TOKEN_INVALID_MARKERS = (
    "2001106", "其他地方登录", "登录状态已过期", "登录已过期",
    "重新登录", "token 无效", "Token 已失效", "未登录",
)


def _is_token_invalid(msg: str) -> bool:
    if not msg:
        return False
    return any(m in msg for m in _TOKEN_INVALID_MARKERS)


# ======================================================================
# [签名] HMAC-SHA1 — 完全复刻 MSTPlayer makeSecretKey()
# ======================================================================
def make_signature(action: int, duration: int, mstid: str,
                   timestamp_ms: int, secret: str) -> str:
    params = {
        "action": str(action),
        "duration": str(duration),
        "mstid": mstid,
        "signatureMethod": "HMAC-SHA1",
        "signatureVersion": "1.0",
        "timestamp": str(timestamp_ms),
        "version": "2022-08-02",
    }
    sign_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hmac.new(secret.encode(), sign_str.encode(), hashlib.sha1).hexdigest()


# ======================================================================
# [限速器] 全局 EWT 网关令牌桶（跨所有请求共享）
# ======================================================================
class _TokenBucket:
    def __init__(self) -> None:
        self._rate = 120.0 / 60.0   # tokens/秒
        self._capacity = 120.0
        self._tokens = 0.0
        self._last_ts = 0.0

    def configure(self, per_minute: float) -> None:
        per_minute = max(0.1, float(per_minute))
        self._rate = per_minute / 60.0
        self._capacity = max(1.0, per_minute)

    async def acquire(self) -> None:
        now = time.monotonic()
        if self._last_ts == 0:
            self._last_ts = now
            self._tokens = self._capacity
        else:
            self._tokens = min(self._capacity, self._tokens + (now - self._last_ts) * self._rate)
            self._last_ts = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return
        wait = (1.0 - self._tokens) / max(self._rate, 1e-6)
        await asyncio.sleep(wait)
        self._tokens = 0.0
        self._last_ts = time.monotonic()


_gateway_limiter = _TokenBucket()


def set_gateway_qps_cap(per_minute: float) -> None:
    """由 CLI（--qps）覆盖全局网关 QPS 上限。"""
    _gateway_limiter.configure(per_minute)


# ======================================================================
# [热更新] 运行中动态调整 burst / qps（网页端 /api/config 写配置文件）
# ======================================================================
LIVE_CONFIG_FILE = "/tmp/ewt_live_config.json"


def _load_live_config() -> dict | None:
    """读取网页端热更新配置；无文件/损坏返回 None。"""
    try:
        with open(LIVE_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _apply_live_config() -> None:
    """把热更新配置应用到全局（burst→BURST_SIZE，qps→限流器）。"""
    global BURST_SIZE
    live = _load_live_config()
    if not live:
        return
    try:
        b = int(live.get("burst") or 0)
        if 1 <= b <= 64:
            BURST_SIZE = b
    except (TypeError, ValueError):
        pass
    try:
        q = int(live.get("qps") or 0)
        if q > 0:
            set_gateway_qps_cap(q)
    except (TypeError, ValueError):
        pass


def _live_config_watcher() -> None:
    """后台线程：每 2 秒检查一次热更新配置，运行中即时生效。"""
    while True:
        try:
            _apply_live_config()
        except Exception:
            pass
        time.sleep(2)


threading.Thread(target=_live_config_watcher, daemon=True).start()


# ======================================================================
# [登录] AES 加密密码 → oauth 登录 → token
# ======================================================================
def aes_encrypt(word: str) -> str:
    key = b"20171109124536982017110912453698"
    iv = b"2017110912453698"
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct = cipher.encrypt(pad(word.encode("utf-8"), AES.block_size))
    return ct.hex().upper()


def _find_token(obj, depth=0) -> str | None:
    """递归查找响应里的 token 字段。"""
    if depth > 4 or obj is None:
        return None
    if isinstance(obj, dict):
        for k in ("token", "accessToken", "access_token", "ticket"):
            v = obj.get(k)
            if isinstance(v, str) and re.match(r"^\d+-(1|2)-[0-9a-fA-F]+$", v):
                return v
        for v in obj.values():
            t = _find_token(v, depth + 1)
            if t:
                return t
    elif isinstance(obj, list):
        for v in obj:
            t = _find_token(v, depth + 1)
            if t:
                return t
    return None


async def login(account: str, password: str, save_file: str = TOKEN_FILE) -> str:
    """登录获取 token 并保存到文件。"""
    enc = aes_encrypt(password)
    url = f"{GATEWAY}/api/authcenter/v2/oauth/login/account"
    ts = int(time.time() * 1000)
    body = {
        "userName": account,
        "password": enc,
        "webVersion": "pc_20250101",
        "platform": 1,          # ⚠️ 必须是 platform（不是 platformType）
        "autoLogin": "true",
    }
    headers = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Origin": "https://web.ewt360.com",
        "Referer": "https://web.ewt360.com/",
        # [测试版] 补齐 Web 端签名头（secretId=2）：模拟真实浏览器登录，降低风控识别概率
        "secretid": "2",
        "timestamp": str(ts),
        "sign": hashlib.md5(f"{ts}bdc739ff2dcf".encode()).hexdigest().upper(),
        "platform": "1",
    }
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as c:
        r = await c.post(url, json=body, headers=headers)
        try:
            j = r.json()
        except Exception:
            raise RuntimeError(f"登录失败: 非 JSON 响应 HTTP {r.status_code}")
        if not j.get("success"):
            raise RuntimeError(f"登录失败: {j.get('msg', j)}")
        tok = _find_token(j.get("data"))
        if not tok:
            raise RuntimeError(f"登录成功但未找到 token: {str(j)[:200]}")
    try:
        with open(save_file, "w") as f:
            f.write(tok)
    except Exception:
        pass
    return tok


def load_token_file(path: str = TOKEN_FILE) -> str | None:
    try:
        with open(path) as f:
            tok = f.read().strip()
        if re.match(r"^\d+-(1|2)-[0-9a-fA-F]+$", tok):
            return tok
    except Exception:
        pass
    return None

# ======================================================================
# [登录方式] 账号密码 / 扫码 / 手动 token
#   扫码端点逆向自 web.ewt360.com/register 前端（register-pc）
# ======================================================================

def _auth_headers() -> dict:
    """web 端鉴权请求头（签名 secretId=2）。"""
    ts = int(time.time() * 1000)
    return {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Origin": "https://web.ewt360.com",
        "Referer": "https://web.ewt360.com/",
        "secretid": "2",
        "timestamp": str(ts),
        "sign": hashlib.md5(f"{ts}bdc739ff2dcf".encode()).hexdigest().upper(),
        "platform": "1",
    }


async def qrcode_generate() -> dict:
    """生成登录二维码，返回 {uuid, qrcodeUrl, h5Url, nativeUrl, expireTime}。"""
    url = f"{GATEWAY}/api/authcenter/v2/oauth/login/qrcode/generate"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, json={}, headers=_auth_headers())
        j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"生成二维码失败: {j.get('msg', j)}")
    return j["data"]


async def qrcode_status(uuid: str) -> dict:
    """查询扫码状态：1未扫 2已扫 3取消 4确认 5过期。status=4 时 loginInfo 含 token。"""
    url = f"{GATEWAY}/api/authcenter/v2/oauth/login/qrcode/status"
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, json={"uuid": uuid}, headers=_auth_headers())
        j = r.json()
    if not j.get("success"):
        raise RuntimeError(f"查询扫码状态失败: {j.get('msg', j)}")
    return j.get("data") or {}


def _render_qr_terminal(text: str):
    """把文本渲染成终端二维码；依赖 qrcode 库，缺失时返回 None。"""
    try:
        import qrcode  # type: ignore
    except Exception:
        return None
    try:
        qr = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(text)
        qr.make(fit=True)
        m = qr.get_matrix()
        lines = []
        for y in range(0, len(m), 2):
            row = ""
            for x in range(len(m[0])):
                top = m[y][x]
                bot = m[y + 1][x] if y + 1 < len(m) else False
                if top and bot:
                    row += "█"
                elif top:
                    row += "▀"
                elif bot:
                    row += "▄"
                else:
                    row += " "
            lines.append(row)
        return "\n".join(lines)
    except Exception:
        return None


async def _qrcode_show() -> tuple:
    """生成并展示二维码，返回 (uuid, qr_url)。"""
    data = await qrcode_generate()
    uuid = data.get("uuid") or ""
    qr_url = (data.get("qrcodeUrl") or data.get("h5Url")
              or data.get("nativeUrl") or "")
    pr()
    pr(color("   ─────────────   二维码   ─────────────", C.CYAN))
    art = _render_qr_terminal(qr_url)
    if art:
        for line in art.split("\n"):
            pr("   " + line)
    else:
        warn("未安装 qrcode 库，无法在终端绘制二维码")
        pr(color("   请复制下方链接到手机浏览器打开扫码：", C.CYAN))
        pr(f"   {color(qr_url, C.B + C.BLUE)}")
        pr(color("   或安装后重跑：pip install qrcode", C.DIM))
    pr(color("   ─────────────────────────────────────", C.CYAN))
    pr()
    info("用【升学 e网通 APP】> 首页 > 扫一扫 扫描二维码")
    pr(color("   [R] 刷新二维码    [Q] 取消登录", C.DIM))
    return uuid, qr_url


async def login_by_qrcode(save_file: str = TOKEN_FILE,
                          timeout_sec: int = 300,
                          poll_interval: float = 2.0) -> str:
    """扫码登录：生成二维码 → 轮询（可 R 刷新 / Q 取消）→ 返回 token。"""
    try:
        import select as _select
    except Exception:
        _select = None

    pr()
    title("扫码登录", "📱")
    uuid, _ = await _qrcode_show()
    start = time.time()
    last_status = None
    interactive = bool(sys.stdin.isatty()) and _select is not None

    while time.time() - start < timeout_sec:
        if interactive:
            try:
                rl, _, _ = _select.select([sys.stdin], [], [], poll_interval)
            except Exception:
                rl = []
                await asyncio.sleep(poll_interval)
            if rl:
                line = sys.stdin.readline()
                if line:
                    key = line.strip().lower()
                    if key == "q":
                        raise RuntimeError("已取消扫码登录")
                    if key == "r":
                        info("正在刷新二维码…")
                        uuid, _ = await _qrcode_show()
                        start = time.time()
                        last_status = None
                        continue
        else:
            await asyncio.sleep(poll_interval)

        try:
            st = await qrcode_status(uuid)
        except Exception as e:
            warn(f"状态查询失败：{str(e)[:60]}")
            continue

        status = st.get("status")
        if status == 3:
            warn("二维码已被取消，正在刷新…")
            uuid, _ = await _qrcode_show()
            start = time.time()
            last_status = None
            continue
        if status == 5:
            warn("二维码已过期，正在自动刷新…")
            uuid, _ = await _qrcode_show()
            start = time.time()
            last_status = None
            continue

        if status != last_status:
            if status == 1:
                pr(color("   ⏳ 等待扫码…", C.DIM))
            elif status == 2:
                pr(color("   📲 已扫码，请在手机上点击「确认登录」", C.B + C.YELLOW))
            last_status = status

        if status == 4:
            li = st.get("loginInfo") or {}
            tok = _find_token(li)
            if not tok:
                for k in ("token", "accessToken", "ticket"):
                    v = li.get(k)
                    if isinstance(v, str) and v:
                        tok = v
                        break
            if not tok:
                raise RuntimeError(f"扫码成功但未取到 token：{str(li)[:150]}")
            pr()
            ok(f"扫码登录成功！{tok[:14]}…{tok[-6:]}")
            try:
                with open(save_file, "w") as f:
                    f.write(tok)
            except Exception:
                pass
            return tok

    raise RuntimeError("扫码登录超时，请重新运行")


async def login_interactive(cfg: dict) -> str:
    """交互式选择登录方式，返回 token。"""
    pr()
    title("选择登录方式", "🔐")
    pr(color("   1", C.B + C.CYAN) + "  账号密码登录")
    pr(color("   2", C.B + C.CYAN) + "  扫码登录")
    pr(color("   3", C.B + C.CYAN) + "  手动粘贴 token")
    pr()

    saved = str(cfg.get("login_method", "1"))
    if saved not in ("1", "2", "3"):
        saved = "1"
    choice = ask("请选择（1-3）", saved).strip() or saved

    if choice == "2":
        cfg["login_method"] = "2"
        return await login_by_qrcode()

    if choice == "3":
        tok = ask("token", None, "格式：数字-1-十六进制")
        if not re.match(r"^\d+-(1|2)-[0-9a-fA-F]+$", tok or ""):
            raise RuntimeError("token 格式不正确")
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(tok)
        except Exception:
            pass
        cfg["login_method"] = "3"
        ok(f"已保存 token：{tok[:14]}…{tok[-6:]}")
        return tok

    account = ask("账号", cfg.get("account"))
    if not account:
        raise RuntimeError("账号不能为空")
    password = ask("密码", cfg.get("password"))
    if not password:
        raise RuntimeError("密码不能为空")
    cfg["account"] = account
    cfg["password"] = password
    cfg["login_method"] = "1"
    pr(color("  ⏳ 正在登录，请稍候…", C.BLUE))
    tok = await login(account, password)
    ok(f"登录成功  {tok[:14]}…{tok[-6:]}")
    return tok

# ======================================================================
# [客户端] EwtClient — 网关请求封装（带全局限速 + WAF 识别）
# ======================================================================
class EwtClient:
    def __init__(self, token: str):
        self.token = token
        self.user_id = int(token.split("-")[0])
        self._client = httpx.AsyncClient(timeout=30, verify=True)

    @property
    def _headers(self):
        return {
            "User-Agent": UA,
            "token": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://teacher.ewt360.com",
            "Referer": "https://teacher.ewt360.com/",
            "Ewt-Requestsource": "web",
            "Ewt-Contentstyle": "CamelCase",
        }

    @staticmethod
    def _parse(r: httpx.Response) -> dict:
        """解析网关响应；WAF 拦截统一抛 WafCaptchaBlocked。"""
        try:
            data = r.json()
        except Exception:
            raise WafCaptchaBlocked(f"WAF 滑块验证拦截（HTTP {r.status_code}，非 JSON）")
        if is_waf_blocked(data):
            raise WafCaptchaBlocked(f"EWT 风控拦截: {data.get('msg', '')[:80]}")
        return data

    async def _get(self, path: str, params: dict = None) -> dict:
        await _gateway_limiter.acquire()
        r = await self._client.get(f"{GATEWAY}{path}", params=params or {}, headers=self._headers)
        return self._parse(r)

    async def _post(self, path: str, body: dict = None, headers: dict = None) -> dict:
        h = {**self._headers}
        if headers:
            h.update(headers)
        await _gateway_limiter.acquire()
        r = await self._client.post(f"{GATEWAY}{path}", json=body or {}, headers=h)
        return self._parse(r)

    # ---------- 播放器 ----------
    async def fetch_global_conf(self, biz_code: str = VIDEO_BIZ_CODE) -> dict:
        """返回 {sessionId, secret, clientIp, ts, diffTime}"""
        local_ts = int(time.time() * 1000)
        data = await self._get(
            "/api/videoplayerprod/videoplayer/getPlayerGlobalConf",
            {"videoBizCode": biz_code, "sdkVersion": "3.0.37", "_": local_ts},
        )
        if not data.get("success"):
            raise RuntimeError(f"getPlayerGlobalConf failed: {data}")
        g = data["data"]["globalInfo"]
        return {
            "sessionId": g["sessionId"],
            "secret": g["secret"],
            "clientIp": g["clientIp"],
            "ts": int(g.get("ts", 0)),
            "diffTime": int(g.get("ts", 0)) - local_ts,
        }

    async def fetch_player_token(self, school_id: int, lesson_id: int,
                                 content_type: int = 1) -> str:
        data = await self._post(
            "/api/homeworkprod/player/getPlayerToken",
            {"schoolId": school_id, "lessonId": lesson_id, "type": 1,
             "contentType": content_type, "videoBizCode": VIDEO_BIZ_CODE},
        )
        if not data.get("success"):
            raise RuntimeError(f"getPlayerToken failed: {data}")
        return data["data"]

    # ---------- 作业/任务 ----------
    async def list_homeworks(self, school_id: int) -> list[dict]:
        """获取作业列表。优先 status=0 一次拉取全部（含已截止，参考
        chentinghong578-bit/ewt-auto-player 实测参数），失败回退 1/2/3 分态查询。
        token 失效抛 TokenInvalidError。"""
        # 快路径：status=0 全量单次查询（1 次请求 vs 原来 3+ 次）
        try:
            page_index = 1
            all_hws = []
            while True:
                data = await self._post(
                    "/api/homeworkprod/homework/student/getStudentHomeworkInfo",
                    {"schoolId": school_id, "status": 0, "pageIndex": page_index, "pageSize": 100},
                )
                if data.get("success"):
                    hws = data["data"]
                    all_hws.extend(hws)
                    if len(hws) < 100:
                        break
                    page_index += 1
                else:
                    code = str(data.get("code", ""))
                    msg = str(data.get("msg", ""))
                    if _is_token_invalid(f"{code} {msg}"):
                        raise TokenInvalidError(f"EWT Token 已失效（{code} {msg[:40]}）")
                    all_hws = []  # status=0 不被支持，回退分态查询
                    break
            if all_hws:
                seen = set()
                uniq = []
                for hw in all_hws:
                    hid = hw.get("homeworkId")
                    if hid and hid not in seen:
                        seen.add(hid)
                        uniq.append(hw)
                return uniq
        except TokenInvalidError:
            raise
        except Exception:
            pass  # 任何异常都回退老路径
        # 慢路径：status 1/2/3 分态查询（兼容回退）
        seen = set()
        all_hws = []
        for st in [1, 2, 3]:
            page_index = 1
            while True:
                data = await self._post(
                    "/api/homeworkprod/homework/student/getStudentHomeworkInfo",
                    {"schoolId": school_id, "status": st, "pageIndex": page_index, "pageSize": 100},
                )
                if data.get("success"):
                    hws = data["data"]
                    for hw in hws:
                        hid = hw.get("homeworkId")
                        if hid and hid not in seen:
                            seen.add(hid)
                            all_hws.append(hw)
                    if len(hws) < 100:
                        break
                    page_index += 1
                else:
                    code = str(data.get("code", ""))
                    msg = str(data.get("msg", ""))
                    if _is_token_invalid(f"{code} {msg}"):
                        raise TokenInvalidError(f"EWT Token 已失效（{code} {msg[:40]}）")
                    break
        return all_hws

    async def get_homework_must_subjects(self, school_id: int, homework_id: int) -> list[int]:
        """获取作业详情里的必学科目清单（学生真实选科）。"""
        data = await self._post(
            "/api/homeworkprod/student/homework/task/getStudentHomeworkInfo",
            {"schoolId": school_id, "homeworkId": homework_id},
        )
        if not data.get("success") or not data.get("data"):
            raise RuntimeError(f"getStudentHomeworkInfo failed: {data.get('msg', '')}")
        return data["data"].get("mustLearnSubjectList") or []

    async def list_tasks(self, school_id: int, homework_id: int,
                         subject_id: str | int = None,
                         day_id: str = None,
                         must_learn_subjects: list[int] = None) -> list[dict]:
        """获取作业下的课时任务（16 科目并发拉取，queryMustLearn=1 必学）。"""
        if must_learn_subjects is None:
            must_learn_subjects = list(range(1, 17))
        if not day_id and not subject_id:
            async def _fetch_subj(subj: int) -> list[dict]:
                subj_tasks: list[dict] = []
                page_index = 1
                while True:
                    body = {
                        "schoolId": school_id,
                        "homeworkId": homework_id,
                        "pageIndex": page_index,
                        "pageSize": 500,   # [优化] 100→500，减少翻页请求
                        "subjectId": subj,
                        "mustLearnSubjectList": [subj],
                        "queryMustLearn": 1,
                    }
                    data = await self._post(
                        "/api/homeworkprod/student/homework/task/pageHomeworkTasks", body)
                    if not data.get("success"):
                        break
                    pkg = data.get("data", {})
                    tasks = pkg.get("data") or pkg.get("list") or pkg.get("records") or []
                    subj_tasks.extend(tasks)
                    total = pkg.get("totalRecords", 0)
                    if len(subj_tasks) >= total or len(tasks) == 0:
                        break
                    page_index += 1
                return subj_tasks
            # [修复] 并发拉取 + 失败重试2次（原先静默丢弃失败科目 → 会漏课时）
            subjects = list(range(1, 17))
            results = await asyncio.gather(
                *(_fetch_subj(s) for s in subjects),
                return_exceptions=True,
            )
            failed = [subjects[i] for i, r in enumerate(results)
                      if isinstance(r, BaseException)]
            for _retry in range(2):
                if not failed:
                    break
                retry_res = await asyncio.gather(
                    *(_fetch_subj(s) for s in failed),
                    return_exceptions=True,
                )
                for i, r in enumerate(retry_res):
                    if not isinstance(r, BaseException):
                        idx = subjects.index(failed[i])
                        results[idx] = r
                failed = [failed[i] for i, r in enumerate(retry_res)
                          if isinstance(r, BaseException)]
            if failed:
                print(f"  WARNING: 科目 {failed} 拉取失败（已重试2次）")
            all_tasks: list[dict] = []
            seen_ids: set = set()
            for r in results:
                if isinstance(r, BaseException):
                    continue
                for t in r:
                    lid = t.get("contentId")
                    if lid and lid in seen_ids:
                        continue
                    if lid:
                        seen_ids.add(lid)
                    all_tasks.append(t)
            return all_tasks
        # 按日期/科目过滤模式（queryMustLearn=1 和 =2 都查）
        all_tasks = []
        for query_must in (1, 2):
            page_index = 1
            mode_count = 0
            while True:
                body = {
                    "schoolId": school_id,
                    "homeworkId": homework_id,
                    "pageIndex": page_index,
                    "pageSize": 100,
                    "mustLearnSubjectList": must_learn_subjects,
                    "queryMustLearn": query_must,
                }
                if day_id:
                    body["dayId"] = day_id
                if subject_id:
                    body["subjectId"] = int(subject_id)
                data = await self._post(
                    "/api/homeworkprod/student/homework/task/pageHomeworkTasks", body)
                if not data.get("success"):
                    break
                pkg = data.get("data", {})
                tasks = pkg.get("data") or pkg.get("list") or pkg.get("records") or []
                all_tasks.extend(tasks)
                mode_count += len(tasks)
                total = pkg.get("totalRecords", 0)
                if mode_count >= total or len(tasks) == 0:
                    break
                page_index += 1
        return all_tasks

    async def get_day_subject_stat(self, school_id: int, homework_id: int,
                                   must_learn_subjects: list[int] = None) -> dict:
        """获取作业的日期分组统计，返回 {dateStat, subjectStat, homeworkStat}"""
        if must_learn_subjects is None:
            must_learn_subjects = list(range(1, 17))
        data = await self._post(
            "/api/homeworkprod/student/homework/task/getStudentHomeworkDaySubjectStat",
            {"schoolId": school_id, "homeworkId": homework_id,
             "mustLearnSubjectList": must_learn_subjects},
        )
        if not data.get("success") or not data.get("data"):
            raise RuntimeError(f"getStudentHomeworkDaySubjectStat failed: {data.get('msg', '')}")
        return data["data"]

    async def list_video_tasks(self, school_id: int, homework_id: int,
                               must_learn_subjects: list[int] = None,
                               include_finished: bool = False,
                               max_concurrency: int = 10) -> list[dict]:
        """按日期分组**并行**拉取作业下全部视频/校本课时（contentType 1/11）。"""
        if must_learn_subjects is None:
            must_learn_subjects = list(range(1, 17))
        try:
            stat = await self.get_day_subject_stat(school_id, homework_id,
                                                   must_learn_subjects=must_learn_subjects)
            date_stat = stat.get("dateStat", [])
        except Exception:
            date_stat = []
        sem = asyncio.Semaphore(max_concurrency)

        def _build(t: dict, ds: dict | None) -> dict | None:
            ct = t.get("contentType", 1)
            # [测试版] 扩展收集任务型：1=视频 11=校本 3=FM收听 5=板报
            if ct not in (1, 11, 3, 5):
                return None
            lid = t.get("contentId")
            if not lid:
                return None
            finished = t.get("finished", False)
            if not include_finished and finished:
                return None
            return {
                "lessonId": lid,
                "homeworkId": homework_id,
                "courseId": t.get("parentContentId"),
                "title": t.get("title", ""),
                "duration": t.get("duration", 0),
                "finished": finished if include_finished else False,
                "mustLearn": t.get("mustLearning") == 1,
                "subjectId": t.get("subjectId") or 0,
                "subjectName": t.get("subjectName", ""),
                "studyDate": f"{ds['month']}-{ds['day']}" if ds else "",
                "dateTimestamp": ds.get("date", 0) if ds else 0,
                "contentType": ct,
            }

        async def _fetch_day(ds: dict) -> list[dict]:
            async with sem:
                subj_tasks = await self.list_tasks(school_id, homework_id, day_id=ds["dateId"],
                                                   must_learn_subjects=must_learn_subjects)
            return [i for i in (_build(t, ds) for t in subj_tasks) if i]

        async def _fetch_subject(subj: int) -> list[dict]:
            async with sem:
                subj_tasks = await self.list_tasks(school_id, homework_id, subject_id=subj,
                                                   must_learn_subjects=must_learn_subjects)
            return [i for i in (_build(t, None) for t in subj_tasks) if i]

        if date_stat:
            groups: list = list(date_stat)
            _fetch = _fetch_day
        else:
            groups = list(must_learn_subjects)
            _fetch = _fetch_subject
        results = await asyncio.gather(*(_fetch(g) for g in groups),
                                       return_exceptions=True)
        # [修复] 失败组自动重试2次（SSL/WAF偶发失败，原先直接丢弃会漏课时）
        for _retry in range(2):
            bad = [i for i, r in enumerate(results) if isinstance(r, BaseException)]
            if not bad:
                break
            logger.warning("list_video_tasks 重试%d: hw=%s 失败组=%d",
                           _retry + 1, homework_id, len(bad))
            await asyncio.sleep(1.5 * (_retry + 1))
            rr = await asyncio.gather(*(_fetch(groups[i]) for i in bad),
                                      return_exceptions=True)
            for j, r in enumerate(rr):
                if not isinstance(r, BaseException):
                    results[bad[j]] = r
        seen: set = set()
        out: list[dict] = []
        for group, items in zip(groups, results):
            if isinstance(items, BaseException):
                logger.warning("list_video_tasks 单组失败(已重试2次): hw=%s group=%s err=%s",
                               homework_id, group, items)
                continue
            for item in items:
                if item["lessonId"] in seen:
                    continue
                seen.add(item["lessonId"])
                out.append(item)
        return out

    async def get_lesson_info(self, school_id: int, homework_id: int,
                              lesson_id: int, content_type: int = 1) -> dict:
        data = await self._post(
            "/api/homeworkprod/homework/student/getUserHomeworkLessonTaskInfo",
            {"schoolId": school_id, "homeworkId": homework_id,
             "lessonId": lesson_id, "contentType": content_type},
        )
        if not data.get("success") or not data.get("data"):
            raise RuntimeError(f"getUserHomeworkLessonTaskInfo failed: {data}")
        return data["data"]

    async def check_detection_passed(self, school_id: int, homework_id: int,
                                     lesson_id: int) -> bool:
        """检查刷课后 EWT 是否认定课时已完成（finished/ratio/percent）。
        [测试版] 对齐 spark 更新版 [OPTIM]：平台达标阈值=80%（finishPercent=0.8），
        用 percent>=0.8 判定，避免 1.0 过严导致已达标课时被误判重刷；
        查询失败不误判（返回 True）。"""
        try:
            info = await self.get_lesson_info(school_id, homework_id, lesson_id)
            if (info.get("percent") or 0) >= 0.8:
                return True
            if info.get("finished") is True:
                return True
        except Exception:
            return True  # 查询失败不误判
        item = await self._query_serious_check_item(school_id, homework_id, lesson_id)
        if item is not None:
            if item.get("finished") is True or (item.get("ratio") or 0) >= 0.8:
                return True
        return False

    async def _query_serious_check_item(self, school_id: int, homework_id: int,
                                        lesson_id: int) -> dict | None:
        """查询目标课时的看课检测条目（seriousCheckResult/finished/ratio），翻页遍历。"""
        page_index = 1
        page_size = 30  # 必须 <50
        while True:
            data = await self._post(
                "/api/homeworkprod/homework/student/pageUserVideoTaskByCondition",
                {
                    "schoolId": str(school_id),
                    "pageSize": page_size,
                    "missionType": 2,
                    "homeworkIds": [homework_id],
                    "pageIndex": page_index,
                    "queryMustLearn": True,
                    "mustLearnSubjectList": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                                             11, 12, 13, 14, 15, 16],
                },
            )
            if not data.get("success") or not data.get("data"):
                return None
            items = data["data"].get("data", [])
            for item in items:
                if str(item.get("contentId") or item.get("lessonId")) == str(lesson_id):
                    return item
            total = data["data"].get("totalRecords", 0)
            if len(items) < page_size or page_index * page_size >= total:
                break
            page_index += 1
        return None

    async def report_video_point(self, school_id: int, homework_id: int,
                                 lesson_id: int, content_type: int = 1) -> bool:
        """自动通过看课检测（addVideoss 两步时序：scr=0 激活 → scr=2 通过）。
        [测试版] 对齐 luoying2334/EWT360-NEW-Helper 逆向参数（2026.7.30 平台检测）：
          - 校本视频(contentType=11) 的 lessonId 需 +2000000 偏移
          - type: 普通视频=1，其他（校本/FM/板报）=2；互动视频=3"""
        submit_lesson_id = (str(int(lesson_id) + 2000000) if content_type == 11
                            else str(lesson_id))
        submit_type = 1 if content_type == 1 else 2
        await self._post(
            "/api/homeworkprod/homework/student/addVideoss",
            {"schoolId": school_id, "homeworkId": homework_id,
             "lessonId": submit_lesson_id, "type": submit_type,
             "interactivePointId": None, "platform": 1, "seriousCheckResult": 0},
        )
        await asyncio.sleep(3 + random.random() * 2)
        data = await self._post(
            "/api/homeworkprod/homework/student/addVideoss",
            {"schoolId": school_id, "homeworkId": homework_id,
             "lessonId": submit_lesson_id, "type": submit_type,
             "interactivePointId": None, "platform": 1, "seriousCheckResult": 2},
        )
        return data.get("success", False)

    async def pass_serious_check(self, school_id: int, homework_id: int,
                                 lesson_id: int, content_type: int = 1) -> bool:
        """刷课后把 seriousCheckResult 置为 2（看课检测通过）。
        [测试版-降级] 课时进度已达标即可（percent>=0.8），seriousCheckResult 标记
        不影响课时完成。仅做一次 best-effort 置 2，失败不重试、不触发重刷，始终返回 True，
        避免"看课检测未置为通过"导致大量重刷浪费时间和触发风控。"""
        # 最多尝试一次置2（轻量），失败静默
        try:
            info = await self.get_lesson_info(school_id, homework_id, lesson_id)
            scr = info.get("seriousCheckResult")
            if scr is not None:
                scr = int(scr)
                if scr >= 2:
                    return True      # 已通过
                # scr==0/1：做一次 best-effort 置2，失败不回滚
                try:
                    await self.report_video_point(school_id, homework_id, lesson_id,
                                                  content_type=content_type)
                except Exception:
                    pass
                return True          # 无论如何返回 True（不阻断、不重刷）
        except Exception:
            pass
        return True                  # 查询失败也返回 True（不误判、不重刷）

    # ---------- 互动弹题 ----------
    async def get_external_video_info(self, lesson_id: int, video_token: str,
                                      biz_code: str = VIDEO_BIZ_CODE) -> dict:
        """获取视频外部信息，包含 interactiveInfo（弹题检测时间点）。"""
        data = await self._get(
            "/api/videoplayerprod/videoplayer/getExternalVideoInfo",
            {"videoBizCode": biz_code, "lessonId": str(lesson_id),
             "videoToken": video_token, "sdkVersion": "3.0.37"},
        )
        if not data.get("success"):
            raise RuntimeError(f"getExternalVideoInfo failed: {data}")
        return data["data"]

    async def get_interactive_config_detail(self, interactive_config_id: str,
                                            biz_code: str = VIDEO_BIZ_CODE) -> dict:
        """获取弹题详情（题目和选项列表）。"""
        data = await self._get(
            "/api/videoplayerprod/videoplayer/getInteractiveConfigDetail",
            {"interactiveConfigId": interactive_config_id, "videoBizCode": biz_code},
        )
        if not data.get("success"):
            raise RuntimeError(f"getInteractiveConfigDetail failed: {data}")
        return data["data"]

    async def submit_answer(self, interactive_scene_id: str, question_id: str,
                            my_answers: list, total_seconds: int,
                            lesson_id: int, biz_code: str = VIDEO_BIZ_CODE) -> dict:
        """提交弹题答案，解除播放器暂停状态。"""
        data = await self._post(
            "/api/videoplayerprod/videoplayer/submitAnswer",
            {"interactiveSceneId": interactive_scene_id,
             "questionId": question_id, "myAnswers": my_answers,
             "totalSeconds": total_seconds, "videoBizCode": biz_code,
             "lessonId": str(lesson_id)},
        )
        if not data.get("success"):
            raise RuntimeError(f"submitAnswer failed: {data}")
        return data["data"]

    # ---------- 用户 ----------
    async def fetch_user_info(self) -> dict:
        """校验 token 有效性并获取基本信息。"""
        data = await self._get("/api/usercenter/user/baseinfo")
        if not data.get("success"):
            raise RuntimeError(f"Token 校验失败: {data.get('msg', '')}")
        return data["data"]

    async def fetch_school_info(self) -> dict:
        data = await self._get("/api/eteacherproduct/school/getSchoolUserInfo")
        if not data.get("success"):
            raise RuntimeError(f"获取学校信息失败: {data.get('msg', '')}")
        return data["data"]

    async def close(self):
        await self._client.aclose()


# ======================================================================
# [刷课核心] 竞态爆发 + 播放上报 + 看课检测
# ======================================================================
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """BFE 上报用共享异步客户端（连接复用省 TLS 握手）。"""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=100),
        )
    return _client


class BrushEvent:
    __slots__ = ("type", "round", "play_time_ms", "percent", "needed_ms",
                 "requests_ok", "requests_total", "credited_sec", "message",
                 "lesson_time_ms")

    def __init__(self, type, round=0, play_time_ms=0, percent=0.0, needed_ms=0,
                 requests_ok=0, requests_total=0, credited_sec=0, message="",
                 lesson_time_ms=0):
        self.type = type          # "progress" | "done" | "error" | "waf_blocked"
        self.round = round
        self.play_time_ms = play_time_ms
        self.percent = percent
        self.needed_ms = needed_ms
        self.requests_ok = requests_ok
        self.requests_total = requests_total
        self.credited_sec = credited_sec
        self.message = message
        self.lesson_time_ms = lesson_time_ms


class QuizTimepoint:
    __slots__ = ("config_id", "timepoint_ms", "resolved")

    def __init__(self, config_id: str, timepoint_ms: int):
        self.config_id = config_id       # interactiveConfigId（字符串雪花ID）
        self.timepoint_ms = timepoint_ms  # 弹题触发时间（毫秒）
        self.resolved = False


async def _concurrent_burst(conf, token, lesson_id, course_id, school_id,
                            biz_code, video_type, n_threads, stay_time=10000,
                            speed=SPEED, burst_override=False):
    """异步竞态爆发：asyncio.Event 栅栏同时放行 n_threads 个协程打 bfe。
    竞态条件利用不变——服务端 check-and-deduct 非原子，多数请求滑过限流。
    返回 (ok_count, total_count, waf_count)。"""
    global BURST_SIZE
    # 热更新：以全局 BURST_SIZE 为准（watcher 线程每 2 秒同步配置文件）
    # [v3-test] burst_override > 0 时用显式传参（快速模式独立路数，不受热更新影响）
    if not burst_override:
        n_threads = BURST_SIZE
    client = _get_client()
    start_evt = asyncio.Event()
    results: list = [None] * n_threads

    async def fire_one(i):
        await start_evt.wait()
        try:
            now = int(time.time() * 1000)
            report_time = now + conf["diffTime"]
            begin_time = conf.get("ts", int(time.time() * 1000))
            event_uuid = f"{uuid.uuid4().hex[:8]}_{i}"
            sig = make_signature(2, stay_time, token, report_time, conf["secret"])
            event_pkg = {
                "lesson_id": str(lesson_id),
                "stay_time": stay_time,
                "media_time": 0,
                "status": 1,
                "begin_time": begin_time,
                "report_time": report_time,
                "point_time_id": 200 + i,
                "point_time": 60000,
                "point_num": 20,
                "video_type": video_type,
                "speed": speed,
                "quality": "高清",
                "action": 2,
                "fallback": 0,
                "uuid": event_uuid,
            }
            if course_id is not None:
                event_pkg["course_id"] = str(course_id)
            body = {
                "CommonPackage": {
                    "userid": int(token.split("-")[0]),
                    "ip": conf["clientIp"],
                    "os": "Windows",
                    "resolution": "1920*1080",
                    "mstid": token,
                    "browser": "Edge",
                    "browser_ver": (
                        "5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76"
                    ),
                    "playerType": 1,
                    "sdkVersion": "3.0.37",
                    "videoBizCode": biz_code,
                    "memberProvinceCode": "320000",
                    "schoolId": str(school_id),
                    "schoolProvinceCode": "320000",
                },
                "EventPackage": [event_pkg],
                "signature": sig,
                "sn": "ewt_web_video_detail",
                "_": int(time.time() * 1000),
            }
            user_id = token.split("-")[0]
            r = await client.post(
                f"{BFE}/monitor/web/collect/batch",
                params={
                    "TrVideoBizCode": biz_code,
                    "TrFallback": "0",
                    "TrUserId": user_id,
                    "TrLessonId": str(lesson_id),
                    "TrUuId": event_uuid,
                    "sdkVersion": "3.0.37",
                    "_": str(int(time.time() * 1000)),
                },
                headers={
                    "token": token,
                    "x-bfe-session-id": conf["sessionId"],
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=10,
            )
            ct = r.headers.get("Content-Type", "")
            if "text/html" in ct or not r.text.startswith("{"):
                results[i] = "waf"
            else:
                results[i] = r.status_code == 200
        except Exception:
            results[i] = False

    tasks = [asyncio.create_task(fire_one(i)) for i in range(n_threads)]
    await asyncio.sleep(0.03)  # 0.03s 就绪窗口
    start_evt.set()
    await asyncio.gather(*tasks)

    return (sum(1 for r in results if r is True),
            len(results),
            sum(1 for r in results if r == "waf"))


async def _fire_play(conf, token, lesson_id, course_id, school_id, biz_code,
                     video_type, stay_time_ms, speed, use_burst, n_threads=BURST_SIZE):
    """发一轮播放进度上报。
    use_burst=True:  竞态爆发（默认，~5x 等效加速，speed=2）。
    use_burst=False: 官方顺序单发（--speed 倍速路径）。
    返回 (ok_count, total_count, waf_count)。"""
    if use_burst:
        return await _concurrent_burst(
            conf, token, lesson_id, course_id, school_id,
            biz_code, video_type, n_threads, stay_time_ms, speed,
        )
    try:
        await _report_point(
            conf, token, lesson_id, course_id, school_id, 2, 200, 20,
            stay_time=stay_time_ms, speed=speed, begin_offset_ms=stay_time_ms,
            biz_code=biz_code, video_type=video_type,
        )
        return 1, 1, 0
    except WafCaptchaBlocked:
        return 0, 1, 1


async def _report_point(conf, token, lesson_id, course_id,
                        school_id, action, point_id, point_num,
                        stay_time=0, speed=1, begin_offset_ms=60000,
                        biz_code=VIDEO_BIZ_CODE, video_type=1):
    client = _get_client()
    now = int(time.time() * 1000)
    report_time = now + conf["diffTime"]
    begin_time = report_time - begin_offset_ms
    event_uuid = f"{uuid.uuid4().hex[:8]}_{point_id}"

    sig = make_signature(action, stay_time, token, report_time, conf["secret"])
    event_pkg = {
        "lesson_id": str(lesson_id),
        "stay_time": stay_time,
        "media_time": 0,
        "status": 3 if action == 3 else 1,
        "begin_time": begin_time,
        "report_time": report_time,
        "point_time_id": point_id,
        "point_time": 60000,
        "point_num": point_num,
        "video_type": video_type,
        "speed": speed,
        "quality": "高清",
        "action": action,
        "fallback": 0,
        "uuid": event_uuid,
    }
    if course_id is not None:
        event_pkg["course_id"] = str(course_id)
    body = {
        "CommonPackage": {
            "userid": int(token.split("-")[0]),
            "ip": conf["clientIp"],
            "os": "Windows",
            "resolution": "1920*1080",
            "mstid": token,
            "browser": "Edge",
            "browser_ver": (
                "5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76"
            ),
            "playerType": 1,
            "sdkVersion": "3.0.37",
            "videoBizCode": biz_code,
            "memberProvinceCode": "320000",
            "schoolId": str(school_id),
            "schoolProvinceCode": "320000",
        },
        "EventPackage": [event_pkg],
        "signature": sig,
        "sn": "ewt_web_video_detail",
        "_": int(time.time() * 1000),
    }
    user_id = token.split("-")[0]
    r = await client.post(
        f"{BFE}/monitor/web/collect/batch",
        params={
            "TrVideoBizCode": biz_code,
            "TrFallback": "0",
            "TrUserId": user_id,
            "TrLessonId": str(lesson_id),
            "TrUuId": event_uuid,
            "sdkVersion": "3.0.37",
            "_": str(int(time.time() * 1000)),
        },
        headers={
            "token": token,
            "x-bfe-session-id": conf["sessionId"],
            "Content-Type": "application/json",
        },
        json=body,
    )
    if is_waf_captcha(r):
        raise WafCaptchaBlocked("WAF 滑块验证拦截 — 同IP发包过频触发人机验证")
    return r.json()


async def run_brush_task(
    ewt_client,       # EwtClient instance
    school_id: int,
    homework_id: int,
    lesson_id: int,
    course_id: int | None,
    token: str,       # EWT raw token string
    content_type: int = 1,  # 1=视频, 11=校本视频
    force_rounds: int = 0,  # 强制至少跑N轮（=1事后恢复用）
    phase_offset_ms: int = 0,  # 首轮爆发相位错峰（批量并行用）
    speed: float | None = None,  # None=默认竞态爆发；有值=官方顺序单发倍速
    n_threads: int = BURST_SIZE,  # 竞态并发路数（可调）
):
    """执行一次刷课任务，通过 async generator yield 进度事件。
    v12 策略:
    - stay_time=10s 最优；speed=2 硬上限（2.1 触发 699001）
    - Bucket 按 (token, lesson_id) 分片 → 多 lesson 并行 = N× 加速
    - 竞态并发: n_threads 协程 Event 同步发射，利用 check-and-deduct 非原子性
    - 等效 ~5x 单 lesson 加速 + N× 多 lesson 并行
    """
    use_burst = speed is None
    if use_burst:
        speed = SPEED
    else:
        try:
            speed = float(speed)
        except (TypeError, ValueError):
            speed = SPEED
        speed = max(0.5, min(speed, 2.0))
    is_school_video = content_type == 11
    biz_code = SCHOOL_VIDEO_BIZ_CODE if is_school_video else VIDEO_BIZ_CODE
    video_type = 6 if is_school_video else 1
    try:
        # Step 1: 获取课时信息
        info = await ewt_client.get_lesson_info(school_id, homework_id, lesson_id, content_type=content_type)
        lesson_time_ms = info.get("lessonTime", 0)
        finish_play_time = info.get("finishPlayTime", int(lesson_time_ms * 0.8))
        initial_play_time = info.get("playTime", 0)
        needed = max(0, finish_play_time - initial_play_time)
        if needed <= 0 and force_rounds <= 0:
            yield BrushEvent(type="done", credited_sec=0)
            return
        # Step 2: 获取会话凭证
        conf = await ewt_client.fetch_global_conf(biz_code=biz_code)
        video_token = await ewt_client.fetch_player_token(school_id, lesson_id, content_type=content_type)
        # Step 2.5: 获取弹题时间点（优雅降级，失败不影响刷课）
        quiz_timepoints: list[QuizTimepoint] = []
        interactive_scene_id: str | None = None
        try:
            video_info = await ewt_client.get_external_video_info(
                lesson_id, video_token, biz_code=biz_code,
            )
            interactive_info = video_info.get("interactiveInfo") or {}
            interactive_scene_id = interactive_info.get("id")
            config_list = interactive_info.get("interactiveConfigList") or []
            for cfg in config_list:
                cfg_id = cfg.get("id")
                if not cfg_id:
                    continue
                tpoint_ms = cfg.get("interactiveTimePoint", 0)
                quiz_timepoints.append(QuizTimepoint(
                    config_id=str(cfg_id),
                    timepoint_ms=tpoint_ms,
                ))
        except Exception:
            pass  # 无弹题或 API 异常，继续正常刷课
        # 校本视频不带 course_id
        report_cid = course_id if not is_school_video else None
        # WAF 冷却重试
        waf_streak = 0

        async def _waf_cooldown() -> bool:
            """WAF 拦截冷却：返回 True=超限需失败，False=已冷却可继续。"""
            nonlocal waf_streak
            waf_streak += 1
            if waf_streak > WAF_RETRY_COUNT:
                return True
            await asyncio.sleep(WAF_BACKOFF_SECONDS)
            return False

        # Step 3: action=1 (play start)
        try:
            await _report_point(conf, token, lesson_id, report_cid,
                                school_id, 1, 0, 20, 0,
                                biz_code=biz_code, video_type=video_type)
        except WafCaptchaBlocked:
            if await _waf_cooldown():
                yield BrushEvent(
                    type="waf_blocked",
                    message=f"EWT 风控拦截（触发人机验证/安全威胁），同 IP 发包过频，"
                            f"请稍后重试或切换网络",
                )
                return
        total_reqs = 1
        ok_count = 1
        current_play_time = initial_play_time
        stall_count = 0
        round_num = 0

        # Step 4: 竞态爆发循环（stay_time=10s 最优，实测验证）
        # [v3-test] FAST_MODE：小间隔高频爆发 + 每波查 percent 提前停（实测 ≈9~32倍速）
        cur_percent = 0.0
        while (needed > 0 or round_num < force_rounds) and stall_count < 3:
            if FAST_MODE and round_num >= FAST_MAX_ROUNDS:
                break  # 快速模式兜底：防死循环
            if FAST_MODE and cur_percent >= 0.8 and round_num > force_rounds:
                break  # [v3-test] 达标即停（平台阈值0.8），不再多打一波
            round_num += 1
            if FAST_MODE:
                # 快速节奏：固定小间隔（首轮仍加相位错峰）
                wait_sec = FAST_INTERVAL + (phase_offset_ms / 1000 if round_num == 1 else 0)
                await asyncio.sleep(wait_sec)
                # conf 节流刷新：仅每 20 波刷一次（secret 短期有效，省去每波一次请求）
                if round_num % 20 == 1 and round_num > 1:
                    try:
                        conf = await ewt_client.fetch_global_conf(biz_code=biz_code)
                    except WafCaptchaBlocked:
                        if await _waf_cooldown():
                            yield BrushEvent(type="waf_blocked", message="EWT 风控拦截，请稍后重试或切换网络")
                            return
                        continue
                    except Exception:
                        pass  # 沿用旧 conf
            else:
                # 等待间隔（bucket refill ~12s）。首轮加 phase_offset_ms 错峰。
                # BURST_WAIT 加 ±20% 抖动——打散节奏降低 WAF 频率识别概率。
                wait_sec = BURST_WAIT * random.uniform(0.8, 1.2) + (phase_offset_ms / 1000 if round_num == 1 else 0)
                await asyncio.sleep(wait_sec)
                # 刷新 session（secret 可能过期）
                try:
                    conf = await ewt_client.fetch_global_conf(biz_code=biz_code)
                except WafCaptchaBlocked:
                    if await _waf_cooldown():
                        yield BrushEvent(type="waf_blocked", message="EWT 风控拦截，请稍后重试或切换网络")
                        return
                    continue
                except Exception:
                    pass  # 沿用旧 conf
            # 播放上报
            _stay = STAY_MS if use_burst else int(wait_sec * 1000)
            burst_ok, burst_total, burst_waf = await _fire_play(
                conf, token, lesson_id, report_cid, school_id,
                biz_code, video_type, _stay, speed, use_burst,
                n_threads=n_threads,
            )
            total_reqs += burst_total
            ok_count += burst_ok
            # WAF 拦截 → 冷却后继续下一轮
            if burst_waf > 0:
                if await _waf_cooldown():
                    yield BrushEvent(
                        type="waf_blocked",
                        message=f"EWT 风控拦截（{burst_waf}/{burst_total} 请求被拦截），"
                                f"同 IP 发包过频，请稍后重试或切换网络",
                    )
                    return
                continue
            # 查询进度
            try:
                info2 = await ewt_client.get_lesson_info(school_id, homework_id, lesson_id, content_type=content_type)
            except WafCaptchaBlocked:
                if await _waf_cooldown():
                    yield BrushEvent(type="waf_blocked", message="EWT 风控拦截，请稍后重试或切换网络")
                    return
                continue
            waf_streak = 0
            delta = info2.get("playTime", 0) - current_play_time
            current_play_time = info2.get("playTime", 0)
            needed = max(0, finish_play_time - current_play_time)
            pct = info2.get("percent", 0)
            cur_percent = pct  # [v3-test] 快速模式达标即停判据
            yield BrushEvent(
                type="progress", round=round_num,
                play_time_ms=current_play_time, percent=pct,
                needed_ms=needed, requests_ok=ok_count, requests_total=total_reqs,
                lesson_time_ms=finish_play_time,
            )
            # 停滞检测：两层恢复策略
            # 机制A: 弹题检测 → 答题绕过（仅非强制模式）
            # 机制B: 看课检测 → addVideoss (原 reportVideoPoint)
            if delta == 0:
                quiz_resolved = False
                # --- 机制A：弹题绕过 ---
                if round_num > force_rounds:
                    for qt in quiz_timepoints:
                        if qt.resolved:
                            continue
                        if abs(qt.timepoint_ms - current_play_time) > 5000:
                            continue
                        try:
                            detail = await ewt_client.get_interactive_config_detail(
                                qt.config_id, biz_code=biz_code,
                            )
                            scene_id = detail.get("interactiveSceneId") or interactive_scene_id
                            question = detail.get("question") or {}
                            qid = question.get("id")
                            options = question.get("options") or []
                            play_sec = max(1, current_play_time // 1000)
                            if qid and options:
                                # 选第一个选项（HAR 实测 A 选对了，rightStatus=1）
                                my_answers = [str(options[0])]
                                await ewt_client.submit_answer(
                                    str(scene_id), str(qid), my_answers, play_sec,
                                    lesson_id=lesson_id, biz_code=biz_code,
                                )
                            qt.resolved = True
                            quiz_resolved = True
                            # 重试上报验证是否恢复
                            await asyncio.sleep(2)
                            burst_ok2, burst_total2, _ = await _fire_play(
                                conf, token, lesson_id, report_cid, school_id,
                                biz_code, video_type, STAY_MS, speed, use_burst,
                                n_threads=n_threads,
                            )
                            total_reqs += burst_total2
                            ok_count += burst_ok2
                            info3 = await ewt_client.get_lesson_info(
                                school_id, homework_id, lesson_id, content_type=content_type,
                            )
                            delta2 = info3.get("playTime", 0) - current_play_time
                            current_play_time = info3.get("playTime", 0)
                            needed = max(0, finish_play_time - current_play_time)
                            if delta2 > 0:
                                stall_count = 0
                                yield BrushEvent(
                                    type="progress", round=round_num,
                                    play_time_ms=current_play_time, percent=info3.get("percent", 0),
                                    needed_ms=needed, requests_ok=ok_count, requests_total=total_reqs,
                                    lesson_time_ms=finish_play_time,
                                )
                                continue
                        except Exception:
                            pass  # 弹题绕过失败，回退到机制B
                # --- 机制B：看课检测（"点击继续观看"挑战） ---
                if not quiz_resolved:
                    b_passed = False
                    for b_attempt in range(1, 4):
                        try:
                            await ewt_client.report_video_point(school_id, homework_id, lesson_id,
                                                                content_type=content_type)
                            await asyncio.sleep(2)
                            burst_ok2, burst_total2, _ = await _fire_play(
                                conf, token, lesson_id, report_cid, school_id,
                                biz_code, video_type, STAY_MS, speed, use_burst,
                                n_threads=n_threads,
                            )
                            total_reqs += burst_total2
                            ok_count += burst_ok2
                            info3 = await ewt_client.get_lesson_info(
                                school_id, homework_id, lesson_id, content_type=content_type,
                            )
                            delta2 = info3.get("playTime", 0) - current_play_time
                            current_play_time = info3.get("playTime", 0)
                            needed = max(0, finish_play_time - current_play_time)
                            if delta2 > 0:
                                b_passed = True
                                break
                            # 进度未恢复：复查 scr 是否已变 2
                            try:
                                item_c = await ewt_client._query_serious_check_item(
                                    school_id, homework_id, lesson_id,
                                )
                                if item_c and int(item_c.get("seriousCheckResult") or 0) >= 2:
                                    b_passed = True
                                    break
                            except Exception:
                                pass
                            if b_attempt < 3:
                                await asyncio.sleep(3)
                        except Exception:
                            break
                    if b_passed:
                        stall_count = 0
                        yield BrushEvent(
                            type="progress", round=round_num,
                            play_time_ms=current_play_time, percent=info3.get("percent", 0),
                            needed_ms=needed, requests_ok=ok_count, requests_total=total_reqs,
                            lesson_time_ms=finish_play_time,
                        )
                        continue
                    # 强制轮次中 delta=0 是预期行为（已100%），不计入停滞
                    if round_num <= force_rounds:
                        pass
                    elif FAST_MODE and cur_percent >= 0.8:
                        pass  # [v3-test] 已达标，delta=0 属预期，不算停滞
                    else:
                        stall_count += 1
            else:
                stall_count = 0

        # Step 5: action=3 (ended)
        await _report_point(
            conf, token, lesson_id, report_cid,
            school_id, 3, 20, 20,
            stay_time=0, speed=speed, begin_offset_ms=0,
            biz_code=biz_code, video_type=video_type,
        )
        total_reqs += 1
        ok_count += 1

        credited_sec = max(0, (current_play_time - initial_play_time) // 1000)
        yield BrushEvent(
            type="done", credited_sec=credited_sec,
            requests_ok=ok_count, requests_total=total_reqs,
        )
    except WafCaptchaBlocked as e:
        yield BrushEvent(type="waf_blocked", message=str(e))
    except Exception as e:
        msg = str(e)
        if _is_token_invalid(msg):
            yield BrushEvent(type="token_invalid", message=msg)
        else:
            yield BrushEvent(type="error", message=msg)


# ======================================================================
# [主流程] 作业扫描 + 分片 + N路并行 + token自动续期
# ======================================================================
def _translate_error(msg: str) -> str:
    """把网关/HTTP 错误翻译为用户友好中文。"""
    if not msg:
        return msg
    ml = msg.lower()
    if "429" in msg or "安全威胁" in msg or "风控" in msg:
        return "EWT 网关 429「安全威胁」风控拦截（IP 可能被临时标记，稍后重试或换网络）"
    if "2001106" in msg or "其他地方登录" in msg or "登录状态已过期" in msg:
        return "Token 已失效/被挤下线（2001106）"
    if "699001" in msg:
        return "speed 超限（699001，倍速硬上限 2.0）"
    if "timeout" in ml or "timed out" in ml:
        return "网络超时"
    if "connection" in ml and "refused" in ml:
        return "连接被拒绝（可能被限流封禁）"
    return msg


async def _list_homeworks(client: EwtClient, school_id: int) -> list[dict]:
    """拉取作业列表；TokenInvalidError 透传，其余异常翻译。"""
    try:
        return await client.list_homeworks(school_id)
    except TokenInvalidError:
        raise
    except Exception as e:
        raise RuntimeError(_translate_error(str(e))) from e


async def _load_tasks(client: EwtClient, school_id: int, hw_id,
                      include_finished: bool = False) -> list[dict] | None:
    """返回作业下未完成视频课时列表（失败返回 None，不抛错）。
    include_finished=True 时返回全部课时（含已完成，配合 force_rounds 强制重刷）。"""
    try:
        subjects = await client.get_homework_must_subjects(school_id, hw_id)
    except TokenInvalidError:
        raise
    except Exception:
        subjects = None  # 拿不到必学清单 → list_video_tasks 回退 [1..16]
    try:
        return await client.list_video_tasks(school_id, hw_id,
                                             must_learn_subjects=subjects,
                                             include_finished=include_finished)
    except TokenInvalidError:
        raise
    except Exception as e:
        print(f"  ✗ 获取课时列表失败: {_translate_error(str(e))}")
        return None


async def scan_pending_tasks(client: EwtClient, school_id: int,
                             hw_filter=None,
                             include_finished: bool = False) -> list[tuple]:
    """扫描课时，返回 [(homework_id, task), ...]。
    include_finished=True 时含已完成课时（强制重刷模式）。"""
    hws = await _list_homeworks(client, school_id)
    if not hws:
        return []
    if hw_filter is not None and not any(str(h.get("homeworkId")) == str(hw_filter) for h in hws):
        raise RuntimeError(f"作业 {hw_filter} 不存在或无权访问")
    # 先打印将要扫描的作业（并发前，让用户看到进度）
    targets = []
    for hw in hws:
        hid = hw.get("homeworkId")
        if hw_filter is not None and str(hid) != str(hw_filter):
            continue
        targets.append(hw)
        print(f"查询作业 [{hid}] {str(hw.get('title', ''))[:40]}…")
    if not targets:
        return []

    # [优化] 多作业【并发】扫描（原先逐个串行，多作业时慢 3~5 倍）
    # 全局限速器 _gateway_limiter 会自动排队，不会超速触发风控
    results = await asyncio.gather(
        *[_load_tasks(client, school_id, hw.get("homeworkId"),
                      include_finished=include_finished)
          for hw in targets],
        return_exceptions=True,
    )

    all_tasks: list[tuple] = []
    for hw, res in zip(targets, results):
        hid = hw.get("homeworkId")
        if isinstance(res, BaseException):
            warn(f"  ⚠ 作业 [{hid}] 扫描失败：{str(res)[:60]}")
            continue
        if not res:
            continue
        for t in res:
            t["homeworkTitle"] = hw.get("title", "")
            t["homeworkId"] = hid
            all_tasks.append((hid, t))
    return all_tasks


async def _run_once(client: EwtClient, school_id: int, hw_id, lesson_id, course_id,
                    token: str, content_type: int, speed, burst_size: int,
                    phase_offset_ms: int, force_rounds: int) -> str:
    """消费 run_brush_task 一次，返回状态: ok | error | waf_blocked | token_invalid。"""
    status = "ok"
    async for ev in run_brush_task(
        client, school_id, hw_id, lesson_id, course_id, token,
        content_type=content_type, force_rounds=force_rounds,
        phase_offset_ms=phase_offset_ms, speed=speed, n_threads=burst_size,
    ):
        if ev.type == "progress":
            _p = (ev.play_time_ms / ev.lesson_time_ms) if ev.lesson_time_ms else 0.0
            _p = max(0.0, min(1.0, _p))
            _detail = ("已播 %s/%s  还需 %s  请求 %d/%d"
                       % (human_time(ev.play_time_ms / 1000),
                          human_time(ev.lesson_time_ms / 1000),
                          human_time(ev.needed_ms / 1000),
                          ev.requests_ok, ev.requests_total))
            if _PROGRESS_SINK is not None:
                _PROGRESS_SINK.update(lesson_id, _p, _detail)
            else:
                print("  ▶ [%s] %s %3d%%  %s"
                      % (lesson_id, progress_bar(_p, 22), int(_p * 100), _detail),
                      flush=True)
        elif ev.type == "done":
            _p_log("  [完成][%s] 累加 %ss | 请求 %d/%d"
                   % (lesson_id, ev.credited_sec, ev.requests_ok, ev.requests_total))
        elif ev.type == "waf_blocked":
            _p_log("  [WAF拦截] " + str(ev.message))
            status = "waf_blocked"
        elif ev.type == "token_invalid":
            status = "token_invalid"
        elif ev.type == "error":
            _p_log("  [错误] " + _translate_error(ev.message))
            status = "token_invalid" if _is_token_invalid(ev.message) else "error"
    return status


# ======================================================================
# [测试版新增] 任务型直写（FM=3/板报=5）+ clog 播放日志伪造
# ======================================================================
CLOG_URL = "https://clog.ewt360.com"

def _clog_rand_str(n: int = 16) -> str:
    """生成随机 hex 串（避免依赖 string 模块）。"""
    return "".join(random.choice("0123456789abcdef") for _ in range(n))


def _build_clog_payload(lesson_id: str, course_id: str, user_id: str,
                        duration_sec: int) -> tuple:
    """构建 BFE 4 段播放日志（开始/周期/缓冲/结束），与 clog.ewt360.com 无鉴权端点匹配。
    参考 zjy2fz/ewt-auto-study 的 clog_sender.py（2026-08 实测该端点仍无鉴权）。"""
    duration_ms = max(1000, int(duration_sec or 0) * 1000)
    uuid_ = _clog_rand_str()
    dev_id = _clog_rand_str()
    trace_id = _clog_rand_str(32)
    log_id = _clog_rand_str(32)
    begintime = int(time.time() * 1000) - duration_ms - 5000
    brands = [
        {"brand": "Xiaomi", "os": "Android", "os_ver": "14", "model": "Redmi 8", "res": "1417*720"},
        {"brand": "Xiaomi", "os": "Android", "os_ver": "14", "model": "Xiaomi 12", "res": "2400*1080"},
        {"brand": "Huawei", "os": "Android", "os_ver": "12", "model": "Huawei Mate 50", "res": "2700*1224"},
        {"brand": "Apple", "os": "IOS", "os_ver": "17", "model": "iPhone 13 Pro Max", "res": "2778*1284"},
    ]
    dev = random.choice(brands)
    base_extra = {
        "course_id": str(course_id), "trace_id": trace_id,
        "content_type": "video_record", "videoBizCode": 2001,
        "lesson_id": str(lesson_id), "log_index": "42",
        "uuid": uuid_, "fallback": "0", "isonline": "0",
    }

    def _base():
        return {
            "oper_type": "", "version": "10.2.5", "begin_time": begintime,
            "brand": dev["brand"], "carrier": "N/A", "channel": "ewt360",
            "dev_id": dev_id, "imei": "", "imsi": "", "language": "zh",
            "device_model": dev["model"], "sdk_version": "2.0.95-test-rc21",
            "access": "NO_NETWORK", "online": "2", "os": dev["os"],
            "os_version": dev["os_ver"], "point_id": "120",
            "point_time": "60000", "resolution": dev["res"], "speed": "1.0",
            "type": "video_oper", "uploadStatus": -1,
            "url": "com.mistong.ewt360.core.media.video.MediaPlayFragment",
            "userid": str(user_id),
        }

    arr = []
    # Event 1: 主播放开始 (status=2)
    e1 = _base()
    e1["extra"] = base_extra
    e1["log_id"] = log_id
    e1["media_time"] = str(duration_ms)
    e1["stay_time"] = str(duration_ms - 50)
    e1["status"] = "2"
    e1["ts"] = begintime + 100
    arr.append(e1)
    # Event 2: 周期上报 (oper_type=1)
    e2 = _base()
    e2["extra"] = base_extra
    e2["log_id"] = _clog_rand_str(32)
    e2["oper_type"] = "1"
    e2["media_time"] = str(duration_ms)
    e2["stay_time"] = str(duration_ms)
    e2["status"] = ""
    e2["ts"] = begintime + duration_ms // 2
    arr.append(e2)
    # Event 3: 缓冲标记 (status=2, 短停留)
    e3 = _base()
    e3["extra"] = base_extra
    e3["log_id"] = _clog_rand_str(32)
    e3["media_time"] = "0"
    e3["stay_time"] = "350"
    e3["status"] = "2"
    e3["ts"] = begintime + duration_ms + 200
    arr.append(e3)
    # Event 4: 结束标记 (oper_type=6)
    e4 = _base()
    e4["extra"] = base_extra
    e4["log_id"] = _clog_rand_str(32)
    e4["oper_type"] = "6"
    e4["media_time"] = "0"
    e4["stay_time"] = ""
    e4["status"] = ""
    e4["ts"] = begintime + duration_ms + 400
    arr.append(e4)
    body = "sn=moses_ewt_video&log=" + urllib.parse.quote(
        json.dumps(arr, separators=(",", ":"))
    )
    return uuid_, body


async def send_clog_log(user_id: str, lesson_id, course_id, duration_sec: int) -> bool:
    """补发 BFE 播放日志（clog.ewt360.com 无鉴权），提高完成判定率（机制C 补充）。
    失败不影响主流程（best-effort）。"""
    try:
        uuid_, body = _build_clog_payload(str(lesson_id), str(course_id or ""),
                                          str(user_id), int(duration_sec or 0))
        url = f"{CLOG_URL}/?TrUserId={user_id}&TrUuId={uuid_}&TrVideoBizCode=2001&TrFallback=0"
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                url,
                content=body,
                headers={
                    "Host": "clog.ewt360.com",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "okhttp/3.12.0",
                    "sn": "moses_ewt_video",
                },
            )
        return r.status_code == 200
    except Exception:
        return False


async def _mission_direct_complete(client: EwtClient, school_id: int, task: dict) -> bool:
    """[测试版] 任务型直写完成度：FM(3)/板报(5) 等不走播放心跳，
    POST updateMission {schoolId, contentId, contentType, percent:1} 一次直写 100%。
    参考 ECXiaobai/ewt360_tool（2026-08 实测有效）。"""
    lesson_id = task.get("lessonId")
    content_type = task.get("contentType", 3)
    title = task.get("title") or f"课时 {lesson_id}"
    try:
        data = await client._post(
            "/api/homeworkprod/homework/student/updateMission",
            {"schoolId": school_id, "contentId": str(lesson_id),
             "contentType": content_type, "percent": 1},
        )
        ok = bool(data.get("success"))
        _p_log(f"  [直写][{lesson_id}] {str(title)[:40]} "
              f"updateMission(ct={content_type}) → {'✅ 100%' if ok else str(data)[:120]}",
              flush=True)
        return ok
    except Exception as e:
        _p_log(f"  [直写失败][{lesson_id}] {_translate_error(str(e))}", flush=True)
        return False


async def _brush_one(client: EwtClient, school_id: int, hw_id, task: dict,
                     token: str, speed, burst_size: int, phase_offset_ms: int,
                     force_rounds: int = 0) -> bool:
    """刷单个课时（含机制C重试：检测未通过自动重刷，最多 3 次）。
    返回 True=完成；False=失败/WAF/检测重试耗尽。Token 失效抛 TokenInvalidError。"""
    lesson_id = task.get("lessonId")
    course_id = task.get("courseId")
    content_type = task.get("contentType", 1)
    title = task.get("title") or f"课时 {lesson_id}"
    # [测试版] 任务型直写：FM(3)/板报(5) 不走播放心跳，updateMission 一次直写 100%
    if content_type in (3, 5):
        return await _mission_direct_complete(client, school_id, task)
    DETECTION_MAX_RETRIES = 3
    for attempt in range(1, DETECTION_MAX_RETRIES + 1):
        fr = 3 if attempt > 1 else force_rounds  # 第 2 次起强制 3 轮（机制B 触发 addVideoss）
        status = await _run_once(client, school_id, hw_id, lesson_id, course_id,
                                 token, content_type, speed, burst_size,
                                 phase_offset_ms, fr)
        if status == "ok":
            # 机制C：刷完后检查看课检测 seriousCheckResult（finished 维度）
            # [修复] 进度数据有延迟（刷完需几百ms~几秒才刷新到 percent>=0.8），
            # 未通过时先等待+复核，避免误判导致大量重刷浪费时间
            detection_passed = True
            for _check in range(3):   # 最多复核3次
                try:
                    detection_passed = await client.check_detection_passed(
                        school_id, hw_id, lesson_id)
                except Exception:
                    detection_passed = True  # 查询失败不误判
                if detection_passed:
                    break
                await asyncio.sleep(2)   # 等进度刷新后复查
            if not detection_passed:
                _p_log(f"  ⚠ 看课检测未通过（第 {attempt}/{DETECTION_MAX_RETRIES} 次），"
                      f"{'3s 后自动重刷…' if attempt < DETECTION_MAX_RETRIES else ''}")
                if attempt < DETECTION_MAX_RETRIES:
                    await asyncio.sleep(3)
                continue
            # 完成判定通过 → 额外把 scr 拉成 2 清理后台标记（best-effort，失败不重刷）
            try:
                scr_ok = await client.pass_serious_check(school_id, hw_id, lesson_id,
                                                          content_type=content_type)
            except Exception:
                scr_ok = False
            if scr_ok:
                _p_log("  [通过] 看课检测已通过")
            # scr_ok 恒为 True（pass_serious_check 已降级为不重试不重刷），无 else 分支
            # [测试版] 补发 clog 播放日志（无鉴权端点），提高后台完成判定率（best-effort）
            try:
                clog_ok = await send_clog_log(
                    str(getattr(client, "user_id", "0")),
                    lesson_id, course_id or "", task.get("duration") or 0)
                if clog_ok:
                    _p_log("  [clog] 播放日志已补发")
            except Exception:
                pass
            return True
        if status == "token_invalid":
            raise TokenInvalidError()
        if status == "waf_blocked":
            _p_log("  ✗ 风控拦截（不自动重试），请稍后重试或更换网络")
            return False
        return False  # error — 不重试
    _p_log(f"  ✗ 看课检测未通过，已重试 {DETECTION_MAX_RETRIES} 次，请手动检查")
    return False


async def _relogin(account: str, password: str) -> str:
    """自动登录并保存 token，返回新 token。"""
    token = await login(account, password)
    print(f"  ✓ 新 token: {token[:16]}…{token[-8:]}")
    return token
async def run_brush_all(
    token: str,
    account: str,
    password: str,
    hw_filter: str | None = None,
    concurrency: int = 12,
    qps: float = 400.0,
    offset: int = 0,
    limit: int = 0,
    dry_run: bool = False,
    speed: float | None = None,
    force_rounds: int = 0,
    phase_offset_ms: int = 0,
    burst_size: int = BURST_SIZE,
    force_all: bool = False,
    use_fast: bool | None = None,
    interval: float | None = None,
    stay_ms: int | None = None,
) -> int:
    """主流程：扫描 → 分片 → N路并行刷课 → token 自动续期。返回退出码。
    force_all=True：扫描含已完成课时并强制重刷（force_rounds<=0 时默认每课时跑2轮）。"""
    global BURST_SIZE, FAST_MODE, FAST_INTERVAL, BURST_WAIT, STAY_MS
    if use_fast is not None:
        FAST_MODE = bool(use_fast)
    # 可调参数：波间隔（秒）/ 单轮推进（毫秒）
    if interval is not None and interval > 0:
        if use_fast is None:
            FAST_MODE = (float(interval) < 1.0)   # 未显式指定时按波间隔自动判定
        if FAST_MODE:
            FAST_INTERVAL = float(interval)
        else:
            BURST_WAIT = float(interval)
    if stay_ms is not None and stay_ms > 0:
        STAY_MS = int(stay_ms)
    if burst_size and burst_size > 0:
        BURST_SIZE = int(burst_size)  # CLI 参数同步全局（热更新 watcher 以此为基准）
    concurrency = max(1, int(concurrency))
    if qps and qps > 0:
        set_gateway_qps_cap(qps)
    # force_all 且未显式指定轮数 → 默认 2 轮（已完成课时 needed<=0，必须 force_rounds>0 才会真跑）
    if force_all and force_rounds <= 0:
        force_rounds = 2
    # 倍速 clamp（越界回退竞态模式）
    if speed is not None:
        try:
            speed = float(speed)
        except (TypeError, ValueError):
            speed = None
        if speed is not None and not (0.5 <= speed <= 2.0):
            print(f"⚠ 倍速 {speed} 超出 [0.5, 2.0]，已忽略，回退默认竞态模式")
            speed = None

    client = EwtClient(token)
    login_retries = 0
    try:
        # ---- 获取 school_id（token 有效性在这跳验证）----
        while True:
            try:
                school_info = await client.fetch_school_info()
                school_id = int(school_info["schoolId"])
                break
            except Exception as e:
                msg = _translate_error(str(e))
                if _is_token_invalid(msg) and login_retries < MAX_LOGIN_RETRY:
                    login_retries += 1
                    print(f"⚠ Token 失效，自动重新登录（{login_retries}/{MAX_LOGIN_RETRY}）…")
                    token = await _relogin(account, password)
                    await client.close()
                    client = EwtClient(token)
                    continue
                print(f"✗ 获取学校信息失败: {msg}")
                return 1
        print(f"schoolId: {school_id}")

        # ---- 扫描课时（force_all 时含已完成）----
        tasks = await scan_pending_tasks(client, school_id, hw_filter,
                                         include_finished=force_all)
        if not tasks:
            print("\n没有未完成的课时（可能已全部刷完）")
            return 0
        if offset or limit:
            tasks = tasks[offset:] if not limit else tasks[offset:offset + limit]
            if not tasks:
                print("✗ 分片范围内没有课时")
                return 0
        if force_all:
            print(f"\n共发现 {len(tasks)} 个课时（含已完成，强制重刷模式，每课时至少 {force_rounds} 轮）")
        else:
            print(f"\n共发现 {len(tasks)} 个未完成课时")
        total_duration = sum((t.get("duration") or 0) for _, t in tasks)
        print(f"总时长: {total_duration // 60}min{total_duration % 60}s")

        # ---- dry-run：仅扫描 ----
        if dry_run:
            for i, (hid, t) in enumerate(tasks, 1):
                ct = "[校本] " if t.get("contentType") == 11 else ""
                print(f"  [{i}/{len(tasks)}] {ct}[{t.get('subjectName', '')}] "
                      f"{str(t.get('title', ''))[:50]} (hw={hid} lesson={t.get('lessonId')}) "
                      f"时长{(t.get('duration') or 0)//60}min{(t.get('duration') or 0)%60}s")
            print("\n[dry-run] 仅扫描，未执行刷课")
            return 0

        # ---- N路并行刷课（分批 gather，每批 concurrency 个）----
        if speed:
            _mode_desc = "倍速 " + str(speed) + "x"
        else:
            _iv = FAST_INTERVAL if FAST_MODE else BURST_WAIT
            _mode_desc = "竞态爆发 %.2gs/波%s" % (
                _iv, " · 达标即停" if FAST_MODE else "")
        print(f"\n并行路数: {concurrency} | QPS: {qps or '不限'} | "
              f"竞态爆发: {burst_size}路 | 模式: {_mode_desc} | 单轮 {STAY_MS/1000:.0f}s")
        ok_count = 0
        failed: list[dict] = []
        pending = list(tasks)
        _total_all = len(tasks)
        _dash = ProgressDashboard(_total_all)
        _install_sink(_dash)
        if _PROGRESS_SINK is None:
            print("  ── 总进度 %s 0/%d (0%%)  准备开始" % (progress_bar(0.0, 26), _total_all), flush=True)
        while pending:
            batch = pending[:concurrency]
            pending = pending[concurrency:]

            async def _worker(item):
                hid, t = item
                ct = "[校本] " if t.get("contentType") == 11 else ""
                _lesson = t.get("lessonId")
                _label = (ct + "[" + str(t.get("subjectName", "")) + "] "
                          + str(t.get("title", ""))[:36]
                          + " [" + str((t.get("duration") or 0) // 60) + "min]")
                if _PROGRESS_SINK is not None:
                    _PROGRESS_SINK.start(_lesson, _label)
                else:
                    print("\n▶ [%s] %s" % (t.get("homeworkId"), _label), flush=True)
                try:
                    ok = await _brush_one(client, school_id, hid, t, client.token,
                                          speed, burst_size, phase_offset_ms, force_rounds)
                except TokenInvalidError:
                    if _PROGRESS_SINK is not None:
                        _PROGRESS_SINK.finish(_lesson, False)
                    raise
                if _PROGRESS_SINK is not None:
                    _PROGRESS_SINK.finish(_lesson, bool(ok))
                return (hid, t, ok)

            try:
                results = await asyncio.gather(*[_worker(item) for item in batch])
            except TokenInvalidError:
                if login_retries >= MAX_LOGIN_RETRY:
                    print("✗ Token 再次失效，已达上限 %d 次，中止" % MAX_LOGIN_RETRY)
                    break
                login_retries += 1
                print("\n⚠ Token 失效/被挤下线，自动重登（%d/%d）…" % (login_retries, MAX_LOGIN_RETRY))
                token = await _relogin(account, password)
                await client.close()
                client = EwtClient(token)
                try:
                    school_info = await client.fetch_school_info()
                    school_id = int(school_info["schoolId"])
                except Exception as e:
                    print("✗ 重登后仍无法获取学校信息: " + _translate_error(str(e)))
                    break
                try:
                    remaining = await scan_pending_tasks(client, school_id, hw_filter,
                                                         include_finished=force_all)
                except Exception as e:
                    print("✗ 重新扫描失败: " + _translate_error(str(e)))
                    remaining = []
                pending = remaining + pending
                continue
            for hid, t, ok in results:
                if ok:
                    ok_count += 1
                else:
                    failed.append(t)
            if _PROGRESS_SINK is None:
                _done = ok_count + len(failed)
                _pct = (_done / _total_all) if _total_all else 0.0
                print("  ── 总进度 %s %d/%d (%d%%)  成功 %d  失败 %d"
                      % (progress_bar(_pct, 26), _done, _total_all,
                         int(_pct * 100), ok_count, len(failed)), flush=True)

        _install_sink(None)
        print("\n" + "=" * 62)
        print("处理完成：成功 %d/%d" % (ok_count, len(tasks)))
        if failed:
            print("失败课时：")
            for t in failed:
                print("  - " + str(t.get("title", ""))[:50])
        return 0 if ok_count == len(tasks) else 1
    finally:
        _install_sink(None)
        await client.close()


# ======================================================================
# [CLI]
# ======================================================================

# ======================================================================
#                    🌟 一体化智能 UI 层 🌟
#  说明：本文件是「单文件完整版」，引擎代码已内嵌，无需任何外部依赖脚本。
#        直接运行本文件即可，不会再有"找不到主脚本"问题。
# ======================================================================

APP_VERSION = "Optimized v1.0"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ewt_optimized_config.json")

# ---------- 终端配色 ----------
class C:
    R = "\033[0m"; B = "\033[1m"; DIM = "\033[2m"
    RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
    BLUE = "\033[34m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"; WHITE = "\033[37m"
    BG_BLUE = "\033[44m"; BG_GREEN = "\033[42m"


def _supports_color() -> bool:
    """Windows 老终端/重定向时关闭颜色。"""
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        try:
            os.system("")  # 开启 Windows 10+ ANSI 支持
            return True
        except Exception:
            return False
    return True


USE_COLOR = _supports_color()


def color(text: str, c: str) -> str:
    return f"{c}{text}{C.R}" if USE_COLOR else text


def pr(text: str = ""):
    print(text, flush=True)


def title(text: str, icon: str = ""):
    line = "─" * 62
    pr(color(line, C.CYAN))
    pr(color(f"  {icon} {text}", C.B + C.CYAN))
    pr(color(line, C.CYAN))


def ok(text: str):
    pr(color(f"  ✅ {text}", C.GREEN))


def warn(text: str):
    pr(color(f"  ⚠️  {text}", C.YELLOW))


def err(text: str):
    pr(color(f"  ❌ {text}", C.RED))


def info(text: str):
    pr(color(f"  ℹ️  {text}", C.BLUE))


def step(n: int, total: int, text: str):
    pr()
    pr(color(f"  【第 {n}/{total} 步】", C.B + C.MAGENTA) + color(text, C.B))


def divider():
    pr(color("  " + "·" * 58, C.DIM))


def banner():
    os.system("cls" if os.name == "nt" else "clear")
    pr()
    pr(color("  ══════════════════════════════════════════════════════", C.CYAN))
    pr()
    pr(color("        🎓   E W T 3 6 0   智 能 刷 课 助 手", C.B + C.WHITE))
    pr(color(f"             单文件完整版 · {APP_VERSION}", C.DIM))
    pr()
    pr(color("  ══════════════════════════════════════════════════════", C.CYAN))
    pr()
    pr(color("   ✨ 全程只需回答几个问题，其余自动完成", C.GREEN))
    pr(color("   ✨ 智能识别任务 · 自动分片 · 实时进度 · 自动验证", C.GREEN))
    pr()


def _normalize_input(s: str) -> str:
    """全角→半角归一化。解决中文输入法打出“２”而不是“2”的问题。"""
    out = []
    for ch in s:
        code = ord(ch)
        if code == 0x3000:            # 全角空格
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:  # 全角 ASCII 区（数字/字母/符号）
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def ask(question: str, default=None, hint: str = "") -> str:
    """带默认值的交互提问。"""
    suffix = f" {color('[' + str(default) + ']', C.DIM)}" if default is not None else ""
    pr(color(f"  {question}", C.B) + suffix)
    if hint:
        pr(color(f"     {hint}", C.DIM))
    try:
        val = input(color("   ▸ ", C.CYAN))
    except (EOFError, KeyboardInterrupt):
        pr()
        val = ""
    val = _normalize_input(val).strip()
    if not val and default is not None:
        return str(default)
    return val


def ask_int(question: str, default=None, hint: str = "", lo=None, hi=None) -> int:
    while True:
        val = ask(question, default, hint)
        try:
            n = int(val)
        except ValueError:
            err("请输入数字")
            continue
        if lo is not None and n < lo:
            err(f"不能小于 {lo}")
            continue
        if hi is not None and n > hi:
            err(f"不能大于 {hi}")
            continue
        return n


def ask_yes(question: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    pr(color(f"  {question}", C.B) + f" {color('[' + d + ']', C.DIM)}")
    try:
        v = input(color("   ▸ ", C.CYAN))
    except (EOFError, KeyboardInterrupt):
        pr()
        return default
    v = _normalize_input(v).replace(" ", "").strip().lower()
    if not v:
        return default
    return v in ("y", "yes", "是", "1")


def load_cfg() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cfg(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def progress_bar(pct: float, width: int = 34) -> str:
    """绘制进度条。"""
    pct = max(0.0, min(1.0, pct))
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    if pct >= 1.0:
        c = C.GREEN
    elif pct >= 0.5:
        c = C.CYAN
    else:
        c = C.YELLOW
    return color(bar, c)


def _term_width(default: int = 80) -> int:
    """终端列宽，留 2 列余量防自动换行。"""
    try:
        import shutil
        w = shutil.get_terminal_size((default, 24)).columns
    except Exception:
        w = default
    return max(30, min(w - 2, 120))


def bar_prefix(key) -> str:
    """面板行前缀：[后6位lessonId] """
    k = str(key)
    return "[%s] " % (k[-6:] if len(k) > 6 else k)


DASH_MIN_INTERVAL = 0.1   # 面板最快刷新间隔（秒）=10Hz，防止高频重绘拖慢事件循环

class ProgressDashboard:
    """刷课实时面板：总体进度 + 每个并发课时的进度条，原地刷新不刷屏。
    非交互终端（重定向/管道）自动降级为普通滚动输出。"""

    def __init__(self, total: int):
        self.total = max(1, int(total))
        try:
            self.enabled = bool(sys.stdout.isatty())
        except Exception:
            self.enabled = False
        if os.environ.get("EWT_NO_DASHBOARD"):
            self.enabled = False   # 环境变量可强制关闭面板，回退滚动输出
        self.width = _term_width()
        self.lines = 0      # 已渲染行数
        self.done = 0
        self.ok = 0
        self.fail = 0
        self.tasks = {}     # key -> [title, pct, detail]
        self._last_render = 0.0   # 上次渲染时刻（节流用）
        self._last_width_t = 0.0  # 上次读终端宽度时刻（缓存用）
        self._dirty = False       # 有未渲染的更新

    # ---------------- 内部 ----------------
    def _fit(self, s: str) -> str:
        """按可见宽度截断（ANSI 不计宽，中文算 2 列），避免自动换行。"""
        width = self.width
        out = []
        w = 0
        i = 0
        n = len(s)
        _esc = chr(27)
        while i < n:
            ch = s[i]
            if ch == _esc and i + 1 < n and s[i + 1] == "[":
                j = i + 2
                while j < n and not ("@" <= s[j] <= "~"):
                    j += 1
                j = min(j + 1, n)
                out.append(s[i:j])
                i = j
                continue
            cw = 2 if ord(ch) > 0x2E80 else 1
            if w + cw > width - 1:
                out.append("…")
                break
            out.append(ch)
            w += cw
            i += 1
        return "".join(out)

    def _clear(self) -> None:
        if not self.enabled or self.lines <= 0:
            return
        _cr = chr(13)
        _esc = chr(27)
        for _ in range(self.lines):
            sys.stdout.write(_esc + "[1A")
            sys.stdout.write(_cr + _esc + "[K")
        sys.stdout.write(_cr)
        sys.stdout.flush()
        self.lines = 0

    def _build(self) -> list:
        """构造面板各行内容（截断前）。"""
        pct = self.done / self.total
        head = ("总体 %s %d/%d (%d%%) 成功 %d 失败 %d"
                % (progress_bar(pct, 24), self.done, self.total,
                   int(pct * 100), self.ok, self.fail))
        out = [self._fit(color("  " + head, C.B + C.CYAN))]
        for key, t in self.tasks.items():
            p, detail = t[1], t[2]
            out.append(self._fit("   " + bar_prefix(key)
                                 + progress_bar(p, 16)
                                 + " %3d%%  %s" % (int(p * 100), detail)))
        return out

    def _render(self, force: bool = False) -> None:
        """重绘面板。默认节流（最快 DASH_MIN_INTERVAL 一次）。
        节流 + 宽度缓存 + 单次 write，避免高频刷新抢事件循环。"""
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and (now - self._last_render) < DASH_MIN_INTERVAL:
            self._dirty = True
            return
        self._last_render = now
        self._dirty = False
        if now - self._last_width_t > 1.0:   # 宽度最多每秒读一次（系统调用）
            self.width = _term_width()
            self._last_width_t = now
        _cr = chr(13)
        _esc = chr(27)
        lines = self._build()
        buf = []
        for _ in range(self.lines):          # 上移并清掉旧内容
            buf.append(_esc + "[1A" + _cr + _esc + "[K")
        if self.lines:
            buf.append(_cr)
        for line in lines:                    # 写新内容
            buf.append(_cr + _esc + "[K" + line + chr(10))
        sys.stdout.write("".join(buf))        # 单次 write + flush
        sys.stdout.flush()
        self.lines = len(lines)

    # ---------------- 对外 ----------------
    def start(self, key, title: str = "") -> None:
        key = str(key)
        self.tasks[key] = [title, 0.0, "开始…"]
        self._render(force=True)
        if not self.enabled:
            print("  ▶ " + str(title or key), flush=True)

    def update(self, key, pct: float, detail: str = "") -> None:
        key = str(key)
        try:
            pct = max(0.0, min(1.0, float(pct)))
        except Exception:
            pct = 0.0
        if key in self.tasks:
            self.tasks[key][1] = pct
            self.tasks[key][2] = detail
        else:
            self.tasks[key] = ["", pct, detail]
        self._render()

    def finish(self, key, ok: bool = True) -> None:
        key = str(key)
        self.tasks.pop(key, None)
        self.done = min(self.total, self.done + 1)
        if ok:
            self.ok += 1
        else:
            self.fail += 1
        self._render(force=True)
        if not self.enabled:
            pct = self.done / self.total
            print("  ✓ 完成 " + key + ("" if ok else "（失败）")
                  + "   总进度 %d/%d (%d%%)" % (self.done, self.total, int(pct * 100)),
                  flush=True)

    def show_log(self, msg: str) -> None:
        if not self.enabled:
            print(msg, flush=True)
            return
        self._clear()
        print(msg, flush=True)
        self._render(force=True)

    def close(self) -> None:
        self._clear()


def human_time(sec: float) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec}秒"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}分{s}秒"
    h, m = divmod(m, 60)
    return f"{h}时{m}分{s}秒"




# ======================================================================
#                       主流程 UI
# ======================================================================

async def ui_login(account: str, password: str) -> str:
    """登录获取 token，带清晰提示与错误处理。"""
    pr(color("  ⏳ 正在登录，请稍候…", C.BLUE))
    try:
        token = await login(account, password)
        if not token:
            raise RuntimeError("登录返回空 token")
        ok(f"登录成功  {token[:14]}…{token[-6:]}")
        return token
    except Exception as e:
        msg = str(e)
        if "安全验证" in msg or "验证" in msg:
            err("登录被平台拦截（需完成安全验证）")
            warn("常见原因：短时间内登录太频繁")
            warn("建议：等 5~10 分钟后再试，期间不要反复登录")
        elif "密码" in msg or "账号" in msg:
            err("账号或密码错误，请检查后重试")
        else:
            err(f"登录失败：{msg[:80]}")
        raise


def _cw(text: str) -> int:
    """按显示宽度计算（中文=2）。"""
    w = 0
    for ch in str(text):
        w += 2 if ord(ch) > 0x2E80 else 1
    return w


def _pad(text: str, width: int) -> str:
    """中英文混排补空格对齐。"""
    t = str(text)
    return t + " " * max(0, width - _cw(t))


def _cut(text: str, width: int) -> str:
    """按显示宽度截断（中文算2宽），超出部分用省略号。"""
    t = str(text)
    if _cw(t) <= width:
        return t
    out = ""
    w = 0
    for ch in t:
        cw = 2 if ord(ch) > 0x2E80 else 1
        if w + cw > width - 1:
            break
        out += ch
        w += cw
    return out + "."


def _task_done(t: dict) -> bool:
    """课时是否已完成（finished=True 或 percent>=0.8）。"""
    if t.get("finished") is True:
        return True
    try:
        return float(t.get("percent") or 0) >= 0.8
    except (TypeError, ValueError):
        return False


async def ui_scan_overview(token: str):
    """扫描全部作业并显示完成情况总览（所有作业都列出）。
    返回 (all_tasks, pending, client, school_id)
    """
    pr(color("  ⏳ 正在扫描全部作业，请稍候（约 5~60 秒）…", C.BLUE))
    client = EwtClient(token)
    school_info = await client.fetch_school_info()
    school_id = int(school_info["schoolId"])

    # 1) 先拿全部作业清单——保证「没有视频课时的作业」也能列出
    try:
        all_hws = await client.list_homeworks(school_id)
    except Exception:
        all_hws = []

    # 2) 扫描全部视频类课时
    all_tasks = await scan_pending_tasks(client, school_id, include_finished=True)
    pending = [(h, t) for (h, t) in all_tasks if not _task_done(t)]

    # 3) 用作业清单打底，再填课时统计
    stat = {}
    for hw in all_hws:
        hid = hw.get("homeworkId")
        stat[hid] = {
            "title": str(hw.get("title", "")) or ("作业 " + str(hid)),
            "total": 0, "done": 0,
        }
    for hid, t in all_tasks:
        d = stat.setdefault(hid, {
            "title": str(t.get("homeworkTitle", "")) or ("作业 " + str(hid)),
            "total": 0, "done": 0,
        })
        d["total"] += 1
        if _task_done(t):
            d["done"] += 1

    if not stat:
        return [], [], client, school_id

    # 4) 渲染总览
    pr()
    title("作业完成情况总览", "*")
    pr(color("  序号  作业名称                          完成度          状态", C.B))
    divider()
    for idx, (hid, d) in enumerate(stat.items(), 1):
        total, done = d["total"], d["done"]
        name = _pad(d["title"][:26], 30)
        if total == 0:
            pr("  %3d   %s %s  %s" % (
                idx, name, " " * 12, color("无视频课时", C.DIM)))
            continue
        left = total - done
        pct = done / total
        bar = progress_bar(pct, 12)
        if left == 0:
            status = color("已完成", C.GREEN)
        else:
            status = color("剩 %d 个" % left, C.YELLOW)
        pr("  %3d   %s %s %3d/%-3d  %s" % (idx, name, bar, done, total, status))
    divider()
    total_all = len(all_tasks)
    total_done = total_all - len(pending)
    skip = sum(1 for d in stat.values() if d["total"] == 0)
    pr("  合计：%s 个课时  |  已完成 %s  |  未完成 %s" % (
        color(str(total_all), C.B), color(str(total_done), C.GREEN),
        color(str(len(pending)), C.B + C.YELLOW)))
    if skip:
        pr(color("  另有 %d 个作业无视频课时（仅试卷/测评类，不在本工具范围）" % skip, C.DIM))
    sec = sum(int(t.get("duration") or 0) for _, t in pending)
    if sec:
        pr("  待刷视频总时长：%s" % color(human_time(sec), C.CYAN))
    return all_tasks, pending, client, school_id


def _print_task_list(lst: list, label: str, page_size: int = 0):
    """直接列出全部任务：序号 / 状态 / 科目 / 标题 / 归属作业 / 时长。"""
    total = len(lst)
    if total == 0:
        warn("没有%s" % label)
        ask("按回车返回", "")
        return
    os.system("cls" if os.name == "nt" else "clear")
    pr()
    title("%s（共 %d 个）" % (label, total), "*")
    pr(color("  序号  状态    科目       标题                              归属作业            时长", C.B))
    divider()
    for i, item in enumerate(lst, 1):
        t = item[1] if isinstance(item, tuple) else item
        hid = item[0] if isinstance(item, tuple) else t.get("homeworkId", "")
        df = _task_done(t)
        st = "已完成" if df else "未完成"
        st_col = color(st, C.GREEN if df else C.YELLOW)
        st_pad = " " * max(0, 8 - _cw(st))
        subj = _pad(_cut(t.get("subjectName", ""), 8), 10)
        name = _pad(_cut(t.get("title", ""), 30), 34)
        hw = _pad(_cut(t.get("homeworkTitle", "") or ("作业" + str(hid)), 16), 18)
        dur = human_time(int(t.get("duration") or 0))
        pr("  %4d  %s%s%s%s%s%s" % (i, st_col, st_pad, subj, name, hw, dur))
    divider()
    ok("以上为全部 %d 个任务" % total)
    ask("按回车返回", "")


def ui_show_tasks(all_tasks: list):
    """查看具体任务：全部 / 未完成 / 已完成 / 按作业。"""
    while True:
        pending = [(h, t) for (h, t) in all_tasks if not _task_done(t)]
        done = [(h, t) for (h, t) in all_tasks if _task_done(t)]
        pr()
        title("查看任务详情", "*")
        pr(color("  [ 1 ]", C.B + C.GREEN) + "  全部任务     "
           + color("共 %d 个" % len(all_tasks), C.DIM))
        pr(color("  [ 2 ]", C.B + C.GREEN) + "  未完成任务   "
           + color("共 %d 个" % len(pending), C.B + C.YELLOW))
        pr(color("  [ 3 ]", C.B + C.GREEN) + "  已完成任务   "
           + color("共 %d 个" % len(done), C.GREEN))
        pr(color("  [ 4 ]", C.B + C.GREEN) + "  按作业查看   "
           + color("先选作业再看课时", C.DIM))
        pr(color("  [ 0 ]", C.B + C.RED) + "  返回")
        pr()
        c = ask("请选择（0-4）", "2").strip() or "2"
        if c == "0":
            return
        if c == "1":
            _print_task_list(all_tasks, "全部任务")
        elif c == "2":
            _print_task_list(pending, "未完成任务")
        elif c == "3":
            _print_task_list(done, "已完成任务")
        elif c == "4":
            by_hw = {}
            for hid, t in all_tasks:
                by_hw.setdefault(hid, []).append((hid, t))
            keys = list(by_hw.keys())
            pr()
            for i, hid in enumerate(keys, 1):
                tl = by_hw[hid]
                left = sum(1 for _h, _t in tl if not _task_done(_t))
                ttl = str(tl[0][1].get("homeworkTitle", ""))[:30]
                pr("  %3d  %s  未完成 %d / %d" % (i, _pad(ttl, 32), left, len(tl)))
            pr()
            sel = ask_int("请输入作业序号（0=返回）", 0, lo=0, hi=len(keys))
            if sel == 0:
                continue
            sub = by_hw[keys[sel - 1]]
            _print_task_list(sub, str(sub[0][1].get("homeworkTitle", ""))[:18])


def ui_choose_tasks(all_tasks: list, pending: list):
    """选择刷课范围，返回 (选中任务列表, hw_filter)。
    hw_filter 为 None 表示全部作业，否则限定单个作业。"""
    pr()
    title("选择刷课范围", "*")
    pr(color("  [ 1 ]", C.B + C.GREEN) + "  刷全部未完成   "
       + color("共 %d 个课时，推荐" % len(pending), C.DIM))
    pr(color("  [ 2 ]", C.B + C.GREEN) + "  只刷指定作业   "
       + color("按序号挑一个", C.DIM))
    pr(color("  [ 3 ]", C.B + C.GREEN) + "  强制重刷全部   "
       + color("共 %d 个课时，含已完成" % len(all_tasks), C.YELLOW))
    pr(color("  [ 4 ]", C.B + C.GREEN) + "  查看任务详情   "
       + color("列出全部/未完成/已完成", C.DIM))
    pr(color("  [ 0 ]", C.B + C.RED) + "  返回主菜单")
    pr()
    choice = ask("请选择（0-4）", "1").strip() or "1"

    if choice == "4":
        ui_show_tasks(all_tasks)
        return None, None

    if choice == "0":
        return [], None
    if choice == "2":
        by_hw = {}
        for hid, t in all_tasks:
            by_hw.setdefault(hid, []).append((hid, t))
        # 只列「还有未完成课时」的作业（本菜单语义=挑一个来刷）
        keys = [k for k in by_hw if any(not _task_done(_t) for _h, _t in by_hw[k])]
        if not keys:
            warn("所有作业的视频课时都已完成，如需重刷请返回并选 [3] 强制重刷")
            return [], None
        pr()
        for i, hid in enumerate(keys, 1):
            tl = by_hw[hid]
            left = sum(1 for _h,_t in tl if not _task_done(_t))
            ttl = str(tl[0][1].get("homeworkTitle", ""))[:30]
            pr("  %3d  %s  未完成 %d / %d" % (i, _pad(ttl, 32), left, len(tl)))
        pr()
        sel = ask_int("请输入作业序号", 1, lo=1, hi=len(keys))
        hid = keys[sel - 1]
        picked = [(h, t) for (h, t) in pending if h == hid]
        if not picked:
            warn("该作业没有未完成课时，改为强制重刷该作业")
            picked = [(h, t) for (h, t) in all_tasks if h == hid]
        return picked, hid
    if choice == "3":
        return list(all_tasks), None
    if not pending:
        warn("没有未完成的课时")
        return [], None
    return list(pending), None


async def ui_scan(token: str, account: str, password: str,
                  hw_filter: str = "", force_all: bool = False) -> list:
    """扫描课时，返回任务列表 [(hw_id, task), ...]。"""
    pr(color("  ⏳ 正在扫描你的作业，请稍候（约 10~60 秒）…", C.BLUE))
    client = EwtClient(token)
    school_info = await client.fetch_school_info()
    school_id = int(school_info["schoolId"])
    info(f"学校 ID：{school_id}")

    tasks = await scan_pending_tasks(client, school_id,
                                     hw_filter=hw_filter or None,
                                     include_finished=force_all)
    if not tasks:
        return []

    # 按作业分组统计
    by_hw: dict = {}
    for hid, t in tasks:
        by_hw.setdefault(hid, []).append(t)

    pr()
    ok(f"共找到 {color(str(len(tasks)), C.B + C.YELLOW)} 个课时"
       f"{color('（含已完成，强制重刷）', C.YELLOW) if force_all else color('（未完成）', C.GREEN)}")
    divider()
    for hid, tl in by_hw.items():
        hw_title = str(tl[0].get("homeworkTitle", ""))[:30]
        pr(color(f"   📚 作业 {hid}", C.B) + color(f"  {hw_title}", C.DIM)
           + color(f"   —— {len(tl)} 个课时", C.GREEN))
    divider()

    total_sec = sum(int(t.get("duration") or 0) for _, t in tasks)
    pr(color(f"   ⏱  视频总时长：{human_time(total_sec)}", C.CYAN))
    return tasks


def ui_choose_config(cfg: dict, task_count: int) -> dict:
    """交互式收集刷课配置。"""
    pr()
    pr(color("  💡 建议：直接用推荐值（一路回车）即可，速度已经很快！", C.GREEN))
    pr()

    n_inst = ask_int(
        "并行实例数（开几个进程同时刷）",
        cfg.get("n_inst", 1),
        "推荐 1（单实例最稳）；想更快可填 2~4，但多实例容易触发风控",
        lo=1)
    concurrency = ask_int(
        "并发路数（每个实例同时刷几个课时）",
        cfg.get("concurrency", 18),
        "推荐 18（实测 18 路最快最稳）",
        lo=1)
    burst = ask_int(
        "爆发路数（每个课时同时发几个上报包）",
        cfg.get("burst", 48),
        "推荐 48（越高越快，但过高可能被拦截）",
        lo=1)
    qps = ask(
        "限速 QPS",
        cfg.get("qps", "100000"),
        "推荐 100000（即不限速，实测不易触发风控）")
    try:
        qps_val = float(qps)
        if qps_val <= 0:
            qps_val = 100000.0
    except ValueError:
        qps_val = 100000.0
    # ---- 刷课节奏：波间隔 / 单轮推进 ----
    pr()
    pr(color("  ── 刷课节奏 ──", C.B + C.MAGENTA))
    pr(color("    波间隔越小越快：0.2 秒 ≈ 30 倍速，10 秒 ≈ 4 倍速（保守）", C.DIM))
    _iv_def = cfg.get("interval", 0.2)
    _iv = ask("波间隔（秒）", str(_iv_def),
              "每波之间等多久，越小越快（推荐 0.2）")
    try:
        interval_val = float(_iv)
    except (TypeError, ValueError):
        interval_val = float(_iv_def)
    interval_val = max(0.05, min(interval_val, 60.0))
    _st_def = cfg.get("stay", 10)
    _st = ask("单轮推进（秒）", str(_st_def),
              "每次上报声称看了多久，越大越快（推荐 10）")
    try:
        stay_val = float(_st)
    except (TypeError, ValueError):
        stay_val = float(_st_def)
    stay_val = max(1.0, min(stay_val, 120.0))
    # 波间隔 < 1 秒 → 自动启用「快速复核」行为（达标即停 + 防死循环兜底）
    use_fast = (interval_val < 1.0)

    force_rounds = 0
    force_all = cfg.get("_force_all", False)
    if force_all:
        force_rounds = ask_int(
            "每课时强制重刷轮数",
            cfg.get("force_rounds", 2),
            "默认 2 轮，用于修复看课检测状态",
            lo=1)

    return {
        "n_inst": n_inst, "concurrency": concurrency,
        "burst": burst, "qps": qps_val, "force_rounds": force_rounds,
        "use_fast": use_fast,
        "interval": interval_val, "stay": stay_val,
    }


def ui_confirm(account: str, cfg: dict, task_count: int, force_all: bool) -> bool:
    """配置确认页。"""
    pr()
    title("配置确认", "📋")
    pr(f"   账号      : {color(account, C.B)}")
    pr(f"   课时数    : {color(str(task_count), C.B + C.YELLOW)}")
    pr(f"   模式      : "
       + (color(f"🔁 强制重刷（每课时 {cfg['force_rounds']} 轮）", C.YELLOW) if force_all
          else color("▶ 只刷未完成", C.GREEN)))
    pr(f"   实例数    : {color(str(cfg['n_inst']), C.CYAN)}")
    pr(f"   并发路数  : {color(str(cfg['concurrency']), C.CYAN)}")
    pr(f"   爆发路数  : {color(str(cfg['burst']), C.CYAN)}")
    pr(f"   限速 QPS  : {color(str(cfg['qps']), C.CYAN)}")
    pr("   波间隔    : " + color(str(cfg.get("interval", 0.2)) + " 秒/波", C.YELLOW)
       + color("（越小越快）", C.DIM))
    pr("   单轮推进  : " + color(str(cfg.get("stay", 10)) + " 秒", C.YELLOW))
    divider()
    return ask_yes("确认开始？", True)


async def ui_verify(token: str, account: str, password: str, hw_filter: str):
    """刷完后自动复扫验证。"""
    pr()
    pr(color("  ⏳ 正在复扫验证剩余课时…", C.BLUE))
    try:
        tasks = await ui_scan_quiet(token, hw_filter)
    except Exception as e:
        warn(f"验证扫描失败（不影响已刷结果）：{str(e)[:60]}")
        return
    pr()
    if not tasks:
        ok(color("✅ 确认：已无未完成课时，全部搞定！", C.B + C.GREEN))
    else:
        warn(f"仍有 {len(tasks)} 个课时未完成")
        info("若这些课时提示 506/无权限，说明是账号选科未开通，属正常情况")
        info("否则可重新运行本脚本继续刷")


async def ui_scan_quiet(token: str, hw_filter: str) -> list:
    """静默扫描（不打印列表）。"""
    client = EwtClient(token)
    school_info = await client.fetch_school_info()
    school_id = int(school_info["schoolId"])
    return await scan_pending_tasks(client, school_id,
                                    hw_filter=hw_filter or None,
                                    include_finished=False)


# ======================================================================
#                           主入口
# ======================================================================

def show_help():
    """新手帮助页：手把手教怎么用。"""
    os.system("cls" if os.name == "nt" else "clear")
    pr()
    title("新手使用说明", "📖")
    pr()
    pr(color("  【怎么启动】", C.B + C.YELLOW))
    pr("     直接在本文件所在文件夹打开终端，输入：")
    pr(color("         python ewt_brush_optimized.py", C.B + C.GREEN))
    pr(color("     （Windows 也可以直接双击本文件）", C.DIM))
    pr()
    pr(color("  【首次运行】", C.B + C.YELLOW))
    pr("     程序会自动安装缺失的组件，无需手动操作。")
    pr("     若自动安装失败，按屏幕提示复制命令执行即可。")
    pr()
    pr(color("  【需要准备什么】", C.B + C.YELLOW))
    pr("     · EWT360 账号 + 密码（或准备扫码 / token）")
    pr("     · 一个能上网的环境")
    pr()
    pr(color("  【整个流程】", C.B + C.YELLOW))
    pr("     第 1 步  登录  →  选登录方式，按提示输入")
    pr("     第 2 步  扫描  →  自动找出未完成的课时")
    pr("     第 3 步  设置  →  一路回车用推荐值就行")
    pr("     第 4 步  刷课  →  自动跑，看进度条即可")
    pr()
    pr(color("  【遇到问题】", C.B + C.YELLOW))
    pr("     · 提示\u201c需完成安全验证\u201d → 等 5~10 分钟再试")
    pr("     · 提示\u201c506 无权限\u201d     → 该课时账号没开通，正常")
    pr("     · 中途想停止              → 按 Ctrl + C")
    pr()
    pr(color("  【推荐配置】", C.B + C.YELLOW))
    pr("     实例数 1  ·  并发 18  ·  爆发 48  ·  QPS 100000")
    pr(color("     实测：21 分钟的视频约 41 秒刷完", C.GREEN))
    pr()
    divider()
    ask("按回车返回主菜单", "")


async def main_menu():
    """主菜单：所有功能入口。"""
    cfg = load_cfg()
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        banner()
        title("主菜单", "")
        pr(color("  [ 1 ]", C.B + C.GREEN) + "  开始刷课      "
           + color("推荐，一键完成", C.DIM))
        pr(color("  [ 2 ]", C.B + C.GREEN) + "  只扫描不刷    "
           + color("先看看还剩多少课时", C.DIM))
        pr(color("  [ 3 ]", C.B + C.GREEN) + "  强制重刷全部  "
           + color("修复看课检测状态", C.DIM))
        pr(color("  [ 4 ]", C.B + C.GREEN) + "  清除登录状态  "
           + color("换账号时用", C.DIM))
        pr(color("  [ 5 ]", C.B + C.GREEN) + "  新手使用说明  "
           + color("不知道咋用就看这里", C.DIM))
        pr(color("  [ 0 ]", C.B + C.RED) + "  退出程序")
        divider()
        if cfg.get("account"):
            pr(color(f"  当前账号：{cfg.get('account')}", C.DIM))
            pr()

        choice = ask("请输入数字（0-5）", "1").strip() or "1"
        # [容错] 输入法可能带全角/多余字符，提取其中唯一数字
        _only = "".join(ch for ch in choice if ch.isdigit())
        if len(_only) == 1 and _only in "012345":
            choice = _only

        if choice == "1":
            return "brush", False
        if choice == "2":
            return "scan", False
        if choice == "3":
            return "brush", True
        if choice == "4":
            try:
                if os.path.exists(TOKEN_FILE):
                    os.remove(TOKEN_FILE)
                ok("已清除登录状态，下次需要重新登录")
            except Exception as e:
                warn(f"清除失败：{str(e)[:60]}")
            ask("按回车返回主菜单", "")
            continue
        if choice == "5":
            show_help()
            continue
        if choice == "0":
            return "exit", False
        warn("请输入 0-5 之间的数字")
        ask("按回车重试", "")


async def ui_main(action: str = "brush", force_all_forced: bool = False):
    cfg = load_cfg()

    # 第 1 步：登录（支持 token / 账号密码 / 扫码）
    step(1, 4, "登录账号")

    # 优先复用本地已保存 token（免登录，最省事）
    token = ""
    try:
        token = load_token_file() or ""
    except Exception:
        token = ""
    token_valid = bool(token) and bool(re.match(r"^\d+-(1|2)-[0-9a-fA-F]+$", token))

    if token_valid:
        info(f"检测到本地已保存 token：{token[:14]}…{token[-6:]}")
        if ask_yes("直接使用该 token（免登录，推荐）？", True):
            ok("已复用本地 token")
        else:
            token_valid = False

    # token 无效或用户选择重新登录 → 进入多方式登录
    if not token_valid:
        while True:
            try:
                token = await login_interactive(cfg)
                break
            except KeyboardInterrupt:
                pr()
                info("已取消")
                return 0
            except Exception as e:
                pr()
                err(f"登录失败：{str(e)[:150]}")
                pr()
                if not ask_yes("是否换个方式重试？", True):
                    return 1

    account = cfg.get("account", "")
    password = cfg.get("password", "")
    save_cfg(cfg)

    # 第 2 步：扫描任务（总览 + 选择范围）
    step(2, 4, "扫描作业")
    try:
        all_tasks, pending, client, school_id = await ui_scan_overview(token)
    except Exception as e:
        err("扫描失败：%s" % str(e)[:100])
        warn("可能是 token 失效，请重新运行脚本登录")
        return 1

    if not all_tasks:
        warn("没有扫描到任何课时")
        ask("按回车返回主菜单", "")
        return 0

    # 让用户选择刷课范围
    while True:
        selected, hw_filter = ui_choose_tasks(all_tasks, pending)
        if selected is None:
            continue
        if not selected:
            pr()
            info("已取消")
            return 0
        break

    force_all = False
    # 判断是否含已完成课时（判断模式）
    if any(_task_done(t) for _, t in selected):
        force_all = True

    tasks = selected

    # 第 3 步：配置
    step(3, 4, "刷课设置")
    cfg["_force_all"] = force_all
    run_cfg = ui_choose_config(cfg, len(tasks))
    save_cfg({"account": account, "password": password,
              "n_inst": run_cfg["n_inst"], "concurrency": run_cfg["concurrency"],
              "burst": run_cfg["burst"], "qps": str(int(run_cfg["qps"])),
              "force_rounds": run_cfg["force_rounds"],
              "use_fast": "2" if run_cfg.get("use_fast") else "1",
              "interval": run_cfg.get("interval"),
              "stay": run_cfg.get("stay")})

    if not ui_confirm(account, run_cfg, len(tasks), force_all):
        pr()
        info("已取消")
        return 0

    # 第 4 步：执行
    step(4, 4, "开始刷课")

    async def _one_round(tk: str) -> str:
        """用引擎跑一轮（run_brush_all 内部自带登录/扫描/刷课/续期）。"""
        await run_brush_all(
            tk, account, password,
            hw_filter=hw_filter, concurrency=run_cfg["concurrency"],
            qps=run_cfg["qps"], offset=0, limit=0, dry_run=False, speed=None,
            force_rounds=run_cfg.get("force_rounds", 0),
            phase_offset_ms=0, burst_size=run_cfg["burst"], force_all=force_all,
            use_fast=run_cfg.get("use_fast"),
            interval=run_cfg.get("interval"),
            stay_ms=int(float(run_cfg.get("stay", 10)) * 1000))
        return tk

    title("开始刷课", "🚀")
    pr(color("   刷课期间可随时 Ctrl+C 中断，已完成课时不会丢失。", C.DIM))
    pr()
    t0 = time.time()
    rc = 0
    try:
        await _one_round(token)
    except KeyboardInterrupt:
        pr()
        warn("已手动中断")
        rc = 130
    except TokenInvalidError:
        warn("token 失效，尝试重新登录…")
        try:
            token = await ui_login(account, password)
            await _one_round(token)
        except Exception as e:
            err(f"续刷失败：{str(e)[:100]}")
            rc = 1
    except Exception as e:
        err(f"执行异常：{str(e)[:120]}")
        rc = 1

    elapsed = time.time() - t0
    pr()
    title("刷课结束", "🏁")
    pr(f"   总耗时    : {color(human_time(elapsed), C.B + C.CYAN)}")
    if rc == 0:
        ok(color("🎉 本轮完成！", C.B + C.GREEN))
    else:
        warn("部分课时未完成（可能无权限或触发风控），可稍后重跑续刷")

    # 自动验证
    pr()
    if ask_yes("是否复扫验证剩余课时？", True):
        await ui_verify(token, account, password, "")
    pr()
    pr(color("  感谢使用！有问题欢迎反馈 💬", C.DIM))
    return rc


def _build_parser():
    """精简 CLI 解析器（兼容高级用户直接用参数运行）。"""
    import argparse
    p = argparse.ArgumentParser(
        prog="ewt_brush_optimized.py",
        description="EWT360 智能刷课助手（单文件版）",
        epilog="不带参数运行会进入图形化菜单，更适合日常使用。")
    p.add_argument("--account", help="账号")
    p.add_argument("--password", help="密码")
    p.add_argument("--token", help="已有 token（跳过登录）")
    p.add_argument("--hw", help="只刷指定作业 ID")
    p.add_argument("--concurrency", type=int, default=18, help="并发路数（默认18）")
    p.add_argument("--burst", type=int, default=48, help="爆发路数（默认48）")
    p.add_argument("--qps", type=float, default=100000.0, help="限速QPS（默认100000=不限速）")
    p.add_argument("--interval", type=float, default=None,
                   help="波间隔秒（默认0.2，越小越快；≥1秒自动转保守节奏）")
    p.add_argument("--stay", type=float, default=None,
                   help="单轮推进秒（默认10，越大越快）")
    p.add_argument("--offset", type=int, default=0, help="起始分片（多实例用）")
    p.add_argument("--limit", type=int, default=0, help="分片数量（多实例用）")
    p.add_argument("--phase-offset", type=int, default=0, help="首轮错峰毫秒")
    p.add_argument("--force-rounds", type=int, default=0, help="强制重刷轮数")
    p.add_argument("--force-all", action="store_true", help="强制重刷全部（含已完成）")
    p.add_argument("--dry-run", action="store_true", help="仅扫描不刷课")
    return p


async def _run(args) -> int:
    """CLI 模式：直接调用引擎执行。"""
    token = (args.token or "").strip()
    account = (args.account or "").strip()
    password = (args.password or "").strip()
    if not token:
        token = load_token_file() or ""
    if not re.match(r"^\d+-(1|2)-[0-9a-fA-F]+$", token or ""):
        if not account or not password:
            print("需要 --account/--password 或 --token")
            return 1
        print("正在登录…")
        token = await login(account, password)
        print("登录成功:", token[:16] + "…")
    if args.dry_run:
        args.force_all = True   # dry-run 需要扫全量
    return await run_brush_all(
        token, account, password,
        hw_filter=args.hw,
        concurrency=args.concurrency,
        qps=args.qps,
        offset=args.offset,
        limit=args.limit,
        dry_run=args.dry_run,
        speed=None,
        force_rounds=args.force_rounds,
        phase_offset_ms=args.phase_offset,
        burst_size=args.burst,
        force_all=args.force_all,
        interval=args.interval,
        stay_ms=int(args.stay * 1000) if args.stay else None,
    )


def main() -> int:
    logging.basicConfig(level=logging.WARNING,
                        format="%(asctime)s %(levelname)s %(message)s")

    argv = sys.argv[1:]
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    # 无参数 → 图形化主菜单（小白友好）
    if not argv:
        try:
            while True:
                action, force_all = asyncio.run(main_menu())
                if action == "exit":
                    os.system("cls" if os.name == "nt" else "clear")
                    pr()
                    pr(color("  感谢使用，再见！", C.B + C.GREEN))
                    pr()
                    return 0
                try:
                    asyncio.run(ui_main(action, force_all))
                except KeyboardInterrupt:
                    pr()
                    warn("已中断本次任务，返回主菜单")
                    time.sleep(1.5)
        except KeyboardInterrupt:
            pr()
            pr(color("  已退出，再见！", C.GREEN))
            return 130

    # 有参数 → 传统 CLI 路径（兼容高级用户）
    args = _build_parser().parse_args()
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        pr()
        warn("已退出")
        return 130


if __name__ == "__main__":
    sys.exit(main())
