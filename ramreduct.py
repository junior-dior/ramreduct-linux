#!/usr/bin/env python3
"""RAM Reduct for Linux - memory cleaner (GTK3). By 4133F DEV."""
import gi, math, os, json, threading, subprocess, time, webbrowser
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo
import cairo

VERSION = "2.0.0"
APP = "RAM Reduct"
CREDIT = "4133F DEV."
GITHUB = "https://github.com/junior-dior"
WIN_W, WIN_H = 420, 610
HELPER = "/usr/lib/ramreduct/ramreduct-helper"
if not os.path.exists(HELPER):  # running from the source folder
    HELPER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ramreduct-helper")

FONT = "Inter, Noto Sans Thai, Sarabun, Noto Sans, Ubuntu, Cantarell, DejaVu Sans"
MONO = "JetBrains Mono, DejaVu Sans Mono, monospace"

# ------------------------------------------------------------------ i18n
STR = {
    "en": {
        "sub": "Free up system memory", "clean": "Clean Memory", "cleaning": "Cleaning...",
        "used": "Used", "avail": "Available", "free": "Free", "cached": "Cached",
        "swap_used": "Swap used", "swap_total": "Swap total",
        "auto": "Auto clean", "auto_when": "When RAM ≥",
        "settings": "Settings", "back": "Back", "language": "LANGUAGE",
        "options": "CLEAN OPTIONS", "opt_c": "Clear cache, dentries & inodes",
        "opt_p": "Trim process memory (to swap)", "opt_m": "Compact memory",
        "opt_s": "Cycle swap (needs free RAM)", "top": "TOP MEMORY USERS", "log": "ACTIVITY LOG",
        "ready": "Ready", "freed": "Freed {x}", "none": "Select at least one option",
        "auth": "Authentication is needed for auto clean", "auto_msg": "Auto clean at {p}%",
        "result": "Used {a} → {b}  |  Free {c} → {d}", "about": "RAM Reduct v{v}  ·  by 4133F DEV.",
        "failed": "Clean failed",
    },
    "th": {
        "sub": "ล้างหน่วยความจำระบบ", "clean": "ล้างหน่วยความจำ", "cleaning": "กำลังล้าง...",
        "used": "ใช้งาน", "avail": "พร้อมใช้", "free": "ว่างจริง", "cached": "แคช",
        "swap_used": "Swap ที่ใช้", "swap_total": "Swap ทั้งหมด",
        "auto": "ล้างอัตโนมัติ", "auto_when": "เมื่อ RAM ≥",
        "settings": "ตั้งค่า", "back": "กลับ", "language": "ภาษา",
        "options": "ตัวเลือกการล้าง", "opt_c": "ล้างแคช, dentries และ inodes",
        "opt_p": "ลดหน่วยความจำโปรเซส (ย้ายไป swap)", "opt_m": "จัดระเบียบหน่วยความจำ",
        "opt_s": "หมุนเวียน swap (ต้องมี RAM ว่าง)", "top": "โปรแกรมที่ใช้แรมมากสุด", "log": "บันทึกการทำงาน",
        "ready": "พร้อมใช้งาน", "freed": "ล้างแล้ว {x}", "none": "เลือกอย่างน้อย 1 ตัวเลือก",
        "auth": "ต้องยืนยันตัวตนเพื่อใช้ล้างอัตโนมัติ", "auto_msg": "ล้างอัตโนมัติที่ {p}%",
        "result": "ใช้งาน {a} → {b}  |  ว่าง {c} → {d}", "about": "RAM Reduct v{v}  ·  โดย 4133F DEV.",
        "failed": "ล้างไม่สำเร็จ",
    },
}

CFG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "ramreduct")
CFG_FILE = os.path.join(CFG_DIR, "config.json")

def default_lang():
    return "th" if os.environ.get("LANG", "").lower().startswith("th") else "en"

def load_cfg():
    cfg = {"lang": default_lang(), "opts": {"c": True, "p": True, "m": True, "s": False}, "threshold": 85}
    try:
        with open(CFG_FILE) as f:
            d = json.load(f)
        cfg["lang"] = d.get("lang", cfg["lang"]) if d.get("lang") in STR else cfg["lang"]
        cfg["opts"].update({k: bool(v) for k, v in d.get("opts", {}).items() if k in cfg["opts"]})
        cfg["threshold"] = int(min(99, max(50, d.get("threshold", 85))))
    except (OSError, ValueError, TypeError):
        pass
    return cfg

def save_cfg(cfg):
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(CFG_FILE, "w") as f:
            json.dump(cfg, f)
    except OSError:
        pass

# ------------------------------------------------------------------ system info
def meminfo():
    d = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")
            d[k] = int(v.split()[0]) * 1024
    return d

def fmt(b):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024 or u == "TB":
            return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}"
        b /= 1024

def top_procs(n=4):
    page = os.sysconf("SC_PAGE_SIZE"); agg = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            with open(f"/proc/{pid}/statm") as f:
                rss = int(f.read().split()[1]) * page
            if rss <= 0:
                continue
            with open(f"/proc/{pid}/comm") as f:
                name = f.read().strip()
        except (OSError, IndexError, ValueError):
            continue
        agg[name] = agg.get(name, 0) + rss
    return sorted(agg.items(), key=lambda x: -x[1])[:n]

class RootHelper:
    """One pkexec prompt per session; commands go over a pipe to the root helper."""
    def __init__(self):
        self.p = None; self.lock = threading.Lock()

    def _start(self):
        if self.p and self.p.poll() is None:
            return True
        self.p = subprocess.Popen(["pkexec", HELPER, "--serve"], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, bufsize=1)
        if self.p.stdout.readline().strip() != "READY":
            self.p = None
            return False
        return True

    def ensure(self):
        with self.lock:
            try:
                return self._start()
            except OSError:
                return False

    def clean(self, flags):
        with self.lock:
            try:
                if not self._start():
                    return False, "Authentication cancelled or failed"
                self.p.stdin.write(f"clean {flags}\n"); self.p.stdin.flush()
                while True:
                    line = self.p.stdout.readline()
                    if not line:
                        self.p = None
                        return False, "Helper stopped unexpectedly"
                    if line.startswith("DONE"):
                        return True, line[5:].strip()
            except OSError as e:
                self.p = None
                return False, f"Helper error: {e}"

    def close(self):
        try:
            if self.p and self.p.poll() is None:
                self.p.stdin.write("quit\n"); self.p.stdin.flush()
        except OSError:
            pass

# ------------------------------------------------------------------ drawing helpers
def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

def setc(cr, c, a=1.0):
    cr.set_source_rgba(c[0], c[1], c[2], a)

def rrect(cr, x, y, w, h, r):
    r = max(0, min(r, h / 2, w / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()

WEIGHTS = {"normal": Pango.Weight.NORMAL, "semibold": Pango.Weight.SEMIBOLD, "bold": Pango.Weight.BOLD}

def text_layout(widget, text, size, weight="normal", family=None):
    lay = widget.create_pango_layout(text)
    fd = Pango.FontDescription()
    fd.set_family(family or FONT)
    fd.set_absolute_size(size * Pango.SCALE)
    fd.set_weight(WEIGHTS[weight])
    lay.set_font_description(fd)
    return lay

def draw_text(cr, widget, text, x, y, size, color, weight="normal", align="left", alpha=1.0):
    lay = text_layout(widget, text, size, weight)
    w, h = lay.get_pixel_size()
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    cr.move_to(x, y - h / 2)
    setc(cr, color, alpha)
    PangoCairo.show_layout(cr, lay)
    return w

def draw_icon(cr, kind, cx, cy, s, color, alpha=1.0):
    cr.save()
    setc(cr, color, alpha)
    cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if kind == "gear":
        cr.set_line_width(1.6)
        cr.arc(cx, cy, s * 0.2, 0, 2 * math.pi); cr.stroke()
        cr.arc(cx, cy, s * 0.34, 0, 2 * math.pi); cr.stroke()
        cr.set_line_width(2.4)
        for i in range(8):
            a = i * math.pi / 4
            cr.move_to(cx + math.cos(a) * s * 0.36, cy + math.sin(a) * s * 0.36)
            cr.line_to(cx + math.cos(a) * s * 0.5, cy + math.sin(a) * s * 0.5)
            cr.stroke()
    elif kind == "back":
        cr.set_line_width(2)
        cr.move_to(cx + s * 0.15, cy - s * 0.35); cr.line_to(cx - s * 0.2, cy); cr.line_to(cx + s * 0.15, cy + s * 0.35)
        cr.stroke()
    elif kind == "git":
        cr.set_line_width(1.6)
        xl, xr = cx - s * 0.22, cx + s * 0.26
        yt, yb, yr = cy - s * 0.32, cy + s * 0.32, cy - s * 0.1
        rad = s * 0.12
        cr.move_to(xl, yt + rad); cr.line_to(xl, yb - rad); cr.stroke()
        cr.move_to(xr, yr + rad); cr.curve_to(xr, cy + s * 0.12, xl, cy + s * 0.02, xl, cy + s * 0.2); cr.stroke()
        for px, py in ((xl, yt), (xl, yb), (xr, yr)):
            cr.arc(px, py, rad, 0, 2 * math.pi); cr.fill_preserve(); cr.stroke()
    elif kind == "arrow":
        cr.set_line_width(1.8)
        cr.move_to(cx - s * 0.3, cy + s * 0.3); cr.line_to(cx + s * 0.3, cy - s * 0.3); cr.stroke()
        cr.move_to(cx - s * 0.05, cy - s * 0.3); cr.line_to(cx + s * 0.3, cy - s * 0.3); cr.line_to(cx + s * 0.3, cy + s * 0.05)
        cr.stroke()
    elif kind == "spark":
        pts = []
        for i in range(8):
            rr = s * (0.5 if i % 2 == 0 else 0.15)
            a = -math.pi / 2 + i * math.pi / 4
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        cr.move_to(*pts[0])
        for p in pts[1:]:
            cr.line_to(*p)
        cr.close_path(); cr.fill()
    cr.restore()

# ------------------------------------------------------------------ animated widgets
class Anim(Gtk.DrawingArea):
    """DrawingArea with named values that ease toward targets every frame."""
    def __init__(self):
        super().__init__()
        self._cur = {}; self._tgt = {}; self._tid = 0; self._last = None

    def snap(self, name, value):
        self._cur[name] = value; self._tgt[name] = (value, 10.0); self.queue_draw()

    def go(self, name, target, speed=14.0):
        self._cur.setdefault(name, target)
        self._tgt[name] = (target, speed)
        self._kick()

    def val(self, name, default=0.0):
        return self._cur.get(name, default)

    def keep_animating(self):
        return False

    def _kick(self):
        if not self._tid:
            self._last = None
            self._tid = self.add_tick_callback(self._tick)

    def _tick(self, widget, clock):
        t = clock.get_frame_time() / 1e6
        dt = 0.016 if self._last is None else min(0.1, max(0.0, t - self._last))
        self._last = t
        moving = False
        for k, (tg, sp) in self._tgt.items():
            c = self._cur.get(k, tg)
            d = tg - c
            if abs(d) > 0.0005:
                c += d * (1 - math.exp(-sp * dt)); moving = True
                if abs(tg - c) < 0.0005:
                    c = tg
                self._cur[k] = c
        self.queue_draw()
        if not moving and not self.keep_animating():
            self._tid = 0
            return False
        return True

class Clickable(Anim):
    def __init__(self):
        super().__init__()
        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.enabled = True; self._down = False; self.callback = None
        self.snap("hover", 0.0); self.snap("press", 0.0)
        self.connect("enter-notify-event", self._enter)
        self.connect("leave-notify-event", self._leave)
        self.connect("button-press-event", self._press)
        self.connect("button-release-event", self._release)
        self.connect("realize", self._realize)

    def _realize(self, *_):
        win = self.get_window()
        if win:
            win.set_cursor(Gdk.Cursor.new_from_name(self.get_display(), "pointer"))

    def _enter(self, *_):
        self.go("hover", 1.0, 16); return False

    def _leave(self, *_):
        self._down = False; self.go("hover", 0.0, 12); self.go("press", 0.0, 20); return False

    def _press(self, w, e):
        if e.button == 1 and self.enabled:
            self._down = True; self.go("press", 1.0, 30)
        return True

    def _release(self, w, e):
        if e.button == 1 and self._down:
            self._down = False; self.go("press", 0.0, 18)
            if self.enabled:
                self.on_click(e)
        return True

    def on_click(self, event):
        if self.callback:
            self.callback(self)

    def connect_clicked(self, cb):
        self.callback = cb

class PillButton(Clickable):
    def __init__(self, text="", icon=None, trailing=None, w=-1, h=34):
        super().__init__()
        self.text, self.icon, self.trailing = text, icon, trailing
        self.set_size_request(w, h)

    def set_text(self, t):
        self.text = t; self.queue_draw()

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        h, p = self.val("hover"), self.val("press")
        cr.save()
        s = 1 - 0.04 * p
        cr.translate(W / 2, H / 2); cr.scale(s, s); cr.translate(-W / 2, -H / 2)
        rrect(cr, 0.5, 0.5, W - 1, H - 1, H / 2)
        setc(cr, mix(hexc("#181818"), hexc("#2c2c2c"), h)); cr.fill_preserve()
        setc(cr, mix(hexc("#2e2e2e"), hexc("#707070"), h)); cr.set_line_width(1); cr.stroke()
        fg = mix(hexc("#b8b8b8"), hexc("#ffffff"), h)
        isz, gap = 14, 7
        tw = 0
        if self.text:
            tw, _ = text_layout(self, self.text, 12, "semibold").get_pixel_size()
        aw = 10 if self.trailing else 0
        total = (isz if self.icon else 0) + (gap if self.icon and self.text else 0) + tw
        if self.trailing:
            total += (gap if self.text else 0) + aw
        x = (W - total) / 2
        cy = H / 2
        if self.icon:
            draw_icon(cr, self.icon, x + isz / 2, cy, isz, fg); x += isz + (gap if self.text else 0)
        if self.text:
            draw_text(cr, self, self.text, x, cy, 12, fg, "semibold"); x += tw + gap
        if self.trailing:
            draw_icon(cr, self.trailing, x + aw / 2 + h * 2, cy - h * 2, 10, fg)
        cr.restore()
        return False

class PrimaryButton(Clickable):
    def __init__(self, text):
        super().__init__()
        self.text = text; self.busy = False
        self.snap("busy", 0.0)
        self.set_size_request(-1, 60)

    def set_text(self, t):
        self.text = t; self.queue_draw()

    def set_busy(self, b):
        self.busy = b; self.enabled = not b
        self.go("busy", 1.0 if b else 0.0, 8); self._kick()

    def keep_animating(self):
        return self.busy

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        h, p, b = self.val("hover"), self.val("press"), self.val("busy")
        phase = GLib.get_monotonic_time() / 1e6
        m = 6; x, y, w, hh, r = m, m, W - 2 * m, H - 2 * m, 18
        cr.save()
        s = 1 - 0.025 * p
        cr.translate(W / 2, H / 2); cr.scale(s, s); cr.translate(-W / 2, -H / 2)
        # glow
        if h > 0.01 and b < 0.99:
            for i in range(1, 6):
                rrect(cr, x - i, y - i, w + 2 * i, hh + 2 * i, r + i)
                setc(cr, hexc("#ffffff"), 0.07 * h * (1 - b) * (6 - i) / 5)
                cr.set_line_width(1); cr.stroke()
        top = mix(mix(hexc("#efefef"), hexc("#ffffff"), h), hexc("#2c2c2c"), b)
        bot = mix(mix(hexc("#b9b9b9"), hexc("#d8d8d8"), h), hexc("#1b1b1b"), b)
        g = cairo.LinearGradient(0, y, 0, y + hh)
        g.add_color_stop_rgb(0, *top); g.add_color_stop_rgb(1, *bot)
        rrect(cr, x, y, w, hh, r); cr.set_source(g); cr.fill()
        # glossy top
        g2 = cairo.LinearGradient(0, y, 0, y + hh * 0.55)
        g2.add_color_stop_rgba(0, 1, 1, 1, 0.38 * (1 - b)); g2.add_color_stop_rgba(1, 1, 1, 1, 0)
        rrect(cr, x, y, w, hh, r); cr.set_source(g2); cr.fill()
        if b > 0.01:
            rrect(cr, x + 0.5, y + 0.5, w - 1, hh - 1, r); setc(cr, hexc("#454545"), b)
            cr.set_line_width(1); cr.stroke()
            # shimmer sweep
            cr.save(); rrect(cr, x, y, w, hh, r); cr.clip()
            sx = x + ((phase * 0.55) % 1.6 - 0.3) * w
            g3 = cairo.LinearGradient(sx, 0, sx + 110, 0)
            g3.add_color_stop_rgba(0, 1, 1, 1, 0); g3.add_color_stop_rgba(0.5, 1, 1, 1, 0.11 * b)
            g3.add_color_stop_rgba(1, 1, 1, 1, 0)
            cr.set_source(g3); cr.rectangle(x, y, w, hh); cr.fill(); cr.restore()
        fg = mix(hexc("#0f0f0f"), hexc("#d2d2d2"), b)
        isz, gap = 18, 10
        tw, _ = text_layout(self, self.text, 16, "bold").get_pixel_size()
        sx0 = (W - (isz + gap + tw)) / 2
        cy = H / 2
        if b < 0.99:
            draw_icon(cr, "spark", sx0 + isz / 2, cy, isz, fg, 1 - b)
        if b > 0.01:
            cr.save(); setc(cr, fg, b); cr.set_line_width(2.4); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            a0 = phase * 4.5
            cr.arc(sx0 + isz / 2, cy, 7.5, a0, a0 + 1.5 * math.pi); cr.stroke(); cr.restore()
        draw_text(cr, self, self.text, sx0 + isz + gap, cy, 16, fg, "bold")
        cr.restore()
        return False

class Switch(Clickable):
    def __init__(self, active=False):
        super().__init__()
        self.active = active; self.toggled_cb = None
        self.snap("on", 1.0 if active else 0.0)
        self.set_size_request(50, 30)
        self.set_valign(Gtk.Align.CENTER)

    def set_active(self, a):
        self.active = bool(a); self.go("on", 1.0 if self.active else 0.0, 14)

    def on_click(self, event):
        self.set_active(not self.active)
        if self.toggled_cb:
            self.toggled_cb(self.active)

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        on, h, p = self.val("on"), self.val("hover"), self.val("press")
        tw, th = 46, 26
        x, y = (W - tw) / 2, (H - th) / 2
        rrect(cr, x, y, tw, th, th / 2)
        setc(cr, mix(mix(hexc("#232323"), hexc("#2e2e2e"), h), hexc("#e4e4e4"), on)); cr.fill_preserve()
        setc(cr, mix(hexc("#454545"), hexc("#e4e4e4"), on)); cr.set_line_width(1); cr.stroke()
        kr = 9 + h * 0.8 + p * 1.2
        kx = x + 13 + on * (tw - 26)
        setc(cr, hexc("#000000"), 0.25); cr.arc(kx, y + th / 2 + 1.2, kr, 0, 2 * math.pi); cr.fill()
        setc(cr, mix(hexc("#a8a8a8"), hexc("#111111"), on)); cr.arc(kx, y + th / 2, kr, 0, 2 * math.pi); cr.fill()
        return False

class Segmented(Clickable):
    def __init__(self, labels, index=0):
        super().__init__()
        self.labels = labels; self.index = index; self.changed_cb = None
        self.snap("pos", float(index)); self.set_size_request(-1, 44)

    def set_index(self, i):
        self.index = i; self.go("pos", float(i), 12)

    def on_click(self, event):
        i = 0 if event.x < self.get_allocated_width() / 2 else 1
        if i != self.index:
            self.set_index(i)
            if self.changed_cb:
                self.changed_cb(i)

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        pos = self.val("pos")
        rrect(cr, 0.5, 0.5, W - 1, H - 1, 14); setc(cr, hexc("#151515")); cr.fill_preserve()
        setc(cr, hexc("#2a2a2a")); cr.set_line_width(1); cr.stroke()
        segw = (W - 8) / 2
        rrect(cr, 4 + pos * segw, 4, segw, H - 8, 11)
        g = cairo.LinearGradient(0, 4, 0, H - 4)
        g.add_color_stop_rgb(0, *hexc("#f0f0f0")); g.add_color_stop_rgb(1, *hexc("#c2c2c2"))
        cr.set_source(g); cr.fill()
        for i, lab in enumerate(self.labels):
            act = 1 - min(1.0, abs(pos - i))
            draw_text(cr, self, lab, 4 + segw * (i + 0.5), H / 2, 13, mix(hexc("#9a9a9a"), hexc("#0f0f0f"), act),
                      "bold", "center")
        return False

class BarSlider(Anim):
    """Signal-strength style slider made of rising bars."""
    def __init__(self, lo, hi, value, n=22):
        super().__init__()
        self.lo, self.hi, self.value, self.n = lo, hi, value, n
        self.changed_cb = None; self._drag = False
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)
        self.snap("fill", self._frac()); self.snap("drag", 0.0); self.snap("dim", 0.0)
        self.set_size_request(-1, 34)
        self.connect("button-press-event", self._press)
        self.connect("button-release-event", self._release)
        self.connect("motion-notify-event", self._motion)
        self.connect("realize", self._realize)

    def _frac(self):
        return (self.value - self.lo) / float(self.hi - self.lo)

    def _realize(self, *_):
        win = self.get_window()
        if win:
            win.set_cursor(Gdk.Cursor.new_from_name(self.get_display(), "pointer"))

    def set_value(self, v):
        self.value = int(min(self.hi, max(self.lo, v))); self.go("fill", self._frac(), 16)

    def set_dim(self, d):
        self.go("dim", 1.0 if d else 0.0, 10)

    def _from_x(self, x):
        W = self.get_allocated_width(); pad = 2
        frac = max(0.0, min(1.0, (x - pad) / max(1, W - 2 * pad)))
        v = int(round(self.lo + frac * (self.hi - self.lo)))
        if v != self.value:
            self.set_value(v)
            if self.changed_cb:
                self.changed_cb(v)

    def _press(self, w, e):
        if e.button == 1:
            self._drag = True; self.go("drag", 1.0, 14); self._from_x(e.x)
        return True

    def _motion(self, w, e):
        if self._drag:
            self._from_x(e.x)
        return True

    def _release(self, w, e):
        self._drag = False; self.go("drag", 0.0, 10); return True

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        pad, gap, n = 2, 4, self.n
        bw = (W - 2 * pad - (n - 1) * gap) / n
        fill, drag, dim = self.val("fill"), self.val("drag"), self.val("dim")
        for i in range(n):
            t = i / (n - 1)
            bh = (9 + (H - 13) * t) * (1 + 0.1 * drag)
            bh = min(bh, H - 2)
            lit = max(0.0, min(1.0, fill * (n - 1) + 1 - i))
            on = mix(mix(hexc("#8a8a8a"), hexc("#f2f2f2"), t), hexc("#ffffff"), 0.3 * drag)
            col = mix(hexc("#262626"), on, lit)
            rrect(cr, pad + i * (bw + gap), (H - bh) / 2, bw, bh, bw / 2)
            setc(cr, col, 1 - 0.55 * dim); cr.fill()
        return False

class Gauge(Anim):
    def __init__(self):
        super().__init__()
        self.used_txt = ""; self.total_txt = ""; self.busy = False
        self.snap("pct", 0.0); self.snap("pulse", 1.0); self.snap("busy", 0.0)
        self.set_size_request(-1, 150)

    def update(self, pct, used_txt, total_txt):
        self.used_txt, self.total_txt = used_txt, total_txt
        self.go("pct", pct, 5.0); self.queue_draw()

    def set_busy(self, b):
        self.busy = b; self.go("busy", 1.0 if b else 0.0, 6); self._kick()

    def pulse(self):
        self.snap("pulse", 0.0); self.go("pulse", 1.0, 3.0)

    def keep_animating(self):
        return self.busy

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        pct, pulse, busy = self.val("pct"), self.val("pulse", 1.0), self.val("busy")
        phase = GLib.get_monotonic_time() / 1e6
        cx, cy = W / 2, H / 2
        r = min(W, H) / 2 - 24
        start, sweep = math.radians(135), math.radians(270)
        frac = max(0.0, min(1.0, pct / 100.0))
        # tick ring
        n = 54
        cr.set_line_width(1.6); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for i in range(n + 1):
            t = i / n
            a = start + sweep * t
            lit = t <= frac
            col = mix(hexc("#5a5a5a"), hexc("#e8e8e8"), t) if lit else hexc("#252525")
            r1, r2 = r + 13, r + (19 if i % 6 == 0 else 16)
            setc(cr, col)
            cr.move_to(cx + math.cos(a) * r1, cy + math.sin(a) * r1)
            cr.line_to(cx + math.cos(a) * r2, cy + math.sin(a) * r2); cr.stroke()
        # track
        cr.set_line_width(12)
        setc(cr, hexc("#1d1d1d")); cr.arc(cx, cy, r, start, start + sweep); cr.stroke()
        # progress
        steps = max(1, int(frac * 90))
        if frac > 0.002:
            for k in range(steps):
                a0 = start + sweep * frac * k / steps
                a1 = start + sweep * frac * (k + 1) / steps + 0.012
                lv = 0.42 + 0.52 * (k / steps)
                cr.set_source_rgb(lv, lv, lv); cr.arc(cx, cy, r, a0, a1); cr.stroke()
        # knob
        ae = start + sweep * frac
        kx, ky = cx + math.cos(ae) * r, cy + math.sin(ae) * r
        setc(cr, hexc("#ffffff"), 0.10); cr.arc(kx, ky, 15, 0, 2 * math.pi); cr.fill()
        setc(cr, hexc("#f4f4f4")); cr.arc(kx, ky, 8, 0, 2 * math.pi); cr.fill()
        setc(cr, hexc("#161616")); cr.arc(kx, ky, 3, 0, 2 * math.pi); cr.fill()
        # inner ring
        cr.set_line_width(1); setc(cr, hexc("#1c1c1c")); cr.arc(cx, cy, r - 15, 0, 2 * math.pi); cr.stroke()
        # busy spinner
        if busy > 0.01:
            cr.set_line_width(3); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            a0 = phase * 3.2
            setc(cr, hexc("#f0f0f0"), 0.6 * busy); cr.arc(cx, cy, r - 15, a0, a0 + 1.2); cr.stroke()
            setc(cr, hexc("#9a9a9a"), 0.35 * busy); cr.arc(cx, cy, r - 15, a0 + math.pi, a0 + math.pi + 0.7); cr.stroke()
        # pulse ring
        if pulse < 0.995:
            cr.set_line_width(2); setc(cr, hexc("#ffffff"), 0.35 * (1 - pulse))
            cr.arc(cx, cy, r + pulse * 24, 0, 2 * math.pi); cr.stroke()
        draw_text(cr, self, f"{pct:.0f}%", cx, cy - 8, 42, hexc("#f6f6f6"), "bold", "center")
        draw_text(cr, self, f"{self.used_txt} / {self.total_txt}", cx, cy + 26, 12, hexc("#858585"), "normal", "center")
        return False

class LogoIcon(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_size_request(40, 40)

    def do_draw(self, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        g = cairo.LinearGradient(0, 0, 0, H)
        g.add_color_stop_rgb(0, *hexc("#303030")); g.add_color_stop_rgb(1, *hexc("#111111"))
        rrect(cr, 1, 1, W - 2, H - 2, 11); cr.set_source(g); cr.fill_preserve()
        setc(cr, hexc("#3a3a3a")); cr.set_line_width(1); cr.stroke()
        rrect(cr, 8, 13, 24, 14, 3); setc(cr, hexc("#3b3b3b")); cr.fill_preserve()
        setc(cr, hexc("#c4c4c4")); cr.set_line_width(1.5); cr.stroke()
        for i in range(4):
            rrect(cr, 11 + i * 5.2, 16, 3, 8, 1); setc(cr, hexc("#e6e6e6")); cr.fill()
        for i in range(5):
            cr.rectangle(10 + i * 5, 28, 2, 4); setc(cr, hexc("#8c8c8c")); cr.fill()
        return False

# ------------------------------------------------------------------ CSS
CSS = """
* { font-family: "Inter","Noto Sans Thai","Sarabun","Noto Sans","Ubuntu","Cantarell","DejaVu Sans",sans-serif; }
window, .root { background-color: #0c0c0c; color: #d6d6d6; }
.card { background-color: #151515; border: 1px solid #262626; border-radius: 14px; padding: 12px 14px; }
.tile { background-color: #151515; border: 1px solid #262626; border-radius: 12px; padding: 7px 12px; }
.title { font-size: 19px; font-weight: 700; color: #f4f4f4; }
.sub { font-size: 11px; color: #7d7d7d; }
.credit { font-size: 11px; font-weight: 700; color: #e6e6e6; }
.k { font-size: 10px; color: #858585; }
.v { font-size: 13px; font-weight: 700; color: #f0f0f0; }
.section { font-size: 11px; font-weight: 700; color: #8a8a8a; }
.rowtext { font-size: 13px; color: #dcdcdc; }
.hint { font-size: 12px; color: #9a9a9a; }
.pctv { font-size: 14px; font-weight: 700; color: #f2f2f2; }
.status { font-size: 12px; color: #9a9a9a; }
.mono { font-family: "JetBrains Mono","DejaVu Sans Mono",monospace; font-size: 11px; color: #a6a6a6; }
.page-title { font-size: 17px; font-weight: 700; color: #f4f4f4; }
.footer { font-size: 11px; color: #666666; }
"""

# ------------------------------------------------------------------ application
class App(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP)
        self.cfg = load_cfg()
        self.lang = self.cfg["lang"]
        self.helper = RootHelper()
        self.busy = False; self.last_auto = 0; self.tick = 0
        self.pct = 0.0; self.logs = []; self.texts = []   # texts: (setter, key, kwargs)

        self.set_size_request(WIN_W, WIN_H)
        self.set_default_size(WIN_W, WIN_H)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name("ramreduct")
        self.connect("realize", self._on_realize)

        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
        prov = Gtk.CssProvider()
        try:
            prov.load_from_data(CSS.encode())
        except GLib.Error:
            pass
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(280)
        self.stack.set_homogeneous(True)
        self.stack.get_style_context().add_class("root")
        self.add(self.stack)
        self.stack.add_named(self.build_main(), "main")
        self.stack.add_named(self.build_settings(), "settings")

        self.apply_lang()
        self.refresh()
        GLib.timeout_add_seconds(1, self.refresh)

    # -- helpers
    def _on_realize(self, *_):
        win = self.get_window()
        if win:
            try:
                win.set_functions(Gdk.WMFunction.MOVE | Gdk.WMFunction.MINIMIZE | Gdk.WMFunction.CLOSE)
            except Exception:
                pass

    def t(self, key, **kw):
        s = STR[self.lang][key]
        return s.format(**kw) if kw else s

    def label(self, key=None, css=None, xalign=0.0, **kw):
        lb = Gtk.Label(xalign=xalign)
        if css:
            lb.get_style_context().add_class(css)
        if key:
            self.texts.append((lb.set_text, key, kw))
        return lb

    def bind(self, widget, key):
        self.texts.append((widget.set_text, key, {}))

    def apply_lang(self):
        for setter, key, kw in self.texts:
            setter(self.t(key, **kw) if kw else self.t(key))
        self.status_set(self.t("ready"))
        self.render_log()

    def card(self, css="card"):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        b.get_style_context().add_class(css)
        return b

    # -- pages
    def build_main(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.get_style_context().add_class("root"); root.set_border_width(16)

        hdr = Gtk.Box(spacing=10); root.pack_start(hdr, False, False, 0)
        hdr.pack_start(LogoIcon(), False, False, 0)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); left.set_valign(Gtk.Align.CENTER)
        t = Gtk.Label(label=APP, xalign=0); t.get_style_context().add_class("title")
        left.pack_start(t, False, False, 0)
        left.pack_start(self.label("sub", "sub"), False, False, 0)
        hdr.pack_start(left, True, True, 0)
        gear = PillButton(icon="gear", w=36, h=36); gear.set_valign(Gtk.Align.CENTER)
        gear.connect_clicked(lambda *_: self.stack.set_visible_child_name("settings"))
        hdr.pack_end(gear, False, False, 0)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); right.set_valign(Gtk.Align.CENTER)
        cr = Gtk.Label(label=CREDIT, xalign=1); cr.get_style_context().add_class("credit")
        gh = PillButton("GitHub", icon="git", trailing="arrow", w=104, h=28)
        gh.set_tooltip_text(GITHUB); gh.connect_clicked(self.open_github)
        right.pack_start(cr, False, False, 0); right.pack_start(gh, False, False, 0)
        hdr.pack_end(right, False, False, 0)

        self.gauge = Gauge(); self.gauge.set_vexpand(True)
        root.pack_start(self.gauge, True, True, 0)

        grid = Gtk.Grid(column_spacing=8, row_spacing=8, column_homogeneous=True)
        root.pack_start(grid, False, False, 0)
        self.vals = {}
        for i, (key, name) in enumerate([("used", "used"), ("avail", "avail"), ("free", "free"),
                                         ("cached", "cached"), ("swap_used", "swap_used"), ("swap_total", "swap_total")]):
            tile = self.card("tile")
            tile.pack_start(self.label(name, "k"), False, False, 0)
            v = Gtk.Label(label="-", xalign=0); v.get_style_context().add_class("v")
            tile.pack_start(v, False, False, 0)
            grid.attach(tile, i % 3, i // 3, 1, 1); self.vals[key] = v

        auto = self.card(); root.pack_start(auto, False, False, 0)
        row1 = Gtk.Box(spacing=8); auto.pack_start(row1, False, False, 0)
        row1.pack_start(self.label("auto", "rowtext"), True, True, 0)
        self.auto_sw = Switch(False); self.auto_sw.toggled_cb = self.on_auto
        row1.pack_end(self.auto_sw, False, False, 0)
        row2 = Gtk.Box(spacing=10); auto.pack_start(row2, False, False, 4)
        row2.pack_start(self.label("auto_when", "hint"), False, False, 0)
        self.slider = BarSlider(50, 99, self.cfg["threshold"]); self.slider.set_dim(True)
        self.slider.changed_cb = self.on_threshold
        row2.pack_start(self.slider, True, True, 0)
        self.pct_lbl = Gtk.Label(label=f"{self.cfg['threshold']}%", xalign=1)
        self.pct_lbl.get_style_context().add_class("pctv"); self.pct_lbl.set_size_request(40, -1)
        row2.pack_end(self.pct_lbl, False, False, 0)

        self.btn = PrimaryButton(""); self.btn.connect_clicked(lambda *_: self.clean())
        root.pack_start(self.btn, False, False, 0)
        self.status = Gtk.Label(xalign=0.5); self.status.get_style_context().add_class("status")
        root.pack_start(self.status, False, False, 0)
        return root

    def build_settings(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        root.get_style_context().add_class("root"); root.set_border_width(16)

        hdr = Gtk.Box(spacing=12); root.pack_start(hdr, False, False, 0)
        back = PillButton("", icon="back", w=36, h=36)
        back.connect_clicked(lambda *_: self.stack.set_visible_child_name("main"))
        hdr.pack_start(back, False, False, 0)
        hdr.pack_start(self.label("settings", "page-title"), False, False, 0)

        root.pack_start(self.label("language", "section"), False, False, 2)
        self.seg = Segmented(["ไทย", "English"], 0 if self.lang == "th" else 1)
        self.seg.changed_cb = self.on_lang
        root.pack_start(self.seg, False, False, 0)

        root.pack_start(self.label("options", "section"), False, False, 2)
        oc = self.card(); root.pack_start(oc, False, False, 0)
        self.opt_sw = {}
        for i, key in enumerate(["c", "p", "m", "s"]):
            row = Gtk.Box(spacing=8)
            row.pack_start(self.label("opt_" + key, "rowtext"), True, True, 0)
            sw = Switch(self.cfg["opts"][key]); sw.toggled_cb = (lambda a, k=key: self.on_opt(k, a))
            row.pack_end(sw, False, False, 0)
            oc.pack_start(row, False, False, 1); self.opt_sw[key] = sw

        root.pack_start(self.label("top", "section"), False, False, 2)
        tc = self.card(); root.pack_start(tc, False, False, 0)
        self.top = Gtk.Label(xalign=0); self.top.get_style_context().add_class("mono")
        self.top.set_size_request(-1, 56); self.top.set_yalign(0.0)
        tc.pack_start(self.top, False, False, 0)

        root.pack_start(self.label("log", "section"), False, False, 2)
        lc = self.card(); root.pack_start(lc, False, False, 0)
        self.log_lbl = Gtk.Label(xalign=0); self.log_lbl.get_style_context().add_class("mono")
        self.log_lbl.set_size_request(-1, 58); self.log_lbl.set_yalign(0.0)
        self.log_lbl.set_line_wrap(True); self.log_lbl.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.log_lbl.set_max_width_chars(48); self.log_lbl.set_width_chars(48)
        lc.pack_start(self.log_lbl, False, False, 0)

        foot = Gtk.Label(xalign=0.5); foot.get_style_context().add_class("footer")
        self.texts.append((foot.set_text, "about", {"v": VERSION}))
        root.pack_end(foot, False, False, 0)
        return root

    # -- callbacks
    def open_github(self, *_):
        try:
            Gtk.show_uri_on_window(self, GITHUB, Gdk.CURRENT_TIME)
        except Exception:
            webbrowser.open(GITHUB)

    def on_lang(self, idx):
        self.lang = "th" if idx == 0 else "en"
        self.cfg["lang"] = self.lang; save_cfg(self.cfg); self.apply_lang()

    def on_opt(self, key, active):
        self.cfg["opts"][key] = active; save_cfg(self.cfg)

    def on_threshold(self, v):
        self.pct_lbl.set_text(f"{v}%"); self.cfg["threshold"] = v; save_cfg(self.cfg)

    def on_auto(self, active):
        self.slider.set_dim(not active)
        if active:
            def chk():
                if not self.helper.ensure():
                    GLib.idle_add(self.auth_failed)
            threading.Thread(target=chk, daemon=True).start()

    def auth_failed(self):
        self.auto_sw.set_active(False); self.slider.set_dim(True)
        self.status_set(self.t("auth")); self.add_log(self.t("auth"))

    def status_set(self, text):
        self.status.set_text(text)
        self.status.set_opacity(0.0)
        start = [None]
        def step(w, clock):
            t = clock.get_frame_time() / 1e6
            if start[0] is None:
                start[0] = t
            k = min(1.0, (t - start[0]) / 0.35)
            w.set_opacity(k)
            return k < 1.0
        self.status.add_tick_callback(step)

    def add_log(self, msg):
        self.logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.logs = self.logs[-4:]
        self.render_log()

    def render_log(self):
        if hasattr(self, "log_lbl"):
            self.log_lbl.set_text("\n".join(self.logs))

    def refresh(self):
        m = meminfo()
        total, avail = m["MemTotal"], m["MemAvailable"]
        used = total - avail
        self.pct = used / total * 100
        st, sf = m.get("SwapTotal", 0), m.get("SwapFree", 0)
        self.gauge.update(self.pct, fmt(used), fmt(total))
        self.vals["used"].set_text(fmt(used)); self.vals["avail"].set_text(fmt(avail))
        self.vals["free"].set_text(fmt(m["MemFree"]))
        self.vals["cached"].set_text(fmt(m.get("Cached", 0) + m.get("SReclaimable", 0)))
        self.vals["swap_used"].set_text(fmt(st - sf)); self.vals["swap_total"].set_text(fmt(st))
        if self.stack.get_visible_child_name() == "settings" and self.tick % 3 == 0:
            self.top.set_text("\n".join(f"{n[:20]:<20} {fmt(b):>9}" for n, b in top_procs()))
        self.tick += 1
        if (self.auto_sw.active and not self.busy and self.pct >= self.slider.value
                and time.time() - self.last_auto > 60):
            self.last_auto = time.time()
            self.add_log(self.t("auto_msg", p=f"{self.pct:.0f}"))
            self.clean()
        return True

    def clean(self):
        if self.busy:
            return
        flags = "".join(k for k, sw in self.opt_sw.items() if sw.active)
        if not flags:
            self.status_set(self.t("none")); return
        self.busy = True
        self.btn.set_text(self.t("cleaning")); self.btn.set_busy(True); self.gauge.set_busy(True)
        threading.Thread(target=self.worker, args=(flags,), daemon=True).start()

    def worker(self, flags):
        b = meminfo()
        ok, msg = self.helper.clean(flags)
        time.sleep(0.5)
        a = meminfo()
        GLib.idle_add(self.done, ok, msg, b, a)

    def done(self, ok, msg, b, a):
        self.busy = False
        self.btn.set_busy(False); self.btn.set_text(self.t("clean")); self.gauge.set_busy(False)
        self.add_log(msg)
        if ok:
            ub, ua = b["MemTotal"] - b["MemAvailable"], a["MemTotal"] - a["MemAvailable"]
            self.add_log(self.t("result", a=fmt(ub), b=fmt(ua), c=fmt(b["MemFree"]), d=fmt(a["MemFree"])))
            self.status_set(self.t("freed", x=fmt(max(0, ub - ua))))
            self.gauge.pulse()
        else:
            self.status_set(self.t("failed"))
        self.refresh()

    # keep button label in sync with language even while idle
    def apply_lang(self):
        for setter, key, kw in self.texts:
            setter(self.t(key, **kw) if kw else self.t(key))
        self.btn.set_text(self.t("cleaning") if self.busy else self.t("clean"))
        self.status_set(self.t("ready"))
        self.render_log()

def main():
    w = App()
    def quit_(*_):
        w.helper.close(); Gtk.main_quit()
    w.connect("destroy", quit_); w.show_all(); Gtk.main()

if __name__ == "__main__":
    main()
