# 下面是你原有的代码...
import os
import time
import os
import sys
import time
import random
import json
import re
import subprocess
import shutil
import ssl
import http.client
import urllib.request
import urllib.parse
import urllib.error
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv():
        return False

def _setup_stdio():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_setup_stdio()

# 加载 .env 文件中的变量
load_dotenv()

# 现在通过系统变量读取，代码里再也看不到明文 Key 了
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
SERVER_CHAN_KEY = os.getenv("SERVER_CHAN_KEY")
NETWORK_STACK_BROKEN = False

from src.config.settings import (
    WHOLESALE_KEYWORDS,
    INVENTORY_STYLE_KEYWORDS,
    INVENTORY_STYLE_PATTERNS,
    NON_PERSONAL_STRONG_KEYWORDS,
    NON_PERSONAL_SOFT_KEYWORDS,
    NON_PERSONAL_PATTERNS,
    IMPLICIT_VARIANT_PATTERNS
)

def parse_single_price(price_text):
    if not price_text:
        return None
    text = str(price_text).strip()
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if not numbers:
        return None
    range_markers = ["-", "~", "～", "到", "至", "起", "最低", "区间", "元起", "起拍"]
    has_range_marker = any(marker in text for marker in range_markers)
    if len(numbers) >= 2 and has_range_marker:
        return None
    if "起" in text and len(numbers) >= 1:
        return None
    try:
        return float(numbers[0])
    except Exception:
        return None

def is_range_price(price_text):
    if not price_text:
        return False
    text = str(price_text).strip()
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    range_markers = ["-", "~", "～", "到", "至", "起", "最低", "区间", "元起", "起拍"]
    if len(numbers) >= 2 and any(marker in text for marker in range_markers):
        return True
    if "起" in text and len(numbers) >= 1:
        return True
    return False

def detect_non_personal_signals(title, price_text, item_text):
    merged = f"{title} {price_text} {item_text}".lower()
    reasons = []
    strong_hits = [keyword for keyword in NON_PERSONAL_STRONG_KEYWORDS if keyword in merged]
    if strong_hits:
        reasons.append(f"强商家词:{'|'.join(strong_hits[:2])}")

    wholesale_hits = [keyword for keyword in WHOLESALE_KEYWORDS if keyword in merged]
    if wholesale_hits:
        reasons.append(f"批发词:{'|'.join(wholesale_hits[:2])}")

    inventory_hits = [keyword for keyword in INVENTORY_STYLE_KEYWORDS if keyword in merged]
    if inventory_hits:
        reasons.append(f"库存词:{'|'.join(inventory_hits[:2])}")

    soft_hits = [keyword for keyword in NON_PERSONAL_SOFT_KEYWORDS if keyword in merged]
    if len(soft_hits) >= 2:
        reasons.append(f"弱商家词:{'|'.join(soft_hits[:2])}")

    if any(re.search(pattern, merged) for pattern in INVENTORY_STYLE_PATTERNS):
        reasons.append("命中库存样式模式")

    if any(re.search(pattern, merged) for pattern in NON_PERSONAL_PATTERNS):
        reasons.append("命中商家规则模式")

    if "x" in merged and re.search(r"x\s*\d+", merged):
        reasons.append("命中组合数量表达")

    if any(re.search(pattern, merged) for pattern in IMPLICIT_VARIANT_PATTERNS):
        reasons.append("命中隐式多款枚举")
    else:
        lines = re.split(r"[\n；;。]", merged)
        for line in lines:
            if not line.strip():
                continue
            has_attr = any(token in line for token in ["颜色", "款式", "型号", "版本", "内存", "容量", "配色", "机型"])
            if not has_attr:
                continue
            variant_sep_count = len(re.findall(r"[/、|,，]|和|或", line))
            if variant_sep_count >= 2:
                reasons.append("命中属性多选描述")
                break

    hard_exclude = any(text.startswith("强商家词") for text in reasons) or any(text.startswith("批发词") for text in reasons)
    variant_exclude = any("隐式多款" in text or "属性多选" in text for text in reasons)
    soft_exclude = len(reasons) >= 2
    return (hard_exclude or variant_exclude or soft_exclude), reasons

def decode_process_output(raw):
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8", "gb18030", "cp936", "latin-1"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")

def http_request_via_httpclient(url, method, headers, data, timeout):
    conn = None
    try:
        parsed = urllib.parse.urlsplit(url)
        if not parsed.scheme or not parsed.netloc:
            return False, 0, "invalid url", "httpclient"
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        request_headers = dict(headers or {})
        body = data
        if isinstance(data, str):
            body = data.encode("utf-8")
        if parsed.scheme.lower() == "https":
            conn = http.client.HTTPSConnection(
                parsed.hostname,
                parsed.port or 443,
                timeout=timeout,
                context=ssl.create_default_context()
            )
        else:
            conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 80, timeout=timeout)
        conn.request(method=method, url=path, body=body, headers=request_headers)
        response = conn.getresponse()
        raw = response.read()
        return True, response.status, raw.decode("utf-8", errors="ignore"), "httpclient"
    except Exception as e:
        return False, 0, str(e), "httpclient"
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

def fetch_dom_via_edge(url, timeout):
    edge_candidates = [
        shutil.which("msedge"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    edge_path = next((path for path in edge_candidates if path and os.path.exists(path)), None)
    if not edge_path:
        return False, 0, "edge not found", "edge-dom"
    command = [edge_path, "--headless", "--disable-gpu", "--dump-dom", url]
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout + 5)
        stdout_text = decode_process_output(result.stdout).strip()
        stderr_text = decode_process_output(result.stderr).strip()
        if result.returncode == 0 and "<html" in stdout_text.lower():
            return True, 200, stdout_text, "edge-dom"
        return False, result.returncode, stderr_text or stdout_text or "edge fetch failed", "edge-dom"
    except Exception as e:
        return False, 0, str(e), "edge-dom"

def http_request_with_fallback(url, method="GET", headers=None, data=None, timeout=30):
    global NETWORK_STACK_BROKEN
    final_headers = headers or {}
    try:
        req = urllib.request.Request(url, data=data, headers=final_headers, method=method)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(req, timeout=timeout) as response:
            body = response.read().decode('utf-8', errors='ignore')
            return True, response.status, body, "urllib-no-proxy"
    except Exception as e:
        if "WinError 10022" in str(e):
            NETWORK_STACK_BROKEN = True
    try:
        req = urllib.request.Request(url, data=data, headers=final_headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode('utf-8', errors='ignore')
            return True, response.status, body, "urllib"
    except Exception:
        pass
    ok, status, body, channel = http_request_via_httpclient(url, method, final_headers, data, timeout)
    if ok:
        return True, status, body, channel
    if "WinError 10022" in str(body):
        NETWORK_STACK_BROKEN = True
    if method == "GET" and not data:
        ok, status, body, channel = fetch_dom_via_edge(url, timeout)
        if ok:
            return True, status, body, channel
    curl_data = ""
    if data:
        try:
            curl_data = data.decode("utf-8", errors="ignore")
        except Exception:
            curl_data = ""
    command = ["curl.exe", "-sS", "-L", "--max-time", str(timeout), "--noproxy", "*", "-x", "", "-X", method]
    for key, value in final_headers.items():
        command.extend(["-H", f"{key}: {value}"])
    if curl_data:
        command.extend(["--data-raw", curl_data])
    command.append(url)
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout + 2)
        stdout_text = decode_process_output(result.stdout).strip()
        stderr_text = decode_process_output(result.stderr).strip()
        if result.returncode == 0 and stdout_text:
            return True, 200, stdout_text, "curl"
        curl_error = stderr_text or stdout_text or f"curl returncode={result.returncode}"
        if "WinError 10022" in curl_error:
            NETWORK_STACK_BROKEN = True
    except Exception:
        curl_error = ""
    ps_script = (
        "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
        "$OutputEncoding=[System.Text.Encoding]::UTF8;"
        "$ProgressPreference='SilentlyContinue';"
        f"$u='{url}';"
        f"$m='{method}';"
        "$res=Invoke-WebRequest -Uri $u -Method $m -UseBasicParsing -TimeoutSec "
        f"{max(3, int(timeout))} -Proxy $null;"
        "Write-Output $res.Content"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            timeout=timeout + 3
        )
        stdout_text = decode_process_output(result.stdout).strip()
        stderr_text = decode_process_output(result.stderr).strip()
        if result.returncode == 0 and stdout_text:
            return True, 200, stdout_text, "powershell"
        final_error = stderr_text or stdout_text or curl_error or "network request failed"
        if "WinError 10022" in final_error:
            NETWORK_STACK_BROKEN = True
        return False, result.returncode, final_error, "powershell"
    except Exception as e:
        final_error = str(e) or curl_error or "network request failed"
        if "WinError 10022" in final_error:
            NETWORK_STACK_BROKEN = True
        return False, 0, final_error, "powershell"

def send_wechat_alert(title, price, reason):
    print(f"📡 正在发射红色警报到手机微信...")
    if not SERVER_CHAN_KEY:
        print("Warning 未设置 SERVER_CHAN_KEY，跳过微信报警")
        return
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
    data = {
        "title": f"Alert 发现捡漏机！{price}元",
        "desp": f"**商品:** {title}\n\n**价格:** {price}元\n\n**AI分析:** {reason}\n\n[点击前往闲鱼查看](https://www.goofish.com/search?q=Switch+Lite)"
    }
    try:
        encoded_data = urllib.parse.urlencode(data).encode('utf-8')
        ok, status, _, channel = http_request_with_fallback(
            url=url,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=encoded_data,
            timeout=20
        )
        if ok and status == 200:
            print(f"OK 警报送达成功 ({channel})")
        else:
            print(f"Error 报警发送失败: {status}")
    except Exception as e:
        print(f"Error 报警发送失败: {e}")

def analyze_with_ai(title, price, threshold):
    if not DEEPSEEK_KEY:
        return {"is_arbitrage_opportunity": price <= threshold * 0.92, "reason": "未配置AI Key，已使用本地阈值规则"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个二手套利专家。价格极低且无暗病时推荐购买。返回 JSON: is_arbitrage_opportunity (bool), reason (str)"},
            {"role": "user", "content": f"标题:{title}, 价格:{price}, 阈值:{threshold}"}
        ],
        "response_format": {"type": "json_object"}
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}", 
        "Content-Type": "application/json",
        "User-Agent": "TradeSniper/1.0"
    }
    
    try:
        ok, status, body, _ = http_request_with_fallback(
            url="https://api.deepseek.com/chat/completions",
            method="POST",
            headers=headers,
            data=json.dumps(payload).encode('utf-8'),
            timeout=30
        )
        if ok and status == 200:
            api_response = json.loads(body)
            content = api_response['choices'][0]['message']['content']
            return json.loads(content)
        return {"is_arbitrage_opportunity": price <= threshold * 0.9, "reason": "AI接口不可用，已使用本地阈值规则"}
    except Exception as e:
        print(f"AI Analysis failed: {e}")
        return {"is_arbitrage_opportunity": price <= threshold * 0.9, "reason": "AI分析异常，已使用本地阈值规则"}

def calculate_median(data):
    n = len(data)
    if n == 0:
        return 0
    sorted_data = sorted(data)
    if n % 2 == 1:
        return sorted_data[n // 2]
    else:
        return (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2

def calculate_dynamic_threshold(prices_str):
    clean_prices = []
    for p in prices_str:
        try:
            val = parse_single_price(p)
            if val is None:
                continue
            if 300 < val < 1200:
                clean_prices.append(val)
        except:
            continue
    
    if len(clean_prices) < 3:
        return 520.0
    
    median = calculate_median(clean_prices)
    return median * 0.8

def get_sync_playwright():
    try:
        from playwright.sync_api import sync_playwright as playwright_sync_playwright
        return playwright_sync_playwright, None
    except Exception as e:
        return None, e

def get_env_int(name, default_value, min_value, max_value):
    raw = os.getenv(name, str(default_value)).strip()
    try:
        value = int(raw)
    except Exception:
        value = default_value
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value

def get_patrol_sleep_seconds():
    min_sleep = get_env_int("PATROL_SLEEP_MIN", 300, 10, 3600)
    max_sleep = get_env_int("PATROL_SLEEP_MAX", 600, 10, 7200)
    if max_sleep < min_sleep:
        min_sleep, max_sleep = max_sleep, min_sleep
    return random.uniform(min_sleep, max_sleep)

def get_pause_flag_file():
    return os.getenv("PATROL_PAUSE_FILE", "patrol.pause").strip() or "patrol.pause"

def is_patrol_paused():
    return os.path.exists(get_pause_flag_file())

def wait_if_paused():
    paused_once = False
    flag_file = get_pause_flag_file()
    while is_patrol_paused():
        if not paused_once:
            print(f"⏸️ 巡逻已暂停，删除 {flag_file} 后自动恢复")
            paused_once = True
        time.sleep(1)
    if paused_once:
        print("▶️ 已恢复巡逻")

def controlled_sleep(seconds):
    remaining = max(0, int(round(float(seconds))))
    while remaining > 0:
        wait_if_paused()
        time.sleep(1)
        remaining -= 1

def is_socket_runtime_error(err):
    text = str(err)
    return "WinError 10022" in text or "_overlapped" in text

def start_patrol_fallback_http():
    print("Warning 浏览器模式不可用，已切换到HTTP兜底巡逻模式")
    print("该模式仅用于保持程序可运行，筛选精度低于浏览器模式")
    history_alerts = set()
    query_url = "https://www.goofish.com/search?q=Switch+Lite"
    network_unavailable = False
    sample_titles = [
        "任天堂 Switch Lite 自用闲置",
        "Switch Lite 国行/日版 多版本可选",
        "Switch Lite 成色9新 正常使用"
    ]
    sample_prices = ["¥699", "¥599", "¥730"]
    sample_texts = [
        "个人自用 闲置出 有轻微使用痕迹",
        "多型号 颜色可选 长期有货",
        "家用一台 正常使用 功能完好"
    ]
    while True:
        wait_if_paused()
        print(f"\nTime 兜底Patrol check-in: {time.strftime('%H:%M:%S')}")
        titles = []
        prices_str = []
        item_texts = []
        try:
            if not network_unavailable:
                ok, _, html, channel = http_request_with_fallback(
                    url=query_url,
                    method="GET",
                    headers={"User-Agent": "Mozilla/5.0 TradeSniper/1.0"},
                    timeout=30
                )
                if ok and html:
                    if "error-container" in html and "goofish" in html.lower():
                        network_unavailable = True
                        print(f"Warning 已连通网络，但被目标站点拦截访问({channel})，本轮切换离线兜底样本")
                        titles = sample_titles[:]
                        prices_str = sample_prices[:]
                        item_texts = sample_texts[:]
                        continue
                    blocks = re.findall(r'(?s)<a[^>]*href="[^"]*"[^>]*>(.*?)</a>', html)
                    for block in blocks[:80]:
                        text = re.sub(r"<[^>]+>", " ", block)
                        text = re.sub(r"\s+", " ", text).strip()
                        if not text:
                            continue
                        price_match = re.search(r"(?:¥|￥)\s*\d+(?:\.\d+)?", text)
                        title_match = re.search(r"(switch|lite|任天堂)[^¥￥]{0,60}", text, re.IGNORECASE)
                        if price_match and title_match:
                            prices_str.append(price_match.group(0))
                            titles.append(title_match.group(0).strip())
                            item_texts.append(text)
                else:
                    network_unavailable = True
                    print(f"Warning HTTP抓取失败({channel})，本轮直接切换离线兜底样本")
                    titles = sample_titles[:]
                    prices_str = sample_prices[:]
                    item_texts = sample_texts[:]
            else:
                titles = sample_titles[:]
                prices_str = sample_prices[:]
                item_texts = sample_texts[:]
            if not prices_str or not titles:
                print("Warning HTTP兜底模式未抓取到有效数据")
            else:
                THRESHOLD = calculate_dynamic_threshold(prices_str)
                print(f"Stats 当前动态阈值: {THRESHOLD}")
                for i in range(min(len(titles), len(prices_str), 8)):
                    title = titles[i].strip()
                    raw_price = prices_str[i].strip()
                    item_text = item_texts[i] if i < len(item_texts) else ""
                    if is_range_price(raw_price):
                        print(f"🚫 跳过区间价商品: {title} ({raw_price})")
                        continue
                    is_non_personal, exclude_reasons = detect_non_personal_signals(title, raw_price, item_text)
                    if is_non_personal:
                        reason_text = "、".join(exclude_reasons[:2]) if exclude_reasons else "命中非个人闲置规则"
                        print(f"🚫 跳过非个人闲置商品: {title} ({raw_price}) - {reason_text}")
                        continue
                    price = parse_single_price(raw_price)
                    if price is None:
                        continue
                    if price <= THRESHOLD and title not in history_alerts:
                        print(f"Search 发现潜在机会: {title} ({price}元), 正在AI分析...")
                        decision = analyze_with_ai(title, price, THRESHOLD)
                        if decision and decision.get("is_arbitrage_opportunity"):
                            send_wechat_alert(title, price, decision.get('reason', '无理由'))
                            history_alerts.add(title)
                        else:
                            reason = decision.get('reason') if decision else "AI分析失败或不推荐"
                            print(f"⚪ 忽略: {title} ({price}元) - {reason}")
        except Exception as e:
            if "WinError 10022" in str(e) or NETWORK_STACK_BROKEN:
                network_unavailable = True
                print("Warning 检测到系统网络调用异常，已切换到离线兜底样本模式")
            print(f"Warning HTTP兜底巡逻异常: {e}")
        sleep_time = get_patrol_sleep_seconds()
        print(f"💤 本轮巡逻结束，进入深度睡眠 {int(sleep_time)} 秒...")
        controlled_sleep(sleep_time)

def start_patrol():
    if os.getenv("FORCE_HTTP_FALLBACK", "0").strip() == "1":
        print("Warning 已启用强制HTTP巡逻模式，跳过Playwright浏览器流程")
        start_patrol_fallback_http()
        return
    sync_playwright, import_error = get_sync_playwright()
    if sync_playwright is None:
        print(f"Warning Playwright加载失败: {import_error}")
        if is_socket_runtime_error(import_error):
            print("Warning 检测到系统异步IO/套接字运行时异常（_overlapped），当前不是页面访问超时问题")
            print("建议先修复本机 Python 运行时或 Winsock 环境，再恢复浏览器模式")
        start_patrol_fallback_http()
        return
    with sync_playwright() as p:
        print("Agent Agent 已进入潜伏模式，开始 24H 巡逻...")
        
        browser = None
        # 尝试使用多种浏览器通道
        # 1. 默认 Chromium (Playwright 自带)
        # 2. 本地 Chrome (channel="chrome")
        # 3. 本地 Edge (channel="msedge")
        
        use_local_browser_only = os.getenv("USE_LOCAL_BROWSER_ONLY", "1").strip() != "0"
        if use_local_browser_only:
            launch_configs = [
                {"channel": "msedge", "args": ["--disable-blink-features=AutomationControlled"]},
                {"channel": "chrome", "args": ["--disable-blink-features=AutomationControlled"]}
            ]
        else:
            launch_configs = [
                {"channel": "msedge", "args": ["--disable-blink-features=AutomationControlled"]},
                {"channel": "chrome", "args": ["--disable-blink-features=AutomationControlled"]},
                {"args": ["--disable-blink-features=AutomationControlled"]}
            ]

        for config in launch_configs:
            browser_name = config.get("channel", "Default Chromium")
            try:
                print(f"尝试启动浏览器: {browser_name}...")
                # 从环境变量获取 HEADLESS 配置
                headless_mode = os.getenv("HEADLESS", "True").lower() == "true"
                # 如果需要登录（LOGIN_MODE=1），强制关闭 headless
                if os.getenv("LOGIN_MODE", "0") == "1":
                    headless_mode = False
                    print("Warning 登录模式：已强制显示浏览器窗口")

                browser = p.chromium.launch(headless=headless_mode, **config)
                print(f"OK 成功启动: {browser_name} (Headless: {headless_mode})")
                break
            except Exception as e:
                print(f"Error 启动 {browser_name} 失败: {e}")
        
        if not browser:
            print("\nAlert 所有浏览器启动尝试均失败！")
            if use_local_browser_only:
                print("当前已启用本地浏览器优先模式，运行时不会触发Playwright浏览器下载。")
                print("请确认本机已安装 Edge 或 Chrome，或设置 USE_LOCAL_BROWSER_ONLY=0 后重试。")
            else:
                print("请尝试手动安装驱动（推荐使用国内镜像加速）：")
                print("1. 设置环境变量: $env:PLAYWRIGHT_DOWNLOAD_HOST='https://npmmirror.com/mirrors/playwright/'")
                print("2. 运行安装命令: playwright install chromium")
            start_patrol_fallback_http()
            return

        try:
            # 加载状态
            if os.path.exists("state.json"):
                try:
                    context = browser.new_context(storage_state="state.json")
                    print("OK 成功加载 state.json")
                except Exception as e:
                    print(f"Warning state.json 加载失败，将使用新会话: {e}")
                    context = browser.new_context()
            else:
                context = browser.new_context()

                
            page = context.new_page()
            history_alerts = set()

            while True:
                wait_if_paused()
                print(f"\nTime Patrol check-in: {time.strftime('%H:%M:%S')}")
                try:
                    # 使用 domcontentloaded 等待页面加载完成
                    page.goto("https://www.goofish.com/search?q=Switch+Lite", wait_until="domcontentloaded", timeout=60000)
                    
                    # 检查是否需要登录或验证码
                    if "login" in page.url or "verify" in page.url:
                        print("Warning 检测到可能需要登录或验证，请在浏览器中手动操作...")
                        if headless_mode:
                            print("Error 警告：当前为无头模式，无法手动登录！建议重启使用登录模式。")
                        
                        # 给用户300秒时间登录，期间不断尝试保存状态
                        for i in range(10): 
                             print(f"Waiting 等待登录操作 ({i+1}/10)...")
                             controlled_sleep(30)
                             try:
                                 context.storage_state(path="state.json")
                                 print("OK 已尝试保存当前状态到 state.json")
                                 # 如果URL不再包含 login/verify，可能登录成功了
                                 if "login" not in page.url and "verify" not in page.url:
                                     print("OK 检测到页面跳转，假设登录成功！")
                                     break
                             except: pass

                    # 尝试多种选择器策略，提高鲁棒性
                    try:
                        # 策略1: 尝试通用卡片结构 (适配常见电商布局)
                        # 查找包含价格符号的元素
                        price_elements = page.locator("text=¥").all()
                        if not price_elements:
                             # 策略2: 尝试旧的 hash 类名 (作为备选)
                             page.wait_for_selector('.main-title--sMrtWSJa', timeout=5000)
                             prices_str = page.locator('.number--NKh1vXWM').all_inner_texts()
                             titles = page.locator('.main-title--sMrtWSJa').all_inner_texts()
                             item_texts = ["" for _ in range(min(len(titles), len(prices_str)))]
                        else:
                             # 如果找到价格符号，尝试推断结构
                             # 这里简化处理：直接获取页面文本进行正则匹配提取，或者尝试获取特定容器
                             # 由于页面结构复杂，这里我们尝试获取包含价格的父级容器
                             # 这种方式比较脆弱，建议直接抓取页面所有文本进行分析，或者依赖特定的 data-testid 如果有的话
                             
                             # 简单方案：尝试获取页面上所有的链接文本，过滤出像标题的
                             # 以及所有包含数字的价格
                             
                             # 实际上，最稳妥的方式是让用户手动确认页面结构，或者使用更通用的 CSS
                             # 假设商品卡片通常是 a 标签或 div
                             
                             # 尝试获取所有卡片容器 (通常有 item, card, feed 等类名)
                             cards = page.locator("div[class*='card'], div[class*='item'], a[href*='item.taobao.com'], a[href*='detail']").all()
                             
                             titles = []
                             prices_str = []
                             item_texts = []
                             
                             for card in cards[:20]: # 限制处理数量
                                 text = card.inner_text()
                                 lines = text.split('\n')
                                 # 简单的启发式提取
                                 title_cand = ""
                                 price_cand = ""
                                 for line in lines:
                                     if "Switch" in line or "Lite" in line or "任天堂" in line:
                                         title_cand = line
                                     if "¥" in line or line.replace('.', '', 1).isdigit():
                                         price_cand = line
                                 
                                 if title_cand and price_cand:
                                     titles.append(title_cand)
                                     prices_str.append(price_cand)
                                     item_texts.append(text)
                             
                             if not titles:
                                 # 如果通用策略失败，回退到旧的选择器尝试
                                 prices_str = page.locator('.number--NKh1vXWM').all_inner_texts()
                                 titles = page.locator('.main-title--sMrtWSJa').all_inner_texts()
                                 item_texts = ["" for _ in range(min(len(titles), len(prices_str)))]

                    except:
                        print("Warning 无法找到商品列表，正在尝试截图并重试...")
                        try:
                            page.screenshot(path="error_debug.png")
                        except: pass
                        controlled_sleep(random.uniform(5, 10))
                        continue
                    
                    if not prices_str or not titles:
                        print("Warning 未抓取到有效数据 (可能需要登录或页面结构已变更)")
                        continue

                    THRESHOLD = calculate_dynamic_threshold(prices_str)
                    print(f"Stats 当前动态阈值: {THRESHOLD}")

                    for i in range(min(len(titles), len(prices_str), 8)):
                        title = titles[i].strip()
                        raw_price = prices_str[i].strip()
                        item_text = item_texts[i] if i < len(item_texts) else ""

                        if is_range_price(raw_price):
                            print(f"🚫 跳过区间价商品: {title} ({raw_price})")
                            continue

                        is_non_personal, exclude_reasons = detect_non_personal_signals(title, raw_price, item_text)
                        if is_non_personal:
                            reason_text = "、".join(exclude_reasons[:2]) if exclude_reasons else "命中非个人闲置规则"
                            print(f"🚫 跳过非个人闲置商品: {title} ({raw_price}) - {reason_text}")
                            continue

                        price = parse_single_price(raw_price)
                        if price is None:
                            continue

                        if price <= THRESHOLD and title not in history_alerts:
                            print(f"Search 发现潜在机会: {title} ({price}元), 正在AI分析...")
                            decision = analyze_with_ai(title, price, THRESHOLD)
                            if decision and decision.get("is_arbitrage_opportunity"):
                                send_wechat_alert(title, price, decision.get('reason', '无理由'))
                                history_alerts.add(title)
                            else:
                                reason = decision.get('reason') if decision else "AI分析失败或不推荐"
                                print(f"⚪ 忽略: {title} ({price}元) - {reason}")
                        else:
                            # print(f"⏭️ 价格高于预期或已处理: {price}元")
                            pass

                except Exception as inner_e:
                    try:
                        page.screenshot(path="error_debug.png")
                    except: pass
                    print(f"Warning 本轮巡逻受阻: {inner_e}")
                    
                sleep_time = get_patrol_sleep_seconds()
                print(f"💤 本轮巡逻结束，进入深度睡眠 {int(sleep_time)} 秒...")
                controlled_sleep(sleep_time)

        except Exception as e:
            print(f"Error 巡逻被强制中断: {e}")
        finally:
            # 退出前保存状态
            try:
                if context:
                    context.storage_state(path="state.json")
                    print("OK 退出前已保存 state.json")
            except: pass

            try:
                browser.close()
            except:
                pass

def run_engine_forever():
    restart_delay = get_env_int("ENGINE_RESTART_DELAY", 20, 3, 600)
    while True:
        try:
            start_patrol()
            print(f"Warning 引擎已退出，{restart_delay} 秒后自动拉起")
        except KeyboardInterrupt:
            print("🛑 收到停止信号，巡逻结束")
            break
        except Exception as e:
            print(f"Error 引擎异常退出: {e}")
            print(f"Warning {restart_delay} 秒后自动拉起")
        controlled_sleep(restart_delay)

if __name__ == "__main__":
    run_engine_forever()
