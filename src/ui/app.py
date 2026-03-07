import os
import re
import queue
import time
import threading
import subprocess
import shutil
import tkinter as tk
from tkinter import ttk, messagebox


class TradeSniperUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TradeSniper 前端控制台")
        self.root.geometry("1200x760")
        # Calculate project root (assuming src/ui/app.py)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.process = None
        self.output_queue = queue.Queue()
        self.records_seen = set()
        self.status_counts = {"潜在机会": 0, "已忽略": 0, "跳过区间价": 0, "跳过商家": 0}
        self.max_log_lines = 2000
        self.log_line_count = 0
        self.patterns = [
            ("潜在机会", re.compile(r"发现潜在机会:\s*(?P<title>.+?)\s*\((?P<price>[\d.]+)元\)")),
            ("已忽略", re.compile(r"忽略:\s*(?P<title>.+?)\s*\((?P<price>[\d.]+)元\)")),
            ("跳过区间价", re.compile(r"跳过区间价商品:\s*(?P<title>.+?)\s*\((?P<price>[^)]+)\)")),
            ("跳过商家", re.compile(r"跳过非个人闲置商品:\s*(?P<title>.+?)\s*\((?P<price>[^)]+)\)")),
        ]
        self._build_ui()
        self.root.after(100, self._poll_output)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(outer)
        top.pack(fill=tk.X)

        self.start_btn = ttk.Button(top, text="启动巡逻", command=lambda: self.start_engine(login_mode=False))
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.stop_btn = ttk.Button(top, text="停止巡逻", command=self.stop_engine, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.login_btn = ttk.Button(top, text="登录闲鱼", command=lambda: self.start_engine(login_mode=True))
        self.login_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.clear_btn = ttk.Button(top, text="清空记录", command=self.clear_records)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 配置区域
        config_frame = ttk.LabelFrame(top, text="配置", padding=4)
        config_frame.pack(side=tk.LEFT, padx=(16, 0), fill=tk.Y)
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="无头模式", variable=self.headless_var).pack(side=tk.LEFT, padx=4)
        
        self.status_var = tk.StringVar(value="状态：未启动")
        status_label = ttk.Label(top, textvariable=self.status_var, font=("微软雅黑", 10, "bold"))
        status_label.pack(side=tk.RIGHT, padx=16)

        body = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=2)
        body.add(right, weight=3)

        title_left = ttk.Label(left, text="闲鱼产品记录")
        title_left.pack(anchor=tk.W, pady=(0, 8))

        columns = ("time", "title", "price", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=28)
        self.tree.heading("time", text="时间")
        self.tree.heading("title", text="标题")
        self.tree.heading("price", text="价格")
        self.tree.heading("status", text="状态")
        self.tree.column("time", width=80, anchor=tk.CENTER)
        self.tree.column("title", width=360, anchor=tk.W)
        self.tree.column("price", width=80, anchor=tk.CENTER)
        self.tree.column("status", width=100, anchor=tk.CENTER)

        yscroll = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

        title_right = ttk.Label(right, text="运行日志")
        title_right.pack(anchor=tk.W, pady=(0, 8))
        self.summary_var = tk.StringVar(value="摘要：潜在机会 0 | 已忽略 0 | 跳过 0")
        summary_label = ttk.Label(right, textvariable=self.summary_var)
        summary_label.pack(anchor=tk.W, pady=(0, 6))

        self.log_text = tk.Text(right, wrap=tk.WORD, font=("Consolas", 10))
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.tag_configure("info", foreground="#2c3e50")
        self.log_text.tag_configure("action", foreground="#0b57d0")
        self.log_text.tag_configure("success", foreground="#0f7b0f")
        self.log_text.tag_configure("warn", foreground="#b26a00")
        self.log_text.tag_configure("error", foreground="#b00020")
        log_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _resolve_python(self):
        candidates = [
            os.path.join(self.project_root, ".venv312", "Scripts", "python.exe"),
            os.path.join(self.project_root, ".venv", "Scripts", "python.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return shutil.which("python") or "python"

    def start_engine(self, login_mode=False):
        action_text = "登录闲鱼" if login_mode else "启动巡逻"
        self._append_log(f"👉 点击：{action_text}", "action")
        if self.process and self.process.poll() is None:
            self._append_log("⚠️ 引擎正在运行，请先停止后再启动")
            self.status_var.set("状态：已在运行")
            return
        self.start_btn.config(state=tk.DISABLED)
        self.login_btn.config(state=tk.DISABLED)
        python_exe = self._resolve_python()
        engine_file = os.path.join(self.project_root, "src", "core", "engine.py")
        if not os.path.exists(engine_file):
            self._append_log(f"启动失败：未找到 {engine_file}")
            self.status_var.set("状态：启动失败")
            messagebox.showerror("启动失败", f"未找到引擎文件：\n{engine_file}")
            self.start_btn.config(state=tk.NORMAL)
            self.login_btn.config(state=tk.NORMAL)
            return
        if not os.path.exists(python_exe) and python_exe.lower() == "python":
            self._append_log("启动失败：未找到可用的 Python 解释器")
            self.status_var.set("状态：启动失败")
            messagebox.showerror("启动失败", "未找到可用的 Python 解释器，请检查虚拟环境")
            self.start_btn.config(state=tk.NORMAL)
            self.login_btn.config(state=tk.NORMAL)
            return
        ok, reason, force_http_fallback = self._preflight_check(python_exe)
        if not ok:
            self._append_log(f"启动前检查失败：{reason}")
            self.status_var.set("状态：依赖缺失")
            messagebox.showerror("启动失败", reason)
            self.start_btn.config(state=tk.NORMAL)
            self.login_btn.config(state=tk.NORMAL)
            return
        
        env = os.environ.copy()
        # Add project root to PYTHONPATH
        env["PYTHONPATH"] = self.project_root
        env["HEADLESS"] = "true" if self.headless_var.get() else "false"
        if login_mode:
            env["LOGIN_MODE"] = "1"
            env["HEADLESS"] = "false"
        else:
            env["LOGIN_MODE"] = "0"
        
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if force_http_fallback:
            env["FORCE_HTTP_FALLBACK"] = "1"
            self._append_log("⚠️ 检测到 Playwright 运行时异常，已自动切换到 HTTP 巡逻模式")
        else:
            env["FORCE_HTTP_FALLBACK"] = "0"
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            env.pop(key, None)
        env["NO_PROXY"] = "*"
        env["no_proxy"] = "*"
        
        command = [python_exe, "-u", engine_file]
        self._append_log(f"启动命令：{' '.join(command)}")
        if login_mode:
            self._append_log("⚠️ 正在以登录模式启动，请在弹出的窗口中登录闲鱼")
            self.status_var.set("状态：登录模式启动中")
        else:
            self.status_var.set("状态：启动中")

        try:
            self.process = subprocess.Popen(
                command,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env
            )
        except Exception as e:
            self._append_log(f"启动失败：{e}")
            self.status_var.set("状态：启动失败")
            messagebox.showerror("启动失败", str(e))
            self.start_btn.config(state=tk.NORMAL)
            self.login_btn.config(state=tk.NORMAL)
            return
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("状态：运行中")
        self._append_log("✅ 启动成功，正在读取引擎输出...")
        threading.Thread(target=self._reader_thread, daemon=True).start()
        self.root.after(1800, self._check_start_health)

    def stop_engine(self):
        self._append_log("👉 点击：停止巡逻", "action")
        if not self.process or self.process.poll() is not None:
            self._set_stopped("状态：未运行")
            self._append_log("⚠️ 当前没有运行中的引擎")
            return
        pid = self.process.pid
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True
            )
            self.process.wait(timeout=5)
        except Exception:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                pass
        self._append_log("已发送停止信号")
        self._set_stopped("状态：已停止")

    def clear_records(self):
        self._append_log("👉 点击：清空记录", "action")
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.records_seen.clear()
        self.status_counts = {"潜在机会": 0, "已忽略": 0, "跳过区间价": 0, "跳过商家": 0}
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        self.log_line_count = 0
        self.status_var.set("状态：已清空记录")
        self._refresh_summary()

    def _reader_thread(self):
        try:
            if not self.process or not self.process.stdout:
                return
            for line in self.process.stdout:
                self.output_queue.put(line.rstrip("\n"))
        finally:
            self.output_queue.put("__PROCESS_DONE__")

    def _poll_output(self):
        while True:
            try:
                line = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if line == "__PROCESS_DONE__":
                if self.process and self.process.poll() is not None:
                    self._set_stopped(f"状态：已退出（代码 {self.process.returncode}）")
                continue
            self._append_log(line)
            self._collect_record(line)
        self.root.after(120, self._poll_output)

    def _collect_record(self, line):
        for status, pattern in self.patterns:
            match = pattern.search(line)
            if not match:
                continue
            title = match.groupdict().get("title", "").strip()
            price = match.groupdict().get("price", "").strip()
            if not title:
                return
            key = (title, price, status)
            if key in self.records_seen:
                return
            self.records_seen.add(key)
            self.status_counts[status] = self.status_counts.get(status, 0) + 1
            now = time.strftime("%H:%M:%S")
            self.tree.insert("", 0, values=(now, title, price, status))
            self._refresh_summary()
            return

    def _append_log(self, text, level=None):
        if level is None:
            level = self._infer_level(text)
        display = self._humanize_log(text)
        line = f"[{time.strftime('%H:%M:%S')}] {display}"
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n", level)
        self.log_line_count += 1
        if self.log_line_count > self.max_log_lines:
            self.log_text.delete("1.0", "2.0")
            self.log_line_count -= 1
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _infer_level(self, text):
        if "❌" in text or "失败" in text or "异常" in text:
            return "error"
        if "⚠️" in text or "警告" in text:
            return "warn"
        if "✅" in text or "成功" in text:
            return "success"
        if "点击：" in text:
            return "action"
        return "info"

    def _humanize_log(self, text):
        text = text.strip()
        if "巡逻打卡" in text:
            return "正在执行新一轮巡逻检查"
        if "尝试启动浏览器" in text:
            return text.replace("尝试启动浏览器", "正在尝试启动浏览器")
        if "本轮巡逻结束" in text:
            return "本轮巡逻已结束，系统进入等待"
        if "发现潜在机会" in text:
            return text.replace("发现潜在机会", "检测到潜在机会")
        return text

    def _refresh_summary(self):
        skipped = self.status_counts.get("跳过区间价", 0) + self.status_counts.get("跳过商家", 0)
        self.summary_var.set(
            f"摘要：潜在机会 {self.status_counts.get('潜在机会', 0)} | 已忽略 {self.status_counts.get('已忽略', 0)} | 跳过 {skipped}"
        )

    def _preflight_check(self, python_exe):
        try:
            base_result = subprocess.run(
                [python_exe, "-c", "import json, re, os, time"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=8
            )
            if base_result.returncode != 0:
                err = (base_result.stderr or base_result.stdout or "").strip()
                return False, f"Python运行时检查失败：\n{err}", False
            playwright_result = subprocess.run(
                [python_exe, "-c", "import playwright.sync_api"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=8
            )
            if playwright_result.returncode != 0:
                err = (playwright_result.stderr or playwright_result.stdout or "").strip()
                if "WinError 10022" in err or "_overlapped" in err:
                    return True, "", True
                return False, f"Playwright依赖异常：\n{err}", False
            return True, "", False
        except Exception as e:
            return False, f"依赖检查异常：{e}", False

    def _check_start_health(self):
        if not self.process:
            return
        code = self.process.poll()
        if code is not None:
            self._append_log(f"❌ 引擎启动后很快退出，退出码：{code}")
            self._set_stopped(f"状态：已退出（代码 {code}）")

    def _set_stopped(self, status_text):
        self.status_var.set(status_text)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.login_btn.config(state=tk.NORMAL)

    def _on_close(self):
        self.stop_engine()
        self.root.destroy()


def main():
    root = tk.Tk()
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    TradeSniperUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
