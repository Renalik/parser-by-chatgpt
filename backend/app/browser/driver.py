from __future__ import annotations
import json, os, shutil, subprocess, time, threading, urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from ..providers.base import ProviderError
from ..settings import settings


def browser_path():
    override = os.getenv("DGIS_BROWSER_PATH")
    if override and Path(override).is_file():
        return override
    if os.name == "nt":
        for directory in [
            os.getenv("PROGRAMFILES(X86)"),
            os.getenv("PROGRAMFILES"),
            os.getenv("LOCALAPPDATA"),
        ]:
            if not directory:
                continue
            for tail in [
                "Microsoft/Edge/Application/msedge.exe",
                "Google/Chrome/Application/chrome.exe",
            ]:
                p = Path(directory) / tail
                if p.is_file():
                    return str(p)
    for name in ["msedge", "google-chrome", "chromium", "chromium-browser"]:
        if shutil.which(name):
            return shutil.which(name)
    return None


def local_json(url, method="GET"):
    parsed = urlsplit(url)
    if parsed.hostname not in ("localhost", "127.0.0.1"):
        raise ProviderError("Недопустимый адрес управления браузером")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(urllib.request.Request(url, method=method), timeout=4) as r:
        return json.load(r)


class Tab:
    def __init__(self, url):
        import websocket

        parsed = urlsplit(url)
        if parsed.scheme != "ws" or parsed.hostname not in ("127.0.0.1", "localhost"):
            raise ProviderError("Недопустимое подключение к браузеру")
        self.ws = websocket.create_connection(
            url,
            timeout=5,
            suppress_origin=True,
            http_no_proxy=["localhost", "127.0.0.1"],
        )
        self.sequence = 0
        self.lock = threading.Lock()

    def call(self, method, params=None):
        with self.lock:
            self.sequence += 1
            identifier = self.sequence
            try:
                self.ws.send(
                    json.dumps(
                        {"id": identifier, "method": method, "params": params or {}}
                    )
                )
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    message = json.loads(self.ws.recv())
                    if message.get("id") != identifier:
                        continue
                    if message.get("error"):
                        raise ProviderError(
                            "Браузер не выполнил действие. Проверьте открытое окно 2ГИС."
                        )
                    return message.get("result", {})
            except ProviderError:
                raise
            except Exception:
                raise ProviderError(
                    "Связь с браузером потеряна. Откройте браузер из настроек и продолжите задачу.",
                    paused=True,
                ) from None
        raise ProviderError(
            "Браузер не отвечает. Проверьте открытое окно.", paused=True
        )

    def evaluate(self, expression):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
                "userGesture": True,
            },
        )
        if result.get("exceptionDetails"):
            raise ProviderError(
                "Разметка страницы изменилась. Не удалось прочитать видимую карточку."
            )
        return result.get("result", {}).get("value")

    def navigate(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "2gis.ru":
            raise ProviderError("Браузерный источник открывает только страницы 2gis.ru")
        self.call("Page.navigate", {"url": url})

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


class BrowserService:
    def __init__(self):
        self.process = None
        self.port = None
        self.tabs = {}
        self.lock = threading.RLock()

    def ensure(self):
        with self.lock:
            if self.port:
                try:
                    local_json(f"http://127.0.0.1:{self.port}/json/version")
                    return
                except Exception:
                    self.port = None
            binary = browser_path()
            if not binary:
                raise ProviderError(
                    "Не найден Microsoft Edge или Google Chrome. Установите один из этих браузеров."
                )
            directory = (
                Path(settings.desktop_data_dir or "data").resolve() / "browser-profile"
            )
            directory.mkdir(parents=True, exist_ok=True)
            active = directory / "DevToolsActivePort"
            if active.exists():
                try:
                    port = int(active.read_text().splitlines()[0])
                    local_json(f"http://127.0.0.1:{port}/json/version")
                    self.port = port
                    return
                except Exception:
                    active.unlink(missing_ok=True)
            args = [
                binary,
                "--remote-debugging-address=127.0.0.1",
                "--remote-debugging-port=0",
                "--user-data-dir=" + str(directory),
                "--no-first-run",
                "--no-default-browser-check",
                "--disk-cache-size=33554432",
                "--media-cache-size=8388608",
                "https://2gis.ru",
            ]
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                if active.exists():
                    try:
                        port = int(active.read_text().splitlines()[0])
                        local_json(f"http://127.0.0.1:{port}/json/version")
                        self.port = port
                        return
                    except Exception:
                        pass
                if self.process.poll() is not None:
                    break
                time.sleep(0.2)
            raise ProviderError(
                "Не удалось открыть браузер. Закройте оставшееся окно браузерного профиля приложения и повторите попытку."
            )

    def tab(self, kind):
        self.ensure()
        with self.lock:
            if kind in self.tabs:
                try:
                    self.tabs[kind].evaluate("1")
                    return self.tabs[kind]
                except ProviderError:
                    self.tabs.pop(kind).close()
            result = None
            if kind == "search":
                targets=local_json(f"http://127.0.0.1:{self.port}/json/list")
                result=next((t for t in targets if t.get("type")=="page" and t.get("webSocketDebuggerUrl") and (t.get("url","").startswith("https://2gis.ru") or t.get("url")=="about:blank")),None)
            if result is None:
                result = local_json(f"http://127.0.0.1:{self.port}/json/new?about:blank",method="PUT")
            tab = Tab(result["webSocketDebuggerUrl"])
            self.tabs[kind] = tab
            return tab

    def open_home(self):
        tab = self.tab("search")
        tab.navigate("https://2gis.ru")
        return {"opened": True}

    def close(self):
        with self.lock:
            for tab in self.tabs.values():
                tab.close()
            self.tabs = {}
            # Only terminate the dedicated browser process created by this service.
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            self.process = None
            self.port = None


browser_service = BrowserService()
