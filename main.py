import json, os, re, threading, io, time
from urllib.parse import urljoin
import requests
from PIL import Image
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.image import AsyncImage
from kivy.utils import platform

Window.clearcolor = (0.07, 0.08, 0.10, 1)
HDRS = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) PathPresenterDownloader"}
MAX_SIDE = 12000  # cap on stitched image size (phone RAM safety)


def out_dir():
    if platform == "android":
        try:
            from android.storage import primary_external_storage_path
            base = os.path.join(primary_external_storage_path(), "Pictures")
        except Exception:
            base = "/sdcard/Pictures"
    else:
        base = os.path.expanduser("~/Pictures")
    d = os.path.join(base, "PathPresenter")
    os.makedirs(d, exist_ok=True)
    return d


def safe(s):
    return re.sub(r"[^\w\-. ]+", "_", s).strip()[:60] or "slide"


def meta_of(html, url):
    m = {"url": url}
    t = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    m["title"] = t.group(1).strip() if t else "slide"
    for k in ("og:title", "og:description", "og:image"):
        r = re.search(r'property=["\']%s["\']\s+content=["\'](.*?)["\']' % k, html, re.I)
        if r:
            m[k] = r.group(1)
    for k, pat in (("stain", r"stain[^<\"']{0,40}[:=]\s*([\w\-& ]+)"),
                   ("diagnosis", r"diagnosis[^<\"']{0,40}[:=]\s*([\w\-& ,]+)")):
        r = re.search(pat, html, re.I)
        if r:
            m[k] = r.group(1).strip()
    d = re.search(r'["\'](https?:[^"\']+?\.dzi)["\']', html) or re.search(r'["\']([^"\']+?\.dzi)["\']', html)
    if d:
        m["dzi"] = urljoin(url, d.group(1).replace("\\/", "/"))
    return m


def fetch_info(url):
    r = requests.get(url, headers=HDRS, timeout=30)
    r.raise_for_status()
    return meta_of(r.text, url)


def download_slide(info, folder, progress):
    os.makedirs(folder, exist_ok=True)
    name = safe(info.get("title", "slide"))
    path = os.path.join(folder, "%s_%d.jpg" % (name, int(time.time())))
    if "dzi" in info:
        x = requests.get(info["dzi"], headers=HDRS, timeout=30).text
        w = int(re.search(r'Width="(\d+)"', x).group(1))
        h = int(re.search(r'Height="(\d+)"', x).group(1))
        ts = int(re.search(r'TileSize="(\d+)"', x).group(1))
        ov = int(re.search(r'Overlap="(\d+)"', x).group(1))
        fmt = re.search(r'Format="(\w+)"', x).group(1)
        maxl = 0
        while (1 << maxl) < max(w, h):
            maxl += 1
        lvl, scale = maxl, 1
        while max(w, h) / scale > MAX_SIDE:
            lvl -= 1
            scale *= 2
        lw, lh = -(-w // scale), -(-h // scale)
        base = info["dzi"].rsplit(".", 1)[0] + "_files/%d/" % lvl
        cols, rows = -(-lw // ts), -(-lh // ts)
        canvas = Image.new("RGB", (lw, lh), "white")
        n = 0
        for cx in range(cols):
            for ry in range(rows):
                u = "%s%d_%d.%s" % (base, cx, ry, fmt)
                try:
                    t = Image.open(io.BytesIO(requests.get(u, headers=HDRS, timeout=30).content)).convert("RGB")
                    px = cx * ts - (ov if cx else 0)
                    py = ry * ts - (ov if ry else 0)
                    canvas.paste(t, (px, py))
                except Exception:
                    pass
                n += 1
                progress("Tiles %d/%d" % (n, cols * rows))
        canvas.save(path, "JPEG", quality=92)
    elif "og:image" in info:
        progress("Downloading image...")
        data = requests.get(info["og:image"], headers=HDRS, timeout=60).content
        Image.open(io.BytesIO(data)).convert("RGB").save(path, "JPEG", quality=95)
    else:
        raise RuntimeError("No image source found in this link")
    return path


class Root(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", padding=10, spacing=8, **kw)
        self.app = app
        self.queue = []
        self.history = app.load_history()
        self.url = TextInput(hint_text="Paste PathPresenter slide link", multiline=False,
                             size_hint_y=None, height=100, background_color=(.15, .17, .2, 1),
                             foreground_color=(1, 1, 1, 1))
        self.add_widget(self.url)
        row = BoxLayout(size_hint_y=None, height=110, spacing=6)
        for txt, fn in (("Preview", self.on_preview), ("Download", self.on_download),
                        ("+ Queue", self.on_queue), ("Run queue", self.on_run_queue)):
            row.add_widget(Button(text=txt, on_release=fn, background_color=(.1, .45, .8, 1)))
        self.add_widget(row)
        self.thumb = AsyncImage(size_hint_y=None, height=300)
        self.add_widget(self.thumb)
        self.status = Label(text="Ready", size_hint_y=None, height=140, text_size=(Window.width - 30, None),
                            halign="left", valign="top")
        self.add_widget(self.status)
        self.add_widget(Label(text="History / Bookmarks (tap to reuse)", size_hint_y=None, height=50))
        sv = ScrollView()
        self.hbox = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        self.hbox.bind(minimum_height=self.hbox.setter("height"))
        sv.add_widget(self.hbox)
        self.add_widget(sv)
        self.refresh_history()

    def say(self, t):
        Clock.schedule_once(lambda dt: setattr(self.status, "text", t))

    def refresh_history(self):
        self.hbox.clear_widgets()
        for u in reversed(self.history[-30:]):
            self.hbox.add_widget(Button(text=u[-60:], size_hint_y=None, height=90,
                                        background_color=(.2, .22, .26, 1),
                                        on_release=lambda b, u=u: setattr(self.url, "text", u)))

    def remember(self, u):
        if u not in self.history:
            self.history.append(u)
            self.app.save_history(self.history)
            Clock.schedule_once(lambda dt: self.refresh_history())

    def on_preview(self, *a):
        u = self.url.text.strip()
        if not u:
            return
        self.say("Loading preview...")
        threading.Thread(target=self._preview, args=(u,), daemon=True).start()

    def _preview(self, u):
        try:
            i = fetch_info(u)
            lines = ["Title: " + i.get("title", "?")]
            for k in ("stain", "diagnosis", "og:description"):
                if k in i:
                    lines.append("%s: %s" % (k, i[k]))
            lines.append("Source: " + ("DeepZoom tiles" if "dzi" in i else "image" if "og:image" in i else "NOT FOUND"))
            self.say("\n".join(lines))
            if "og:image" in i:
                Clock.schedule_once(lambda dt: setattr(self.thumb, "source", i["og:image"]))
        except Exception as e:
            self.say("Error: %s" % e)

    def on_download(self, *a):
        u = self.url.text.strip()
        if u:
            threading.Thread(target=self._dl, args=([u],), daemon=True).start()

    def on_queue(self, *a):
        u = self.url.text.strip()
        if u:
            self.queue.append(u)
            self.say("Queued: %d link(s)" % len(self.queue))

    def on_run_queue(self, *a):
        if self.queue:
            items, self.queue = self.queue, []
            threading.Thread(target=self._dl, args=(items,), daemon=True).start()

    def _dl(self, urls):
        for k, u in enumerate(urls, 1):
            try:
                self.say("[%d/%d] Reading link..." % (k, len(urls)))
                i = fetch_info(u)
                folder = os.path.join(out_dir(), safe(i.get("diagnosis") or i.get("stain") or "Slides"))
                p = download_slide(i, folder, lambda t: self.say("[%d/%d] %s" % (k, len(urls), t)))
                self.remember(u)
                self.say("Saved: " + p)
            except Exception as e:
                self.say("Error on %s: %s" % (u[-40:], e))


class PathPresenterApp(App):
    title = "PathPresenterDownloader Pro"

    def hist_path(self):
        return os.path.join(self.user_data_dir, "download_history.json")

    def load_history(self):
        try:
            return json.load(open(self.hist_path()))
        except Exception:
            return []

    def save_history(self, h):
        json.dump(h, open(self.hist_path(), "w"))

    def build(self):
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except Exception:
                pass
        return Root(self)


if __name__ == "__main__":
    PathPresenterApp().run()
    
