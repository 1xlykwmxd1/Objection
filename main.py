"""NBA 2K20 OBB / IFF Tool - Android (Kivy) front end.

All logic lives in the ``nba2k20`` package (shared with cli.py).  This file only
builds the touch UI and runs slow work on a background thread.

UI notes
* Dark theme, rounded buttons, two-line list rows.
* IFF browser: search + category filter (Court / Logo / Title Page / ...), Logo
  IFFs are grouped separately, star = favourite.  Inside an IFF the "IFF List"
  button opens a side drawer to jump to any other IFF of the same OBB (pending
  edits are staged automatically).
* Import PNG / Import all PNG auto-resize to the exact texture size.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import sys
import threading
import traceback
from functools import partial
from pathlib import Path

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Mesh, PopMatrix, PushMatrix, Rectangle, Rotate, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.uix.stencilview import StencilView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import escape_markup, platform

try:
    from nba2k20 import ai_assist, android_install, cfalloc, facelab, headsculpt, overlay as overlay_core, ownerlock, updater, workshop
    from nba2k20.version import VERSION_CODE, VERSION_NAME
    from nba2k20 import iff_core as core
    from nba2k20.service import CATEGORIES, Workspace, WorkspaceError, copy_with_suffix, list_sort_key
except ModuleNotFoundError as _missing:
    if _missing.name == "PIL":
        print(
            "\n[-] Kulang ang Pillow (PIL) - kailangan ito para magbasa/magsulat ng texture PNG.\n\n"
            "    I-install muna (sa Termux):\n"
            "        pip install pillow\n\n"
            "    Kung mag-error yan sa pag-build, i-try muna:\n"
            "        pkg update\n"
            "        pkg install python libjpeg-turbo libpng zlib freetype -y\n"
            "        pip install pillow\n\n"
            "    Pagkatapos, i-verify:\n"
            "        python -c \"import PIL; print(PIL.__version__)\"\n\n"
            "    Tapos buksan mo ulit ang app.\n",
            file=sys.stderr,
        )
    else:
        print(
            f"\n[-] Kulang ang Python package na '{_missing.name}'.\n\n"
            f"    I-install: pip install {_missing.name}\n",
            file=sys.stderr,
        )
    sys.exit(1)

APP_TITLE = "David2k Tool"
APP_SUBTITLE = "NBA 2K20  |  OBB / IFF / Textures / 3D / Ogg"
# Put your manifest URL here, or (no rebuild needed) in NBA2K20Tool/update_url.txt on the phone.
DEFAULT_UPDATE_URL = ""
ASSETS = Path(__file__).resolve().parent / "assets"
LOGO_SMALL = ASSETS / "logo_small.png"
LOGO_HOME = ASSETS / "logo_home.png"

# ------------------------------------------------------------------- theme
BG = (0.035, 0.035, 0.045, 1)
BAR = (0.075, 0.075, 0.09, 1)
CARD = (0.105, 0.105, 0.125, 1)
CARD_HI = (0.16, 0.16, 0.19, 1)
SEL = (0.30, 0.09, 0.10, 1)
ACCENT = (0.95, 0.27, 0.22, 1)
DANGER = (0.70, 0.18, 0.22, 1)
GOLD = (1.0, 0.78, 0.18, 1)
TEXT = (0.93, 0.94, 0.96, 1)
MUTED = (0.60, 0.60, 0.66, 1)
MUTED_HEX = "9a9aa8"
ACCENT_HEX = "f24538"

KIND_COLORS = {
    "ovr_top": (0.36, 0.25, 0.70, 1),
    "ovr_hi": (0.14, 0.40, 0.28, 1),
    "ovr_mid": (0.17, 0.24, 0.36, 1),
    "ovr_lo": (0.30, 0.20, 0.22, 1),
    "card": CARD,
    "ghost": CARD_HI,
    "primary": ACCENT,
    "danger": DANGER,
    "selected": SEL,
    "bar": BAR,
}

PREVIEW_MODES = {
    "Auto (best view)": "Auto",  # picks RGB-only for jerseys/atlases whose alpha hides the picture
    "Actual image": "RGBA + checker",  # the real picture, transparency shown on a checker
    "RGB only": "RGB (ignore alpha)",
    "Alpha": "Alpha channel",
    "Red": "Red channel",
    "Green": "Green channel",
    "Blue": "Blue channel",
}
FAV_LABEL = "Favorites"
# Starred automatically the first time this version runs (the user can un-star them later).
# Any OBB entry whose name starts with one of these is starred automatically the first time it is seen
# (so variants such as titleoverlays.iff are covered too).  "english." is exact: ENGLISHBOOTUP is not it.
AUTO_FAV_PREFIXES = (
    "newscorebug", "gamedataextra", "english.", "crowd", "gooeyoverlaysstatic", "gooeyglobal",
    "startinglineup3d", "titleoverlay", "title_overlay",
)
DEFAULT_FAVS = (
    "newscorebug.iff", "gamedataextra.iff", "english.iff", "crowd.iff", "gooeyoverlaysstatic.iff",
    "gooeyglobal.iff", "startinglineup3d.iff", "Titleoverlay.iff",
)
AUDIO_PICK_EXT = (".ogg", ".oga", ".aac", ".mp3", ".wav", ".m4a", ".flac", ".opus", ".wma", ".mp4", ".3gp", ".amr")
NON_IFF = "Non-IFF"  # cdf / dram / filelist / ogg entries: listed, exportable, not openable
# Audio is NOT an IFF: it only lives in the Audio / OGG Explorer, never in the IFF list.
_IFF_CATEGORIES = tuple(c for c in CATEGORIES if c != "Audio")
CATEGORY_CHOICES = [_IFF_CATEGORIES[0], FAV_LABEL, *_IFF_CATEGORIES[1:], NON_IFF]
# "All IFF" view order. Logo is last on purpose: it always stays in its own group.
GROUP_ORDER = [c for c in _IFF_CATEGORIES[1:] if c not in ("Logo", "Other")] + ["Other", "Logo", NON_IFF]

Window.clearcolor = BG
try:
    Window.softinput_mode = "below_target"
except Exception:  # noqa: BLE001
    pass

try:  # monospace font bundled with Kivy; fall back to the default font
    import kivy

    _mono = os.path.join(kivy.kivy_data_dir, "fonts", "RobotoMono-Regular.ttf")
    MONO_FONT = _mono if os.path.exists(_mono) else "Roboto"
except Exception:  # noqa: BLE001
    MONO_FONT = "Roboto"


# ----------------------------------------------------------------- platform
def storage_root() -> Path:
    if platform == "android":
        return Path("/storage/emulated/0")
    return Path.home()


def output_root() -> Path:
    """Output folder. Falls back to app storage if /sdcard is not writable yet."""
    folder = storage_root() / "David2kTool"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write_test"
        probe.write_bytes(b"")
        probe.unlink()
        return folder
    except OSError:
        fallback = Path(App.get_running_app().user_data_dir) / "output"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def has_storage_access() -> bool:
    """True when the app may read /sdcard (runtime permission on Android 6-10, All files access on 11-16)."""
    if platform != "android":
        return True
    try:
        from nba2k20 import storage_access

        return storage_access.has_access(str(storage_root()))
    except Exception:  # noqa: BLE001
        traceback.print_exc()
    try:
        os.listdir(str(storage_root()))
        return True
    except OSError:
        return False


def storage_roots() -> list[tuple[str, Path]]:
    """Internal storage plus SD cards / USB volumes under /storage."""
    roots = [("Internal", storage_root())]
    if platform == "android":
        try:
            for name in sorted(os.listdir("/storage")):
                if name in ("emulated", "self"):
                    continue
                roots.append((name[:9], Path("/storage") / name))
        except OSError:
            pass
        obb = storage_root() / "Android" / "obb"
        roots.append(("Android/obb", obb))
    return roots


def friendly_error(error: BaseException) -> str:
    if isinstance(error, PermissionError):
        return (
            "Permission denied.\n\nTurn on 'All files access' for this app "
            "(Settings > Apps > NBA2K20 OBB Tool > Permissions). If the file is in "
            "Android/obb, Android 11+ (also 13-16) blocks that folder: copy the OBB to Download first, "
            "open that copy, then put the patched OBB back with a file manager "
            "that has access (or ADB/Shizuku/root)."
        )
    if isinstance(error, FileNotFoundError):
        return f"File not found:\n{error}"
    return str(error) or error.__class__.__name__


def update_url() -> str:
    try:
        file = output_root() / "update_url.txt"
        if file.is_file():
            text = file.read_text(encoding="utf-8").strip()
            if text:
                return text.splitlines()[0].strip()
    except OSError:
        pass
    return DEFAULT_UPDATE_URL


def log_error(task: str, error: BaseException) -> None:
    """Append the full traceback to NBA2K20Tool/error_log.txt so a failed save can be diagnosed."""
    try:
        import datetime
        folder = output_root()
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / "error_log.txt").open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== {datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {task}\n")
            handle.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))
    except Exception:  # noqa: BLE001
        pass


def request_android_permissions() -> None:
    """Android 6-10: runtime dialog.  Android 11-16: opens the 'All files access' screen (see storage_access.py)."""
    if platform != "android":
        return
    try:
        from nba2k20 import storage_access

        result = storage_access.request_access()
        if result == "failed":
            show_message(
                "File access",
                "Could not open the permission screen.\nOpen Settings > Apps > this app > Permissions > "
                "Files and media (or 'All files access') and allow it.\nOr use Roster Editor > System file picker.",
            )
    except Exception:  # noqa: BLE001
        traceback.print_exc()


# ------------------------------------------------------------------ widgets
class RoundBg(Widget):
    """Rounded coloured background; colour comes from ``kind`` (see KIND_COLORS)."""

    kind = StringProperty("card")
    radius = ListProperty([dp(16)])

    def _init_bg(self) -> None:
        with self.canvas.before:
            self._bg_color = Color(*CARD)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
        self.bind(pos=self._sync_bg, size=self._sync_bg, kind=self._sync_bg)
        if hasattr(self, "state"):
            self.bind(state=self._sync_bg)
        self._sync_bg()

    def _sync_bg(self, *_args) -> None:
        r, g, b, a = KIND_COLORS.get(self.kind, CARD)
        if getattr(self, "state", "normal") == "down":
            r, g, b = min(1, r + 0.10), min(1, g + 0.10), min(1, b + 0.10)
        if getattr(self, "disabled", False):
            a = 0.45
        self._bg_color.rgba = (r, g, b, a)
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._bg_rect.radius = self.radius


def fade_in(widget, delay: float = 0.0, duration: float = 0.14, rise: float = 0.0) -> None:
    """Fade a widget in (optionally after ``delay`` s). Safe to call on any widget."""
    widget.opacity = 0

    def start(_dt):
        Animation(opacity=1, d=duration, t="out_cubic").start(widget)

    Clock.schedule_once(start, delay)


def stagger_in(container, step: float = 0.012, limit: int = 8) -> None:
    """Children of ``container`` appear one after another (first ``limit`` only, rest instantly)."""
    kids = list(reversed(container.children))
    for i, kid in enumerate(kids):
        if i < limit:
            fade_in(kid, delay=0.0 + i * step)


VIOLET = (0.80, 0.10, 0.14, 1)


def _glow_texture() -> Texture:
    """Soft round glow (white, alpha falls off to the edge); tinted per use with Color()."""
    size = 64
    buf = bytearray()
    for y in range(size):
        for x in range(size):
            d = math.hypot((x - size / 2 + 0.5) / (size / 2), (y - size / 2 + 0.5) / (size / 2))
            a = max(0.0, 1.0 - d)
            a = a * a * (3 - 2 * a)
            buf += bytes((255, 255, 255, int(a * 255)))
    tex = Texture.create(size=(size, size), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "clamp_to_edge"
    return tex


_GLOW_TEX = None


def glow_texture() -> Texture:
    global _GLOW_TEX
    if _GLOW_TEX is None:
        _GLOW_TEX = _glow_texture()
    return _GLOW_TEX


class GlowBg(Widget):
    """Slowly drifting violet / cyan light behind the whole app (gives the dark UI some depth)."""

    phase = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        tex = glow_texture()
        with self.canvas:
            self._c1 = Color(*VIOLET[:3], 0.20)
            self._r1 = Rectangle(texture=tex)
            self._c2 = Color(*ACCENT[:3], 0.16)
            self._r2 = Rectangle(texture=tex)
            self._c3 = Color(*GOLD[:3], 0.05)
            self._r3 = Rectangle(texture=tex)
        self.bind(pos=self._layout, size=self._layout, phase=self._layout)
        self._layout()
        self.phase = 0.35  # static: the endless drift animation made every screen lag

    def _layout(self, *_a) -> None:
        w, h = self.size
        if w <= 1 or h <= 1:
            return
        t = self.phase
        big = max(w, h) * 1.25
        self._r1.size = (big, big)
        self._r1.pos = (self.x - big * 0.35 + w * 0.35 * t, self.y + h * 0.55 - big * 0.5 + h * 0.10 * t)
        self._r2.size = (big * 0.9, big * 0.9)
        self._r2.pos = (self.right - big * 0.65 - w * 0.30 * t, self.y - big * 0.30 + h * 0.20 * t)
        self._r3.size = (big * 0.6, big * 0.6)
        self._r3.pos = (self.x + w * 0.5 - big * 0.3 + w * 0.2 * (1 - t), self.y + h * 0.3 - big * 0.3)


class ShimmerLine(Widget):
    """Thin violet-cyan line under the header with a light streak that keeps running across it."""

    shine = NumericProperty(0.0)

    def __init__(self, **kwargs):
        animate = kwargs.pop("animate", True)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(2))
        super().__init__(**kwargs)
        tex = glow_texture()
        with self.canvas:
            self._base = Color(*ACCENT[:3], 0.35)
            self._line = Rectangle()
            self._streak_c = Color(1, 1, 1, 0.9)
            self._streak = Rectangle(texture=tex)
        self.bind(pos=self._layout, size=self._layout, shine=self._layout)
        if animate:
            loop = Animation(shine=1.0, d=2.6, t="in_out_quad") + Animation(shine=0.0, d=0.01) + Animation(shine=0.0, d=0.9)
            loop.repeat = True
            loop.start(self)
        else:
            self._streak_c.a = 0.0

    def _layout(self, *_a) -> None:
        self._line.pos = self.pos
        self._line.size = self.size
        sw = max(dp(120), self.width * 0.28)
        self._streak.size = (sw, dp(14))
        self._streak.pos = (self.x - sw + (self.width + sw * 2) * min(1.0, self.shine), self.y - dp(6))


class FxPopup(Popup):
    """Popup whose content fades / slides in piece by piece."""

    def on_open(self, *args):
        try:
            content = self.content
            if content is not None:
                content.opacity = 0
                Animation(opacity=1, d=0.10, t="out_cubic").start(content)
                stagger_in(content, 0.01, 6)
        except Exception:  # noqa: BLE001
            pass


class Btn(RoundBg, Button):
    glow = NumericProperty(0.0)

    def on_press(self):
        Animation.cancel_all(self, "opacity")
        Animation.cancel_all(self, "glow")
        Animation(opacity=0.8, glow=0.9, d=0.05, t="out_quad").start(self)

    def on_release(self):
        Animation.cancel_all(self, "opacity")
        Animation.cancel_all(self, "glow")
        Animation(opacity=1, glow=0.0, d=0.15, t="out_quad").start(self)

    def _sync_glow(self, *_a) -> None:
        self._gc.rgba = (*ACCENT[:3], self.glow)
        r = self.radius[0] if self.radius else dp(12)
        self._gl.rounded_rectangle = (self.x, self.y, self.width, self.height, r)

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("kind", "ghost")
        super().__init__(**kwargs)
        self._init_bg()
        with self.canvas.after:
            self._gc = Color(*ACCENT[:3], self.glow)
            self._gl = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=dp(1.1))
        self.bind(pos=self._sync_glow, size=self._sync_glow, glow=self._sync_glow)
        self._sync_glow()


class Card(RoundBg, BoxLayout):
    def __init__(self, **kwargs):
        kwargs.setdefault("kind", "card")
        super().__init__(**kwargs)
        self._init_bg()


class PlayerRow(ButtonBehavior, Card):
    """One roster row: jersey chip | name + position/CF | OVR badge."""

    def __init__(self, jersey, name, sub, ovr, on_tap, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(66))
        kwargs.setdefault("padding", (dp(10), dp(8)))
        kwargs.setdefault("spacing", dp(10))
        super().__init__(**kwargs)
        self._on_tap = on_tap
        chip = Card(size_hint=(None, 1), width=dp(50), kind="ghost")
        chip.add_widget(Label(text=f"#{jersey}", font_size=sp(14), bold=True, color=MUTED))
        self.add_widget(chip)
        mid = BoxLayout(orientation="vertical")
        mid.add_widget(left_label(f"[b]{escape_markup(str(name))}[/b]", 16))
        mid.add_widget(left_label(escape_markup(str(sub)), 12, MUTED))
        self.add_widget(mid)
        if ovr:
            kind = "ovr_top" if ovr >= 90 else "ovr_hi" if ovr >= 70 else "ovr_mid" if ovr >= 55 else "ovr_lo"
            badge = Card(orientation="vertical", size_hint=(None, 1), width=dp(64), kind=kind)
            badge.add_widget(Label(text="OVR", font_size=sp(10), color=MUTED))
            badge.add_widget(Label(text=str(ovr), font_size=sp(24), bold=True, color=TEXT))
            self.add_widget(badge)

    def on_release(self):
        if self._on_tap:
            self._on_tap()


HOLD_SECONDS = 0.45


class HoldMixin:
    """Long-press detection. Set ``on_hold`` to a callable; a normal tap is unaffected.
    After a hold fired, ``_held`` stays True until the release was swallowed by the owner."""

    on_hold = None
    _held = False
    _hold_ev = None

    def _hold_start(self, touch) -> None:
        self._held = False
        self._hold_cancel()
        if self.on_hold is not None:
            self._hold_ev = Clock.schedule_once(lambda _dt, t=touch: self._hold_fire(t), HOLD_SECONDS)

    def _hold_cancel(self) -> None:
        if self._hold_ev is not None:
            self._hold_ev.cancel()
            self._hold_ev = None

    def _hold_fire(self, touch) -> None:
        self._hold_ev = None
        try:  # finger moved a lot = the user is scrolling, not holding
            if abs(touch.pos[0] - touch.opos[0]) > dp(12) or abs(touch.pos[1] - touch.opos[1]) > dp(12):
                return
        except Exception:  # noqa: BLE001
            pass
        self._held = True
        if self.on_hold is not None:
            self.on_hold()


class HoldCard(HoldMixin, Card):
    """Card that reports a long-press on its text area (buttons keep their own taps)."""

    def on_touch_down(self, touch):
        handled = super().on_touch_down(touch)
        if not handled and self.collide_point(*touch.pos):
            self._hold_start(touch)
        return handled

    def on_touch_up(self, touch):
        self._hold_cancel()
        return super().on_touch_up(touch)


class Opt(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = CARD_HI
        self.color = TEXT
        self.height = dp(46)
        self.font_size = sp(15)


class Drop(RoundBg, Spinner):
    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("kind", "ghost")
        kwargs.setdefault("option_cls", Opt)
        super().__init__(**kwargs)
        self._init_bg()


class DragImage(Image):
    """Image you can swipe: calls on_drag(dx, dy) when the finger is lifted."""

    def __init__(self, on_drag, **kwargs):
        super().__init__(**kwargs)
        self.on_drag = on_drag
        self._start = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self._start = touch.pos
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            dx, dy = touch.x - self._start[0], touch.y - self._start[1]
            if abs(dx) + abs(dy) > dp(12):
                self.on_drag(dx, dy)
            return True
        return super().on_touch_up(touch)


class TapImage(ButtonBehavior, Image):
    """Image that can be pressed."""


class OverlayCanvas(StencilView):
    """Texture with a movable overlay: drag = move, drag a corner = resize,
    two fingers = pinch to resize + twist to rotate."""

    def __init__(self, on_change, **kwargs):
        super().__init__(**kwargs)
        self.on_change = on_change
        self.texture = None
        self.has_overlay = False
        self.cx, self.cy = 0.5, 0.5
        self.size_frac = 0.2
        self.aspect = 1.0  # overlay height / width
        self.rot = 0.0
        self.zoom = 1.0
        self._touches: dict = {}
        self._mode = "move"
        self._pinch = None
        self.bind(pos=self._redraw, size=self._redraw)

    def image_rect(self):
        side = min(self.width, self.height) * self.zoom
        return self.center_x - side / 2, self.center_y - side / 2, side

    def _centre_px(self):
        x, y, side = self.image_rect()
        return x + self.cx * side, y + (1 - self.cy) * side, side

    def _corners(self):
        sx, sy, side = self._centre_px()
        w = self.size_frac * side
        h = w * self.aspect
        cos_a, sin_a = math.cos(math.radians(self.rot)), math.sin(math.radians(self.rot))
        out = []
        for ox, oy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            out.append((sx + ox * cos_a - oy * sin_a, sy + ox * sin_a + oy * cos_a))
        return out

    def set_texture(self, texture) -> None:
        self.texture = texture
        self._redraw()

    def _redraw(self, *_args) -> None:
        self.canvas.clear()
        x, y, side = self.image_rect()
        with self.canvas:
            Color(0.04, 0.04, 0.05, 1)
            Rectangle(pos=self.pos, size=self.size)
            if self.texture is not None:
                Color(1, 1, 1, 1)
                Rectangle(texture=self.texture, pos=(x, y), size=(side, side))
            if self.has_overlay:
                sx, sy, _side = self._centre_px()
                w = self.size_frac * side
                h = w * self.aspect
                PushMatrix()
                Rotate(angle=self.rot, origin=(sx, sy))
                Color(0.10, 0.75, 0.95, 1)
                Line(rectangle=(sx - w / 2, sy - h / 2, w, h), width=dp(1.4))
                PopMatrix()
                radius = dp(7)
                for cx, cy in self._corners():
                    Color(0.10, 0.75, 0.95, 1)
                    Ellipse(pos=(cx - radius, cy - radius), size=(radius * 2, radius * 2))

    def _changed(self, final: bool = False) -> None:
        self._redraw()
        self.on_change(final)

    def on_touch_down(self, touch):
        if not self.has_overlay or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        touch.grab(self)
        self._touches[touch.uid] = touch
        if len(self._touches) == 1:
            self._mode = "move"
            for cx, cy in self._corners():
                if math.hypot(touch.x - cx, touch.y - cy) < dp(26):
                    self._mode = "resize"
        elif len(self._touches) == 2:
            a, b = list(self._touches.values())[:2]
            self._pinch = (
                max(1.0, math.hypot(a.x - b.x, a.y - b.y)),
                math.atan2(b.y - a.y, b.x - a.x),
                self.size_frac,
                self.rot,
            )
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        if len(self._touches) >= 2 and self._pinch is not None:
            a, b = list(self._touches.values())[:2]
            dist = max(1.0, math.hypot(a.x - b.x, a.y - b.y))
            angle = math.atan2(b.y - a.y, b.x - a.x)
            d0, a0, size0, rot0 = self._pinch
            self.size_frac = max(0.03, min(1.2, size0 * dist / d0))
            self.rot = (rot0 + math.degrees(angle - a0) + 180) % 360 - 180
        elif self._mode == "resize":
            sx, sy, side = self._centre_px()
            dist = math.hypot(touch.x - sx, touch.y - sy)
            diagonal = math.sqrt(1 + self.aspect ** 2)
            self.size_frac = max(0.03, min(1.2, 2 * dist / diagonal / side))
        else:
            _x, _y, side = self.image_rect()
            self.cx = max(0.0, min(1.0, self.cx + touch.dx / side))
            self.cy = max(0.0, min(1.0, self.cy - touch.dy / side))
        self._changed(False)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._touches.pop(touch.uid, None)
            self._pinch = None
            if len(self._touches) == 1:
                self._mode = "move"
            if not self._touches:
                self._changed(True)
            return True
        return super().on_touch_up(touch)


class StarButton(ButtonBehavior, Widget):
    """Favourite star drawn with canvas (no font glyph needed)."""

    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw, active=self._draw)
        self._draw()

    def _draw(self, *_args) -> None:
        self.canvas.clear()
        cx, cy = self.center
        outer = min(self.width, self.height) * 0.34
        inner = outer * 0.45
        pts: list[float] = []
        for i in range(10):
            angle = math.pi / 2 + i * math.pi / 5
            radius = outer if i % 2 == 0 else inner
            pts += [cx + radius * math.cos(angle), cy + radius * math.sin(angle)]
        with self.canvas:
            if self.active:
                Color(*GOLD)
                verts = [cx, cy, 0, 0]
                for i in range(10):
                    verts += [pts[2 * i], pts[2 * i + 1], 0, 0]
                verts += [pts[0], pts[1], 0, 0]
                Mesh(vertices=verts, indices=list(range(12)), mode="triangle_fan")
            else:
                Color(*MUTED)
                Line(points=pts, close=True, width=dp(1.3))


def make_btn(text: str, on_release, height: float = 48, kind: str = "ghost", **kwargs) -> Btn:
    button = Btn(text=text, size_hint_y=None, height=dp(height), kind=kind, **kwargs)
    button.bind(on_release=lambda *_: on_release())
    return button


def make_input(hint: str, height: float = 46, **kwargs) -> TextInput:
    return TextInput(
        hint_text=hint,
        multiline=False,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_active="",
        background_color=CARD,
        foreground_color=TEXT,
        hint_text_color=MUTED,
        cursor_color=ACCENT,
        selection_color=(*ACCENT[:3], 0.35),
        padding=(dp(14), dp(13), dp(14), dp(10)),
        font_size=sp(15),
        **kwargs,
    )


def make_label(text: str = "", size: float = 14, color=TEXT, **kwargs) -> Label:
    label = Label(text=text, font_size=sp(size), color=color, markup=True, **kwargs)
    return label


def left_label(text: str = "", size: float = 14, color=TEXT, height: float | None = None, **kwargs) -> Label:
    extra = {}
    if height is not None:
        extra = {"size_hint_y": None, "height": dp(height)}
    label = make_label(text, size, color, halign="left", valign="middle", **extra, **kwargs)
    label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], s[1])))
    return label


def wrap_label(text: str = "", size: float = 14, color=TEXT, halign: str = "left", **kwargs) -> Label:
    """Label that wraps to its own width and grows in height (never runs off the screen)."""
    label = Label(text=text, font_size=sp(size), color=color, markup=True, halign=halign, valign="top",
                  size_hint_y=None, **kwargs)
    label.bind(width=lambda w, v: setattr(w, "text_size", (max(1, v), None)))
    label.bind(texture_size=lambda w, ts: setattr(w, "height", max(dp(size + 6), ts[1] + dp(2))))
    return label


def make_popup(title: str, content, size_hint=(0.92, 0.5), **kwargs) -> Popup:
    kwargs.setdefault("_anim_duration", 0.1)
    kwargs.setdefault("overlay_color", (0, 0, 0, 0.72))
    kwargs.setdefault("title_align", "center")
    return FxPopup(
        title=title,
        content=content,
        size_hint=size_hint,
        background="",
        background_color=BAR,
        separator_color=ACCENT,
        separator_height=dp(2),
        title_color=ACCENT,
        title_size=sp(16),
        **kwargs,
    )


class ArcSpinner(Widget):
    """Spinning arc used by the loading overlay."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*ACCENT[:3], 0.18)
            self._track = Line(circle=(0, 0, 1), width=dp(3))
            PushMatrix()
            self._rot = Rotate(angle=0, origin=(0, 0))
            Color(*ACCENT[:3], 1)
            self._arc = Line(circle=(0, 0, 1, 0, 110), width=dp(3.4), cap="round")
            Color(*GOLD[:3], 0.9)
            self._arc2 = Line(circle=(0, 0, 1, 180, 230), width=dp(3.4), cap="round")
            PopMatrix()
        self.bind(pos=self._layout, size=self._layout)
        self._layout()
        self._ev = Clock.schedule_interval(self._spin, 1 / 30)

    def _layout(self, *_a) -> None:
        cx, cy = self.center
        r = max(dp(6), min(self.width, self.height) / 2 - dp(4))
        self._track.circle = (cx, cy, r)
        self._arc.circle = (cx, cy, r, 0, 110)
        self._arc2.circle = (cx, cy, r, 180, 230)
        self._rot.origin = (cx, cy)

    def _spin(self, dt) -> None:
        self._rot.angle -= 300 * dt

    def stop(self) -> None:
        self._ev.cancel()


class BrandLogo(Widget):
    """Vector David2k badge (port of the Java BrandLogoView) - used when the PNG logo files are missing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_a) -> None:
        self.canvas.clear()
        w, h = self.size
        if w < 2 or h < 2:
            return
        cx, cy = self.center
        r = min(w, h) * 0.38
        blue = (72 / 255, 143 / 255, 255 / 255, 1)
        with self.canvas:
            Color(30 / 255, 115 / 255, 1, 0.22)                       # soft glow
            Ellipse(pos=(cx - r * 1.12, cy - r * 1.12), size=(r * 2.24, r * 2.24))
            Color(24 / 255, 28 / 255, 36 / 255, 1)                    # disc
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(*blue)
            Line(circle=(cx, cy, r), width=max(dp(2), r * 0.08))
            Color(228 / 255, 233 / 255, 244 / 255, 1)
            Line(circle=(cx, cy, r * 0.62, -20, 100), width=max(dp(1.6), r * 0.06))
            Line(circle=(cx, cy, r * 0.62, 160, 280), width=max(dp(1.6), r * 0.06))
            Color(1, 1, 1, 1)                                         # chevron
            Line(points=[cx - r * 0.33, cy + r * 0.28, cx, cy - r * 0.34, cx + r * 0.33, cy + r * 0.28],
                 width=max(dp(2.2), r * 0.09), joint="miter", cap="square")
            Color(*blue)
            Line(points=[cx + r * 0.06, cy - r * 0.34, cx + r * 0.5, cy + r * 0.14], width=max(dp(1.6), r * 0.06))


class MenuCard(ButtonBehavior, Card):
    """Big tappable home-screen card: glyph chip | title + subtitle | arrow."""

    def __init__(self, title: str, sub: str, glyph: str, on_tap, primary: bool = False, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(78))
        kwargs.setdefault("padding", (dp(12), dp(10)))
        kwargs.setdefault("spacing", dp(12))
        kwargs.setdefault("kind", "selected" if primary else "card")
        super().__init__(**kwargs)
        self._on_tap = on_tap
        chip = Card(size_hint=(None, 1), width=dp(56), kind="primary" if primary else "ghost")
        chip.add_widget(Label(text=glyph, font_size=sp(15), bold=True, color=TEXT))
        self.add_widget(chip)
        mid = BoxLayout(orientation="vertical")
        mid.add_widget(left_label(f"[b]{escape_markup(title)}[/b]", 17))
        mid.add_widget(left_label(escape_markup(sub), 12, MUTED))
        self.add_widget(mid)
        self.add_widget(Label(text=">", font_size=sp(22), bold=True, color=ACCENT, size_hint_x=None, width=dp(24)))

    def on_press(self):
        Animation.cancel_all(self, "opacity")
        Animation(opacity=0.8, d=0.04).start(self)

    def on_release(self):
        Animation.cancel_all(self, "opacity")
        Animation(opacity=1, d=0.12, t="out_quad").start(self)
        if self._on_tap:
            self._on_tap()


def row_entry(title, sub="", cb=None, key=None, star=None, on_star=None, header=False,
              on_export=None, badge=None, thumb=None, on_import=None) -> dict:
    """title is PLAIN text (the list escapes it); badge is plain text shown on the right."""
    return {
        "title": title, "sub": sub, "cb": cb, "key": key,
        "star": star, "on_star": on_star, "header": header, "on_export": on_export,
        "on_import": on_import,
        "badge": badge, "thumb": thumb,
    }


class ListRow(HoldMixin, Btn):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.on_hold is not None:
            self._hold_start(touch)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self._hold_cancel()
        return super().on_touch_up(touch)

    def __init__(self, **kwargs):
        kwargs.setdefault("kind", "card")
        kwargs.setdefault("bold", False)
        kwargs.setdefault("markup", True)
        super().__init__(**kwargs)
        self.halign = "left"
        self.valign = "middle"
        self.padding = (dp(14), 0)
        self.shorten = True
        self.shorten_from = "right"
        self.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(28), s[1])))


class RowList(BoxLayout):
    """Paged list of two-line rows. Row dicts come from ``row_entry``."""

    PAGE = 120
    ROW_H = 60

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(6), **kwargs)
        self.rows: list[dict] = []
        self.page = 0
        self.selected_key = None
        self._focus = None
        self._buttons: list[tuple[object, ListRow]] = []
        self.select_mode = False          # multi-select: tap rows to tick them
        self.checked: set = set()
        self.on_check = None              # callback(count) when ticks change
        self.on_mode = None               # callback(bool) when select mode turns on/off
        self.hold_to_select = True        # long-press a row = start multi-select with that row ticked
        self._row_buttons: dict = {}
        self.scroll = ScrollView(bar_width=dp(4), bar_color=(*ACCENT[:3], 0.8),
                                 bar_inactive_color=(*ACCENT[:3], 0.25))
        self.grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6), padding=(0, 0, dp(6), 0))
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        self.add_widget(self.scroll)
        self.pager = BoxLayout(size_hint_y=None, height=0, spacing=dp(6), opacity=0)
        self.pager.add_widget(make_btn("<", self._prev, 42, size_hint_x=0.22))
        self.info = make_label("", 13, MUTED)
        self.pager.add_widget(self.info)
        self.pager.add_widget(make_btn(">", self._next, 42, size_hint_x=0.22))
        self.add_widget(self.pager)

    def set_rows(self, rows: list[dict], keep_page: bool = False, focus_key=None) -> None:
        """Show rows. With focus_key the list opens on that row (right page + scrolled)."""
        self.rows = rows
        if not keep_page or self.page * self.PAGE >= max(1, len(rows)):
            self.page = 0
        self._focus = None
        if focus_key is not None:
            for position, row in enumerate(rows):
                if not row["header"] and row["key"] == focus_key:
                    self.page = position // self.PAGE
                    self._focus = focus_key
                    break
        self._render()

    # ---- multi-select
    @staticmethod
    def _row_text(row: dict, ticked: bool | None = None) -> str:
        sub = f"\n[size=12sp][color={MUTED_HEX}]{row['sub']}[/color][/size]" if row["sub"] else ""
        mark = "" if ticked is None else (f"[color={ACCENT_HEX}][b][X][/b][/color]  " if ticked else "[color=8a93a6][ ][/color]  ")
        return f"{mark}[b]{escape_markup(row['title'])}[/b]{sub}"

    def set_select_mode(self, on: bool, first=None) -> None:
        self.select_mode = bool(on)
        self.checked.clear()
        if on and first is not None:
            self.checked.add(first)
        self._render(keep_scroll=True)
        if self.on_mode:
            self.on_mode(self.select_mode)
        if self.on_check:
            self.on_check(len(self.checked))

    def _row_held(self, key) -> None:
        if not self.select_mode:
            self.set_select_mode(True, first=key)
        else:
            self.toggle_check(key)

    def _tap(self, button, fn) -> None:
        """Run ``fn`` on release, unless the release only ended a long-press."""
        if getattr(button, "_held", False):
            button._held = False
            return
        fn()

    def selectable_keys(self) -> list:
        return [r["key"] for r in self.rows if not r["header"] and r["key"] is not None]

    def check_all(self) -> None:
        self.checked = set(self.selectable_keys())
        self._refresh_ticks()

    def check_none(self) -> None:
        self.checked.clear()
        self._refresh_ticks()

    def toggle_check(self, key) -> None:
        if key in self.checked:
            self.checked.discard(key)
        else:
            self.checked.add(key)
        self._refresh_ticks(only=key)

    def _refresh_ticks(self, only=None) -> None:
        for key, (button, row) in self._row_buttons.items():
            if only is not None and key != only:
                continue
            on = key in self.checked
            button.text = self._row_text(row, on)
            button.kind = "selected" if on else "card"
        if self.on_check:
            self.on_check(len(self.checked))

    def _scroll_to_focus(self, *_args) -> None:
        for key, button in self._buttons:
            if key == self._focus and button.parent is not None:
                try:
                    self.scroll.scroll_to(button.parent, padding=dp(60), animate=False)
                except Exception:  # noqa: BLE001
                    pass
                break

    def mark_selected(self, key) -> None:
        self.selected_key = key
        for row_key, button in self._buttons:
            button.kind = "selected" if row_key == key and key is not None else "card"

    def _prev(self) -> None:
        if self.page > 0:
            self.page -= 1
            self._focus = None
            self._render()

    def _next(self) -> None:
        if (self.page + 1) * self.PAGE < len(self.rows):
            self.page += 1
            self._focus = None
            self._render()

    def _queue_thumb(self, holder, loader) -> None:
        """Decode thumbnails one by one in the background; never blocks or crashes the list."""
        self._thumb_gen = getattr(self, "_thumb_gen", 0)
        gen = self._thumb_gen
        queue = getattr(self, "_thumb_queue", None)
        if queue is None:
            queue = self._thumb_queue = []
        queue.append((gen, holder, loader))
        if getattr(self, "_thumb_running", False):
            return
        self._thumb_running = True

        def worker():
            while True:
                try:
                    g, hold, load = self._thumb_queue.pop(0)
                except IndexError:
                    self._thumb_running = False
                    return
                if g != self._thumb_gen:
                    continue
                try:
                    w, h, data = load()
                except Exception:  # noqa: BLE001
                    continue

                def put(_dt, hold=hold, w=w, h=h, data=data, g=g):
                    if g != self._thumb_gen:
                        return
                    tex = Texture.create(size=(w, h), colorfmt="rgba")
                    tex.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
                    tex.flip_vertical()
                    hold.texture = tex

                Clock.schedule_once(put, 0)

        threading.Thread(target=worker, daemon=True).start()

    def _render(self, keep_scroll: bool = False) -> None:
        self._thumb_gen = getattr(self, "_thumb_gen", 0) + 1
        self._thumb_queue = []
        saved_scroll = self.scroll.scroll_y
        self.grid.clear_widgets()
        self._buttons = []
        self._row_buttons = {}
        start = self.page * self.PAGE
        chunk = self.rows[start : start + self.PAGE]
        for row in chunk:
            if row["header"]:
                header = left_label(f"[b]{escape_markup(row['title'])}[/b]", 12, MUTED, height=30)
                header.valign = "bottom"
                self.grid.add_widget(header)
                continue
            line = BoxLayout(size_hint_y=None, height=dp(self.ROW_H), spacing=dp(6))
            if row.get("thumb") is not None:
                holder = Image(size_hint_x=None, width=dp(58), fit_mode="contain")
                line.add_widget(holder)
                self._queue_thumb(holder, row["thumb"])
            selected = row["key"] is not None and row["key"] == self.selected_key
            picking = self.select_mode and row["key"] is not None
            ticked = (row["key"] in self.checked) if picking else None
            button = ListRow(kind="selected" if (selected or ticked) else "card")
            button.text = self._row_text(row, ticked)
            if row["key"] is not None and self.hold_to_select:
                button.on_hold = lambda k=row["key"]: self._row_held(k)
            if picking:
                button.bind(on_release=lambda w, k=row["key"]: self._tap(w, lambda: self.toggle_check(k)))
                self._row_buttons[row["key"]] = (button, row)
            else:
                button.bind(on_release=lambda w, cb=row["cb"]: self._tap(w, lambda: cb() if cb else None))
            line.add_widget(button)
            if row.get("badge"):
                badge = Label(
                    text=escape_markup(str(row["badge"])), font_size=sp(11), bold=True,
                    color=ACCENT, size_hint_x=None, width=dp(104), halign="center",
                    valign="middle", shorten=True, shorten_from="right",
                )
                badge.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(6), s[1])))
                line.add_widget(badge)
            self._buttons.append((row["key"], button))
            if picking:  # in select mode the row is just a tick box
                self.grid.add_widget(line)
                continue
            if row.get("on_export") is not None:
                export = Btn(text="Export", font_size=sp(12), kind="ghost",
                             size_hint_x=None, width=dp(62))
                export.bind(on_release=lambda _w, cb=row["on_export"]: cb())
                line.add_widget(export)
            if row.get("on_import") is not None:
                imp = Btn(text="Import", font_size=sp(12), kind="ghost",
                          size_hint_x=None, width=dp(62))
                imp.bind(on_release=lambda _w, cb=row["on_import"]: cb())
                line.add_widget(imp)
            if row["star"] is not None:
                star = StarButton(active=bool(row["star"]), size_hint_x=None, width=dp(46))
                star.bind(
                    on_release=lambda w, handler=row["on_star"]: (
                        setattr(w, "active", not w.active),
                        handler(w.active) if handler else None,
                    )
                )
                line.add_widget(star)
            self.grid.add_widget(line)
        paged = len(self.rows) > self.PAGE
        self.pager.height = dp(42) if paged else 0
        self.pager.opacity = 1 if paged else 0
        self.info.text = (
            f"{start + 1}-{start + len(chunk)} / {len(self.rows)}" if chunk else "No results"
        )
        if not chunk:
            self.grid.add_widget(left_label("Nothing here.", 14, MUTED, height=40))
        if self._focus is not None:
            Clock.schedule_once(self._scroll_to_focus, 0.1)
        elif keep_scroll:
            Clock.schedule_once(lambda _dt, y=saved_scroll: setattr(self.scroll, "scroll_y", y), 0)
        else:
            self.scroll.scroll_y = 1


class IffBrowser(BoxLayout):
    """Search + category filter + grouped IFF list (shared by the OBB screen and the drawer)."""

    def __init__(self, app, on_pick, current=None, iff_only=False, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(8), **kwargs)
        self.app = app
        self.iff_only = iff_only  # side drawer: only entries that can really be opened
        self.on_pick = on_pick
        self.current = current
        state = app.browser_state  # remembered between screens so the list never "jumps"
        self.visible: list[int] = []
        top = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.search = make_input("Search IFF...")
        self.search.text = state.get("search", "")
        category = state.get("category", CATEGORY_CHOICES[0])
        self.category = Drop(
            text=category if category in CATEGORY_CHOICES else CATEGORY_CHOICES[0],
            values=CATEGORY_CHOICES, size_hint_x=0.5,
        )
        self.search.bind(text=lambda *_: self.refresh(self.current))
        self.category.bind(text=lambda *_: self.refresh(self.current))
        top.add_widget(self.search)
        top.add_widget(self.category)
        if iff_only:
            self.category.values = [c for c in CATEGORY_CHOICES if c != NON_IFF]
            if self.category.text == NON_IFF:
                self.category.text = CATEGORY_CHOICES[0]
        self.show_all = False if iff_only else bool(state.get("show_all", False))
        bar = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self.counter = left_label("", 12, MUTED)
        self.all_btn = make_btn("", self._toggle_all, 36, "ghost", font_size=sp(11), size_hint_x=0.42)
        self.sel_btn = make_btn("MULTI IFF", self._toggle_select, 36, "primary", font_size=sp(12), size_hint_x=0.34)
        bar.add_widget(self.counter)
        bar.add_widget(self.sel_btn)
        bar.add_widget(self.all_btn)
        self.list = RowList()
        self.list.on_check = self._checks_changed
        self.list.on_mode = self._select_ui
        # multi-select action bar (hidden until "Select" is pressed)
        self.sel_bar = BoxLayout(size_hint_y=None, height=0, spacing=dp(6), opacity=0)
        self.sel_all = make_btn("Check all", self.list.check_all, 46, "ghost", font_size=sp(12))
        self.sel_none = make_btn("Clear", self.list.check_none, 46, "ghost", font_size=sp(12))
        self.sel_exp = make_btn("Export (0)", self._export_checked, 46, "primary", font_size=sp(12))
        self.sel_imp = make_btn("Import (0)", self._import_checked, 46, "primary", font_size=sp(12))
        for w in (self.sel_all, self.sel_none, self.sel_exp, self.sel_imp):
            self.sel_bar.add_widget(w)
        self.add_widget(top)
        self.add_widget(bar)
        self.add_widget(self.sel_bar)
        self.add_widget(self.list)
        self.refresh(current)

    @staticmethod
    def _natural(text: str):
        return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", text)]

    def refresh(self, focus=None) -> None:
        choice = self.category.text
        self.app.browser_state.update(category=choice, search=self.search.text)
        rows = self.app.ws.obb_rows(
            # Favorites and any typed search also list non-openable entries, so a known name is never hidden.
            self.search.text,
            editable_only=not self.show_all and choice not in (NON_IFF, FAV_LABEL) and not self.search.text.strip(),
            category="All IFF" if choice in (FAV_LABEL, NON_IFF) else choice,
        )
        if choice == NON_IFF:
            rows = [r for r in rows if not r["editable"]]
        if not self.iff_only:
            self.app.browser_state["show_all"] = self.show_all
        for r in rows:  # non-IFF entries always live in their own group (audio has its own)
            if not r["editable"] and r["type"] not in ("ogg", "aac"):
                r["category"] = NON_IFF
        self.all_btn.text = "Showing: IFF + non-IFF" if self.show_all else "Showing: openable IFF"
        self.all_btn.kind = "primary" if self.show_all else "ghost"
        if choice == FAV_LABEL:
            rows = [r for r in rows if self.app.is_fav(r["label"])]
        order = {name: i for i, name in enumerate(GROUP_ORDER)}
        rows.sort(key=lambda r: (order.get(r["category"], 99), list_sort_key(r)))
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["category"]] = counts.get(r["category"], 0) + 1
        self.visible = [r["index"] for r in rows]
        self._rows_by_index = {r["index"]: r for r in rows}
        self.counter.text = f"{len(rows)} entries  |  " + "  ".join(
            f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:4])
        grouped = choice in (CATEGORY_CHOICES[0], FAV_LABEL)
        out: list[dict] = []
        last = None
        for r in rows:
            if grouped and r["category"] != last:
                last = r["category"]
                out.append(row_entry(f"{last.upper()}  ({counts[last]})", header=True))
            staged = f"  [color={ACCENT_HEX}]STAGED[/color]" if r["staged"] else ""
            out.append(
                row_entry(
                    r["label"],
                    f"#{r['index']}  |  " + (f"{r['kind']}  |  " if r.get("kind") else "") + f"{r['type']}  |  {core.readable_size(r['length'])}"
                    + (f"  |  auto name, hash {r['hash']}" if r.get("guessed") else "") + staged,
                    partial(self.on_pick, r["index"]) if r["editable"]
                    else partial(self.app.play_audio, r["index"], r["label"]) if r["type"] in ("ogg", "aac")
                    else partial(show_message, "Not an IFF",
                                 f"#{r['index']} is a '{r['type']}' entry, not an IFF. "
                                 "It cannot be opened here, but Export saves it as-is."),
                    key=r["index"],
                    star=self.app.is_fav(r["label"]),
                    on_star=partial(self._star, r["label"]),
                    on_export=partial(self.app.export_entry, r["index"]),
                    on_import=partial(self.app.import_entry, r["index"]) if r["editable"] else None,
                )
            )
        self.list.selected_key = self.current
        self.list.set_rows(out, focus_key=focus)

    # ---- multi-select (export / import many IFF at once)
    def _toggle_select(self) -> None:
        self.list.set_select_mode(not self.list.select_mode)

    def _select_ui(self, on: bool) -> None:
        self.sel_btn.text = "DONE" if on else "MULTI IFF"
        self.sel_btn.kind = "danger" if on else "primary"
        self.sel_bar.height = dp(46) if on else 0
        self.sel_bar.opacity = 1 if on else 0

    def _checks_changed(self, count: int) -> None:
        self.sel_exp.text = f"Export ({count})"
        self.counter.text = f"{count} naka-check" if count else self.counter.text
        editable = sum(1 for k in self.list.checked if self._rows_by_index.get(k, {}).get("editable"))
        self.sel_imp.text = f"Import ({editable})"

    def _export_checked(self) -> None:
        indices = sorted(self.list.checked)
        if not indices:
            show_message("Export", "Mag-tick muna ng kahit isang entry.", 0.3)
            return
        folder = output_root() / "iff"
        confirm(
            "Export selected",
            f"Export {len(indices)} entry(s) to:\n{folder}\n(audio entries are saved as .ogg / .aac)",
            lambda: self.app.run_bg(
                lambda: self.app.ws.export_entries(indices, folder, progress=self.app.set_status),
                lambda r: show_message("Exported", f"{r[0]} file(s) saved to:\n{r[1]}", 0.35),
                "Exporting ...",
            ),
        )

    def _import_checked(self) -> None:
        indices = sorted(k for k in self.list.checked if self._rows_by_index.get(k, {}).get("editable"))
        if not indices:
            show_message("Import", "Mag-tick muna ng IFF entry (hindi ma-import dito ang non-IFF).", 0.32)
            return

        def picked(folder: Path) -> None:
            def done(report: dict) -> None:
                self.refresh(self.current)
                lines = [f"Staged: {report['staged']} / {len(indices)}"]
                if report["missing"]:
                    lines.append(f"Walang file sa folder: {len(report['missing'])}  (e.g. {', '.join(report['missing'][:3])})")
                if report["failed"]:
                    lines.append(f"Failed: {len(report['failed'])}  (e.g. {report['failed'][0]})")
                lines.append("\nHindi pa nababago ang OBB hanggang 'Save OBB copy'.")
                show_message("Batch import", "\n".join(lines), 0.5)

            self.app.run_bg(
                lambda: self.app.ws.import_entries_from_folder(indices, folder, progress=self.app.set_status),
                done, "Importing selected ...")

        confirm(
            "Import selected",
            f"Pipili ka ng folder. Ia-match ang {len(indices)} naka-tick na entry sa mga .iff sa folder ayon sa "
            "FILE NAME (kapareho ng export). Dapat exact ang laki.",
            lambda: PickerPopup("Folder ng mga .iff", "dir", (), picked, start=output_root() / "iff").open(),
        )

    def _toggle_all(self) -> None:
        if self.iff_only:
            return
        self.show_all = not self.show_all
        self.refresh(self.current)

    def _star(self, label: str, active: bool) -> None:
        self.app.set_fav(label, active)
        if self.category.text == FAV_LABEL and not active:
            Clock.schedule_once(lambda _dt: self.refresh(self.current), 0)


class PickerPopup(Popup):
    """Simple file / folder chooser (internal storage and SD cards)."""

    def __init__(self, title: str, mode: str, extensions: tuple[str, ...], on_pick, start=None, extra=None):
        super().__init__(
            title=title, size_hint=(0.97, 0.95), auto_dismiss=False, background="",
            background_color=BAR, separator_color=ACCENT, title_color=TEXT, _anim_duration=0.3,
        )
        self.mode = mode
        self.on_pick = on_pick
        start = Path(start) if start else storage_root()
        if not start.exists():
            start = storage_root()

        def file_filter(_folder, name):
            return not extensions or name.lower().endswith(extensions)

        root = BoxLayout(orientation="vertical", spacing=dp(8))
        self.path_input = make_input("Path", 44)
        self.path_input.text = str(start)
        self.path_input.bind(on_text_validate=self._go_to_typed_path)
        root.add_widget(self.path_input)
        self.chooser = FileChooserListView(
            path=str(start),
            dirselect=(mode == "dir"),
            filters=[file_filter] if mode == "file" else [],
        )
        self.chooser.bind(path=self._path_changed)
        root.add_widget(self.chooser)
        self.warning = make_label("", 13, (1, 0.6, 0.4, 1), size_hint_y=None, height=0)
        root.add_widget(self.warning)
        roots_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        roots_bar.add_widget(make_btn("Up", self._go_up, 44))
        for label, folder in storage_roots():
            roots_bar.add_widget(make_btn(label, lambda f=folder: self._go(f), 44))
        root.add_widget(roots_bar)
        if extra:                                  # (label, callback): e.g. the system file picker (no permission needed)
            label, callback = extra
            root.add_widget(make_btn(label, lambda: (self.dismiss(), callback()), 46, "ghost"))
        buttons = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        buttons.add_widget(
            make_btn("Use this folder" if mode == "dir" else "Select", self._choose, 52, "primary")
        )
        buttons.add_widget(make_btn("Cancel", self.dismiss, 52))
        root.add_widget(buttons)
        self.content = root

    def _path_changed(self, _widget, value) -> None:
        self.path_input.text = value
        try:
            os.listdir(value)
            self.warning.text, self.warning.height = "", 0
        except OSError:
            self.warning.text = "Cannot read this folder (no permission)."
            self.warning.height = dp(28)

    def _go(self, folder: Path) -> None:
        if folder.is_dir():
            self.chooser.path = str(folder)
        else:
            self.warning.text = f"{folder} is not accessible."
            self.warning.height = dp(28)

    def _go_up(self) -> None:
        parent = Path(self.chooser.path).parent
        if parent.is_dir():
            self.chooser.path = str(parent)

    def _go_to_typed_path(self, *_args) -> None:
        candidate = Path(self.path_input.text.strip())
        if candidate.is_dir():
            self.chooser.path = str(candidate)

    def _choose(self) -> None:
        if self.mode == "dir":
            chosen = self.chooser.selection[0] if self.chooser.selection else self.chooser.path
            if not os.path.isdir(chosen):
                chosen = self.chooser.path
        else:
            if not self.chooser.selection:
                return
            chosen = self.chooser.selection[0]
        self.dismiss()
        self.on_pick(Path(chosen))


def show_message(title: str, text: str, height: float = 0.45) -> None:
    label = make_label(
        escape_markup(text), 14, halign="left", valign="top",
        text_size=(Window.width * 0.8, None), size_hint_y=None,
    )
    label.bind(texture_size=lambda w, size: setattr(w, "height", size[1]))
    scroll = ScrollView()
    holder = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(4))
    holder.bind(minimum_height=holder.setter("height"))
    holder.add_widget(label)
    scroll.add_widget(holder)
    box = BoxLayout(orientation="vertical", spacing=dp(8))
    box.add_widget(scroll)
    popup = make_popup(title, box, (0.92, height))
    box.add_widget(make_btn("OK", popup.dismiss, 48, "primary"))
    popup.open()


def confirm(title: str, text: str, on_yes) -> None:
    box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(4))
    box.add_widget(
        make_label(escape_markup(text), 14, halign="left", valign="middle",
                   text_size=(Window.width * 0.78, None))
    )
    row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
    popup = make_popup(title, box, (0.9, 0.42))
    row.add_widget(make_btn("Yes", lambda: (popup.dismiss(), on_yes()), 52, "primary"))
    row.add_widget(make_btn("No", popup.dismiss, 52))
    box.add_widget(row)
    popup.open()


# ---------------------------------------------------------------------- app
class _UI:
    """Helpers handed to workshop.py (avoids a circular import)."""

    make_btn = staticmethod(make_btn)
    make_label = staticmethod(make_label)
    left_label = staticmethod(left_label)
    make_popup = staticmethod(make_popup)
    make_input = staticmethod(make_input)
    show_message = staticmethod(show_message)
    confirm = staticmethod(confirm)
    friendly_error = staticmethod(friendly_error)
    output_root = staticmethod(output_root)
    PickerPopup = PickerPopup
    MUTED = MUTED
    TEXT = TEXT


UI = _UI()


class ToolApp(App):
    title = APP_TITLE
    roster_path = Path(".")
    roster_dirty = False

    def build(self):
        scratch = Path(self.user_data_dir) / "scratch"
        self.ws = Workspace(scratch)
        self.ws.owner = ownerlock.OwnerLock(Path(self.user_data_dir) / "owner_lock.json")
        self.ws.audio_names_file = Path(self.user_data_dir) / "audio_names.json"
        try:  # optional list of real IFF names (one per line) to name unknown entries
            from nba2k20 import direct_obb
            direct_obb.EXTRA_NAME_FILES.append(output_root() / "names.txt")
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        self.busy = False
        self.mode = "home"  # home | obb | iff
        self.current_tab = "Textures"
        self.selected_texture: int | None = None
        self.selected_mesh: int | None = None
        self.selected_resource: int | None = None
        self.fav_path = Path(self.user_data_dir) / "favorites.json"
        self.favs: set[str] = self._load_favs()
        self.browser_state: dict = {"category": CATEGORY_CHOICES[0], "search": ""}

        self.root_box = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        self.header = Card(kind="bar", size_hint_y=None, height=dp(54),
                           padding=(dp(14), 0, dp(6), 0), spacing=dp(6))
        self.header_title = left_label(APP_TITLE, 17, TEXT, bold=True)
        self.header.add_widget(self.header_title)
        self.body = BoxLayout(orientation="vertical", spacing=dp(8))
        self.status = left_label("Ready", 13, MUTED, height=30)
        self.status.shorten = True
        self.status.shorten_from = "right"
        self.root_box.add_widget(self.header)
        self.root_box.add_widget(ShimmerLine(animate=False))
        self.root_box.add_widget(self.body)
        self.root_box.add_widget(self.status)
        self.show_home()
        self.root_box.opacity = 0
        Clock.schedule_once(lambda _dt: Animation(opacity=1, d=0.2, t="out_cubic").start(self.root_box), 0.02)
        stage = FloatLayout()
        stage.add_widget(GlowBg(size_hint=(1, 1)))
        self.root_box.size_hint = (1, 1)
        stage.add_widget(self.root_box)
        return stage

    def _edge_to_edge(self):
        """v270: draw under the camera cut-out / status bar / navigation bar (no black strips left and top)."""
        try:
            from android.runnable import run_on_ui_thread  # type: ignore
            from jnius import autoclass  # type: ignore

            @run_on_ui_thread
            def go():
                try:
                    activity = autoclass("org.kivy.android.PythonActivity").mActivity
                    version = autoclass("android.os.Build$VERSION").SDK_INT
                    window = activity.getWindow()
                    if version >= 28:
                        params = window.getAttributes()
                        params.layoutInDisplayCutoutMode = 3 if version >= 30 else 1
                        window.setAttributes(params)
                    view = autoclass("android.view.View")
                    flags = (view.SYSTEM_UI_FLAG_LAYOUT_STABLE | view.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                             | view.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | view.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                             | view.SYSTEM_UI_FLAG_FULLSCREEN | view.SYSTEM_UI_FLAG_IMMERSIVE_STICKY)
                    window.getDecorView().setSystemUiVisibility(flags)
                except Exception:  # noqa: BLE001
                    traceback.print_exc()
            go()
        except Exception:  # noqa: BLE001  (not Android)
            pass

    def on_start(self):
        Clock.schedule_once(lambda _dt: self._edge_to_edge(), 0.3)
        Clock.schedule_once(lambda _dt: self._edge_to_edge(), 2.0)
        # a short delay so the activity is fully in the foreground before a Settings screen is launched
        Clock.schedule_once(lambda _dt: request_android_permissions() if not has_storage_access() else None, 0.8)
        try:  # the system answers the install session with an intent that comes back to this activity
            from android import activity as android_activity  # type: ignore

            android_activity.bind(on_new_intent=self._on_new_intent)
        except Exception:  # noqa: BLE001  (not Android)
            pass
        Clock.schedule_once(lambda _dt: self.check_updates(silent=True), 4.0)
        try:
            self._splash()
        except Exception:  # noqa: BLE001
            traceback.print_exc()

    def _splash(self) -> None:
        view = ModalView(size_hint=(1, 1), auto_dismiss=False, background="", background_color=(*BG[:3], 1),
                         overlay_color=(0, 0, 0, 0))
        stage = FloatLayout()
        splash_glow = GlowBg(size_hint=(1, 1))
        stage.add_widget(splash_glow)
        column = BoxLayout(orientation="vertical", spacing=dp(14), size_hint=(None, None), size=(dp(300), dp(260)),
                           pos_hint={"center_x": 0.5, "center_y": 0.5})
        logo = None
        if LOGO_HOME.exists():
            logo = Image(source=str(LOGO_HOME), size_hint=(1, None), height=dp(130), fit_mode="contain")
        else:
            logo = BrandLogo(size_hint=(1, None), height=dp(130))
        column.add_widget(logo)
        title = make_label("[b]DAVID2K TOOL[/b]", 30, ACCENT, size_hint_y=None, height=dp(44))
        sub = make_label("NBA 2K20  \u2022  OBB / ROSTER STUDIO", 12, MUTED, size_hint_y=None, height=dp(20))
        bar = ShimmerLine(size_hint_x=0.6, pos_hint={"center_x": 0.5})
        for w in (title, sub, bar):
            column.add_widget(w)
        stage.add_widget(column)
        view.add_widget(stage)
        column.opacity = 0
        view.open()
        title.font_size = sp(20)
        Animation(opacity=1, d=0.25, t="out_cubic").start(column)
        Animation(font_size=sp(30), d=0.3, t="out_cubic").start(title)
        if logo is not None:
            logo.height = dp(80)
            Animation(height=dp(130), d=0.3, t="out_cubic").start(logo)

        def leave(_dt):
            anim = Animation(opacity=0, d=0.2, t="in_cubic")
            def done(*_a):
                Animation.cancel_all(splash_glow)
                Animation.cancel_all(bar)
                view.dismiss()

            anim.bind(on_complete=done)
            anim.start(stage)

        Clock.schedule_once(leave, 0.6)
        Clock.schedule_once(lambda _dt: self._license_gate(), 0.9)

    # ------------------------------------------------------------- license key login (v193)
    def _license_gate(self) -> None:
        """Key login against the seller's panel (settings: assets/license.json).  Same flow as the panel's menus:
        copy the key, tap LOGIN WITH CLIPBOARD; a saved key logs in by itself; spinner + red error text."""
        try:
            from nba2k20 import license as lic
            self.lic = lic.LicenseClient(Path(self.user_data_dir))
        except Exception:  # noqa: BLE001  never lock the user out because the login code failed to load
            traceback.print_exc()
            return
        if self.lic.unlocked:
            return
        view = ModalView(size_hint=(1, 1), auto_dismiss=False, background="", background_color=(0.04, 0.04, 0.06, 0.97),
                         overlay_color=(0, 0, 0, 0))
        stage = FloatLayout()
        card = BoxLayout(orientation="vertical", size_hint=(None, None), size=(dp(340), dp(480)),
                         pos_hint={"center_x": 0.5, "center_y": 0.5})

        def paint(_w=None, _v=None) -> None:
            card.canvas.before.clear()
            with card.canvas.before:
                Color(0.11, 0.11, 0.14, 1)
                RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(20)])

        card.bind(pos=paint, size=paint)
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(110), padding=(dp(10), dp(18), dp(10), 0),
                         spacing=dp(4))

        def paint_head(_w=None, _v=None) -> None:
            # the blue header band lives in the header's OWN canvas, so it always follows the header (v198 fix:
            # it used to be drawn from the card's position and could land at the bottom of the card)
            head.canvas.before.clear()
            with head.canvas.before:
                Color(0.14, 0.37, 0.67, 1)
                RoundedRectangle(pos=head.pos, size=head.size, radius=[dp(20), dp(20), 0, 0])
                Color(0.22, 0.49, 0.78, 0.55)
                Rectangle(pos=(head.x + head.width / 2, head.y), size=(head.width / 2, head.height - dp(20)))

        head.bind(pos=paint_head, size=paint_head)
        head.add_widget(make_label("[b]DAVID2K TOOL[/b]", 26, (1, 1, 1, 1), size_hint_y=None, height=dp(40)))
        head.add_widget(make_label("Premium NBA 2K20 OBB / IFF Tool", 12, (0.78, 0.86, 1, 0.8), size_hint_y=None,
                                   height=dp(20)))
        card.add_widget(head)
        body = BoxLayout(orientation="vertical", padding=(dp(24), dp(14), dp(24), dp(14)), spacing=dp(10))
        message = make_label("Copy your license key and tap login", 13, (0.55, 0.55, 0.6, 1), size_hint_y=None,
                             height=dp(54))
        message.halign = "center"
        message.bind(width=lambda w, _v: setattr(w, "text_size", (w.width, None)))
        body.add_widget(message)
        detail = make_label("", 9, (0.5, 0.5, 0.56, 1), size_hint_y=None, height=dp(28))
        detail.halign = "center"
        detail.bind(width=lambda w, _v: setattr(w, "text_size", (w.width, None)))
        body.add_widget(detail)
        entry = make_input("o i-type dito ang key (optional)")
        entry.text = self.lic.saved_key()
        body.add_widget(entry)
        state = {"busy": False, "dots": 0, "tick": None}

        def tick(_dt) -> None:
            state["dots"] = (state["dots"] + 1) % 4
            message.text = "Authenticating" + "." * state["dots"]

        def finish(result) -> None:
            state["busy"] = False
            if state["tick"] is not None:
                state["tick"].cancel()
            if self.lic.unlocked:
                self.lic.remember_key(result.key)
                view.dismiss()
                where = " (offline)" if result.offline else ""
                self.set_status(f"License OK{where} - hanggang {result.exp_text or 'N/A'}")
            else:
                message.color = (1, 0.4, 0.4, 1)
                message.text = result.reason or "Invalid license key"
                detail.text = result.detail
                login_btn.disabled = False

        def go(*_a) -> None:
            if state["busy"]:
                return
            key = entry.text.strip()
            if not key:
                try:
                    from kivy.core.clipboard import Clipboard
                    key = (Clipboard.paste() or "").strip()
                except Exception:  # noqa: BLE001
                    key = ""
            if not key:
                message.color = (1, 0.4, 0.4, 1)
                message.text = "Walang key sa clipboard. I-copy ang key at pindutin ulit."
                return
            entry.text = key
            state["busy"] = True
            login_btn.disabled = True
            detail.text = ""
            message.color = (0.6, 0.6, 0.65, 1)
            state["tick"] = Clock.schedule_interval(tick, 0.35)

            def work() -> None:
                result = self.lic.login(key)
                Clock.schedule_once(lambda _dt: finish(result), 0)

            threading.Thread(target=work, daemon=True).start()

        login_btn = make_btn("LOGIN WITH CLIPBOARD", go, 62, "primary")
        body.add_widget(login_btn)
        body.add_widget(make_label("Your key will be read from clipboard", 11, (0.42, 0.42, 0.48, 1),
                                   size_hint_y=None, height=dp(20)))
        def copy_id() -> None:
            try:
                from kivy.core.clipboard import Clipboard
                Clipboard.copy(self.lic.device)
                detail.text = "Device ID na-copy (ibigay sa panel kung kailangan i-reset ang key)"
            except Exception:  # noqa: BLE001
                detail.text = f"Device ID: {self.lic.device}"

        body.add_widget(make_btn(f"Device ID: {self.lic.device}  (tap = copy)", copy_id, 30, "ghost"))
        body.add_widget(make_btn("EXIT", lambda: App.get_running_app().stop(), 38, "ghost"))
        card.add_widget(body)
        stage.add_widget(card)
        view.add_widget(stage)
        view.open()
        Clock.schedule_once(paint, 0)
        Clock.schedule_once(paint_head, 0)
        Clock.schedule_once(paint, 0.4)
        Clock.schedule_once(paint_head, 0.4)
        if entry.text:                       # a saved key: log in at once (works offline inside the grace period)
            go()

    def on_pause(self):
        # Required on Android: without this the app is killed when the
        # "All files access" settings screen opens.
        return True

    def on_resume(self):
        if self.mode == "home":
            self.show_home()

    def on_stop(self):
        self.ws.close()

    # ------------------------------------------------------------- helpers
    def _load_favs(self) -> set[str]:
        try:
            favs = set(json.loads(self.fav_path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            favs = set()
        # One-time: star the default IFFs (marker file so un-starring them sticks).
        marker = self.fav_path.with_name("favorites_defaults_v139.txt")
        try:
            if not marker.exists():
                known = {f.lower() for f in favs}
                favs.update(n for n in DEFAULT_FAVS if n.lower() not in known)
                self.fav_path.write_text(json.dumps(sorted(favs)), encoding="utf-8")
                marker.write_text("done", encoding="utf-8")
        except OSError:
            favs.update(DEFAULT_FAVS)
        return favs

    def auto_star_known(self) -> int:
        """Star the wanted IFFs found in the OBB that was just opened (once per name; un-starring sticks)."""
        seen_path = self.fav_path.with_name("favorites_auto_seen.json")
        try:
            seen = set(json.loads(seen_path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            seen = set()
        added = 0
        try:
            rows = self.ws.obb_rows("", editable_only=False)
        except Exception:  # noqa: BLE001
            return 0
        for r in rows:
            label = r["label"]
            low = label.lower()
            if low in seen or not low.startswith(AUTO_FAV_PREFIXES):
                continue
            seen.add(low)
            if not self.is_fav(label):
                self.favs.add(label)
                added += 1
        if added or seen:
            try:
                seen_path.write_text(json.dumps(sorted(seen)), encoding="utf-8")
                self.fav_path.write_text(json.dumps(sorted(self.favs)), encoding="utf-8")
            except OSError:
                pass
        return added

    def is_fav(self, label: str) -> bool:
        """Case-insensitive: the OBB name may show as NEWSCOREBUG.IFF or newscorebug.iff."""
        if label in self.favs:
            return True
        low = label.lower()
        return any(f.lower() == low for f in self.favs)

    def set_fav(self, label: str, active: bool) -> None:
        if active:
            self.favs.add(label)
        else:
            low = label.lower()
            self.favs = {f for f in self.favs if f.lower() != low}
        try:
            self.fav_path.write_text(json.dumps(sorted(self.favs)), encoding="utf-8")
        except OSError:
            pass

    def set_header(self, title: str, extra_widgets=()) -> None:
        """Every screen shows the David2k Tool brand on top and the context below."""
        self.header.clear_widgets()
        for widget in extra_widgets:
            self.header.add_widget(widget)
        if LOGO_SMALL.exists():
            self.header.add_widget(
                Image(source=str(LOGO_SMALL), size_hint=(None, None), size=(dp(40), dp(40)),
                      pos_hint={"center_y": 0.5})
            )
        column = BoxLayout(orientation="vertical", spacing=0)
        brand = left_label("DAVID2K TOOL", 12, ACCENT, bold=True)
        context = left_label(
            escape_markup(APP_SUBTITLE if title == APP_TITLE else title), 15, TEXT, bold=True
        )
        context.shorten = True
        context.shorten_from = "right"
        column.add_widget(brand)
        column.add_widget(context)
        self.header_title = context
        self.header.add_widget(column)

    _loading_detail = None

    def set_status(self, text: str) -> None:
        def apply(_dt) -> None:
            self.status.text = escape_markup(text)
            if self._loading_detail is not None:
                self._loading_detail.text = escape_markup(text)

        Clock.schedule_once(apply, 0)

    def _loading_open(self, label: str):
        """David2k Tool loading overlay: spinner + live progress text + timer (appears after 0.25 s)."""
        import time as _time
        state = {"view": None, "tick": None, "spin": None, "t0": _time.time()}

        def build(_dt):
            card = Card(kind="bar", orientation="vertical", padding=dp(18), spacing=dp(8))
            spin = ArcSpinner(size_hint=(None, None), size=(dp(58), dp(58)), pos_hint={"center_x": 0.5})
            brand = make_label("[b]DAVID2K TOOL[/b]", 12, ACCENT, size_hint_y=None, height=dp(16))
            text = wrap_label(escape_markup(label), 16, TEXT, halign="center")
            detail = wrap_label("", 12, MUTED, halign="center")
            clock = make_label("", 11, MUTED, size_hint_y=None, height=dp(16))
            bar = ShimmerLine(size_hint_y=None, height=dp(4))
            for w in (spin, brand, text, detail, bar, clock):
                card.add_widget(w)
            view = ModalView(size_hint=(0.8, None), height=dp(290), auto_dismiss=False, background="",
                             background_color=(0, 0, 0, 0), overlay_color=(0, 0, 0, 0.66))
            view.add_widget(card)
            state.update(view=view, spin=spin, detail=detail)
            self._loading_detail = detail

            def refresh(_dt2=0):
                secs = int(_time.time() - state["t0"])
                clock.text = f"{secs // 60}:{secs % 60:02d}"

            refresh()
            state["tick"] = Clock.schedule_interval(refresh, 0.5)
            view.open()

        state["show"] = Clock.schedule_once(build, 0.25)
        return state

    def _loading_close(self, state) -> None:
        for key in ("show", "tick"):
            event = state.get(key)
            if event is not None:
                event.cancel()
        if state.get("spin") is not None:
            state["spin"].stop()
        if state.get("view") is not None:
            state["view"].dismiss()
        self._loading_detail = None

    def run_bg(self, work, done=None, label: str = "Working ..."):
        if self.busy:
            self.set_status("Please wait for the current task to finish.")
            return
        self.busy = True
        self.set_status(label)
        overlay = self._loading_open(label)

        def target():
            try:
                result = work()
                error = None
            except Exception as exc:  # noqa: BLE001
                result, error = None, exc
                traceback.print_exc()
                log_error(label, exc)

            def finish(_dt):
                self.busy = False
                self._loading_close(overlay)
                if error is not None:
                    self.set_status("Failed")
                    show_message("Error", f"{friendly_error(error)}\n\nLog: {output_root() / 'error_log.txt'}")
                elif done is not None:
                    try:
                        done(result)
                    except Exception as exc:  # noqa: BLE001  a UI error must never close the app
                        traceback.print_exc()
                        log_error(f"{label} (show result)", exc)
                        self.set_status("Failed")
                        show_message("Error", f"{friendly_error(exc)}\n\nLog: {output_root() / 'error_log.txt'}")

            Clock.schedule_once(finish, 0)

        threading.Thread(target=target, daemon=True).start()

    def clear_body(self) -> None:
        """New screen: the old one is cleared and the new widgets fade in one by one."""
        self.body.clear_widgets()
        self._animate_screen()

    def _animate_screen(self) -> None:
        def go(_dt):
            stagger_in(self.body)
            fade_in(self.header, 0.0, 0.10)
        Clock.schedule_once(go, 0)

    # ---------------------------------------------------------------- home
    def show_home(self) -> None:
        self.mode = "home"
        self.set_header(APP_TITLE)
        self.clear_body()
        page = GridLayout(cols=1, size_hint_y=None, spacing=dp(10), padding=(0, 0, 0, dp(10)))
        page.bind(minimum_height=page.setter("height"))
        scroll = ScrollView(bar_width=dp(3), do_scroll_x=False)
        scroll.add_widget(page)
        self.body.add_widget(scroll)
        if not has_storage_access():
            warn = Card(kind="danger", orientation="vertical", size_hint_y=None, height=dp(130),
                        padding=dp(12), spacing=dp(8))
            warn.add_widget(make_label(
                "Storage access is OFF. Tap the button, allow 'All files access', then come back.\nWalang permission? Roster Editor > System file picker.",
                14, halign="center", valign="middle", text_size=(Window.width - dp(70), None)))
            warn.add_widget(make_btn("Grant file access", request_android_permissions, 46, "ghost"))
            page.add_widget(warn)
        if LOGO_HOME.exists():
            page.add_widget(
                Image(source=str(LOGO_HOME), size_hint_y=None, height=dp(120), fit_mode="contain")
            )
        else:
            page.add_widget(BrandLogo(size_hint_y=None, height=dp(120)))
        # ---- Bukod sa START menu: standalone quick-access card, sarili niyang section ----
        page.add_widget(MenuCard("2K14 port to 2K20", "Isang tap lang \u2022 Walang OBB kailangan \u2022 png####.iff -> png####.iff",
                                      "PORT", self.quick_port_14to20, primary=True))
        page.add_widget(left_label("[b]START[/b]", 12, MUTED, height=22))
        page.add_widget(MenuCard("Open OBB", "IFF list \u2022 Cyberface \u2022 Audio \u2022 Multi import / export",
                                      "OBB", self.pick_obb, primary=True))
        page.add_widget(MenuCard("Open IFF file", "Textures \u2022 Models \u2022 Resources",
                                      "IFF", self.pick_iff))
        page.add_widget(MenuCard("Open OBJ + PNG", "Face PNG \u2022 Beard \u2022 Hair \u2022 3D head",
                                      "OBJ", self.pick_face_png))
        page.add_widget(MenuCard("CYBERFACE EDITOR / OBJ", "OBJ head \u2022 Part lock \u2022 Grab \u2022 Inflate \u2022 Axis \u2022 Ref photos",
                                      "SCP", self.head_sculpt))
        page.add_widget(MenuCard("MESH TOOL", "3D viewport + UV \u2022 Transfer shape / UV \u2022 Soft Mod \u2022 menus",
                                      "MSH", self.mesh_tool, primary=True))
        page.add_widget(MenuCard("Roster Editor", "Players \u2022 Names \u2022 Ratings \u2022 Portraits",
                                      "RST", self.pick_roster))
        page.add_widget(MenuCard("2K14 Converter", "2K14 cyberface IFF \u2022 Face > 2K20 \u2022 Head shape fit",
                                      "2K14", self.show_convert14))
        owner = getattr(self.ws, "owner", None)
        owner_sub = ("OFF - set your name + passphrase" if not (owner and owner.enabled) else
                     f"{owner.name} \u2022 {'UNLOCKED' if owner.unlocked else 'LOCKED'}")
        page.add_widget(MenuCard("Scoreboard layout", "newscorebug.iff \u2022 Position / size / scale (experimental)",
                                      "SB", self.show_scoreboard))
        page.add_widget(MenuCard("Court / Scoreboard SCENE", "PC-style IFF / .SCNE \u2022 Export OBJ \u2022 Edit in Blender \u2022 Import back",
                                      "SCN", self.scene_tools))
        page.add_widget(MenuCard("Owner lock", f"Stamp your edited IFFs \u2022 {owner_sub}",
                                      "KEY", self.show_owner_lock))
        page.add_widget(MenuCard("Check for updates", f"Installed: {VERSION_NAME}  (build {VERSION_CODE})",
                                      "UPD", lambda: self.check_updates(silent=False)))
        info = Card(orientation="vertical", padding=dp(12), spacing=dp(2))
        info.add_widget(make_label(
            f"Outputs: {escape_markup(str(output_root()))}", 11, MUTED, halign="center", valign="middle",
            text_size=(Window.width - dp(70), None)))
        etc2 = core.native_available("etcpak")
        info.add_widget(make_label(
            "ETC2 import: [color=6fd16f]FAST (etcpak)[/color]" if etc2 else
            "ETC2 import: [color=6fd16f]ON[/color] (built-in encoder, up to 4096x4096 - malaki = mabagal)",
            11, MUTED, halign="center", valign="middle", text_size=(Window.width - dp(70), None)))
        info.add_widget(make_label(
            "Tip: copy the OBB out of Android/obb first (Android 11+ blocks that folder).",
            11, MUTED, halign="center", valign="middle", text_size=(Window.width - dp(70), None)))
        info.size_hint_y = None
        info.height = dp(86)
        page.add_widget(info)
        page.add_widget(MenuCard("Search IFF folder", "Nested folders • exact / partial filename • titlecard / scorebug",
                                      "FIND", self.pick_iff_folder_search))

    # ------------------------------------------------------------ auto update
    def _on_new_intent(self, intent) -> None:
        try:
            message = android_install.handle_intent(intent)
        except Exception as exc:  # noqa: BLE001
            log_error("update intent", exc)
            return
        if message:
            Clock.schedule_once(lambda _dt: show_message("Update", message, 0.3), 0)

    def check_updates(self, silent: bool = True) -> None:
        url = update_url()
        if not url:
            if not silent:
                show_message(
                    "Auto update",
                    "Wala pang update URL.\n\nGumawa ng file:\n"
                    f"{output_root() / 'update_url.txt'}\n"
                    "at ilagay sa loob ang HTTPS link ng manifest (.json) mo. Format ng manifest ay nasa README.",
                    0.5)
            return
        if self.busy:
            return

        def work():
            return updater.check(url, VERSION_CODE)

        def done(info) -> None:
            self._update_found(info, silent)

        if silent:  # no loading overlay for the quiet check at start-up
            def quiet():
                try:
                    info = work()
                except Exception:  # noqa: BLE001
                    return
                Clock.schedule_once(lambda _dt: self._update_found(info, True), 0)

            threading.Thread(target=quiet, daemon=True).start()
        else:
            self.run_bg(work, done, "Checking for updates ...")

    def _update_found(self, info, silent: bool) -> None:
        if not info.available:
            if not silent:
                show_message("Auto update", f"Updated na ang app ({VERSION_NAME}).", 0.28)
            return
        notes = info.changelog.strip() or "-"
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(wrap_label(
            f"[b]Bagong version: {escape_markup(info.version_name or str(info.version_code))}[/b]\n"
            f"Installed: {VERSION_NAME}\n\n{escape_markup(notes)}", 14, TEXT))
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        popup = make_popup("UPDATE AVAILABLE", box, (0.92, 0.6), auto_dismiss=not info.required)
        if not info.required:
            row.add_widget(make_btn("Later", popup.dismiss, 52))
        row.add_widget(make_btn("Update now", lambda: (popup.dismiss(), self._do_update(info)), 52, "primary"))
        box.add_widget(row)
        popup.open()

    def _do_update(self, info) -> None:
        if not android_install.available():
            show_message("Auto update", "Ang install ay gumagana lang sa Android app.", 0.3)
            return
        try:
            if not android_install.can_request_installs():
                android_install.open_unknown_sources_settings()
                show_message("Auto update",
                             "I-allow ang 'Install unknown apps' para sa David2k Tool, bumalik dito at pindutin "
                             "ulit ang Check for updates.", 0.4)
                return
        except Exception as exc:  # noqa: BLE001
            log_error("update permission", exc)
        folder = output_root() / "updates"

        def work():
            apk = updater.download_and_verify(info, folder, progress=self.set_status)
            self.set_status("Installing update ...")
            android_install.install_apk(apk)
            return apk

        self.run_bg(work, lambda _apk: self.set_status("Confirm the install on the Android screen"),
                    "Downloading update ...")

    def pick_obb(self) -> None:
        PickerPopup("Choose main/patch OBB", "file", (".obb",), self.load_obb).open()

    def pick_iff(self) -> None:
        PickerPopup("Choose IFF file", "file", (".iff",), self.load_iff).open()

    def pick_iff_folder_search(self) -> None:
        """Index filenames recursively off the UI thread, without parsing every IFF."""
        def picked(folder: Path) -> None:
            def scan():
                errors: list[str] = []
                files = core.find_iff_files(folder, errors=errors)
                return folder.resolve(), files, errors

            self.run_bg(
                scan,
                lambda result: self._show_iff_folder_results(*result),
                "Searching nested IFF files ...",
            )

        PickerPopup(
            "Choose game-resource folder", "dir", (), picked, start=storage_root()
        ).open()

    def _show_iff_folder_results(self, folder: Path, files: list[Path], errors: list[str]) -> None:
        content = BoxLayout(orientation="vertical", spacing=dp(7), padding=dp(8))
        content.add_widget(wrap_label(
            f"Scanned {escape_markup(str(folder))} recursively. Search matches the filename or relative path; "
            "select a result to open it.", 12, MUTED))
        if errors:
            content.add_widget(wrap_label(
                f"[color=ff9a70]Partial scan: {len(errors)} folder/file access error(s). "
                f"Example: {escape_markup(errors[0])}[/color]", 11, TEXT))
        query = make_input("Search filename or subfolder ...", 44)
        content.add_widget(query)
        status = left_label("", 11, MUTED, height=dp(24))
        content.add_widget(status)
        scroll = ScrollView()
        results = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
        results.bind(minimum_height=results.setter("height"))
        scroll.add_widget(results)
        content.add_widget(scroll)
        close_row = BoxLayout(size_hint_y=None, height=dp(48))
        popup = make_popup("SEARCH IFF FILES", content, (0.96, 0.90))
        close_row.add_widget(make_btn("Close", popup.dismiss, 48))
        content.add_widget(close_row)

        indexed = [(path, str(path.relative_to(folder)).casefold(), path.name.casefold())
                   for path in files]
        state = {"generation": 0, "debounce": None}

        def draw(generation: int, matches: list[Path], query_text: str) -> None:
            if generation != state["generation"]:
                return
            results.clear_widgets()
            shown = matches[:100]
            for path in shown:
                relative = str(path.relative_to(folder))
                results.add_widget(make_btn(
                    escape_markup(relative),
                    lambda *_, p=path: (popup.dismiss(), self.load_iff(p)),
                    42, "ghost", font_size=sp(11),
                ))
            status.text = (
                f"{len(matches):,} match(es) for {query_text!r}; showing first {len(shown)}"
                if matches else "No matching IFF files. Try a partial name or another folder."
            )

        def search_worker(generation: int, query_text: str) -> None:
            needle = query_text.strip().casefold()
            compact = core.normalize_search_text(query_text)
            matches = [path for path, relative, name in indexed
                       if not needle or needle in relative or needle in name
                       or (compact and (compact in core.normalize_search_text(relative)
                                        or compact in core.normalize_search_text(name)))]
            Clock.schedule_once(lambda _dt: draw(generation, matches, query_text), 0)

        def search_changed(*_args) -> None:
            state["generation"] += 1
            generation = state["generation"]
            event = state.get("debounce")
            if event is not None:
                event.cancel()
            query_text = query.text
            state["debounce"] = Clock.schedule_once(
                lambda _dt: threading.Thread(
                    target=search_worker, args=(generation, query_text), daemon=True
                ).start(),
                0.18,
            )

        query.bind(text=search_changed)
        popup.bind(on_dismiss=lambda *_: state.__setitem__("generation", state["generation"] + 1))
        search_changed()
        popup.open()

    # --------------------------------------------------------------- roster
    # Separate from the OBB / IFF flow: its own screens, its own state.
    def _roster_bridge(self):
        # Pure Python roster engine (nba2k20/roster_core.py) - no Java / pyjnius needed.
        bridge = getattr(self, "_roster_bridge_cls", None)
        if bridge is None:
            from nba2k20.roster_core import RosterBridge
            bridge = RosterBridge
            self._roster_bridge_cls = bridge
        try:                       # v222: the year the GAME counts ages from (set with GAME YEAR in the sync menu)
            from nba2k20 import online_ratings
            if online_ratings.OPTIONS_PATH is None:
                online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
            bridge.AGE_REF_YEAR = online_ratings.load_age_ref_year()
        except Exception:  # noqa: BLE001
            pass
        return bridge

    @staticmethod
    def _rows(text, cols: int = 0) -> list:
        rows = [line.split("\t") for line in str(text or "").split("\n") if line.strip()]
        if cols:  # pad short rows, trim long ones, so tuple-unpacking always matches
            rows = [(r + [""] * cols)[:cols] for r in rows]
        return rows

    def pick_roster(self) -> None:
        try:
            self._roster_bridge()  # imports the roster engine once
        except Exception as exc:  # noqa: BLE001
            log_error("roster engine import", exc)
            show_message("Roster Editor", "Could not start the roster engine:\n" + friendly_error(exc))
            return
        extra = None
        try:
            from nba2k20 import saf
            if saf.available():
                extra = ("System file picker (no permission needed)", self.pick_roster_saf)
        except Exception:  # noqa: BLE001
            traceback.print_exc()

        def chosen(path: Path) -> None:
            self.roster_via_saf = False
            self.load_roster(path)

        PickerPopup("Choose roster file", "file", (), chosen, extra=extra).open()

    roster_via_saf = False

    def pick_roster_saf(self) -> None:
        """Android 10-14 without 'All files access': the system picker copies the roster into the app, we edit that copy
        and hand the edited file back through the system 'save as' dialog."""
        from nba2k20 import saf
        dest = Path(self.user_data_dir) / "picked"

        def got(path, name) -> None:
            def ui(_dt) -> None:
                if path is None:
                    if name:
                        show_message("Roster Editor", "Could not open the file:\n" + str(name))
                    return
                self.roster_via_saf = True
                self.load_roster(Path(path))
            Clock.schedule_once(ui, 0)

        try:
            saf.pick_file(dest, got)
        except Exception as exc:  # noqa: BLE001
            log_error("system picker", exc)
            show_message("Roster Editor", "The system file picker is not available:\n" + friendly_error(exc))

    def _saf_export(self, path) -> None:
        """Hand the edited roster to the system 'save as' dialog (Download, Documents, SD card ...)."""
        from nba2k20 import saf
        path = Path(path)

        def result(ok: bool, message: str) -> None:
            Clock.schedule_once(lambda _dt: show_message("Roster export" if ok else "Roster export - not saved", message, 0.4), 0)

        try:
            saf.export_file(path, path.name, result)
        except Exception as exc:  # noqa: BLE001
            log_error("export roster", exc)
            show_message("Roster export", "Could not open the save dialog:\n%s\nThe edited roster is at:\n%s" % (friendly_error(exc), path))

    def load_roster(self, path: Path) -> None:
        def work():
            return str(self._roster_bridge().load(str(path)))

        def done(summary: str) -> None:
            self.roster_path = Path(path)
            self.roster_dirty = False
            self.set_status(summary)
            try:
                self.show_roster_teams()
            except Exception as exc:  # noqa: BLE001
                log_error("open roster screen", exc)
                show_message("Roster Error", friendly_error(exc))

        self.run_bg(work, done, f"Reading {Path(path).name} ...")

    def _roster_back_bar(self, back, back_text: str = "Back") -> BoxLayout:
        bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        bar.add_widget(make_btn(back_text, back, 52))
        return bar

    def _roster_list(self, rows) -> ScrollView:
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter("height"))
        for text, callback in rows:
            grid.add_widget(make_btn(text, callback, 54))
        scroll = ScrollView()
        scroll.add_widget(grid)
        return scroll

    def _show_roster_diagnostics(self, team_slot: int = -1) -> None:
        try:
            report = self._roster_bridge().diagnostics(team_slot)
            show_message("Roster diagnostics", report, 0.82)
        except Exception as exc:  # noqa: BLE001
            log_error("roster diagnostics", exc)
            show_message("Roster diagnostics", friendly_error(exc))

    def show_roster_teams(self) -> None:
        try:
            self.mode = "roster"
            self.set_header(f"Roster  -  {self.roster_path.name}" + ("  (edited)" if self.roster_dirty else ""))
            self.clear_body()
            bridge = self._roster_bridge()
            rows = []
            for slot, abbr, name, count in self._rows(bridge.teams(), 4):
                label = f"{abbr}  -  {name}  ({count})" if abbr else f"{name}  ({count})"
                rows.append((label, partial(self.show_roster_players, int(slot), label)))
            rows.append(("All players", partial(self.show_roster_players, -1, "All players")))
            self.body.add_widget(self._roster_list(rows))
            bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
            bar.add_widget(make_btn("Save roster copy", self.save_roster_copy, 52, "primary"))
            bar.add_widget(make_btn("SYNC ALL TEAMS", self._sync_all_teams_ask, 52, "primary"))
            bar.add_widget(make_btn("Roster diagnostics", partial(self._show_roster_diagnostics, -1), 52))
            bar.add_widget(make_btn("Close roster", self.show_home, 52))
            self.body.add_widget(bar)
        except Exception as exc:  # noqa: BLE001
            log_error("list roster teams", exc)
            show_message("Roster Error", friendly_error(exc))

    _RP_PAGE = 60  # rows drawn per page (keeps the phone UI snappy)

    def show_roster_players(self, team_slot: int, title: str, keep_query: bool = False) -> None:
        try:
            self.set_header(title)
            self.clear_body()
            bridge = self._roster_bridge()
            if not keep_query:
                self._rp_query, self._rp_sort, self._rp_desc = "", "name", False
            players = [(int(s), n, j, c) for s, n, j, c in self._rows(bridge.players(team_slot), 4)]
            lowered = [(p, p[1].lower()) for p in players]
            box = self.body
            state = {"limit": self._RP_PAGE, "event": None}

            search = make_input("Search player name, CF ID, jersey", 46)
            search.text = getattr(self, "_rp_query", "")
            box.add_widget(search)

            sort_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            holder = BoxLayout(orientation="vertical")
            info = left_label("", 12, MUTED, height=22)
            sort_buttons = {}

            ovr_cache: dict = {}

            def ovr_of(slot: int) -> int:
                if slot not in ovr_cache:
                    try:
                        ovr_cache[slot] = bridge.ovr(slot)
                    except Exception:  # noqa: BLE001
                        ovr_cache[slot] = 0
                return ovr_cache[slot]

            def render(*_args) -> None:
                self._rp_query = search.text.strip()
                q = self._rp_query.lower()
                rows = [p for p, low in lowered if not q or q in low or str(p[3]).startswith(q) or str(p[2]) == q]
                key = self._rp_sort
                if key == "name":
                    rows.sort(key=lambda r: r[1].lower())
                elif key == "jersey":
                    rows.sort(key=lambda r: int(r[2]) if str(r[2]).lstrip("-").isdigit() else 999)
                elif key == "cf":
                    rows.sort(key=lambda r: int(r[3]) if str(r[3]).isdigit() else 10 ** 9)
                else:
                    rows.sort(key=lambda r: ovr_of(r[0]))
                if self._rp_desc:
                    rows.reverse()
                shown = rows[: state["limit"]]
                grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(6))
                grid.bind(minimum_height=grid.setter("height"))
                if team_slot >= 0:
                    grid.add_widget(make_btn("MANUAL OVR - WHOLE TEAM",
                                             partial(self.edit_team_ovr, team_slot, title), 50, "primary"))
                for slot, name, jersey, cf in shown:
                    grid.add_widget(PlayerRow(jersey, name, f"CF {cf}", ovr_of(slot),
                                              partial(self._open_rp_player, slot, name, team_slot, title)))
                if len(rows) > len(shown):
                    def more() -> None:
                        state["limit"] += self._RP_PAGE
                        render()
                    grid.add_widget(make_btn(f"Show more  ({len(rows) - len(shown)} left)", more, 48))
                scroll = ScrollView()
                scroll.add_widget(grid)
                holder.clear_widgets()
                holder.add_widget(scroll)
                info.text = f"{len(rows)} of {len(players)} players"
                for k, text in (("name", "Name"), ("jersey", "#"), ("ovr", "OVR"), ("cf", "CF")):
                    arrow = (" (high-low)" if self._rp_desc else " (low-high)") if self._rp_sort == k else ""
                    sort_buttons[k].text = text + arrow

            def set_sort(key: str) -> None:
                if self._rp_sort == key:
                    self._rp_desc = not self._rp_desc
                else:
                    self._rp_sort, self._rp_desc = key, key == "ovr"
                state["limit"] = self._RP_PAGE
                render()

            def on_text(*_args) -> None:  # debounce: wait for a typing pause
                if state["event"] is not None:
                    state["event"].cancel()
                state["limit"] = self._RP_PAGE
                state["event"] = Clock.schedule_once(render, 0.25)

            for key, text in (("name", "Name"), ("jersey", "#"), ("ovr", "OVR"), ("cf", "CF")):
                btn = make_btn(text, partial(set_sort, key), 44)
                sort_buttons[key] = btn
                sort_bar.add_widget(btn)
            box.add_widget(sort_bar)
            box.add_widget(info)
            box.add_widget(holder)
            bar = self._roster_back_bar(self.show_roster_teams)
            bar.add_widget(make_btn("Diagnostics", partial(self._show_roster_diagnostics, team_slot), 52))
            if team_slot >= 0:
                bar.add_widget(make_btn("Sync team online", partial(self.sync_online_team, team_slot, title), 52, "primary"))
            box.add_widget(bar)
            search.bind(text=on_text)
            render()
        except Exception as exc:  # noqa: BLE001
            log_error("list roster players", exc)
            show_message("Roster Error", friendly_error(exc))

    def _open_rp_player(self, slot, name, team_slot, title) -> None:
        self._rp_return = True
        self.quick_preview(slot, name, team_slot, title)

    def _ensure_obb(self, then) -> None:
        """Run ``then`` once an OBB is open for face images. Reuses the last OBB, else asks for one."""
        if getattr(self.ws, "session", None) is not None:
            then()
            return
        memo = output_root() / "portrait_obb.txt"

        def open_path(path: Path, remember: bool = True) -> None:
            def done(_info) -> None:
                if remember:
                    try:
                        memo.write_text(str(path), encoding="utf-8")
                    except OSError:
                        pass
                self._cf_map_cache = None
                then()
            self.run_bg(lambda: self.ws.open_obb(path), done, f"Reading {path.name} ...")

        try:
            last = Path(memo.read_text(encoding="utf-8").strip()) if memo.is_file() else None
        except OSError:
            last = None
        if last is not None and last.is_file():
            open_path(last, remember=False)
            return
        PickerPopup("Piliin ang game OBB (para sa larawan ng mukha)", "file", (".obb",), open_path).open()

    def _cf_index_map(self) -> dict:
        """CF number -> OBB entry index for the opened OBB (cached per OBB session)."""
        session = getattr(self.ws, "session", None)
        if session is None:
            return {}
        cache = getattr(self, "_cf_map_cache", None)
        if cache is not None and cache[0] is session:
            return cache[1]
        found = {}
        try:
            for r in self.ws.obb_rows("", category="Cyberface"):
                hit = re.search(r"(\d+)", str(r["label"]))
                if hit:
                    found[int(hit.group(1))] = r["index"]
        except Exception as exc:  # noqa: BLE001
            log_error("cf map", exc)
        self._cf_map_cache = (session, found)
        return found

    def quick_preview(self, player_slot, name, team_slot, title) -> None:
        """Small card: portrait image, name, team, #, OVR, portrait status + Portrait / Edit player / Close."""
        try:
            info = self._roster_bridge().playerInfo(player_slot).split("\t")
            pname, team, jersey, ovr, cf, portrait = (info + [""] * 6)[:6]
        except Exception as exc:  # noqa: BLE001
            log_error("quick preview", exc)
            show_message("Roster Error", friendly_error(exc))
            return
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        image = Image(fit_mode="contain", size_hint_y=None, height=0)
        box.add_widget(image)
        box.add_widget(left_label(f"[b]{escape_markup(pname)}[/b]", 20, height=30))
        box.add_widget(left_label(escape_markup(team), 14, MUTED, height=22))
        box.add_widget(left_label(f"#{jersey}  \u2022  OVR {ovr if str(ovr) != '0' else '--'}", 14, height=22))
        status = left_label("PORTRAIT: checking...", 13, MUTED, height=24)
        box.add_widget(status)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        popup = make_popup("PLAYER QUICK PREVIEW", box, (0.92, 0.72))

        def set_status(text: str, ready: bool) -> None:
            status.text = ("[color=4cd964]" if ready else "[color=ff9f43]") + escape_markup(text) + "[/color]"

        index = self._cf_index_map().get(int(cf or 0)) if getattr(self.ws, "session", None) is not None else None
        if getattr(self.ws, "session", None) is None:
            set_status("PORTRAIT: NOT SET", False)
        elif index is None:
            set_status("PORTRAIT: NOT SET", False)
        else:
            def load():
                try:
                    w, h, data = self.ws.cyberface_thumb(index, (256, 256))
                except Exception:  # noqa: BLE001
                    Clock.schedule_once(lambda _dt: set_status("PORTRAIT: NOT SET", False), 0)
                    return

                def put(_dt):
                    tex = Texture.create(size=(w, h), colorfmt="rgba")
                    tex.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
                    tex.flip_vertical()
                    image.texture = tex
                    image.height = dp(230)
                    set_status("PORTRAIT: READY", True)

                Clock.schedule_once(put, 0)

            threading.Thread(target=load, daemon=True).start()

        def portrait() -> None:
            sub_box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
            sub_box.add_widget(wrap_label(
                f"Portrait ni [b]{escape_markup(pname)}[/b]  (CF {escape_markup(str(cf))})\n"
                "Export / Import: ang sariling portrait lang ng player na ito ang puwedeng palitan.",
                13, TEXT))
            sub = make_popup("PORTRAIT", sub_box, (0.92, 0.5))
            own = (cf, pname, player_slot, name, team_slot, title)

            def row(*items) -> BoxLayout:
                line = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
                for text, fn, kind in items:
                    line.add_widget(make_btn(text, fn, 50, kind))
                return line

            def preview() -> None:
                sub.dismiss()
                popup.dismiss()
                self._ensure_obb(lambda: self.portrait_preview(cf, pname, player_slot, name, team_slot, title))

            def update() -> None:
                # reload the face list from the OBB, then reopen the card: the player's portrait shows automatically
                sub.dismiss()
                popup.dismiss()
                self._cf_map_cache = None
                self.set_status("Loading portrait ...")
                self._ensure_obb(lambda: self.quick_preview(player_slot, name, team_slot, title))

            def export_img() -> None:
                self._ensure_obb(lambda: self.portrait_export(cf, pname))

            def import_img() -> None:
                sub.dismiss()
                self._ensure_obb(lambda: self.portrait_import(*own, parent=popup))

            def save_obb() -> None:
                self._ensure_obb(self.save_obb_copy)

            sub_box.add_widget(row(("Export image", export_img, "ghost"), ("Import image", import_img, "primary")))
            sub_box.add_widget(row(("Preview", preview, "ghost"), ("Update", update, "ghost")))
            sub_box.add_widget(row(("Save OBB", save_obb, "ghost"), ("Close", sub.dismiss, "ghost")))
            sub.open()

        def edit() -> None:
            popup.dismiss()
            self.show_roster_player(player_slot, pname, team_slot, title)

        buttons.add_widget(make_btn("Portrait", portrait, 50))
        buttons.add_widget(make_btn("Edit player", edit, 50, "primary"))
        buttons.add_widget(make_btn("Close", popup.dismiss, 50))
        box.add_widget(buttons)
        popup.open()

    def _portrait_index(self, cf, pname):
        """OBB entry of THIS player's own portrait (never another player's)."""
        try:
            number = int(cf or 0)
        except (TypeError, ValueError):
            number = 0
        index = self._cf_index_map().get(number)
        if index is None:
            show_message("Portrait", f"Walang portrait file (CF {cf}) para kay {pname} sa OBB na ito.", 0.35)
        return index

    def portrait_export(self, cf, pname) -> None:
        index = self._portrait_index(cf, pname)
        if index is None:
            return
        safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(pname)).strip("_") or "player"
        target = output_root() / "portrait" / f"{safe}_CF{cf}.png"
        self.run_bg(
            lambda: self.ws.cyberface_export_png(index, target),
            lambda path: show_message("Portrait exported", f"Na-save ang portrait ni {pname}:\n{path}", 0.4),
            "Exporting portrait ...",
        )

    def portrait_import(self, cf, pname, player_slot, name, team_slot, title, parent=None) -> None:
        index = self._portrait_index(cf, pname)
        if index is None:
            return
        used = set()
        shared = 0
        try:
            for r in self._rows(self._roster_bridge().players(-1), 4):
                text = str(r[3]).strip()
                if text.isdigit():
                    used.add(int(text))
                    if int(text) == int(cf):
                        shared += 1
        except Exception:  # noqa: BLE001
            pass

        def start(target_index: int, new_cf=None) -> None:
            def picked(path: Path) -> None:
                def work():
                    report = self.ws.cyberface_auto_png(target_index, path)
                    if new_cf is not None:   # give THIS player the free id; the others keep theirs
                        self._roster_bridge().setField(player_slot, "cyberface", new_cf)
                    return report

                def done(report) -> None:
                    resized = report.get("resized_from")
                    self._cf_map_cache = None
                    if new_cf is not None:
                        self.roster_dirty = True
                    if parent is not None:
                        parent.dismiss()
                    self.set_status("Portrait staged - tap Portrait > Save OBB")
                    show_message(
                        "Portrait imported",
                        f"Naka-stage na ang bagong portrait ni {pname}"
                        + (f" (bagong CFID {new_cf})" if new_cf is not None else "") + ".\n"
                        + (f"Auto-resized from {resized[0]}x{resized[1]}.\n" if resized else "")
                        + "\nHindi pa nababago ang OBB: pindutin ang Portrait > Save OBB"
                        + (" at i-save din ang roster." if new_cf is not None else "."),
                        0.45,
                    )
                    self.quick_preview(player_slot, name, team_slot, title)

                self.run_bg(work, done, "Importing portrait ...")

            PickerPopup(f"Image para kay {pname}", "file", (".png", ".jpg", ".jpeg", ".webp"), picked,
                        start=output_root() / "portrait").open()

        if shared <= 1:
            start(index)
            return

        # several players share this face: ask whether to give this player their own free custom CFID
        cmap = self._cf_index_map()
        free = cfalloc.free_custom_slots(cmap.keys(), used)
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(wrap_label(
            f"{shared} players ang gumagamit ng CF {cf}. Kapag pinalitan ang mukha, lahat sila magbabago.\n"
            + (f"Puwede kang gumamit ng libreng custom CFID [b]{free[0]}[/b] para kay {escape_markup(pname)} lang."
               if free else f"Walang libreng custom CFID ({cfalloc.CUSTOM_START}-{cfalloc.CUSTOM_END}) sa OBB na ito."),
            13, TEXT))
        pop = make_popup("SHARED PORTRAIT", box, (0.92, 0.55))
        if free:
            box.add_widget(make_btn(f"Gamitin ang libreng CFID {free[0]}",
                                    lambda: (pop.dismiss(), start(cmap[free[0]], free[0])), 52, "primary"))
        box.add_widget(make_btn("Palitan pa rin (lahat ng shared)", lambda: (pop.dismiss(), start(index)), 52))
        box.add_widget(make_btn("Cancel", pop.dismiss, 52))
        pop.open()

    def portrait_preview(self, cf, pname, player_slot=None, name=None, team_slot=-1, title="") -> None:
        """PORTRAIT PREVIEW: browse every face png in the OBB (Next / Prev / Close), starting at this player's."""
        cmap = self._cf_index_map()
        keys = sorted(cmap)
        if not keys:
            show_message("Portrait", "No portraits found in this OBB.")
            return
        try:
            pos = keys.index(int(cf))
        except (TypeError, ValueError):
            pos = 0
        state = {"pos": pos, "token": 0}
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        image = Image(fit_mode="contain")
        box.add_widget(image)
        counter = left_label("", 14, height=26)
        box.add_widget(counter)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        popup = make_popup("PORTRAIT PREVIEW", box, (0.92, 0.72))

        def show() -> None:
            state["token"] += 1
            token = state["token"]
            cur = state["pos"]
            counter.text = f"Portrait {cur + 1} / {len(keys)}"
            index = cmap[keys[cur]]

            def load():
                try:
                    w, h, data = self.ws.cyberface_thumb(index, (256, 256))
                except Exception:  # noqa: BLE001
                    return

                def put(_dt):
                    if token != state["token"]:
                        return
                    tex = Texture.create(size=(w, h), colorfmt="rgba")
                    tex.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
                    tex.flip_vertical()
                    image.texture = tex

                Clock.schedule_once(put, 0)

            threading.Thread(target=load, daemon=True).start()

        def step(delta: int) -> None:
            state["pos"] = (state["pos"] + delta) % len(keys)
            show()

        def use() -> None:
            number = keys[state["pos"]]
            try:
                self._roster_bridge().setField(player_slot, "cyberface", number)
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("portrait use", exc)
                show_message("Error", friendly_error(exc))
                return
            state["token"] += 1
            popup.dismiss()
            self.set_status(f"{pname}: portrait set to CF {number}")
            self.quick_preview(player_slot, name or pname, team_slot, title)

        buttons.add_widget(make_btn("Next", partial(step, 1), 50))
        buttons.add_widget(make_btn("Prev", partial(step, -1), 50))
        if player_slot is not None:
            buttons.add_widget(make_btn("Use", use, 50, "primary"))
        buttons.add_widget(make_btn("Close", popup.dismiss, 50))
        box.add_widget(buttons)
        popup.open()
        show()

    def show_roster_player(self, player_slot: int, name: str, team_slot: int, title: str) -> None:
        try:
            self.set_header(name)
            self.clear_body()
            bridge = self._roster_bridge()
            rows = []
            try:
                now = bridge.ovr(player_slot)
            except Exception:  # noqa: BLE001
                now = "?"
            rows.append((f"Change Name:  {name}", partial(self.edit_player_name, player_slot, name, team_slot, title)))
            rows.append((f"Manual OVR  (now {now})", partial(self.edit_player_ovr, player_slot, name, team_slot, title, now)))
            rows.append(("Sync online ratings  (type any name)", partial(self.sync_online_player, player_slot, name, team_slot, title)))
            for key, label, value, mx in self._rows(bridge.profile(player_slot), 4):
                rows.append((f"{label}:  {value}", partial(self.edit_player_field, player_slot, key, label, value, int(mx or 0), name, team_slot, title)))
            for idx, label, value in self._rows(bridge.ratings(player_slot), 3):
                rows.append((f"{label}:  {value}", partial(self.edit_roster_rating, player_slot, int(idx), label, value, name, team_slot, title)))
            for kind, caption in (("tendencies", "Tendencies"), ("appearance", "Appearance (shoes / accessories)"),
                                  ("animations", "Animations (shot / dunk / intro packages)")):
                rows.append((f"{caption}  >", partial(self.show_roster_extra, kind, player_slot, name, team_slot, title)))
            self.body.add_widget(self._roster_list(rows))
            self.body.add_widget(self._roster_back_bar(partial(self.show_roster_players, team_slot, title, True)))
        except Exception as exc:  # noqa: BLE001
            log_error("open roster player", exc)
            show_message("Roster Error", friendly_error(exc))

    def show_roster_extra(self, kind, player_slot, name, team_slot, title) -> None:
        """Tendencies / appearance / animation fields (ported from the Java VIP roster editor)."""
        try:
            self.set_header(f"{name} - {kind}")
            self.clear_body()
            bridge = self._roster_bridge()
            rows = []
            for idx, label, value, mx in self._rows(getattr(bridge, kind)(player_slot), 4):
                rows.append((f"{label}:  {value}", partial(self.edit_roster_extra, kind, player_slot, int(idx), label,
                                                           value, int(mx), name, team_slot, title)))
            self.body.add_widget(self._roster_list(rows))
            self.body.add_widget(self._roster_back_bar(partial(self.show_roster_player, player_slot, name, team_slot, title)))
        except Exception as exc:  # noqa: BLE001
            log_error("open roster extra", exc)
            show_message("Roster Error", friendly_error(exc))

    def edit_roster_extra(self, kind, player_slot, idx, label, value, mx, name, team_slot, title) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(make_label(f"{label}  (0 - {mx})", 15))
        field = make_input("Value", 48, input_filter="int")
        field.text = str(value)
        box.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = make_popup(f"{name}", box, (0.9, 0.42))

        def apply() -> None:
            try:
                number = int(field.text)
                if number < 0 or number > mx:
                    raise ValueError(f"{label} must be 0-{mx}.")
                self._roster_bridge().setExtra(player_slot, kind, idx, number)
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("roster extra", exc)
                show_message("Error", friendly_error(exc))
                return
            popup.dismiss()
            self.show_roster_extra(kind, player_slot, name, team_slot, title)

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 50))
        buttons.add_widget(make_btn("Apply", apply, 50, "primary"))
        box.add_widget(buttons)
        popup.open()

    def edit_player_name(self, player_slot, name, team_slot, title) -> None:
        try:
            first, _tab, last = self._roster_bridge().nameInfo(player_slot).partition("\t")
        except Exception as exc:  # noqa: BLE001
            log_error("name info", exc)
            show_message("Error", friendly_error(exc))
            return
        outer = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        scroll = ScrollView(bar_width=dp(3))
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=(0, 0, dp(4), 0))
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(wrap_label(f"Ngayon:  [b]{escape_markup(name)}[/b]", 15, TEXT))
        limits = wrap_label("Sinusuri ang limit ng pangalan ...", 12, MUTED)
        grid.add_widget(limits)

        def load_limits() -> None:
            try:
                fc, fs, lc, ls = (self._roster_bridge().nameLimits(player_slot).split("\t") + ["0"] * 4)[:4]
            except Exception:  # noqa: BLE001
                return

            def part(label, cap, shared) -> str:
                if shared == "1":
                    return f"{label}: shared sa ibang player - pangalan na nasa roster na lang ang puwede"
                return f"{label}: hanggang {cap} letra (o pangalan na nasa roster na)"

            text = part("First", fc, fs) + "\n" + part("Last", lc, ls)
            Clock.schedule_once(lambda _dt: setattr(limits, "text", escape_markup(text)), 0)

        threading.Thread(target=load_limits, daemon=True).start()
        grid.add_widget(wrap_label("First name", 12, MUTED))
        first_in = make_input("First name", 48)
        first_in.text = first
        grid.add_widget(first_in)
        grid.add_widget(wrap_label("Last name", 12, MUTED))
        last_in = make_input("Last name", 48)
        last_in.text = last
        grid.add_widget(last_in)
        grid.add_widget(wrap_label("Commentary says (optional)", 12, MUTED))
        sound_in = make_input("Buong pangalan ng player sa roster", 48)
        grid.add_widget(sound_in)
        grid.add_widget(wrap_label(
            "Recorded na pangalan ang gamit ng commentator, kaya ilagay sa 'Commentary says' ang player na "
            "gusto mong sabihin nila (kokopyahin ang audio ID). Iwanang blangko kung hindi kailangan.",
            12, MUTED))
        scroll.add_widget(grid)
        outer.add_widget(scroll)
        buttons = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        popup = make_popup("CHANGE NAME", outer, (0.94, 0.8))

        def apply() -> None:
            f_text, l_text, s_text = first_in.text, last_in.text, sound_in.text
            bridge = self._roster_bridge()
            for field in (first_in, last_in, sound_in):
                field.focus = False

            def work():
                return bridge.setName(player_slot, f_text, l_text, s_text)

            def done(result) -> None:
                self.roster_dirty = True
                popup.dismiss()
                self.set_status(f"Name: {result}")
                new_name = " ".join((f_text + " " + l_text).split()) or name
                self.show_roster_player(player_slot, new_name, team_slot, title)

            # runs in the background with the loading overlay: the screen can no longer freeze
            self.run_bg(work, done, "Saving name ...")

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 52))
        buttons.add_widget(make_btn("Apply", apply, 52, "primary"))
        outer.add_widget(buttons)
        popup.open()

    def edit_player_ovr(self, player_slot, name, team_slot, title, now) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(make_label("Target OVR (25 - 99). Shifts all ratings evenly and verifies the result.", 14))
        field = make_input("OVR", 48, input_filter="int")
        field.text = str(now)
        box.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = make_popup(f"MANUAL OVR \u2022 {name}", box, (0.9, 0.5))

        def apply() -> None:
            try:
                target = max(25, min(99, int(field.text)))
                result = self._roster_bridge().setOvr(player_slot, target)
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("manual ovr", exc)
                show_message("Error", friendly_error(exc))
                return
            popup.dismiss()
            self.set_status(f"OVR {result}")
            self.show_roster_player(player_slot, name, team_slot, title)

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 50))
        buttons.add_widget(make_btn("Apply", apply, 50, "primary"))
        box.add_widget(buttons)
        popup.open()

    def edit_team_ovr(self, team_slot, title) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(make_label("Target OVR for every player on this team (25 - 99). All-or-nothing: if any player can't reach it, nobody changes.", 14))
        field = make_input("OVR", 48, input_filter="int")
        field.text = "75"
        box.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = make_popup(f"MANUAL OVR \u2022 WHOLE TEAM", box, (0.9, 0.55))

        def apply() -> None:
            try:
                target = max(25, min(99, int(field.text)))
                count = self._roster_bridge().setTeamOvr(team_slot, target)
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("team ovr", exc)
                show_message("Error", friendly_error(exc))
                return
            popup.dismiss()
            self.set_status(f"{count} players set to OVR {target}")
            self.show_roster_players(team_slot, title, True)

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 50))
        buttons.add_widget(make_btn("Apply", apply, 50, "primary"))
        box.add_widget(buttons)
        popup.open()

    def edit_player_field(self, player_slot, key, label, value, maximum, name, team_slot, title) -> None:
        if key in ("cyberface", "portrait"):
            self.pick_face(player_slot, key, label, value, maximum, name, team_slot, title)
            return
        self._edit_player_number(player_slot, key, label, value, maximum, name, team_slot, title)

    def pick_face(self, player_slot, key, label, value, maximum, name, team_slot, title) -> None:
        """Image picker for CF ID / Portrait: shows png####.iff faces from the opened OBB."""
        if getattr(self.ws, "session", None) is None:
            self._ensure_obb(lambda: self.pick_face(player_slot, key, label, value, maximum, name, team_slot, title))
            return
        import re as _re
        try:
            rows = []
            for r in self.ws.obb_rows("", category="Cyberface"):
                hit = _re.search(r"(\d+)", str(r["label"]))
                if hit:
                    rows.append((int(hit.group(1)), r["index"]))
            rows.sort()
        except Exception as exc:  # noqa: BLE001
            log_error("face list", exc)
            rows = []
        if not rows:
            show_message(label, "Walang nakitang png####.iff cyberface sa OBB na ito. Mag-type ka na lang ng number.")
            self._edit_player_number(player_slot, key, label, value, maximum, name, team_slot, title)
            return

        PAGE = 12
        state = {"page": 0, "gen": 0, "q": ""}
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
        box.add_widget(left_label(f"{escape_markup(label)}: kasalukuyan {value}.  I-tap ang larawan para piliin.", 13, MUTED, height=34))
        search = make_input("Search CF number (e.g. 7200)", 44, input_filter="int")
        box.add_widget(search)
        grid = GridLayout(cols=3, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(grid)
        box.add_widget(scroll)
        info = left_label("", 12, MUTED, height=22)
        box.add_widget(info)
        nav = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        box.add_widget(nav)
        popup = make_popup(f"{name} \u2022 {label}", box, (0.96, 0.94))
        queue: list = []

        def choose(number: int) -> None:
            try:
                self._roster_bridge().setField(player_slot, key, number)
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("pick face", exc)
                show_message("Error", friendly_error(exc))
                return
            state["gen"] += 1
            popup.dismiss()
            self.show_roster_player(player_slot, name, team_slot, title)

        def worker(gen: int) -> None:
            while True:
                try:
                    holder, index = queue.pop(0)
                except IndexError:
                    return
                if gen != state["gen"]:
                    return
                try:
                    w, h, data = self.ws.cyberface_thumb(index)
                except Exception:  # noqa: BLE001
                    continue

                def put(_dt, holder=holder, w=w, h=h, data=data, gen=gen):
                    if gen != state["gen"]:
                        return
                    tex = Texture.create(size=(w, h), colorfmt="rgba")
                    tex.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
                    tex.flip_vertical()
                    holder.texture = tex

                Clock.schedule_once(put, 0)

        def render(*_a) -> None:
            state["gen"] += 1
            gen = state["gen"]
            queue.clear()
            q = state["q"]
            found = [r for r in rows if not q or str(r[0]).startswith(q)]
            pages = max(1, (len(found) + PAGE - 1) // PAGE)
            state["page"] = max(0, min(state["page"], pages - 1))
            chunk = found[state["page"] * PAGE:(state["page"] + 1) * PAGE]
            grid.clear_widgets()
            for number, index in chunk:
                cell = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(150), spacing=dp(2))
                img = Image(fit_mode="contain")
                cell.add_widget(img)
                tap = make_btn(f"CF {number}", partial(choose, number), 34, "primary" if str(number) == str(value) else "ghost")
                cell.add_widget(tap)
                grid.add_widget(cell)
                queue.append((img, index))
            info.text = f"{len(found)} faces  \u2022  page {state['page'] + 1}/{pages}"
            scroll.scroll_y = 1
            threading.Thread(target=worker, args=(gen,), daemon=True).start()

        def go(delta: int) -> None:
            state["page"] += delta
            render()

        def on_search(*_a) -> None:
            state["q"] = search.text.strip()
            state["page"] = 0
            render()

        nav.add_widget(make_btn("< Prev", partial(go, -1), 48))
        nav.add_widget(make_btn("Type number", lambda: (popup.dismiss(), self._edit_player_number(player_slot, key, label, value, maximum, name, team_slot, title)), 48))
        nav.add_widget(make_btn("Next >", partial(go, 1), 48))
        search.bind(text=on_search)
        popup.bind(on_dismiss=lambda *_a: state.__setitem__("gen", state["gen"] + 1))
        popup.open()
        render()

    def _edit_player_number(self, player_slot, key, label, value, maximum, name, team_slot, title) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(make_label(f"{label}  (0 - {maximum})", 15))
        field = make_input(label, 48, input_filter="int")
        field.text = str(value)
        box.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = make_popup(f"{name}", box, (0.9, 0.42))

        def apply() -> None:
            try:
                self._roster_bridge().setField(player_slot, key, int(field.text))
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("roster field", exc)
                show_message("Error", friendly_error(exc))
                return
            popup.dismiss()
            self.show_roster_player(player_slot, name, team_slot, title)

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 50))
        buttons.add_widget(make_btn("Apply", apply, 50, "primary"))
        box.add_widget(buttons)
        popup.open()

    def edit_roster_rating(self, player_slot, idx, label, value, name, team_slot, title) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(make_label(f"{label}  (25 - 99)", 15))
        field = make_input("Rating", 48, input_filter="int")
        field.text = str(value)
        box.add_widget(field)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = make_popup(f"{name}", box, (0.9, 0.42))

        def apply() -> None:
            try:
                number = max(25, min(99, int(field.text)))
                self._roster_bridge().setRating(player_slot, idx, number)
                self.roster_dirty = True
            except Exception as exc:  # noqa: BLE001
                log_error("roster rating", exc)
                show_message("Error", friendly_error(exc))
                return
            popup.dismiss()
            self.show_roster_player(player_slot, name, team_slot, title)

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 50))
        buttons.add_widget(make_btn("Apply", apply, 50, "primary"))
        box.add_widget(buttons)
        popup.open()

    def sync_online_player(self, player_slot, name, team_slot, title) -> None:
        """Pull ratings from 2kratings.com for ANY typed name and write them into this roster slot."""
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        box.add_widget(wrap_label(
            "Ilagay ang pangalan na hahanapin online. Kahit custom/nickname/Jr. - sinusubukan ang iba't ibang "
            "spelling. Puwede ring i-paste ang 2kratings.com link o slug (hal. gary-trent-jr). "
            "Hindi nababago ang jersey, portrait, o pangalan sa roster.", 12, MUTED))
        field = make_input("Name / slug / link", 48)
        field.text = name
        box.add_widget(field)
        from nba2k20 import online_ratings as _orr0
        _orr0.OPTIONS_PATH = output_root() / "sync_options.json"
        state = {"ovr": bool(_orr0.load_sync_options()["ovr"])}      # v223: same switch as the team / all-teams syncs
        toggle = make_btn("Match OVR: ON" if state["ovr"] else "Match OVR: OFF", lambda: None, 44, "ghost")

        def flip() -> None:
            state["ovr"] = not state["ovr"]
            toggle.text = "Match OVR: ON" if state["ovr"] else "Match OVR: OFF"
            try:
                _orr0.save_sync_options({**_orr0.load_sync_options(), "ovr": state["ovr"]})
            except Exception:  # noqa: BLE001
                pass

        toggle.bind(on_release=lambda *_a: flip())
        box.add_widget(toggle)
        # What a sync may write (saved in NBA2K20Tool/sync_options.json, used by ALL syncs). Body is OFF by default.
        from nba2k20 import online_ratings as _orr
        _orr.OPTIONS_PATH = output_root() / "sync_options.json"
        sync_opts = _orr.load_sync_options()
        box.add_widget(wrap_label("Isusulat ng sync (ON lang ang gagalawin):", 12, MUTED))
        opt_row = GridLayout(cols=3, size_hint_y=None, height=dp(48 * ((len(_orr.SYNC_KEYS) + 2) // 3)), spacing=dp(6))
        for key in _orr.SYNC_KEYS:
            btn = make_btn("", lambda: None, 44, "ghost")

            def _label(b=btn, k=key) -> None:
                b.text = "%s: %s" % (k, "ON" if sync_opts[k] else "OFF")

            def _flip(*_a, b=btn, k=key, lab=_label) -> None:
                sync_opts[k] = not sync_opts[k]
                try:
                    _orr.save_sync_options(sync_opts)
                except Exception:  # noqa: BLE001
                    pass
                lab()

            _label()
            btn.bind(on_release=_flip)
            opt_row.add_widget(btn)
        box.add_widget(opt_row)
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        popup = make_popup(f"ONLINE RATINGS \u2022 {name}", box, (0.94, 0.82))

        def apply() -> None:
            from nba2k20 import online_ratings
            online_ratings.ALIAS_PATH = output_root() / "online_aliases.json"
            online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
            lookup, match = field.text, state["ovr"]
            bridge = self._roster_bridge()
            field.focus = False

            def work():
                return online_ratings.sync_player(bridge, player_slot, lookup, match)

            def done(result) -> None:
                self.roster_dirty = True
                popup.dismiss()
                self.set_status(result)
                show_message("Online ratings", result)
                self.show_roster_player(player_slot, name, team_slot, title)

            self.run_bg(work, done, "Fetching online ratings ...")

        buttons.add_widget(make_btn("Cancel", popup.dismiss, 50))
        buttons.add_widget(make_btn("Sync", apply, 50, "primary"))
        box.add_widget(buttons)
        popup.open()

    def sync_online_team(self, team_slot, title) -> None:
        """FULL AUTO = everything: team (trade/sign, names, ratings, age, jerseys, lineup) + free agents."""
        outer = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        sv = ScrollView(bar_width=dp(4))
        inner = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        inner.bind(minimum_height=inner.setter("height"))
        inner.add_widget(wrap_label(
            "[b]FULL AUTO[/b] = roster ng team: kasalukuyang roster sa 2kratings (trade/sign, pangalan, ratings, "
            "[b]age[/b], jersey, lineup) [b]kasama ang portrait[/b] ng bawat player. Auto-save sa <pangalan>_edited; "
            "hindi ginagalaw ang original. Kapag walang naka-open na OBB, roster lang ang gagawin (at sasabihin sa report); "
            "i-Save OBB pagkatapos kung may portrait.\n"
            "[b]FREE AGENTS[/b] = hiwalay na update (ratings, age, mukha) para sa mga free agent.", 13, TEXT))
        for text, kind, fn in (
                ("FULL AUTO (roster + portraits)", "primary", lambda: self._full_team_sync(team_slot, title, True)),
                ("FULL AUTO (roster lang)", "ghost", lambda: self._full_team_sync(team_slot, title, False)),
                ("FREE AGENTS update", "ghost", lambda: self._free_agent_sync(team_slot, title, False)),
                ("FREE AGENTS + portraits", "ghost", lambda: self._free_agent_sync(team_slot, title, True)),
                ("Ratings only", "ghost", lambda: self._ratings_only_team_sync(team_slot, title)),
                ("Fix ages (team)", "ghost", lambda: self._fix_ages_team(team_slot, title)),
                ("GAME YEAR (age) - kung mali ang age sa game", "ghost", lambda: self._game_year_popup())):
            inner.add_widget(make_btn(text, (lambda f=fn: (pop.dismiss(), f())), 52, kind))
        sv.add_widget(inner)
        outer.add_widget(sv)
        outer.add_widget(make_btn("Cancel", lambda: pop.dismiss(), 48))
        pop = make_popup("SYNC TEAM ONLINE", outer, (0.94, 0.8))
        pop.open()

    def _game_year_popup(self) -> None:
        """v222: the game showed 17 for a 24-year-old: it does not count ages from the phone clock.  Type the year it counts from."""
        from nba2k20 import online_ratings
        online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
        current = online_ratings.load_age_ref_year()
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        box.add_widget(wrap_label(
            "[b]GAME YEAR[/b] = ang taon na pinagbabasehan ng game sa age (age = taon - birth year).\n"
            "Halimbawa: Maxey (24) ay lumabas na 17 sa game -> 2026 - 17 = [b]2019[/b]. Ilagay ang 2019, tapos i-run ang "
            "[b]Fix ages (team)[/b] o FULL AUTO ulit.\n0 = sundan ang oras ng phone.\nNgayon: %s" % (current or "0 (phone clock)"), 13, TEXT))
        field = make_input("Year (hal. 2019) o 0", 46)
        field.text = str(current or "")
        field.input_filter = "int"
        box.add_widget(field)

        def save(*_a):
            try:
                online_ratings.save_age_ref_year(int(field.text or 0))
                self._roster_bridge()
                pop.dismiss()
                show_message("GAME YEAR", "Na-save: %s\nI-run ang Fix ages (team) para ma-update ang age." % (field.text or "0"), 0.4)
            except Exception as exc:  # noqa: BLE001
                show_message("GAME YEAR", friendly_error(exc), 0.4)
        box.add_widget(make_btn("SAVE", save, 50, "primary"))
        box.add_widget(make_btn("Cancel", lambda: pop.dismiss(), 46))
        pop = make_popup("GAME YEAR (age)", box, (0.9, 0.62))
        pop.open()

    def _ratings_only_team_sync(self, team_slot, title) -> None:
        from nba2k20 import online_ratings
        online_ratings.ALIAS_PATH = output_root() / "online_aliases.json"
        online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
        bridge = self._roster_bridge()

        def work():
            report = online_ratings.sync_team(bridge, team_slot, False, lambda m: Clock.schedule_once(lambda _d: self.set_status(m), 0))
            try:
                return "%s\nROSTER SAVED: %s" % (report, self._auto_save_roster(team_slot))
            except Exception as exc:  # noqa: BLE001
                return "%s\nAUTO-SAVE FAILED: %s\nTap Save roster copy to try again." % (report, str(exc).splitlines()[0][:160])

        def done(result) -> None:
            self.roster_dirty = "ROSTER SAVED" not in str(result)
            self.set_status("Team synced - roster saved" if not self.roster_dirty else "Team synced")
            show_message("Online team sync", result, 0.6)
            self.show_roster_players(team_slot, title, True)

        self.run_bg(work, done, "Syncing team online ...")

    def _portrait_callback(self, bridge):
        """portrait_cb for team_sync: PNG bytes -> OBB cyberface entry under a free (or the player's own custom) CFID."""
        used = set()
        for r in self._rows(bridge.players(-1), 4):
            if str(r[3]).strip().isdigit():
                used.add(int(str(r[3]).strip()))
        cmap = self._cf_index_map()
        folder = output_root() / "portrait" / "online"
        folder.mkdir(parents=True, exist_ok=True)

        def cb(slot, name, png):
            try:
                cur = int(bridge.playerInfo(slot).split("\t")[4])
            except Exception:  # noqa: BLE001
                cur = 0
            own_custom = (cfalloc.CUSTOM_START <= cur <= cfalloc.CUSTOM_END and cur in cmap
                          and sum(1 for r in self._rows(bridge.players(-1), 4) if str(r[3]).strip() == str(cur)) <= 1)
            if own_custom:
                new_cf = cur
            else:
                free = cfalloc.free_custom_slots(cmap.keys(), used)
                if not free:
                    raise RuntimeError("walang libreng custom CFID (%d-%d)" % (cfalloc.CUSTOM_START, cfalloc.CUSTOM_END))
                new_cf = free[0]
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(name)).strip("_") or "player"
            path = folder / ("%s_CF%d.png" % (safe, new_cf))
            path.write_bytes(png)
            self.ws.cyberface_auto_png(cmap[new_cf], path)
            if new_cf != cur:
                bridge.setField(slot, "cyberface", new_cf)
            used.add(new_cf)
            return "CF %d" % new_cf

        return cb

    def _full_team_sync(self, team_slot, title, with_portraits: bool = False) -> None:
        """Team sync (trade/sign + names + ratings). The roster is saved automatically at the end.  With portraits the
        patch OBB (the one used last, else you pick it once) is opened by itself, the new faces are staged and the
        OBB is saved as a verified copy in patched_obb/ - no extra taps."""
        if with_portraits and not self._cf_index_map():
            self._ensure_obb(lambda: self._full_team_sync_run(team_slot, title, True))
            return
        self._full_team_sync_run(team_slot, title, with_portraits)

    def _sync_all_teams_ask(self) -> None:
        """v222: every team of the roster from 2kratings in one go (names, ratings, age, position, jerseys, lineup, portraits)."""
        outer = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        outer.add_widget(wrap_label(
            "[b]SYNC ALL TEAMS[/b] = lahat ng 30 teams: kasalukuyang roster sa 2kratings (trade/sign, pangalan, ratings, age, "
            "position, jersey, lineup). Isang save sa dulo (<pangalan>_edited; hindi ginagalaw ang original). "
            "Matagal ito (mga 10-20 minuto, kailangan ng internet). Tingnan ang status sa ibaba; may report sa dulo.\n"
            "[b]Kasama ang portraits[/b] = bubuksan ang OBB at gagawa ng patch OBB copy.", 13, TEXT))
        outer.add_widget(make_btn("ALL TEAMS + portraits", lambda: (pop.dismiss(), self._sync_all_teams(True)), 52, "primary"))
        outer.add_widget(make_btn("ALL TEAMS (roster lang)", lambda: (pop.dismiss(), self._sync_all_teams(False)), 52, "ghost"))
        outer.add_widget(make_btn("Cancel", lambda: pop.dismiss(), 46))
        pop = make_popup("SYNC ALL TEAMS", outer, (0.92, 0.62))
        pop.open()

    def _sync_all_teams(self, with_portraits: bool) -> None:
        if with_portraits and not self._cf_index_map():
            self._ensure_obb(lambda: self._sync_all_teams_run(True))
            return
        self._sync_all_teams_run(with_portraits)

    def _sync_all_teams_run(self, with_portraits: bool) -> None:
        import time as _time
        from nba2k20 import online_ratings, team_sync
        online_ratings.ALIAS_PATH = output_root() / "online_aliases.json"
        online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
        team_sync.DEBUG_PATH = output_root() / "online_debug.txt"
        bridge = self._roster_bridge()
        if with_portraits and not self._cf_index_map():
            with_portraits = False

        def work():
            cb = self._portrait_callback(bridge) if with_portraits else None
            before = self.ws.staged_count
            lines, failed = [], 0
            teams = self._rows(bridge.teams(), 4)
            for n, (slot, abbr, name, _count) in enumerate(teams, 1):
                tag = "[%d/%d] %s" % (n, len(teams), abbr or name)
                Clock.schedule_once(lambda _d, t=tag: self.set_status("ALL TEAMS " + t + " ..."), 0)
                try:
                    rep = team_sync.sync_team_full(
                        bridge, int(slot), False, False, cb,
                        lambda m, t=tag: Clock.schedule_once(lambda _d: self.set_status(t + "  " + m), 0),
                        save_cb=None)
                    head = rep.split("\n", 1)[0]
                    problems = rep.count("\n- ")
                    lines.append("%s: %s%s" % (abbr or name, head, ("  (%d problems)" % problems) if problems else ""))
                except online_ratings.OnlineNetworkError as exc:
                    lines.append("%s: STOP - network: %s" % (abbr or name, str(exc).splitlines()[0][:90]))
                    failed += 1
                    break
                except Exception as exc:  # noqa: BLE001
                    lines.append("%s: FAILED - %s" % (abbr or name, str(exc).splitlines()[0][:90]))
                    failed += 1
                _time.sleep(1.0)
            out = "\n".join(lines)
            try:
                out += "\nROSTER SAVED: " + self._auto_save_roster().strip()[:300]
            except Exception as exc:  # noqa: BLE001
                out += "\nAUTO-SAVE FAILED: %s\nTap Save roster copy." % str(exc).splitlines()[0][:160]
            if with_portraits and self.ws.staged_count > before:
                try:
                    source = self.ws.session.path
                    folder = output_root() / "patched_obb"
                    folder.mkdir(parents=True, exist_ok=True)
                    dest = folder / source.name
                    if dest.resolve() == source.resolve():
                        dest = copy_with_suffix(dest, "_patched")
                    saved = self.ws.save_obb(dest, allow_overwrite=dest.exists(),
                                             progress=lambda m: Clock.schedule_once(lambda _d, m=m: self.set_status(m), 0))
                    out += "\nOBB SAVED (%d faces): %s" % (saved["changed_entry_count"], saved["output_obb"])
                except Exception as exc:  # noqa: BLE001
                    out += "\nOBB AUTO-SAVE FAILED: %s" % str(exc).splitlines()[0][:160]
            return out

        def done(result) -> None:
            self.roster_dirty = "ROSTER SAVED" not in str(result)
            self.set_status("All teams synced")
            show_message("SYNC ALL TEAMS", result, 0.85)
            self.show_roster_teams()

        self.run_bg(work, done, "ALL TEAMS: 2kratings ...")

    def _full_team_sync_run(self, team_slot, title, with_portraits: bool) -> None:
        from nba2k20 import online_ratings, team_sync
        online_ratings.ALIAS_PATH = output_root() / "online_aliases.json"
        online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
        team_sync.DEBUG_PATH = output_root() / "online_debug.txt"
        bridge = self._roster_bridge()

        no_obb = False
        if with_portraits and not self._cf_index_map():
            with_portraits, no_obb = False, True      # still no usable OBB: do the roster, tell the user at the end

        def work():
            cb = self._portrait_callback(bridge) if with_portraits else None
            before = self.ws.staged_count
            rep = team_sync.sync_team_full(
                bridge, team_slot, False, False, cb,
                lambda m: Clock.schedule_once(lambda _d: self.set_status(m), 0),
                save_cb=lambda: self._auto_save_roster(team_slot))
            if no_obb:
                rep += "\nPORTRAITS SKIPPED: walang magamit na patch OBB. Buksan ang OBB at i-run ulit para sa mukha."
            elif with_portraits and self.ws.staged_count > before:
                try:
                    source = self.ws.session.path
                    folder = output_root() / "patched_obb"
                    folder.mkdir(parents=True, exist_ok=True)
                    dest = folder / source.name
                    if dest.resolve() == source.resolve():
                        dest = copy_with_suffix(dest, "_patched")
                    Clock.schedule_once(lambda _d: self.set_status("Saving patch OBB ..."), 0)
                    saved = self.ws.save_obb(dest, allow_overwrite=dest.exists(),
                                             progress=lambda m: Clock.schedule_once(lambda _d, m=m: self.set_status(m), 0))
                    rep += "\nOBB SAVED (%d faces): %s\nCopy it over the game's patch OBB to see the new portraits." % (
                        saved["changed_entry_count"], saved["output_obb"])
                except Exception as exc:  # noqa: BLE001
                    rep += "\nOBB AUTO-SAVE FAILED: %s\nTap Save OBB copy to try again." % str(exc).splitlines()[0][:160]
            return rep

        def done(result) -> None:
            self.roster_dirty = "ROSTER SAVED" not in str(result)
            self.set_status("Team synced - roster saved" if not self.roster_dirty else "Team synced")
            show_message("Online team sync", result, 0.6)
            self.show_roster_players(team_slot, title, True)

        self.run_bg(work, done, "FULL AUTO: team roster ...")

    def _fix_ages_team(self, team_slot, title) -> None:
        """Rewrite only the age of every player of the team from the 2kratings pages."""
        from nba2k20 import online_ratings, team_sync
        online_ratings.ALIAS_PATH = output_root() / "online_aliases.json"
        online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
        bridge = self._roster_bridge()

        def work():
            return team_sync.fix_team_ages(
                bridge, team_slot, lambda m: Clock.schedule_once(lambda _d: self.set_status(m), 0),
                save_cb=lambda: self._auto_save_roster(team_slot))

        def done(result) -> None:
            self.roster_dirty = "ROSTER SAVED" not in str(result)
            show_message("Fix ages", result, 0.6)
            self.show_roster_players(team_slot, title, True)

        self.run_bg(work, done, "Fixing ages from 2kratings ...")

    def _free_agent_sync(self, team_slot, title, with_portraits: bool = False) -> None:
        """Ratings + age (+ portrait) for the free agents of the roster, by their roster names."""
        from nba2k20 import online_ratings, team_sync
        online_ratings.ALIAS_PATH = output_root() / "online_aliases.json"
        online_ratings.OPTIONS_PATH = output_root() / "sync_options.json"
        bridge = self._roster_bridge()
        if with_portraits and not self._cf_index_map():
            show_message("Portrait", "Walang naka-open na OBB (o walang cyberface entries). Buksan muna ang OBB, "
                                     "o gamitin ang walang portrait.")
            return

        def work():
            cb = self._portrait_callback(bridge) if with_portraits else None
            return team_sync.sync_free_agents(
                bridge, 60, False, False, cb,
                lambda m: Clock.schedule_once(lambda _d: self.set_status(m), 0),
                save_cb=lambda: self._auto_save_roster(team_slot))

        def done(result) -> None:
            self.roster_dirty = "ROSTER SAVED" not in str(result)
            show_message("Free agents sync", result, 0.6)
            self.show_roster_players(team_slot, title, True)

        self.run_bg(work, done, "Syncing free agents online ...")

    def _auto_save_roster(self, team_slot=None) -> str:
        """Save as <name>_edited<ext> next to the loaded roster (sample.ros -> sample_edited.ros), then read the file
        back from disk and report whether it really holds the edits (and which players the file has)."""
        from nba2k20 import team_sync
        if not self.roster_path.is_file():
            raise IOError("Load a valid roster file before saving.")
        bridge = self._roster_bridge()
        saved = team_sync.save_edited_copy(bridge, self.roster_path, output_root() / "roster")
        path = saved.split("  (could not")[0]
        note = saved[len(path):].strip()
        try:
            proof = bridge.verifyFile(path, team_slot)
        except Exception as exc:  # noqa: BLE001
            proof = "FILE: %s\n(could not read it back: %s)" % (path, str(exc).splitlines()[0][:100])
        if self.roster_via_saf:
            Clock.schedule_once(lambda _dt, p=path: self._saf_export(p), 0.3)
            note = (note + "\n" if note else "") + "System save dialog: choose where to keep %s" % Path(path).name
        return "\n" + proof + (("\n" + note) if note else "")

    def save_roster_copy(self) -> None:
        if not self.roster_path.is_file():
            show_message("Roster Error", "Load a valid roster file before saving.")
            return

        def work():
            return self._auto_save_roster()

        def done(saved: str) -> None:
            self.roster_dirty = False
            self.set_status("Roster saved")
            show_message("Roster saved", f"New file (original untouched):\n{saved}")

        self.run_bg(work, done, "Encoding roster ...")

    # ----------------------------------------------------------------- OBB
    def load_obb(self, path: Path) -> None:
        self.run_bg(
            lambda: self.ws.open_obb(path, wait=False),
            self._after_obb_open,
            f"Reading {path.name} ...",
        )

    def _poll_obb_ready(self, session, info: dict) -> None:
        """First open of an OBB: the list is already usable (hash names); when the background name / grouping scan is
        done, refresh once with the real names.  Later opens of the same OBB are cached and need none of this."""
        def check(_dt) -> bool:
            if self.ws.session is not session:
                return False                              # another OBB was opened / this one closed
            if self.ws.obb_loading:
                return True                               # keep polling
            if self.mode == "obb":
                self._after_obb_open(dict(info, loading=False, extra_names=len(session.names)))
            return False
        Clock.schedule_interval(check, 1.0)

    def _after_obb_open(self, info: dict) -> None:
        self.mode = "obb"
        if info.get("loading"):
            self._poll_obb_ready(self.ws.session, info)
            info = dict(info, loading=False)
            loading_note = "  | reading names in background (first open only) ..."
        else:
            loading_note = ""
        try:
            self.auto_star_known()
        except Exception:  # noqa: BLE001
            traceback.print_exc()
        # Patch OBB: show only the png####.iff cyberfaces. Main OBB: everything, grouped.
        notice = ""
        if self.ws.is_patch_obb():
            if self.ws.obb_rows("", category="Cyberface"):
                self.browser_state.update(category="Cyberface", search="")
            else:
                self.browser_state.update(category=CATEGORY_CHOICES[0], search="")
                notice = "  (no png####.iff names matched - showing all)"
        else:
            self.browser_state.update(category=CATEGORY_CHOICES[0], search="")
        self.set_status(
            f"{info.get('container', '2K20')} OBB | {info['entries']} entries, {info['editable_iff_entries']} editable IFF"
            + (f" | {info['bad_entries']} broken entr{'y' if info['bad_entries'] == 1 else 'ies'} skipped" if info.get("bad_entries") else "")
            + (" | not IFF: " + ", ".join(f"{k} {v}" for k, v in info["non_iff_types"].items())
               if info.get("non_iff_types") else "")
            + (f" | extra names found: {info['extra_names']}" if info.get("extra_names") else "")
            + (notice if not loading_note else "") + loading_note
        )
        self.show_entries()

    def show_entries(self) -> None:
        self.mode = "obb"
        self.ws.opened = None
        previous = self.ws.current_index
        self.ws.current_index = None
        session = self.ws.session
        self.set_header(f"{session.path.name}   (staged: {self.ws.staged_count})")
        self.clear_body()
        self.browser = IffBrowser(self, self.open_entry, current=previous)
        self.body.add_widget(self.browser)
        bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        bar.add_widget(make_btn("Save OBB copy", self.save_obb_copy, 52, "primary"))
        bar.add_widget(make_btn("Cyberface", self.show_cyberface, 52))
        bar.add_widget(make_btn("Audio", self.show_audio, 52))
        bar.add_widget(make_btn("Export list", self.export_shown, 52))
        bar.add_widget(make_btn("Close OBB", self.show_home, 52))
        self.body.add_widget(bar)

    # ------------------------------------------------------------ owner lock
    def show_owner_lock(self) -> None:
        """Owner stamp: your edited IFFs get a signed manifest next to the saved OBB and open only after Unlock."""
        owner = self.ws.owner
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        status = wrap_label("", 13)
        box.add_widget(wrap_label(
            "OWNER LOCK: kapag ON, ang bawat IFF na na-edit mo at na-Save OBB copy ay mase-stamp (signed manifest na katabi ng "
            "OBB: <name>.obb.d2kowner.json). Sa tool na ito, ang stamped na IFF ay mabubuksan lang kapag nai-Unlock gamit "
            "ang passphrase mo.\n\nHINDI nito ginagalaw ang game / IFF bytes, kaya ligtas ito sa game. Pero hindi rin nito "
            "napipigilan ang ibang tool, at kapag binura ang .d2kowner.json ay hindi na ito naka-lock. Ibigay ang OBB kasama "
            "ang .d2kowner.json para may patunay ng pagmamay-ari.", 12))
        box.add_widget(status)
        name_in = make_input("Owner name (e.g. David2k)")
        name_in.text = owner.name
        pass_in = make_input("Passphrase (min 4)", password=True)
        box.add_widget(name_in)
        box.add_widget(pass_in)

        def refresh() -> None:
            if not owner.enabled:
                status.text = "[b]Status:[/b] OFF - wala pang owner."
            else:
                status.text = (f"[b]Status:[/b] Owner [b]{escape_markup(owner.name)}[/b] - "
                               f"{'[color=6fd16f]UNLOCKED[/color]' if owner.unlocked else '[color=ff6b6b]LOCKED[/color]'}")

        def create(*_a) -> None:
            try:
                owner.configure(name_in.text, pass_in.text)
            except ValueError as exc:
                show_message("Owner lock", str(exc), 0.3)
                return
            pass_in.text = ""
            refresh()
            show_message("Owner lock", "Naka-ON na. Ang susunod na Save OBB copy ay mase-stamp.", 0.3)

        def unlock(*_a) -> None:
            if owner.unlock(pass_in.text):
                pass_in.text = ""
                refresh()
            else:
                show_message("Owner lock", "Mali ang passphrase (o wala pang owner).", 0.3)

        def lock(*_a) -> None:
            owner.lock()
            refresh()

        def remove(*_a) -> None:
            owner.disable()
            name_in.text = ""
            refresh()

        box.add_widget(make_btn("SET OWNER + ON", create, 48, "primary"))
        box.add_widget(make_btn("UNLOCK", unlock, 48))
        box.add_widget(make_btn("LOCK AGAIN", lock, 46))
        box.add_widget(make_btn("REMOVE OWNER", remove, 46, "ghost"))
        refresh()
        scroll = ScrollView()
        scroll.add_widget(box)
        popup = make_popup("OWNER LOCK", scroll, (0.94, 0.9))
        box.add_widget(make_btn("Close", lambda *_a: (popup.dismiss(), self.show_home()), 46))
        popup.open()

    # ------------------------------------------------------------ scoreboard layout
    def show_scoreboard(self) -> None:
        """EXPERIMENTAL: list / edit the layout nodes (size, x, y, scale) of a scoreboard IFF such as newscorebug.iff."""
        from nba2k20 import scorelayout as scoreboard

        state: dict = {"opened": None, "path": None}
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        box.add_widget(wrap_label(
            "SCOREBOARD LAYOUT (experimental): pumili ng scoreboard IFF (hal. newscorebug.iff). Lalabas ang mga node na may "
            "size / x / y / scale. Hindi pa alam kung aling node ang shot clock, game clock, fouls o score - baguhin ang "
            "isang node, i-Save, subukan sa laro, at tandaan kung alin ang gumalaw.\n\n"
            "Ang Save ay bagong file (hindi nababago ang original). Mga numero lang ang ginagalaw: size, x, y, scale.", 12))
        info = wrap_label("Wala pang file.", 12)
        listing = wrap_label("", 12)
        node_in = make_input("Node # (e.g. 3)")
        x_in = make_input("x  (empty = unchanged)")
        y_in = make_input("y  (empty = unchanged)")
        s_in = make_input("scale  (empty = unchanged)")
        z_in = make_input("size  (empty = unchanged)")

        def render() -> None:
            opened = state["opened"]
            if opened is None:
                listing.text = ""
                return
            nodes = scoreboard.find_items(opened.data)
            if not nodes:
                listing.text = "Walang nakitang layout node sa file na ito."
                return
            lines = ["#   grp  size      x         y         z/scale   name"]
            for n in nodes:
                lines.append(f"{n['index']:<3} {n.get('table', 0) + 1:<4} {n['size']:<9.2f} {n['x']:<9.2f} "
                             f"{n['y']:<9.2f} {n['scale']:<9.3f} {str(n.get('name', ''))[:24]}")
            listing.text = escape_markup("\n".join(lines))

        def loaded(opened) -> None:
            state["opened"] = opened
            warn = core.CHECKSUM_WARNINGS[-2:]
            info.text = (f"[b]{escape_markup(Path(state['path']).name)}[/b]  nabuksan"
                         + (f"\n[color=ffcc66]Babala: {escape_markup('; '.join(warn))}[/color]" if warn else ""))
            render()
            visual()

        def visual(*_a) -> None:
            """Landscape drag editor: every node is a box, drag it and the x / y bytes of the IFF change."""
            if state["opened"] is None:
                show_message("Scoreboard", "Pumili muna ng IFF.", 0.3)
                return
            from nba2k20 import scoreview
            popup.dismiss()
            scoreview.open_editor(self, UI, state["opened"], state["path"],
                                  Path(self.user_data_dir) / "scoreboard_labels.json")

        def pick(*_a) -> None:
            def chosen(path: Path) -> None:
                state["path"] = str(path)
                self.run_bg(lambda: core.open_iff(Path(path)), loaded, "Opening scoreboard IFF ...")
            PickerPopup("Choose scoreboard IFF", "file", (".iff",), chosen).open()

        def apply(*_a) -> None:
            if state["opened"] is None:
                show_message("Scoreboard", "Pumili muna ng IFF.", 0.3)
                return
            try:
                index = int(node_in.text.strip())
                changes = {name: float(field.text.strip()) for name, field in
                           (("x", x_in), ("y", y_in), ("scale", s_in), ("size", z_in)) if field.text.strip()}
                if not changes:
                    raise ValueError("Maglagay ng kahit isang value (x / y / scale / size).")
                items = scoreboard.find_items(state["opened"].data)
                if items and items[0].get("kind") == "obj":      # v180: write the real transform record
                    if not 0 <= index < len(items):
                        raise ValueError(f"node {index} does not exist (0 - {len(items) - 1})")
                    item = items[index]
                    scoreboard.set_item_xy(state["opened"].data, item, changes.get("x", item["x"]),
                                           changes.get("y", item["y"]),
                                           scoreboard.pair_mirrors(state["opened"].data, items))
                    node = scoreboard.find_items(state["opened"].data)[index]
                else:
                    node = scoreboard.set_node(state["opened"].data, index, **changes)
            except ValueError as exc:
                show_message("Scoreboard", str(exc), 0.3)
                return
            render()
            self.set_status(f"Node {index}: x {node['x']:.2f}  y {node['y']:.2f}  scale {node['scale']:.3f}")

        def save(*_a) -> None:
            if state["opened"] is None:
                show_message("Scoreboard", "Pumili muna ng IFF.", 0.3)
                return
            out = output_root() / "scoreboard" / Path(state["path"]).name
            out.parent.mkdir(parents=True, exist_ok=True)

            def work():
                return core.save_iff(state["opened"], out, allow_overwrite=True)

            self.run_bg(work, lambda rep: show_message("Scoreboard", f"Saved (bagong file):\n{rep['output']}", 0.4),
                        "Saving ...")

        box.add_widget(make_btn("PUMILI NG SCOREBOARD IFF", pick, 48, "primary"))
        box.add_widget(make_btn("BUKSAN ANG VISUAL EDITOR (pahiga, i-drag)", visual, 48, "primary"))
        box.add_widget(info)
        box.add_widget(listing)
        for widget in (node_in, x_in, y_in, s_in, z_in):
            box.add_widget(widget)
        box.add_widget(make_btn("APPLY SA NODE", apply, 48))
        box.add_widget(make_btn("SAVE BAGONG FILE", save, 48, "primary"))
        scroll = ScrollView()
        scroll.add_widget(box)
        popup = make_popup("SCOREBOARD LAYOUT", scroll, (0.94, 0.9))
        box.add_widget(make_btn("Close", lambda *_a: popup.dismiss(), 46))
        popup.open()

    # ------------------------------------------------------------ 2K14 converter
    def quick_port_14to20(self) -> None:
        """2K14 -> 2K20 PORT menu (v249): pick the 2K14 file, the 2K20 target, (optional) a BODY IFF, then START.
        The whole set is ported: main + _hi + _lo (missing ones are made from the main file) + body skin tone."""
        st = {"src": None, "dst": None, "body": None, "lods": False, "tint": 0, "size": 1, "zip": False, "brows": True, "compact": True, "head": True, "beard3d": True}
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))        # v292: scrollable menu, walang overlap / putol

        def fit(button, base_h):
            """Wrap long button text to the button width and grow its height so nothing is clipped."""
            button.halign = "center"
            button.valign = "middle"
            button.bind(width=lambda w, v: setattr(w, "text_size", (max(1, v - dp(20)), None)))
            button.bind(texture_size=lambda w, ts: setattr(w, "height", max(dp(base_h), ts[1] + dp(22))))
            return button

        box.add_widget(wrap_label("1) 2K14 source png####.iff  (ang _hi / _lo / body na katabi nito ay awtomatikong "
                                  "hahanapin, pati sa sub-folder)\n2) 2K20 target png####.iff\n3) Optional: BODY / ARM IFF "
                                  "para mag-match ang skin tone sa bagong mukha\n4) START PORT", 12))
        btn_src = make_btn("1) PILIIN ANG 2K14 SOURCE",
                           lambda: pick("src", btn_src, "2K14 SOURCE", (".iff", ".dds", ".png")), 46, "primary")
        btn_dst = make_btn("2) 2K20 TARGET (optional: BUILT-IN BASE kung wala)", lambda: pick("dst", btn_dst, "2K20 TARGET", (".iff",)), 46, "ghost")
        tint_names = ["OFF", "1 - LOW", "2 - MID", "3 - DAVID AUTO"]
        size_names = ["SD ONLY (512)", "SD + HD (1024)"]
        btn_size = make_btn("TEXTURE SIZE: " + size_names[1], lambda: cycle_size(), 42, "ghost")
        btn_zip = make_btn("EXPORT AS: IFF ONLY", lambda: toggle_zip(), 42, "ghost")
        btn_tint = make_btn("FACE SKIN TINT: " + tint_names[3], lambda: cycle_tint(), 42, "ghost")
        btn_body = make_btn("3) BODY IFF (optional)", lambda: pick("body", btn_body, "BODY IFF", (".iff",)), 42, "ghost")
        btn_lods = make_btn("AUTO _HI / _LO FILES: OFF (nasa loob na ng file ang HI + LO)", lambda: toggle_lods(), 42, "ghost")
        btn_compact = make_btn("COMPACT FILE (mas maliit, ~700KB): ON", lambda: toggle_compact(), 42, "ghost")
        btn_beard3d = make_btn("AUTO 3D BEARD (dagdag na file _3D.iff): ON", lambda: toggle_beard3d(), 42, "ghost")
        btn_head = make_btn("HEAD SHAPE (hugis ng ulo galing 2K14): ON", lambda: toggle_head(), 42, "ghost")
        btn_brows = make_btn("EVEN BROWS (pantay na kilay): ON", lambda: toggle_brows(), 42, "ghost")
        for _b, _h in ((btn_src, 46), (btn_dst, 46), (btn_size, 42), (btn_zip, 42), (btn_tint, 42), (btn_body, 42),
                       (btn_lods, 42), (btn_compact, 42), (btn_beard3d, 42), (btn_head, 42), (btn_brows, 42)):
            fit(_b, _h)
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(box)
        popup = make_popup("2K14 -> 2K20 PORT", scroll, (0.94, 0.9))

        def pick(key, button, title, exts):
            def chosen(path: Path) -> None:
                st[key] = Path(path)
                button.text = f"{title}: {Path(path).name}"
            PickerPopup(title, "file", exts, chosen, start=output_root()).open()

        def cycle_size() -> None:
            st["size"] = (st["size"] + 1) % 2
            btn_size.text = "TEXTURE SIZE: " + size_names[st["size"]]

        def toggle_zip() -> None:
            st["zip"] = not st["zip"]
            btn_zip.text = "EXPORT AS: " + ("ZIP (IFF + OBJ)" if st["zip"] else "IFF ONLY")

        def cycle_tint() -> None:
            st["tint"] = (st["tint"] + 1) % 4
            btn_tint.text = "FACE SKIN TINT: " + tint_names[st["tint"]]

        def toggle_compact() -> None:
            st["compact"] = not st["compact"]
            btn_compact.text = "COMPACT FILE (mas maliit, ~700KB): " + ("ON" if st["compact"] else "OFF")

        def toggle_beard3d() -> None:
            st["beard3d"] = not st["beard3d"]
            btn_beard3d.text = "AUTO 3D BEARD (dagdag na file _3D.iff): " + ("ON" if st["beard3d"] else "OFF")

        def toggle_head() -> None:
            st["head"] = not st["head"]
            btn_head.text = "HEAD SHAPE (hugis ng ulo galing 2K14): " + ("ON" if st["head"] else "OFF - texture lang, pantay ang kilay")

        def toggle_brows() -> None:
            st["brows"] = not st["brows"]
            btn_brows.text = "EVEN BROWS (pantay na kilay): " + ("ON" if st["brows"] else "OFF")

        def toggle_lods() -> None:
            st["lods"] = not st["lods"]
            btn_lods.text = "AUTO _HI / _LO FILES: " + ("ON (3 files)" if st["lods"] else "OFF (nasa loob na ng file ang HI + LO)")

        def start() -> None:
            if st["src"] is None:
                show_message("2K14 -> 2K20 PORT", "Piliin muna ang 2K14 source.", 0.3)
                return
            popup.dismiss()
            self.ws.port_tint = st["tint"]
            self.ws.port_brows = st["brows"]
            self.ws.port_compact = st["compact"]
            self.ws.port_head = st["head"]
            self._port_beard3d = bool(st["beard3d"])
            dst = st["dst"]
            if dst is None:                                  # v264: built-in 2K20 base, auto convert
                dst = self.ws.builtin_base_copy(Path(st["src"]).stem.split("_")[0] + ".iff" if Path(st["src"]).suffix.lower() == ".iff" else "png0.iff",
                                                high=bool(st["size"]))
            self._port_zip = bool(st["zip"])
            self._port_run(st["src"], dst, st["lods"], st["body"])

        for w in (btn_src, btn_dst, btn_size, btn_tint, btn_head, btn_beard3d, btn_brows, btn_compact, btn_zip, btn_body, btn_lods):
            box.add_widget(w)
        def extract_tex() -> None:
            def chosen(path: Path) -> None:
                out = output_root() / "textures14"
                self.run_bg(lambda: __import__("nba2k20.iff14", fromlist=["x"]).extract_textures(path, out),
                            lambda res: show_message("2K14 TEXTURE EXTRACTOR",
                                                     f"{len(res)} PNG na-save sa:\n{out}", 0.5),
                            "Extracting 2K14 textures ...")
            PickerPopup("2K14 TEXTURE EXTRACTOR", "file", (".iff",), chosen, start=output_root()).open()

        box.add_widget(fit(make_btn("START PORT", start, 54, "primary"), 54))
        box.add_widget(fit(make_btn("2K14 TEXTURE EXTRACTOR (PNG)", extract_tex, 42, "ghost"), 42))
        box.add_widget(fit(make_btn("Cancel", popup.dismiss, 42, "danger"), 42))
        popup.open()

    def _port_run(self, face: Path, target: Path, lods: bool, body) -> None:
        out_dir = output_root() / "converted"
        def work():
            res = self.ws.convert14_files(face, target, out_dir, None, 1.0, lods, body)
            if getattr(self, "_port_beard3d", False) and res.get("output"):      # v286: AUTO 3D BEARD (extra _3D.iff)
                try:
                    b = self.ws.port_3d_beard(Path(res["output"]), out_dir)
                    res["beard3d"] = b["output"]
                except Exception as exc:  # noqa: BLE001 - the normal port is never lost
                    res["beard3d_error"] = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
            return res
        self.run_bg(work, lambda res: self._port_done(res, face, target), "Converting 2K14 -> 2K20 ...")

    def _port_done(self, res, face, target) -> None:
        if res.get("output") and (res.get("beard3d") or res.get("beard3d_error")):
            res["output"] = f"{res['output']}\n3D BEARD: " + (res.get("beard3d") or ("hindi nagawa - " + res["beard3d_error"]))
        if getattr(self, "_port_zip", False) and res.get("output"):
            try:
                z = self.ws.zip_port_result(res, Path(res["output"]).with_suffix(".zip"))
                res["output"] = f"{res['output']}\nZIP: {z}"
            except Exception as exc:  # noqa: BLE001
                res["output"] = f"{res['output']}\n(ZIP failed: {exc})"
        if res.get("transplant"):
            # v174+: lahat ng PNG na may katugma sa target - face, hair/back of head, skin/face map,
            # atbp - at ang buong main/_hi/_lo set kung meron, awtomatikong na-port, walang pinili
            lines = ["2K14 -> 2K20 PORT done (buong cyberface set)", ""]
            files_done = res.get("set") or [{"name": Path(res["output"]).name,
                                              "report": res, "error": None}]
            for item in files_done:
                rep = item.get("report")
                if not rep:
                    lines.append(f"  [SKIPPED] {item['name']}: {item.get('error', '?')}")
                    continue
                lines.append(f"  {item['name']}:")
                if rep.get("whole_file"):
                    lines.append(f"    buong file kinopya (walang katugmang texture sa target)")
                for c in rep.get("copied") or []:
                    lines.append(f"    - {c['label']}  {c['from'][0]}x{c['from'][1]} -> {c['to'][0]}x{c['to'][1]}")
                if rep.get("unmatched"):
                    lines.append(f"    walang katugmang texture sa target: {', '.join(rep['unmatched'])}")
                sh = rep.get("shape")
                if sh:
                    extra = f", move {sh['mean_move']}" if "mean_move" in sh else ""
                    lines.append(f"    shape: {sh.get('vertices', '?')} vertex{extra} - naipasa (auto, walang pinili)")
                elif rep.get("shape_error"):
                    lines.append(f"    shape NOT changed: {rep['shape_error']}")
            if res.get("skipped"):
                lines += ["", "Nilaktawan:"] + [f"  - {s}" for s in res["skipped"]]
            lines += ["", f"Source: {Path(face).name}  ->  Target: {Path(target).name}",
                      "Saved (bagong file, hindi nabago ang original):", str(res.get("output") or "")]
            show_message("2K14 -> 2K20 PORT", "\n".join(lines), 0.6)
            return
        lines = ["2K14 -> 2K20 PORT done", "",
                 f"2K14: {Path(face).name}", f"2K20: {Path(target).name}",
                 f"Face: texture #{res['texture']} {res['size'][0]}x{res['size'][1]}"]
        if res["shape"]:
            lines.append(f"Shape: {res['shape']['vertices']} vertex, mean move {res['shape']['mean_move']} "
                         f"- naipasa (auto, walang pinili)")
        elif res["shape_error"]:
            lines.append(f"Shape NOT changed: {res['shape_error']}")
        else:
            lines.append("Shape: face lang (walang 2K14 head OBJ sa parehong folder; ilagay ang "
                          "png1013.obj katabi ng 2K14 file para mailipat din ang hugis)")
        lines += ["", "Saved (bagong file, hindi nabago ang original):", res["output"]]
        show_message("2K14 -> 2K20 PORT", "\n".join(lines), 0.6)


    def show_convert14(self) -> None:
        """Separate 2K14 -> 2K20 tools: face from a 2K14 cyberface IFF, preview/export, head shape fit."""
        from nba2k20 import convert14

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        note = wrap_label(
            "1) FACE -> 2K20: take the face of a 2K14 cyberface (png####.iff, or a DDS / PNG) and put it on a "
            "2K20 cyberface of the OPEN OBB (alpha = hair coverage is kept).\n"
            "2) CONVERT ALL: pick a folder full of 2K14 png####.iff; each one goes to the 2K20 cyberface with "
            "the SAME number (png1013.iff -> 1013).\n"
            "3) PREVIEW: see the 2K14 face and save it as PNG.\n"
            "4) HEAD SHAPE: fit the 2K20 head (assets/head_default.obj) to a 2K14 head OBJ, e.g. HEADKD.obj.\n"
            "5) AUTO (v163): pick the 2K14 png####.iff, then pick the 2K20 png####.iff to replace -> face + head shape "
            "are moved and saved as a NEW file (output/converted). No OBB needed. The head shape needs the 2K14 head OBJ in the SAME folder "
            "(png1013.obj, or the only .obj ending in 1013); without it only the face moves.", 13)
        cfid = make_input("Target 2K20 Cyberface ID, e.g. 1013  (for FACE -> 2K20)")
        strength = make_input("Head shape strength 0 - 1  (empty = 1)")
        scroll = ScrollView()
        scroll.add_widget(box)
        popup = make_popup("2K14 CONVERTER", scroll, (0.94, 0.9))
        face_types = (".iff", ".dds", ".png")

        def say(text: str) -> None:
            show_message("2K14 Converter", text, 0.5)

        def face_to_cf() -> None:
            if self.ws.session is None:
                say("Open an OBB first (Open OBB on the home screen), then come back here.")
                return
            text = cfid.text.strip()
            if not text:
                say("Type the 2K20 Cyberface ID to receive the face (example 1013).")
                return

            def resolved(found) -> None:
                rows = [r for r in (found or []) if r["editable"]]
                if not rows:
                    say(f"No editable cyberface entry found for '{text}'.")
                    return

                def picked(path: Path) -> None:
                    def done(report) -> None:
                        self.set_header(f"{self.ws.session.path.name}   (staged: {self.ws.staged_count})")
                        self.set_status("2K14 face staged - use Save OBB copy")
                        lines = ["2K14 FACE -> 2K20  done", ""]
                        for item in report["patched"]:
                            lines.append(f"OK  {item['label']}  texture #{item['texture']} "
                                         f"{item['size'][0]}x{item['size'][1]} {item['format']}")
                        for item in report["skipped"]:
                            lines.append(f"SKIPPED  {item['label']}: {item['reason']}")
                        lines += ["", "Every file listed OK now has the new face (close-up AND far LOD files).",
                                  "Close the OBB list and tap 'Save OBB copy'. Your original OBB stays untouched."]
                        say("\n".join(lines))

                    self.run_bg(lambda: self.ws.cyberface_face14_rows(rows, path), done, "Converting 2K14 face ...")

                PickerPopup("Choose the 2K14 face (.iff / DDS / PNG)", "file", face_types, picked,
                            start=output_root()).open()

            self.run_bg(lambda: self.ws.resolve_cyberface(text, ""), resolved, "Looking up cyberface ...")

        def convert_all() -> None:
            if self.ws.session is None:
                say("Open an OBB first (Open OBB on the home screen), then come back here.")
                return

            def picked(folder: Path) -> None:
                def work():
                    def progress(n, total, name):
                        Clock.schedule_once(lambda _dt: self.set_status(f"2K14 -> 2K20  {n}/{total}  {name}"), 0)

                    return self.ws.convert_all_face14(folder, progress)

                def done(report) -> None:
                    self.set_header(f"{self.ws.session.path.name}   (staged: {self.ws.staged_count})")
                    self.set_status("2K14 faces staged - use Save OBB copy")
                    lines = [f"CONVERT ALL done  ({report['total']} files)",
                             f"Converted: {len(report['converted'])}",
                             f"No matching 2K20 cyberface: {len(report['skipped'])}",
                             f"Failed: {len(report['failed'])}"]
                    for title, rows in (("Skipped", report["skipped"]), ("Failed", report["failed"])):
                        if rows:
                            lines.append("")
                            lines.append(f"{title}:")
                            lines += [f"  {name}: {why}" for name, why in rows[:20]]
                            if len(rows) > 20:
                                lines.append(f"  ... +{len(rows) - 20} more (see error_log.txt)")
                    for name, why in report["failed"]:
                        log_error(f"convert all: {name}", RuntimeError(why))
                    lines.append("")
                    lines.append("Close this and tap 'Save OBB copy'. Your original OBB stays untouched.")
                    show_message("2K14 Converter", "\n".join(lines), 0.7)

                self.run_bg(work, done, "Converting 2K14 faces ...")

            PickerPopup("Choose the folder with the 2K14 png####.iff files", "dir", (), picked,
                        start=output_root()).open()

        def preview_face() -> None:
            def picked(path: Path) -> None:
                def work():
                    image = convert14.load_face_image(path)
                    target = output_root() / "png" / f"{path.stem}_face14.png"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target)
                    shown = image.convert("RGB")                  # hair alpha would make the face see-through
                    if max(shown.size) > 1024:
                        shown.thumbnail((1024, 1024))
                    return target, image.size, shown.size, shown.convert("RGBA").tobytes()

                def done(result) -> None:
                    target, size, shown_size, rgba = result
                    view = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
                    # texture from raw pixels (like every other preview) - no Image(source=<file in storage>)
                    tex = Texture.create(size=shown_size, colorfmt="rgba")
                    tex.blit_buffer(rgba, colorfmt="rgba", bufferfmt="ubyte")
                    tex.flip_vertical()
                    picture = Image(fit_mode="contain")
                    picture.texture = tex
                    view.add_widget(picture)
                    view.add_widget(make_label(escape_markup(f"{size[0]}x{size[1]}  saved:\n{target}"), 12,
                                               size_hint_y=None, height=dp(48)))
                    pop = make_popup("2K14 FACE", view, (0.94, 0.8))
                    view.add_widget(make_btn("Close", pop.dismiss, 46))
                    pop.open()

                self.run_bg(work, done, "Reading 2K14 face ...")

            PickerPopup("Choose the 2K14 cyberface (.iff / DDS / PNG)", "file", face_types, picked,
                        start=output_root()).open()

        def head_shape() -> None:
            target = ASSETS / "head_default.obj"
            if not target.exists():
                say("assets/head_default.obj is missing from this build.")
                return
            try:
                amount = float(strength.text.strip()) if strength.text.strip() else 1.0
            except ValueError:
                say("Strength must be a number from 0 to 1.")
                return

            def picked(path: Path) -> None:
                def work():
                    out = output_root() / "obj" / f"{path.stem}_fit.obj"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    return convert14.shape_fit_files(target, path, out, strength=amount)

                def done(report) -> None:
                    say(f"HEAD SHAPE FIT done\n{report['vertices']} vertices moved "
                        f"(2K14 head: {report['source_vertices']} vertices)\n"
                        f"mean move {report['mean_move']}   strength {report['strength']}\n\n"
                        f"Saved:\n{report['output']}\n\n"
                        "Same vertex count / UV / faces as the 2K20 head, so it can be imported "
                        "(Cyberface Workshop / OBJ).")

                self.run_bg(work, done, "Fitting head shape ...")

            PickerPopup("Choose the 2K14 head OBJ (e.g. HEADKD.obj)", "file", (".obj",), picked,
                        start=output_root()).open()

        def _auto_lines(res) -> list[str]:
            lines = [f"AUTO 2K14 -> 2K20  cyberface #{res['cfid']}", ""]
            for item in res["patched"]:
                shape = item["shape"]
                extra = (f"  shape: {shape['vertices']} vertex, mean move {shape['mean_move']}" if shape
                         else (f"  shape SKIPPED: {item['shape_error']}" if item["shape_error"] else "  face lang"))
                lines.append(f"OK  {item['label']}  texture #{item['texture']}{extra}")
            for item in res["skipped"]:
                lines.append(f"SKIPPED  {item['label']}: {item['reason']}")
            if res["head_obj"]:
                lines += ["", f"2K14 head OBJ: {Path(res['head_obj']).name}"]
            else:
                lines += ["", "Walang 2K14 head OBJ sa folder, kaya FACE lang ang nalipat. Ilagay ang HEAD obj sa "
                          "parehong folder (png1013.obj) at ulitin para mailipat din ang hugis."]
            lines += ["", "I-close ito at pindutin ang 'Save OBB copy'. Hindi nababago ang original OBB."]
            return lines

        def auto_one() -> None:
            """Pick the 2K14 png####.iff, then pick the 2K20 png####.iff to replace; result is saved as a copy."""
            try:
                amount = float(strength.text.strip()) if strength.text.strip() else 1.0
            except ValueError:
                say("Strength must be a number from 0 to 1.")
                return

            def picked_14(face: Path) -> None:
                def picked_20(target: Path) -> None:
                    def done(res) -> None:
                        if res.get("transplant"):
                            lines = ["CYBERFACE COPY done (IFF -> IFF)", "",
                                     f"Source: {Path(face).name}", f"Target: {Path(target).name}", ""]
                            for part in res.get("set", []):
                                if part["error"]:
                                    lines.append(f"{part['name']}: HINDI NAKOPYA - {part['error']}")
                                    continue
                                rep = part["report"]
                                if rep.get("whole_file"):
                                    src_name = part.get("from")
                                    lines.append(f"{part['name']}: BUONG FILE ng source ang kinopya"
                                                 + (f" ({src_name})" if src_name else "")
                                                 + " - mukha, hair, hugis, lahat")
                                    continue
                                labels = ", ".join(c["label"].split(" 1")[0].split(" 2")[0].split(" 6")[0]
                                                   for c in rep["copied"]) or "walang texture"
                                shape = "hugis OK" if rep["shape"] else f"hugis HINDI ({rep['shape_error']})"
                                lines.append(f"{part['name']}: {labels}; {shape}")
                            for item in res.get("skipped", []):
                                lines.append(f"Skipped: {item}")
                            lines.append("")
                            for item in res["copied"]:
                                lines.append(f"OK  {item['label']}  {item['from'][0]}x{item['from'][1]} -> "
                                             f"{item['to'][0]}x{item['to'][1]}")
                            for item in res["unmatched"]:
                                lines.append(f"HINDI NAILIPAT (walang katumbas sa target): {item}")
                            if res.get("obj_files"):
                                lines.append("OBJ (3D head) na kasama sa output folder - buksan sa Workshop / Blender "
                                             "para sa 3D buhok / balbas:")
                                lines += [f"  {x}" for x in res["obj_files"]]
                                lines.append("")
                            if res.get("unmatched") or not res.get("copied"):
                                tt = res.get("target_textures") or []
                                lines.append("")
                                if tt:
                                    lines.append(f"Mga texture na nakikita sa TARGET ({Path(target).name}):")
                                    lines += [f"  {x}" for x in tt]
                                else:
                                    lines.append(f"Ang TARGET ({Path(target).name}) ay WALANG texture na nakita ng tool "
                                                 "- hindi ito ang file na may face/hair texture. Subukan ang "
                                                 "png####_hi.iff o ibang cyberface na may texture, at ipadala sa akin "
                                                 "ang target file kung gusto mong i-support ang layout nito.")
                                lines.append("")
                            if res["shape"]:
                                lines.append(f"OK  Head shape ({res['shape']['vertices']:,} vertex)")
                            else:
                                lines.append(f"Head shape HINDI nailipat: {res['shape_error']}")
                            if not res["face_diffuse"]:
                                lines.append("Walang FACE DIFFUSE sa source - ang mukha (kulay) ay nasa ibang file "
                                             "(hal. png####_hi.iff); piliin iyon bilang source para mailipat din.")
                            lines += ["", "Saved (bagong file, hindi nabago ang original):", res["output"]]
                            say("\n".join(lines))
                            return
                        lines = ["AUTO 2K14 -> 2K20 done", "",
                                 f"2K14: {Path(face).name}", f"2K20: {Path(target).name}",
                                 f"Face: texture #{res['texture']} {res['size'][0]}x{res['size'][1]}"]
                        if res["shape"]:
                            lines.append(f"Shape: {res['shape']['vertices']} vertex, mean move {res['shape']['mean_move']}")
                        elif res["shape_error"]:
                            lines.append(f"Shape NOT changed: {res['shape_error']}")
                        else:
                            lines.append("Shape: face lang (walang 2K14 head OBJ sa folder; ilagay ang png1013.obj "
                                         "katabi ng 2K14 file para mailipat din ang hugis)")
                        lines += ["", "Saved (bagong file, hindi nabago ang original):", res["output"]]
                        say("\n".join(lines))

                    out_dir = output_root() / "converted"
                    self.run_bg(lambda: self.ws.convert14_files(face, target, out_dir, None, amount), done,
                                "Converting 2K14 -> 2K20 ...")

                PickerPopup("Ngayon piliin ang 2K20 png####.iff na papalitan", "file", (".iff",), picked_20,
                            start=output_root()).open()

            PickerPopup("Piliin ang 2K14 png####.iff", "file", face_types, picked_14, start=output_root()).open()

        def auto_all() -> None:
            if self.ws.session is None:
                say("Open an OBB first (Open OBB on the home screen), then come back here.")
                return
            try:
                amount = float(strength.text.strip()) if strength.text.strip() else 1.0
            except ValueError:
                say("Strength must be a number from 0 to 1.")
                return

            def picked(folder: Path) -> None:
                def work():
                    def progress(n, total, name):
                        Clock.schedule_once(lambda _dt: self.set_status(f"AUTO 2K14 -> 2K20  {n}/{total}  {name}"), 0)

                    return self.ws.auto_convert14_all(folder, progress, amount)

                def done(report) -> None:
                    self.set_header(f"{self.ws.session.path.name}   (staged: {self.ws.staged_count})")
                    shaped = sum(1 for _n, _c, has_obj, errs in report["converted"] if has_obj and not errs)
                    lines = [f"AUTO ALL done  ({report['total']} files)",
                             f"Converted: {len(report['converted'])}  (with head shape: {shaped})",
                             f"No matching 2K20 cyberface / skipped: {len(report['skipped'])}",
                             f"Failed: {len(report['failed'])}"]
                    shape_fail = [(n, e) for n, _c, _o, errs in report["converted"] for e in errs]
                    for title, rows in (("Skipped", report["skipped"]), ("Failed", report["failed"]),
                                        ("Shape not changed", shape_fail)):
                        if rows:
                            lines += ["", f"{title}:"] + [f"  {n}: {w}" for n, w in rows[:20]]
                    for name, why in report["failed"]:
                        log_error(f"auto convert: {name}", RuntimeError(why))
                    lines += ["", "Close this and tap 'Save OBB copy'. Your original OBB stays untouched."]
                    show_message("2K14 Converter", "\n".join(lines), 0.7)

                self.run_bg(work, done, "Auto converting 2K14 ...")

            PickerPopup("Choose the folder with the 2K14 png####.iff (+ head .obj)", "dir", (), picked,
                        start=output_root()).open()

        for widget in (note, cfid, make_btn("AUTO: 2K14 png.iff  ->  2K20 png.iff", auto_one, 54, "primary"),
                       make_btn("AUTO ALL (OBB, FOLDER): face + shape", auto_all, 54, "primary"), strength,
                       make_btn("2K14 FACE  ->  2K20 CYBERFACE", face_to_cf, 52, "primary"),
                       make_btn("CONVERT ALL (FOLDER)  ->  2K20", convert_all, 52, "primary"),
                       make_btn("PREVIEW / EXPORT 2K14 FACE PNG", preview_face, 50),
                       make_btn("HEAD SHAPE: FIT 2K20 HEAD TO 2K14 OBJ", head_shape, 50),
                       make_btn("Close", popup.dismiss, 46)):
            box.add_widget(widget)
        popup.open()

    # ------------------------------------------------------------ cyberface
    def show_cyberface(self) -> None:
        """Cyberface tools: find by CFID, import/replace, export, auto PNG."""
        if self.ws.session is None:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
        cfid = make_input("Existing Cyberface ID, e.g. 1013")
        pattern = make_input("File name pattern (optional), e.g. CF{id}.IFF")
        result = make_label(
            "Type the Cyberface ID, then choose an action.\n"
            "Other ways to pick the entry:  #123 = OBB entry number,  hash:ABCD1234.",
            13, halign="left", valign="top",
            text_size=(Window.width * 0.8, None), size_hint_y=None,
        )
        result.bind(texture_size=lambda w, size: setattr(w, "height", size[1]))
        holder = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(4))
        holder.bind(minimum_height=holder.setter("height"))
        holder.add_widget(result)
        scroll = ScrollView()
        scroll.add_widget(holder)
        popup = make_popup("Cyberface", box, (0.96, 0.92))

        def say(text: str) -> None:
            result.text = escape_markup(text)

        def describe(row: dict) -> str:
            return (
                f"#{row['index']}  {row['label']}  [{row['via']}]  {row['type']}  "
                f"{row['length']:,} bytes  slot {row['slot']:,}"
            )

        def resolve(then) -> None:
            text = cfid.text.strip()
            if not text:
                say("Enter a Cyberface ID first.")
                return

            def work():
                return self.ws.resolve_cyberface(text, pattern.text)

            def done(found):
                if not found:
                    say(
                        f"No OBB entry found for '{text}'.\n\n"
                        "This OBB identifies files only by a hash of their name. Try:\n"
                        "- the exact file name in the pattern box (use {id} for the number)\n"
                        "- '#' + the entry number from the IFF list (example #4020)\n"
                        "- 'hash:' + the 8-digit hash shown in the list"
                    )
                    return
                if not found[0]["editable"]:
                    say(describe(found[0]) + "\n\nThis entry is not a compressed IFF.")
                    return
                then(found)

            self.run_bg(work, done, "Looking up cyberface ...")

        def do_find(found) -> None:
            say("Found:\n" + "\n".join(describe(row) for row in found))

        def do_import(found) -> None:
            row = found[0]

            def picked(path: Path) -> None:
                def done(report) -> None:
                    self.set_header(
                        f"{self.ws.session.path.name}   (staged: {self.ws.staged_count})"
                    )
                    self.set_status("Cyberface staged - use Save OBB copy")
                    say(
                        f"CFID {cfid.text.strip()} IMPORTED  {report['label']}  "
                        f"{report['old_size']:,} -> {report['new_size']:,} bytes  "
                        f"slot {report['slot']:,}  ({report['mode']})\n\n"
                        "Staged only. Close this window and tap 'Save OBB copy'; "
                        "your original OBB stays untouched."
                    )

                self.run_bg(
                    lambda: self.ws.cyberface_import(row["index"], path),
                    done, "Importing cyberface IFF ...",
                )

            PickerPopup("Choose the cyberface IFF", "file", (".iff",), picked).open()

        def do_export(found) -> None:
            row = found[0]
            folder = output_root() / "cyberface"

            def done(path) -> None:
                say(f"EXPORTED\n{path}")

            self.run_bg(
                lambda: self.ws.export_entry(row["index"], folder),
                done, "Exporting cyberface IFF ...",
            )

        def do_auto_png(found) -> None:
            row = found[0]

            def picked(path: Path) -> None:
                def done(report) -> None:
                    self.set_header(
                        f"{self.ws.session.path.name}   (staged: {self.ws.staged_count})"
                    )
                    self.set_status("Cyberface PNG staged - use Save OBB copy")
                    resized = report.get("resized_from")
                    say(
                        f"AUTO PNG  {report['label']}\n"
                        f"Texture #{report['texture']}  {report['size'][0]}x{report['size'][1]}  "
                        f"{report['format']}\n"
                        + (f"Resized from {resized[0]}x{resized[1]}\n" if resized else "")
                        + f"Staged {report['staged_size']:,} bytes.\n\n"
                        "Close this window and tap 'Save OBB copy'."
                    )

                self.run_bg(
                    lambda: self.ws.cyberface_auto_png(row["index"], path),
                    done, "Importing PNG ...",
                )

            PickerPopup("Choose the face PNG (any size)", "file", (".png",), picked,
                        start=output_root() / "png").open()

        box.add_widget(cfid)
        box.add_widget(pattern)
        box.add_widget(scroll)
        box.add_widget(make_btn("Find", lambda: resolve(do_find), 46))
        box.add_widget(make_btn("IMPORT / REPLACE EXISTING CFID", lambda: resolve(do_import), 50, "primary"))
        box.add_widget(make_btn("EXPORT CYBERFACE IFF", lambda: resolve(do_export), 50))
        box.add_widget(make_btn("AUTO PNG -> CYBERFACE", lambda: resolve(do_auto_png), 50))
        box.add_widget(make_btn("Close", popup.dismiss, 46))
        popup.open()

    # ------------------------------------------------------------ audio explorer
    def show_audio(self) -> None:
        """Audio / OGG Explorer: same look as the IFF list (name, #id, Export, star) + bottom player."""
        self.mode = "audio"
        self.ws.opened = None
        self.aud = {"rows": [], "view": [], "sound": None, "index": None, "name": "", "pos": 0.0,
                    "length": 0.0, "paused": False, "drag": False, "order": [], "tick": None}
        self.set_header("Audio / OGG Explorer")
        self.clear_body()
        top = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        self.aud_search = make_input("Search song / music name ...")
        self.aud_search.bind(text=lambda *_a: self._aud_filter())
        self.aud_kind = Drop(text="All audio", values=["All audio", "Named songs", "Theme", "Music", "Ambience", "Voice",
                                                       "Jingle", "SFX", FAV_LABEL],
                             size_hint_x=0.5)
        self.aud_kind.bind(text=lambda *_a: self._aud_filter())
        top.add_widget(self.aud_search)
        top.add_widget(self.aud_kind)
        self.body.add_widget(top)
        bar = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self.aud_counter = left_label("scanning ...", 12, MUTED)
        self.aud_sel_btn = make_btn("MULTI AUDIO", self._aud_toggle_select, 36, "primary", font_size=sp(12), size_hint_x=0.36)
        self.aud_sort = Drop(text="Sort: Named first",
                             values=["Sort: Named first", "Sort: Number", "Sort: Name A-Z", "Sort: Longest", "Sort: Shortest"],
                             size_hint_x=0.4, font_size=sp(11))
        self.aud_sort.bind(text=lambda *_a: self._aud_filter())
        for w in (self.aud_counter, self.aud_sel_btn, self.aud_sort):
            bar.add_widget(w)
        self.body.add_widget(bar)
        self.aud_sel_bar = BoxLayout(size_hint_y=None, height=0, spacing=dp(6), opacity=0)
        self.aud_list = RowList()
        self.aud_list.hold_to_select = True
        self.aud_list.on_check = self._aud_checks_changed
        self.aud_list.on_mode = self._aud_select_ui
        self.aud_sel_all = make_btn("All shown", self.aud_list.check_all, 46, "ghost", font_size=sp(12))
        self.aud_sel_none = make_btn("Clear", self.aud_list.check_none, 46, "ghost", font_size=sp(12))
        self.aud_sel_exp = make_btn("Export (0)", self._aud_export_checked, 46, "primary", font_size=sp(12))
        for w in (self.aud_sel_all, self.aud_sel_none, self.aud_sel_exp):
            self.aud_sel_bar.add_widget(w)
        self.body.add_widget(self.aud_sel_bar)
        self.body.add_widget(self.aud_list)

        # bottom player
        card = Card(kind="bar", orientation="vertical", size_hint_y=None, height=dp(128),
                    padding=dp(10), spacing=dp(4))
        self.aud_title = left_label("No track playing", 14, TEXT, height=dp(22))
        timing = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        self.aud_t0 = make_label("0:00", 12, MUTED, size_hint_x=None, width=dp(42))
        self.aud_slider = Slider(min=0, max=1, value=0, cursor_size=(dp(22), dp(22)))
        self.aud_slider.bind(on_touch_down=self._aud_touch_down, on_touch_up=self._aud_touch_up)
        self.aud_t1 = make_label("0:00", 12, MUTED, size_hint_x=None, width=dp(42))
        for w in (self.aud_t0, self.aud_slider, self.aud_t1):
            timing.add_widget(w)
        ctl = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        ctl.add_widget(make_btn("|<", lambda: self._aud_step(-1), 44))
        self.aud_pp = make_btn("Play", self._aud_toggle, 44, "primary")
        ctl.add_widget(self.aud_pp)
        ctl.add_widget(make_btn("Stop", self._aud_stop, 44))
        ctl.add_widget(make_btn(">|", lambda: self._aud_step(1), 44))
        for w in (self.aud_title, timing, ctl):
            card.add_widget(w)
        self.body.add_widget(card)

        bar2 = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        bar2.add_widget(make_btn("Save OBB copy", self.save_obb_copy, 52, "primary"))
        bar2.add_widget(make_btn("Rename", self._aud_rename_current, 52))
        bar2.add_widget(make_btn("Deep scan", self._aud_deep_scan, 52))
        bar2.add_widget(make_btn("Back", self._aud_close, 52))
        self.body.add_widget(bar2)

        self.run_bg(self.ws.audio_scan, self._aud_loaded, "Scanning audio ...")

    def _aud_loaded(self, rows) -> None:
        if self.mode != "audio":
            return
        self.aud["rows"] = rows
        self._aud_header()
        self._aud_filter()

    def _aud_header(self) -> None:
        rows = self.aud["rows"]
        total = sum(r["seconds"] for r in rows)
        self.set_header(f"Audio / OGG Explorer   {len(rows)} audio \u2022 {total / 60:,.1f} min")

    def _aud_reload(self) -> None:
        self.run_bg(self.ws.audio_scan, lambda rows: (self.aud.update(rows=rows), self._aud_header(), self._aud_filter()),
                    "Refreshing ...")

    def _aud_deep_scan(self) -> None:
        confirm("Deep scan",
                "Hahanapin ang audio na nakatago sa loob ng ibang entry. MATAGAL ito (ilang minuto) pero isang beses lang - "
                "ise-save ang resulta kaya mabilis na sa susunod. Ituloy?",
                lambda: self.run_bg(self.ws.audio_deep_scan, self._aud_loaded, "Deep scanning (matagal) ..."))

    def _aud_filter(self) -> None:
        text = self.aud_search.text.strip().lower()
        kind = self.aud_kind.text
        rows = self.aud["rows"]

        def keep(r) -> bool:
            if text and text not in r["search"] and text not in r["title"].lower():
                return False
            if kind == "All audio":
                return True
            if kind == "Named songs":
                return bool(r.get("real_name"))
            if kind == FAV_LABEL:
                return self.is_fav(r["title"])
            return r["auto_name"].startswith(kind)

        view = [r for r in rows if keep(r)]
        mode = self.aud_sort.text
        if mode == "Sort: Named first":
            view.sort(key=lambda r: (0 if r.get("real_name") else 1, IffBrowser._natural(r["title"])
                                     if r.get("real_name") else [r["number"]]))
        elif mode == "Sort: Name A-Z":
            view.sort(key=lambda r: IffBrowser._natural(r["title"]))
        elif mode == "Sort: Longest":
            view.sort(key=lambda r: -r["seconds"])
        elif mode == "Sort: Shortest":
            view.sort(key=lambda r: r["seconds"])
        else:
            view.sort(key=lambda r: r["number"])
        self.aud["view"] = view
        self.aud_counter.text = f"{len(view)} entries  |  Audio {len(rows)}"
        out = []
        for r in view:
            ch = f"{r['channels']} ch" if r["channels"] else "? ch"
            rate = f"{r['rate']} Hz" if r["rate"] else "? Hz"
            length = self._aud_fmt(r["seconds"]) if r["seconds"] else "?:??"
            sub = (f"#{r['index'] if not r['embedded'] else r['number']}  |  Audio  |  {length}  |  {r['codec']}  |  {ch}  |  {rate}"
                   f"  |  {core.readable_size(r['size'])}")
            if r["embedded"]:
                sub += f"  |  in #{r['parent']}"
            if r["staged"]:
                sub += f"  [color={ACCENT_HEX}]EDITED[/color]"
            out.append(row_entry(
                r["title"], sub,
                partial(self._aud_play, r["index"], r["title"]),
                key=r["index"],
                star=self.is_fav(r["title"]),
                on_star=partial(self.set_fav, r["title"]),
                on_export=partial(self._aud_export, r["index"], r["name"]),
                on_import=partial(self._aud_replace, r["index"]),
            ))
        self.aud_list.set_rows(out)

    # --- multi-select (same MULTI button as the IFF list)
    def _aud_toggle_select(self) -> None:
        self.aud_list.set_select_mode(not self.aud_list.select_mode)

    def _aud_select_ui(self, on: bool) -> None:
        self.aud_sel_btn.text = "DONE" if on else "MULTI AUDIO"
        self.aud_sel_btn.kind = "danger" if on else "primary"
        self.aud_sel_bar.height = dp(46) if on else 0
        self.aud_sel_bar.opacity = 1 if on else 0

    def _aud_checks_changed(self, count: int) -> None:
        self.aud_sel_exp.text = f"Export ({count})"

    def _aud_export_checked(self) -> None:
        names = {r["index"]: r["name"] for r in self.aud["rows"]}
        picked = sorted(self.aud_list.checked)
        if not picked:
            show_message("Export", "Mag-tick muna ng kahit isang track.", 0.3)
            return
        folder = output_root() / "audio"

        def work():
            for n, index in enumerate(picked, 1):
                self.set_status(f"Exporting {n}/{len(picked)} ...")
                self.ws.export_entry(index, folder, names.get(index))
            return len(picked), folder

        confirm("Export selected", f"Export {len(picked)} track(s) to:\n{folder}",
                lambda: self.run_bg(work, lambda r: show_message("Exported", f"{r[0]} track(s) saved to:\n{r[1]}", 0.35),
                                    "Exporting ..."))

    # --- player
    @staticmethod
    def _aud_fmt(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60}:{seconds % 60:02d}"

    def _aud_release(self) -> None:
        sound = self.aud.get("sound")
        if sound is not None:
            try:
                sound.stop()
                sound.unload()
            except Exception:  # noqa: BLE001
                pass
        self.aud["sound"] = None

    def _aud_play(self, index: int, label: str = "", *_a) -> None:
        self._aud_release()
        try:
            path = self.ws.audio_to_file(index)
            from kivy.core.audio import SoundLoader
            sound = SoundLoader.load(str(path))
            if sound is None:
                raise RuntimeError("Hindi ma-play ng phone ang audio na ito. I-Export mo at buksan sa music player.")
        except Exception as error:  # noqa: BLE001
            show_message("Audio", friendly_error(error), 0.35)
            return
        a = self.aud
        a.update(sound=sound, index=index, name=label or a.get("name", ""), paused=False, pos=0.0)
        a["order"] = [r["index"] for r in a.get("view", [])]
        a["names"] = {r["index"]: r["title"] for r in a.get("rows", [])}
        sound.play()
        a["length"] = float(sound.length or 0)
        self.aud_title.text = escape_markup(f"{label}  ({core.readable_size(path.stat().st_size)})")
        self.aud_pp.text = "Pause"
        if a["tick"] is None:
            a["tick"] = Clock.schedule_interval(self._aud_tick, 0.25)

    def _aud_toggle(self) -> None:
        a = self.aud
        sound = a.get("sound")
        if sound is None:
            if a.get("index") is not None:
                self._aud_play(a["index"], a["name"])
            return
        if a["paused"]:
            sound.play()
            if a["pos"]:
                sound.seek(a["pos"])
            a["paused"] = False
            self.aud_pp.text = "Pause"
        else:
            a["pos"] = float(sound.get_pos() or 0)
            sound.stop()
            a["paused"] = True
            self.aud_pp.text = "Play"

    def _aud_stop(self) -> None:
        self._aud_release()
        self.aud.update(paused=False, pos=0.0)
        self.aud_pp.text = "Play"
        self.aud_slider.value = 0
        self.aud_t0.text = "0:00"

    def _aud_step(self, delta: int) -> None:
        order, current = self.aud.get("order") or [r["index"] for r in self.aud.get("view", [])], self.aud.get("index")
        if not order:
            return
        i = order.index(current) + delta if current in order else 0
        i = max(0, min(len(order) - 1, i))
        names = self.aud.get("names") or {r["index"]: r["title"] for r in self.aud["rows"]}
        self._aud_play(order[i], names.get(order[i], ""))

    def _aud_tick(self, _dt) -> None:
        if self.mode != "audio":
            self._aud_close_player()
            return False
        a = self.aud
        sound = a.get("sound")
        if sound is None or a["paused"] or a["drag"]:
            return
        pos = float(sound.get_pos() or 0)
        length = a["length"] or float(sound.length or 0)
        a["length"] = length
        if sound.state == "stop" and length and pos >= length - 0.6:
            self._aud_stop()
            return
        self.aud_slider.max = max(length, 1)
        self.aud_slider.value = min(pos, self.aud_slider.max)
        self.aud_t0.text, self.aud_t1.text = self._aud_fmt(pos), self._aud_fmt(length)

    def _aud_touch_down(self, slider, touch) -> None:
        if slider.collide_point(*touch.pos):
            self.aud["drag"] = True

    def _aud_touch_up(self, slider, touch) -> None:
        if not self.aud.get("drag"):
            return
        self.aud["drag"] = False
        sound = self.aud.get("sound")
        if sound is not None and not self.aud["paused"]:
            sound.seek(slider.value)
        else:
            self.aud["pos"] = slider.value

    def _aud_export(self, index: int, name: str, *_a) -> None:
        folder = output_root() / "audio"
        self.run_bg(lambda: self.ws.export_entry(index, folder, name),
                    lambda path: show_message("Exported", f"{path}", 0.3), f"Exporting {name} ...")

    def _aud_replace(self, index: int, *_a) -> None:
        def picked(chosen: Path):
            def done(report):
                self.set_status(f"Audio staged: {report['label']}  ({report['new_size']:,} bytes)")
                self._aud_reload()
                show_message("Audio napalitan",
                             f"{report['label']}\nDati: {report['old_size']:,} bytes\nBago: {report['new_size']:,} bytes"
                             + ("\n(Na-convert sa OGG Vorbis nang automatic)" if report.get("converted") else "") + "\n\n"
                             "Pindutin ang Save OBB copy para i-save sa OBB.", 0.4)
            if self.aud.get("index") == index:
                self._aud_stop()
            self.run_bg(lambda: self.ws.replace_audio(
                index, chosen, progress=lambda f: self.set_status(f"Converting to OGG ... {int(f * 100)}%")),
                done, "Converting / replacing audio ...")
        PickerPopup("Piliin ang bagong audio (.ogg / .mp3 / .wav / .m4a / .flac ...) - auto convert sa OGG", "file", AUDIO_PICK_EXT, picked, start=output_root()).open()

    def _aud_rename_current(self) -> None:
        """Rename the track that is playing / last played (tap a row first)."""
        index = self.aud.get("index")
        row = next((r for r in self.aud["rows"] if r["index"] == index), None)
        if row is None:
            show_message("Rename", "Pumili / mag-play muna ng track, tapos pindutin ang Rename.", 0.3)
            return
        self._aud_rename(row)

    def _aud_rename(self, row: dict, *_a) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(6))
        field = make_input(f"Pangalan (hal. {row['auto_name']})", 46)
        field.text = row["name"][:-4] if row["name"].lower().endswith(".ogg") else row["name"]
        box.add_widget(field)
        box.add_widget(make_label(f"Auto name: {row['auto_name']}   (iwanang blangko para ibalik)", 12, MUTED,
                                  size_hint_y=None, height=dp(24)))
        popup = make_popup("Rename track", box, (0.92, 0.36))

        def save():
            popup.dismiss()
            try:
                self.ws.rename_audio(row["key"], field.text)
            except Exception as error:  # noqa: BLE001
                show_message("Rename", friendly_error(error), 0.3)
                return
            self._aud_reload()

        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        buttons.add_widget(make_btn("Save", save, 48, "primary"))
        buttons.add_widget(make_btn("Cancel", popup.dismiss, 48))
        box.add_widget(buttons)
        popup.open()

    def _aud_close_player(self) -> None:
        a = getattr(self, "aud", None)
        if a:
            self._aud_release()
            if a.get("tick") is not None:
                a["tick"].cancel()
                a["tick"] = None

    def _aud_close(self) -> None:
        self._aud_close_player()
        self.show_entries()

    def play_audio(self, index: int, label: str) -> None:
        """Small player for OGG entries: Play / Stop / Export .ogg."""
        try:
            path = self.ws.audio_to_file(index)
        except Exception as error:  # noqa: BLE001
            show_message("Audio", friendly_error(error), 0.3)
            return
        state = {"sound": None}
        info = make_label(escape_markup(f"{label}\n#{index}  |  {core.readable_size(path.stat().st_size)}"), 14,
                          halign="center", valign="middle", text_size=(Window.width * 0.75, None))

        def stop(*_a):
            sound = state["sound"]
            if sound is not None:
                try:
                    sound.stop()
                    sound.unload()
                except Exception:  # noqa: BLE001
                    pass
                state["sound"] = None

        def play(*_a):
            stop()
            try:
                from kivy.core.audio import SoundLoader
                sound = SoundLoader.load(str(path))
                if sound is None:
                    raise RuntimeError("Hindi ma-play ng phone ang audio na ito. I-Export mo at buksan sa music player.")
                state["sound"] = sound
                sound.play()
            except Exception as error:  # noqa: BLE001
                show_message("Audio", friendly_error(error), 0.35)

        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
        box.add_widget(info)
        box.add_widget(make_btn("PLAY", play, 52, "primary"))
        box.add_widget(make_btn("STOP", stop, 46))
        box.add_widget(make_btn("EXPORT .OGG", lambda: self.export_entry(index), 46))

        def replace(*_a):
            def picked(chosen: Path):
                def done(report):
                    stop()
                    self.set_status(f"Audio staged: {report['label']}  ({report['new_size']:,} bytes)")
                    if getattr(self, "browser", None):
                        self.browser.refresh()
                    show_message(
                        "Audio napalitan",
                        f"{report['label']}\nDati: {report['old_size']:,} bytes\nBago: {report['new_size']:,} bytes\n\n"
                        "Pindutin ang SAVE OBB (orange bar) para i-save sa OBB.", 0.4)
                    popup.dismiss()

                self.run_bg(lambda: self.ws.replace_audio(
                index, chosen, progress=lambda f: self.set_status(f"Converting to OGG ... {int(f * 100)}%")),
                done, "Converting / replacing audio ...")

            PickerPopup("Piliin ang bagong audio (.ogg / .mp3 / .wav / .m4a / .flac ...) - auto convert sa OGG", "file", AUDIO_PICK_EXT, picked, start=output_root()).open()

        def restore(*_a):
            self.ws.session.discard_stage(index)
            stop()
            if getattr(self, "browser", None):
                self.browser.refresh()
            popup.dismiss()

        box.add_widget(make_btn("REPLACE AUDIO (.ogg / .aac)", replace, 50, "primary"))
        box.add_widget(make_btn("BALIKAN ANG ORIGINAL", restore, 44))
        popup = make_popup("Audio", box, (0.9, 0.7))
        popup.bind(on_dismiss=lambda *_a: stop())
        box.add_widget(make_btn("Close", popup.dismiss, 46))
        popup.open()

    def export_entry(self, index: int) -> None:
        """Export one complete IFF straight from the list (staged edits included)."""
        folder = output_root() / "iff"
        self.run_bg(
            lambda: self.ws.export_entry(index, folder),
            lambda path: show_message("Exported", f"{path}", 0.3),
            f"Exporting entry {index} ...",
        )

    def import_entry(self, index: int) -> None:
        """Import IFF straight from the list: replace entry ``index`` with a complete IFF file."""
        expected = self.ws.session.entry_name(index)

        def run(path: Path) -> None:
            self.run_bg(
                lambda: self.ws.replace_obb_iff(path, check_name=False, index=index, reopen=False),
                lambda r: (
                    self.show_entries(),
                    show_message(
                        "IFF imported",
                        f"{r['label']} staged ({r['mode']}).\nThe OBB is not changed until you "
                        "'Save OBB copy'.", 0.36),
                ),
                "Validating replacement ...",
            )

        def picked(path: Path) -> None:
            if path.name.lower() == expected.lower():
                run(path)
            else:  # allowed (renamed export); the exact decompressed-size check still protects the OBB
                confirm(
                    "Different file name",
                    f"List entry: {expected}\nChosen file: {path.name}\n\n"
                    "Import it into this entry anyway? (The decompressed size must match exactly.)",
                    lambda: run(path),
                )

        PickerPopup(f"Import IFF into {expected}", "file", (".iff",), picked,
                    start=output_root() / "iff").open()

    def export_shown(self) -> None:
        """Export every IFF currently shown in the list (respects search + category)."""
        indices = list(getattr(self, "browser", None).visible) if getattr(self, "browser", None) else []
        if not indices:
            show_message("Export list", "No IFF in the list.", 0.3)
            return
        folder = output_root() / "iff"
        confirm(
            "Export list",
            f"Export {len(indices)} IFF file(s) to:\n{folder}",
            lambda: self.run_bg(
                lambda: self.ws.export_entries(indices, folder, progress=self.set_status),
                lambda r: show_message("Exported", f"{r[0]} file(s) saved to:\n{r[1]}", 0.35),
                "Exporting ...",
            ),
        )

    def open_entry(self, index: int, *_args) -> None:
        self.run_bg(
            lambda: self.ws.open_obb_entry(index),
            lambda summary: self.show_iff_screen(self.ws.current_label, f"OBB #{index}"),
            f"Decompressing entry {index} ...",
        )

    def switch_to_entry(self, index: int) -> None:
        if index == self.ws.current_index:
            return
        had_edits = self.ws.dirty
        self.run_bg(
            lambda: self.ws.switch_entry(index),
            lambda summary: (
                self.show_iff_screen(self.ws.current_label, f"OBB #{index}"),
                self.set_status(
                    ("Previous IFF edits were staged. " if had_edits else "")
                    + f"Opened {self.ws.current_label}"
                ),
            ),
            f"Opening entry {index} ...",
        )

    def save_obb_copy(self) -> None:
        if not self.ws.staged_count and not self.ws.dirty:
            show_message("Save OBB", "Nothing is staged. Open an IFF entry, edit it, then use Stage.")
            return
        source = self.ws.session.path
        folder = output_root() / "patched_obb"
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / source.name  # keep the exact name the game expects
        if destination.resolve() == source.resolve():
            destination = copy_with_suffix(destination, "_patched")
        self._save_obb_to(destination, destination.exists())

    def save_obb_overwrite(self) -> None:
        source = self.ws.session.path
        confirm(
            "Overwrite OBB?",
            f"This replaces:\n{source}\n\nKeep a backup. Free space about the OBB size is needed.",
            lambda: self._save_obb_to(source, True),
        )

    def _save_obb_to(self, destination: Path, overwrite: bool) -> None:
        def work():
            return self.ws.save_obb(
                destination, allow_overwrite=overwrite, progress=self.set_status
            )

        def done(report):
            self.set_status("OBB saved and verified")
            show_message(
                "OBB saved",
                f"{report['output_obb']}\n\nChanged entries: {report['changed_entry_count']}\n"
                f"CRC32: {report['archive_crc32']}\nVerification: {report['verification']}",
            )
            # Stay on the same screen: only the OBB list screen is refreshed.
            if self.mode == "obb" and self.ws.session is not None:
                self.show_entries()

        self.run_bg(work, done, "Rebuilding OBB ...")

    # ----------------------------------------------------------------- IFF
    def load_iff(self, path: Path) -> None:
        self.run_bg(
            lambda: self.ws.open_iff(path),
            lambda summary: self.show_iff_screen(path.name),
            f"Opening {path.name} ...",
        )

    def show_iff_drawer(self) -> None:
        """Side list with every IFF of the OBB (Logo group is separate)."""
        if self.ws.session is None:
            return
        drawer = ModalView(
            size_hint=(0.88, 1), pos_hint={"x": 0, "y": 0}, auto_dismiss=True,
            background="", background_color=BAR, overlay_color=(0, 0, 0, 0.65),
        )
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        box.add_widget(left_label("[b]IFF files[/b]", 18, TEXT, height=36))
        box.add_widget(IffBrowser(
            self,
            lambda index: (drawer.dismiss(), self.switch_to_entry(index)),
            current=self.ws.current_index, iff_only=True,
        ))
        box.add_widget(make_btn("Close", drawer.dismiss, 46))
        drawer.add_widget(box)
        drawer.open()

    def show_iff_screen(self, title: str, subtitle: str = "") -> None:
        self.mode = "iff"
        self.selected_texture = self.selected_mesh = self.selected_resource = None
        summary = self.ws.opened_summary()
        extra = []
        if self.ws.session is not None:
            extra.append(make_btn("IFF List", self.show_iff_drawer, 42, "primary",
                                  size_hint_x=None, width=dp(92), pos_hint={"center_y": 0.5}))
        self.set_header(f"{title}   {subtitle}".strip(), extra)
        self.set_status(
            f"{summary['decodable_textures']}/{summary['textures']} textures, "
            f"{summary['models']} models, {summary['resources']} resources"
        )
        self.clear_body()

        self.tab_views = {
            "Textures": self._build_textures_tab(),
            "Models": self._build_models_tab(),
            "Resources": self._build_resources_tab(),
        }
        self.tab_buttons: dict[str, Btn] = {}
        tab_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        for name in self.tab_views:
            button = make_btn(name, partial(self.select_tab, name), 44)
            self.tab_buttons[name] = button
            tab_bar.add_widget(button)
        self.tab_area = BoxLayout()
        self.body.add_widget(tab_bar)
        self.body.add_widget(self.tab_area)

        bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        bar.add_widget(make_btn("Actions", self.show_actions, 52, "primary"))
        bar.add_widget(make_btn("Back", self.go_back, 52))
        self.body.add_widget(bar)
        self.select_tab(self.current_tab if self.current_tab in self.tab_views else "Textures")

    def select_tab(self, name: str) -> None:
        self.current_tab = name
        for tab_name, button in self.tab_buttons.items():
            button.kind = "primary" if tab_name == name else "ghost"
        self.tab_area.clear_widgets()
        Clock.schedule_once(lambda _dt: stagger_in(self.tab_area, 0.03, 10), 0)
        self.tab_area.add_widget(self.tab_views[name])
        if name == "Models" and getattr(self, "mesh_list", None) is not None:
            if self.selected_mesh is None and self._mesh_numbers:
                self.select_mesh(self._mesh_numbers[0])
            elif self.selected_mesh is not None:
                self.render_mesh()  # pick up the texture chosen / imported meanwhile

    def go_back(self) -> None:
        target = self.show_entries if self.ws.session else self.show_home
        if self.ws.dirty and not self.ws.session:
            confirm(
                "Unsaved edits",
                "This IFF has edits that were not saved. Discard them?",
                target,
            )
        elif self.ws.dirty:
            confirm(
                "Unstaged edits",
                "This IFF has edits that are not staged yet. Discard them?\n"
                "(Use Actions > Stage first to keep them.)",
                target,
            )
        else:
            target()

    # textures tab
    def _build_textures_tab(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        self.tex_filter = make_input("Filter: number, size (1024), format (ETC2)", 42)
        self.tex_filter.bind(text=lambda *_: self.refresh_textures())
        cyberface = self.ws.is_cyberface()  # face tools only for cyberface IFFs; others get a big preview
        self.cyberface_mode = cyberface
        self.texture_list = RowList(size_hint_y=0.27 if cyberface else 0.24)
        info_row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        self.preview_info = left_label("Tap a texture to preview", 13, MUTED)
        self.preview_mode = Drop(
            text="Auto (best view)", values=list(PREVIEW_MODES), size_hint_x=0.42,
            font_size=sp(13),
        )
        self.preview_mode.bind(text=lambda *_: self.refresh_preview())
        self.decoder_drop = Drop(
            text="Dec: Auto", values=[f"Dec: {c}" for c in core.DECODER_CHOICES],
            size_hint_x=0.34, font_size=sp(12),
        )
        self.decoder_drop.bind(text=lambda *_: self.refresh_preview())
        info_row.add_widget(self.preview_info)
        info_row.add_widget(self.decoder_drop)
        info_row.add_widget(self.preview_mode)
        self.preview = TapImage(fit_mode="contain")
        self.preview.bind(on_release=lambda *_: self.preview_tapped())
        preview_card = Card(kind="bar", size_hint_y=0.36 if cyberface else 0.76, padding=dp(6))
        preview_card.add_widget(self.preview)
        extra = GridLayout(cols=2, size_hint_y=None, height=dp(4 * 44 + 3 * 6), spacing=dp(6))
        extra.add_widget(make_btn("EDIT: CYBERFACE EDITOR", self.cyberface_workshop, 44, "primary", font_size=sp(12)))
        extra.add_widget(make_btn("HEAD / HAIR", self.head_hair_dialog, 44, "primary", font_size=sp(12)))
        extra.add_widget(make_btn("UV Editor (tattoo)", self.uv_editor, 44, "primary", font_size=sp(13)))
        extra.add_widget(make_btn("AI Assist", self.ai_assist_popup, 44, "primary", font_size=sp(13)))
        extra.add_widget(make_btn("Blender export", self.blender_export, 44, "ghost", font_size=sp(12)))
        extra.add_widget(make_btn("Blender import", self.blender_import, 44, "ghost", font_size=sp(12)))
        extra.add_widget(make_btn("Sync LOD (malayuan)", self.sync_lod, 44, "primary", font_size=sp(12)))
        grid = GridLayout(cols=2, size_hint_y=None, height=dp(104), spacing=dp(6))
        grid.add_widget(make_btn("Export PNG", self.export_png, 48))
        grid.add_widget(make_btn("Import PNG", self.import_png, 48, "primary"))
        grid.add_widget(make_btn("Export all PNG", self.export_all_png, 48))
        grid.add_widget(make_btn("Import all PNG", self.import_all_png, 48, "primary"))
        widgets = [self.tex_filter, self.texture_list, info_row, preview_card]
        if cyberface:
            widgets.append(extra)
        widgets.append(make_btn("SKIN TONE (arm / body) - ikaw ang pipili ng kulay", self.skin_tone_popup, 46, "primary",
                                font_size=sp(12)))
        widgets.append(grid)
        for widget in widgets:
            box.add_widget(widget)
        self._runtime_ok = None
        self.show_runtime = True        # v183: every texture slot is listed (crowd / gamedataextra / english too)
        self.texture_list.PAGE = 400    # v183: no more 120-row pages for the big IFFs
        self.show_empty = False
        self.refresh_textures()
        self._start_runtime_scan()
        Clock.schedule_once(lambda _dt: self._auto_select_first(), 0.2)
        return box

    def _start_runtime_scan(self) -> None:
        """Background: find which runtime-slot textures really show a picture; the rest get hidden from the list."""
        try:
            if not any(r.get("runtime") and not r["decodable"] for r in self.ws.texture_rows()):
                return
            opened = self.ws._need_iff()
        except Exception:  # noqa: BLE001
            return

        def work() -> None:
            try:
                good = self.ws.runtime_readable_numbers()
            except Exception:  # noqa: BLE001
                return
            Clock.schedule_once(lambda _dt: self._runtime_scan_done(opened, good), 0)

        threading.Thread(target=work, daemon=True).start()

    def _runtime_scan_done(self, opened, good) -> None:
        try:
            if self.ws._need_iff() is not opened:           # another IFF was opened meanwhile
                return
        except Exception:  # noqa: BLE001
            return
        self._runtime_ok = set(good)
        self.refresh_textures()

    def _toggle_empty_rows(self, *_args) -> None:
        self.show_empty = True
        self.refresh_textures()

    def _auto_select_first(self) -> None:
        """v222: open the first real picture straight away, no tapping needed."""
        try:
            empty = self.ws.empty_texture_numbers()
            for row in self.ws.texture_rows():
                if row["decodable"] and row["number"] not in empty:
                    self.select_texture(row["number"])
                    return
        except Exception:  # noqa: BLE001
            pass

    def _toggle_runtime_rows(self, *_args) -> None:
        self.show_runtime = not getattr(self, "show_runtime", False)
        self.refresh_textures()

    def _is_auto_pinned(self, row) -> bool:
        """The 2K logo (Frontend Legacy 1024x614) is always pinned, in every IFF."""
        label = str(row.get("label", "")).lower()
        if row["number"] in (323, 324):  # the 2K logo slot of the Frontend IFF
            return True
        return "frontend legacy" in label or "2k logo" in label

    def _pin_key(self, number: int) -> str:
        try:
            name = self.ws._need_iff().path.name
        except Exception:  # noqa: BLE001
            name = "iff"
        return f"pin:{name}:{number}"

    def _toggle_pin(self, number: int, active: bool) -> None:
        self.set_fav(self._pin_key(number), active)
        self.refresh_textures()

    def refresh_textures(self) -> None:
        query = self.tex_filter.text.strip().lower()
        pinned, normal = [], []
        runtime_ok = getattr(self, "_runtime_ok", None)
        hide_unreal = runtime_ok is not None and not getattr(self, "show_runtime", False)
        hidden = 0
        try:
            empty = self.ws.empty_texture_numbers() if not getattr(self, "show_empty", False) else set()
        except Exception:  # noqa: BLE001
            empty = set()
        hidden_empty = 0
        for row in self.ws.texture_rows():
            if row["number"] in empty and not query:
                hidden_empty += 1                             # v222: flat "EMPTY TEXTURE" buffers are not listed
                continue
            if (hide_unreal and row.get("runtime") and not row["decodable"] and row["number"] not in runtime_ok
                    and not query):
                hidden += 1                                   # no pixels in the file: nothing real to show
                continue
            haystack = f"{row['number']} {row['width']}x{row['height']} {row['format']} {row['label']} {row.get('hash', '')}".lower()
            auto = self._is_auto_pinned(row)
            manual = self._pin_key(row["number"]) in self.favs
            if query and query not in haystack and not auto:
                continue
            generic = row["label"].lower() == f"texture {row['number']}"
            name = f"Texture {row['number']}" if generic else row["label"]
            if generic and row.get("hash"):
                name = f"{name}  {row['hash']}"  # the hash is the only real title these descriptors have
            state = ("READY" if row["decodable"]
                     else "RUNTIME - tap, then Dec: Seq VRAM" if row.get("runtime") else "NO PREVIEW")
            sub = (
                f"{row['width']} x {row['height']}  |  "
                f"{core.readable_size(row.get('payload_size') or 0)}  |  {state}"
            )
            entry = row_entry(
                f"#{row['number']}  {name}",
                sub,
                partial(self.select_texture, row["number"]),
                key=row["number"],
                badge=row["format"],
                star=(auto or manual),
                on_star=partial(self._toggle_pin, row["number"]),
                thumb=(partial(self._thumb_loader, row["number"])
                       if row["decodable"] and not (
                           "ETC2" in str(row["format"]).upper()
                           and row["width"] * row["height"] > 512 * 512)
                       else None),
            )
            (pinned if (auto or manual) else normal).append(entry)
        rows = []
        if pinned:
            rows.append(row_entry("PINNED", header=True))
            rows.extend(pinned)
            if normal:
                rows.append(row_entry("ALL TEXTURES", header=True))
        rows.extend(normal)
        if hidden_empty:
            rows.append(row_entry(f"{hidden_empty} empty textures hidden", "Flat buffers the game fills while running. Tap to show.",
                                  self._toggle_empty_rows, header=False))
        if hidden:
            rows.append(row_entry(f"{hidden} runtime textures hidden",
                                  "No pixels are stored in this IFF for them (the game fills them while running). "
                                  "Tap to show them.", self._toggle_runtime_rows, header=False))
        elif getattr(self, "show_runtime", False) and runtime_ok is not None:
            rows.append(row_entry("Hide the runtime textures", "Tap to hide them again.", self._toggle_runtime_rows))
        self.texture_list.selected_key = self.selected_texture
        self.texture_list.set_rows(rows)

    def _thumb_loader(self, number: int):
        w, h, data, _avg = self.ws.texture_preview_rgba(number, mode="Auto", maximum=(96, 96))
        return w, h, data

    def select_texture(self, number: int, *_args) -> None:
        self.selected_texture = number
        self.texture_list.mark_selected(number)
        # v222: every texture opens in AUTO (a decoder left over from the last one gave stripes / noise)
        if self.decoder_drop.text != "Dec: Auto":
            self.decoder_drop.text = "Dec: Auto"             # the binding refreshes the preview
            return
        self.refresh_preview()

    def refresh_preview(self) -> None:
        number = self.selected_texture
        if number is None:
            return
        mode = PREVIEW_MODES.get(self.preview_mode.text, "Auto")
        info = next((r for r in self.ws.texture_rows() if r["number"] == number), None)
        if info:
            self.preview_info.text = (
                f"[b]#{number}[/b]  {info['width']} x {info['height']}  |  {info['format']}"
            )

        decoder = self.decoder_drop.text.replace("Dec: ", "")

        def work():
            return self.ws.texture_preview_rgba(number, mode=mode, maximum=(1024, 1024), decoder=decoder)

        def done(result):
            if number != self.selected_texture:
                return
            width, height, data, average = result
            tinted = False
            try:   # v251: ang 1 MB cyberface ay grey na SKIN / FACE MAP (kulay nasa _hi file) -> preview lang: lagyan ng kulay ng balat
                if self.ws.is_cyberface() and number == self.ws.face_diffuse_texture_number():
                    from PIL import Image as _P
                    from nba2k20 import headmorph as _hm
                    _im = _P.frombytes("RGBA", (width, height), bytes(data))
                    if _hm.is_gray_map(_im):
                        data = _hm.tint_gray_map(_im, _hm.SKIN_PREVIEW_TONES[1]).tobytes()
                        tinted = True
            except Exception:  # noqa: BLE001
                tinted = False
            # Upload raw RGBA ourselves: more reliable on Android than the PNG loader.
            texture = Texture.create(size=(width, height), colorfmt="rgba")
            texture.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
            texture.flip_vertical()
            texture.mag_filter = "nearest"
            self._preview_texture = texture
            self.preview.color = (1, 1, 1, 1)
            self.preview.texture = texture
            self.preview.canvas.ask_update()
            real = f"{info['width']}x{info['height']}" if info else f"{width}x{height}"
            warn = ""
            try:
                from PIL import Image as _PilImage

                if core.looks_like_noise(_PilImage.frombytes("RGBA", (width, height), bytes(data))):
                    warn = "  |  BABALA: static ang decode - hindi tunay na texture, hindi ito susulatan ng Import"
            except Exception:  # noqa: BLE001
                warn = ""
            self.set_status(
                f"Texture #{number}  {real}  avg RGB {average[0]},{average[1]},{average[2]}{warn}"
                + ("  |  grey face map: kulay ng balat ay PREVIEW lang (nasa _hi file ang tunay na kulay) - puwede pa ring i-EDIT" if tinted else "")
            )

        self.run_bg(work, done, f"Decoding texture #{number} ...")

    def skin_tone_popup(self) -> None:
        """v184: change the SKIN TONE of the selected texture (arm / body / any skin map) to a colour the user types."""
        number = self._need_texture()
        if number is None:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6), size_hint_y=None)
        box.bind(minimum_height=box.setter("height"))
        box.add_widget(wrap_label(
            f"SKIN TONE - texture #{number}. Ikaw ang magsusukat ng kulay: ilagay ang gusto mong kulay ng balat (hex tulad ng "
            "8D6044, o R G B). Ang balat lang ang nagbabago; ang anino / liwanag, ang tattoo ink at ang alpha ay hindi "
            "ginagalaw. PREVIEW muna, tapos APPLY (naka-stage agad; susunod: Back, Save OBB copy).", 12))
        current = wrap_label("Sinusukat ang kulay ng skin ...", 13)
        box.add_widget(current)
        color_in = make_input("Kulay: hex (8D6044) o R G B (141 96 68)")
        strength_in = make_input("Lakas 0 - 100  (empty = 100)")
        box.add_widget(color_in)
        presets = GridLayout(cols=3, size_hint_y=None, height=dp(2 * 44 + 6), spacing=dp(6))
        for name, rgb in facelab.SKIN_PRESETS.items():
            if rgb is None:
                continue
            presets.add_widget(make_btn(name, lambda c=rgb: setattr(color_in, "text", "%02X%02X%02X" % tuple(c)), 44,
                                        "ghost", font_size=sp(12)))
        box.add_widget(presets)
        box.add_widget(strength_in)
        preview = TapImage(fit_mode="contain", size_hint_y=None, height=dp(240))
        box.add_widget(preview)
        result_label = wrap_label("", 12)
        box.add_widget(result_label)

        def read():
            try:
                target = facelab.parse_color(color_in.text)
            except ValueError as exc:
                show_message("Skin tone", str(exc), 0.3)
                return None
            raw = strength_in.text.strip()
            try:
                strength = 1.0 if not raw else max(0.0, min(1.0, float(raw) / 100.0))
            except ValueError:
                show_message("Skin tone", "Ang Lakas ay numero 0 - 100.", 0.3)
                return None
            return target, strength

        def on_info(info) -> None:
            if info["color"] is None:
                current.text = "Walang nakitang skin sa texture na ito (baka hindi ito arm / body texture)."
            else:
                r, g, b = info["color"]
                current.text = (f"Kasalukuyang skin: [b]#{r:02X}{g:02X}{b:02X}[/b]  ({r}, {g}, {b})  -  "
                                f"{round(info['coverage'] * 100)}% ng texture ay skin")

        self.run_bg(lambda: self.ws.skin_tone_info(number), on_info, "Measuring skin ...")

        def do_preview(*_a) -> None:
            got = read()
            if got is None:
                return
            target, strength = got

            def done(result) -> None:
                width, height, data, info = result
                texture = Texture.create(size=(width, height), colorfmt="rgba")
                texture.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
                texture.flip_vertical()
                self._skin_preview_texture = texture
                preview.texture = texture
                preview.canvas.ask_update()
                result_label.text = ("Preview lang - wala pang naisusulat." if info["changed"]
                                     else "Walang skin na nakita, walang mababago.")

            self.run_bg(lambda: self.ws.skin_tone_preview(number, target, strength), done, "Preview ...")

        def finished(report) -> None:
            rows = report["done"]
            text = "Na-apply sa: " + ", ".join(f"#{r['number']}" for r in rows)
            if report["skipped"]:
                text += "\nHindi nabago: " + "; ".join(report["skipped"][:6])
            result_label.text = escape_markup(text)
            self.set_status(text.splitlines()[0] + (" - STAGED" if report.get("staged") else ""))
            self.refresh_textures()
            self.refresh_preview()
            show_message("Skin tone", text + ("\n\nNaka-stage na. Susunod: Back, tapos Save OBB copy."
                                              if report.get("staged") else "\n\nSusunod: Actions > Save."), 0.5)

        def do_apply(*_a) -> None:
            got = read()
            if got is None:
                return
            target, strength = got
            self.run_bg(lambda: self.ws.skin_tone_apply([number], target, strength), finished, "Applying skin tone ...")

        def do_apply_all(*_a) -> None:
            got = read()
            if got is None:
                return
            target, strength = got

            def work():
                numbers = [c["number"] for c in self.ws.skin_tone_candidates(0.25)]
                return self.ws.skin_tone_apply(numbers, target, strength, 0.25)

            self.run_bg(work, finished, "Applying skin tone to every skin texture ...")

        box.add_widget(make_btn("PREVIEW", do_preview, 48))
        box.add_widget(make_btn("APPLY SA TEXTURE NA ITO", do_apply, 50, "primary"))
        box.add_widget(make_btn("APPLY SA LAHAT NG SKIN TEXTURE NG IFF (hal. kaliwa + kanang braso)", do_apply_all, 50,
                                "primary", font_size=sp(11)))
        scroll = ScrollView()
        scroll.add_widget(box)
        popup = make_popup("SKIN TONE", scroll, (0.94, 0.92))
        box.add_widget(make_btn("Close", lambda *_a: popup.dismiss(), 46))
        popup.open()

    def _need_texture(self) -> int | None:
        if self.selected_texture is None:
            show_message("Texture", "Tap a texture in the list first.", 0.3)
        return self.selected_texture

    def export_png(self) -> None:
        number = self._need_texture()
        if number is None:
            return
        folder = output_root() / "png"
        self.run_bg(
            lambda: self.ws.export_texture(number, folder),
            lambda path: self.set_status(f"Saved {path}"),
            "Exporting ...",
        )

    def export_all_png(self) -> None:
        folder = output_root() / "png_all" / Path(self.ws.current_label).stem
        self.run_bg(
            lambda: self.ws.export_all_textures(folder),
            lambda result: show_message(
                "Export all PNG",
                f"{result[0]} texture(s) saved to:\n{folder}\n\n" + "\n".join(result[1][:10]),
            ),
            "Exporting all textures ...",
        )

    def import_png(self) -> None:
        number = self._need_texture()
        if number is None:
            return

        def done(change):
            src = change.get("resized_from")
            info = next((r for r in self.ws.texture_rows() if r["number"] == number), None)
            if src and info:
                note = (f"Imported #{number}: auto-resized {src[0]}x{src[1]} to "
                        f"{info['width']}x{info['height']}. Now use Actions > Stage / Save.")
            else:
                note = f"Imported into texture #{number}. Now use Actions > Stage / Save."
            self.set_status(note)
            self.refresh_preview()

        def pick_file(background: str = "black", as_format: int | None = None, dither: bool | None = None,
                      any_image: bool = False) -> None:
            def picked(path: Path) -> None:
                self.run_bg(lambda: self.ws.import_texture(number, path, background, as_format, dither), done,
                            "Encoding PNG ...")

            PickerPopup("Choose image (any size - auto resize)" if any_image else "Choose PNG (any size - auto resize)",
                        "file", (".png", ".jpg", ".jpeg", ".webp", ".bmp") if any_image else (".png",), picked,
                        start=output_root() / "png").open()

        info = next((r for r in self.ws.texture_rows() if r["number"] == number), None)
        if info and str(info["label"]).startswith("Frontend Legacy"):
            # 2K logo: fully automatic - any image, background becomes transparent, RGBA4444 (2K27).
            pick_file("black", 4, None, any_image=True)
            return
        if info and str(info["format"]).upper() == "RGB565":
            # RGB565 has no transparency (2K logo etc.): let the user choose the colour behind it.
            box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
            box.add_widget(make_label(
                "This texture has no transparency. Pick the background colour:", 14,
                halign="left", valign="middle", text_size=(Window.width * 0.78, None)))
            popup = make_popup("Logo background", box, (0.9, 0.55))
            for name in ("black", "white", "red"):
                box.add_widget(make_btn(
                    name.capitalize(),
                    lambda n=name: (popup.dismiss(), pick_file(n)), 52,
                    "primary" if name == "black" else "ghost"))
            popup.open()
            return
        pick_file()

    def sync_lod(self) -> None:
        """Copy the HI face / skin / normal / hair into the LO + LO2 (far-away) textures of this cyberface."""
        def done(labels):
            show_message(
                "Sync LOD",
                (f"Na-update ang {len(labels)} LOD texture:\n" + "\n".join(labels)
                 + "\n\nNow use Actions > Stage / Save.") if labels else
                "Walang LO / LO2 texture sa IFF na ito.", 0.5)
            self.refresh_textures()
            self.refresh_preview()

        self.run_bg(lambda: self.ws.sync_lod(), done, "Syncing LOD ...")

    def import_all_png(self) -> None:
        def picked(folder: Path) -> None:
            def done(report):
                resized = sum(1 for c in report["changes"] if c.get("resized_from"))
                show_message(
                    "Import all PNG",
                    f"Imported {len(report['changes'])} texture(s)"
                    f" ({resized} auto-resized).\nMissing: {report['missing_count']}\n"
                    "Now use Actions > Stage / Save.",
                    0.4,
                )
                self.refresh_preview()

            self.run_bg(lambda: self.ws.import_texture_folder(folder), done, "Importing PNGs ...")

        PickerPopup("Choose the folder of edited PNGs", "dir", (), picked,
                    start=output_root() / "png_all").open()

    # models tab
    def _build_models_tab(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        meshes = self.ws.mesh_rows()
        self.mesh_list = None
        self._mesh_numbers = [m["number"] for m in meshes]
        self.mesh_view = {"yaw": 0.0, "pitch": 0.0, "zoom": 1.0, "flip": False,
                          "uv": 0, "png": None, "use_tex": True}
        if not meshes:
            box.add_widget(make_label(
                "Walang validated na game mesh sa IFF na ito."
                + ("\nGamitin ang Cyberface Workshop (generic head o sarili mong OBJ) para sa 3D edit."
                   if self.ws.is_cyberface() else ""), 14, MUTED, halign="center"))
            if self.ws.is_cyberface():
                box.add_widget(make_btn("OPEN CYBERFACE EDITOR", self.cyberface_workshop, 56, "primary"))
            return box
        self.mesh_list = RowList(size_hint_y=0.24)
        self.mesh_list.set_rows(
            [
                row_entry(
                    f"Model #{m['number']}",
                    f"{m['vertex_count']} verts  |  {m['triangle_count']} tris  |  stride {m['vertex_stride']}",
                    partial(self.select_mesh, m["number"]),
                    key=m["number"],
                )
                for m in meshes
            ]
        )
        self.mesh_info = left_label("Pick a model. Pick a texture in the Textures tab to see it on the model.",
                                    12, MUTED, height=48)
        self.mesh_info.shorten = False
        self.mesh_image = DragImage(self._drag_mesh, fit_mode="contain")
        mesh_card = Card(kind="bar", size_hint_y=0.5, padding=dp(6))
        mesh_card.add_widget(self.mesh_image)
        grid = GridLayout(cols=4, size_hint_y=None, height=dp(5 * 44 + 4 * 6), spacing=dp(6))
        for text, cb, kind in (
            ("Left", lambda: self._mesh_step(yaw=-25), "ghost"),
            ("Right", lambda: self._mesh_step(yaw=25), "ghost"),
            ("Up", lambda: self._mesh_step(pitch=-15), "ghost"),
            ("Down", lambda: self._mesh_step(pitch=15), "ghost"),
            ("Zoom -", lambda: self._mesh_step(zoom=0.8), "ghost"),
            ("Zoom +", lambda: self._mesh_step(zoom=1.25), "ghost"),
            ("Flip V", self._mesh_flip, "ghost"),
            ("UV", self._mesh_next_uv, "ghost"),
            ("Open PNG", self.mesh_open_png, "primary"),
            ("Use tex", self.mesh_use_selected, "primary"),
            ("Export OBJ", self.export_obj, "ghost"),
            ("Import OBJ", self.import_obj, "ghost"),
            ("Blender export", self.blender_export, "primary"),
            ("Blender import", self.blender_import, "primary"),
            ("AI Assist", self.ai_assist_popup, "primary"),
            ("CYBERFACE EDITOR", self.cyberface_workshop, "primary"),
            ("OBJ Creator", self.obj_creator, "primary"),
        ):
            grid.add_widget(make_btn(text, cb, 44, kind, font_size=sp(12)))
        for widget in (self.mesh_list, self.mesh_info, mesh_card, grid):
            box.add_widget(widget)
        return box

    def _mesh_ready(self) -> bool:
        if getattr(self, "mesh_list", None) is None or self.selected_mesh is None:
            show_message("Model", "Tap a model first.", 0.3)
            return False
        return True

    def _mesh_step(self, yaw=0.0, pitch=0.0, zoom=1.0) -> None:
        if not self._mesh_ready():
            return
        view = self.mesh_view
        view["yaw"] += yaw
        view["pitch"] = max(-85.0, min(85.0, view["pitch"] + pitch))
        view["zoom"] = max(0.3, min(6.0, view["zoom"] * zoom))
        self.render_mesh()

    def _drag_mesh(self, dx: float, dy: float) -> None:
        if getattr(self, "mesh_list", None) is None or self.selected_mesh is None:
            return
        view = self.mesh_view
        view["yaw"] += dx / dp(4)
        view["pitch"] = max(-85.0, min(85.0, view["pitch"] - dy / dp(5)))
        self.render_mesh()

    def _mesh_flip(self) -> None:
        if self._mesh_ready():
            self.mesh_view["flip"] = not self.mesh_view["flip"]
            self.render_mesh()

    def _mesh_next_uv(self) -> None:
        if self._mesh_ready():
            self.mesh_view["uv"] += 1
            self.render_mesh()

    def mesh_use_selected(self) -> None:
        if self.selected_texture is None:
            show_message("Texture", "Tap a texture in the Textures tab first.", 0.3)
            return
        self.mesh_view.update(png=None, use_tex=True)
        if self._mesh_ready():
            self.render_mesh()

    def mesh_open_png(self) -> None:
        if not self._mesh_ready():
            return

        def picked(path: Path) -> None:
            self.mesh_view.update(png=path, use_tex=False)
            self.render_mesh()

        PickerPopup("Choose a PNG to preview on the model", "file", (".png",), picked,
                    start=output_root() / "png").open()

    def render_mesh(self) -> None:
        number = self.selected_mesh
        if number is None or getattr(self, "mesh_list", None) is None:
            return
        view = dict(self.mesh_view)
        texture_number = self.selected_texture if view["use_tex"] and view["png"] is None else None

        def work():
            return self.ws.mesh_textured_png(
                number, texture_number=texture_number, png=view["png"], uv_index=view["uv"],
                flip_v=view["flip"], yaw=view["yaw"], pitch=view["pitch"], zoom=view["zoom"],
            )

        def done(result):
            png, info = result
            if number != self.selected_mesh:
                return
            self.mesh_image.texture = CoreImage(io.BytesIO(png), ext="png").texture
            if info["uv_count"] == 0:
                note = "UV not found for this model - showing shaded model only."
            elif not info["textured"]:
                note = "No texture chosen: pick one in the Textures tab or use Open PNG."
            else:
                source = view["png"].name if view["png"] else f"texture #{texture_number}"
                note = (f"{source}  |  UV {info['uv_index'] + 1}/{info['uv_count']} "
                        f"({info['uv_label']})  |  Flip V {'ON' if view['flip'] else 'off'}")
            self.mesh_info.text = escape_markup(note + "   (swipe to rotate, UV = try next layout)")
            self.mesh_view["uv"] = info["uv_index"]
            self.set_status(f"Model #{number}: {info['triangles']} triangles")

        self.run_bg(work, done, "Rendering 3D ...")

    def select_mesh(self, number: int, *_args) -> None:
        self.selected_mesh = number
        self.mesh_list.mark_selected(number)
        self.render_mesh()

    def export_obj(self) -> None:
        if self.selected_mesh is None:
            show_message("Model", "Tap a model first.", 0.3)
            return
        number = self.selected_mesh
        folder = output_root() / "obj"
        self.run_bg(
            lambda: self.ws.export_mesh(number, folder),
            lambda path: self.set_status(f"Saved {path}"),
            "Exporting OBJ ...",
        )

    def import_obj(self) -> None:
        if self.selected_mesh is None:
            show_message("Model", "Tap a model first.", 0.3)
            return
        number = self.selected_mesh

        def picked(path: Path) -> None:
            def done(report) -> None:
                staged = report.get("staged")
                note = "OBJ imported" + (" + STAGED - next: Save OBB copy" if staged else " - now use Actions > Save")
                if report.get("normals"):
                    note += f" (normals refreshed: {report['normals']})"
                elif report.get("normals_note"):
                    note += " | " + str(report["normals_note"])
                self.set_status(note)

            self.run_bg(
                lambda: self.ws.import_mesh(number, path, stage=self.ws.current_index is not None),
                done,
                "Importing OBJ ...",
            )

        PickerPopup("Choose edited OBJ", "file", (".obj",), picked,
                    start=output_root() / "obj").open()

    # ------------------------------------------------------------ blender
    def scene_tools(self) -> None:
        """v247: court / arena / scoreboard geometry (SCNE, from the David2ktool Blender plugin) <-> OBJ."""
        from nba2k20 import scenetool
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(6))
        box.add_widget(make_label("Court / scoreboard: PC-style IFF (zip with .SCNE) o .SCNE.\n"
                                  "EXPORT OBJ -> i-edit sa Blender (huwag magdagdag / magbawas ng vertex, Keep Vertex Order) "
                                  "-> IMPORT OBJ. Gumagawa ng bagong kopya; hindi ginagalaw ang original.", 12, MUTED,
                                  size_hint_y=None, height=dp(96), text_size=(Window.width * 0.8, None)))
        popup = make_popup("Court / Scoreboard SCENE", box, (0.94, 0.5))

        def pick_export() -> None:
            def chosen(path) -> None:
                dest = output_root() / "scene" / f"{Path(path).stem}.obj"

                def done(rep) -> None:
                    show_message("EXPORT SCENE OBJ", f"{rep['models']} model(s), {rep['vertices']:,} vertices\n{rep['obj']}", 0.4)
                self.run_bg(lambda: scenetool.export_obj(path, dest), done, "Exporting SCENE ...")
            popup.dismiss()
            PickerPopup("Pumili ng IFF / .SCNE", "file", (".iff", ".scne"), chosen, start=output_root()).open()

        def pick_import() -> None:
            def source_chosen(src) -> None:
                def obj_chosen(obj) -> None:
                    out = output_root() / "scene" / f"{Path(src).stem}_EDITED{Path(src).suffix}"

                    def done(rep) -> None:
                        show_message("IMPORT SCENE OBJ", f"Naisulat: {rep['output']}\nBuffers: {rep['buffers']} \u2022 "
                                     f"vertices moved: {rep['vertices_moved']}", 0.4)
                    self.run_bg(lambda: scenetool.import_obj(src, obj, out), done, "Importing SCENE ...")
                PickerPopup("Pumili ng na-edit na OBJ", "file", (".obj",), obj_chosen, start=output_root() / "scene").open()
            popup.dismiss()
            PickerPopup("Pumili ng ORIGINAL IFF / .SCNE", "file", (".iff", ".scne"), source_chosen, start=output_root()).open()

        def pick_move() -> None:
            """v247: move ONE placed Object (scoreboard, hoop ...) - writes a NEW copy, original untouched."""
            def chosen(path) -> None:
                def listed(rows) -> None:
                    if not rows:
                        show_message("MOVE OBJECT", "Walang placed Object na may Matrix sa file na ito.", 0.3)
                        return
                    self._scene_object_popup(path, rows)
                self.run_bg(lambda: scenetool.list_objects(path), listed, "Reading objects ...")
            popup.dismiss()
            PickerPopup("Pumili ng arena / scoreboard IFF", "file", (".iff", ".scne"), chosen, start=output_root()).open()

        for text, func in (("EXPORT OBJ", pick_export), ("IMPORT OBJ (bagong kopya)", pick_import),
                           ("MOVE OBJECT (scoreboard / hoop)", pick_move)):
            box.add_widget(make_btn(text, func, 50, "primary"))
        popup.open()

    def _scene_object_popup(self, path, rows) -> None:
        from nba2k20 import scenetool
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        filt = make_input("filter (regex): score|board|jumbo|led|hoop", 44, text="score|board|jumbo|led")
        listing = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        listing.bind(minimum_height=listing.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(listing)
        box.add_widget(filt)
        box.add_widget(scroll)
        popup = make_popup("Placed objects", box, (0.96, 0.85))

        def move_dialog(row) -> None:
            inner = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
            inner.add_widget(make_label(f"{row['name']} -> {row['target']}\nx {row['x']:.3f}   y {row['y']:.3f}   z {row['z']:.3f}\n"
                                        "Game axes: Y = pataas. Offset sa game units.", 12, MUTED,
                                        size_hint_y=None, height=dp(64), text_size=(Window.width * 0.8, None)))
            fields = [make_input(f"d{axis} (offset)", 44, text="0") for axis in "xyz"]
            for field in fields:
                inner.add_widget(field)
            dialog = make_popup("Move object", inner, (0.9, 0.62))

            def apply() -> None:
                try:
                    dx, dy, dz = (float(f.text.strip() or 0) for f in fields)
                except ValueError:
                    show_message("MOVE OBJECT", "Numero lang ang puwede (hal. 0, 2.5, -10).", 0.3)
                    return
                out = output_root() / "scene" / f"{Path(path).stem}_MOVED{Path(path).suffix}"

                def done(rep) -> None:
                    show_message("MOVE OBJECT", f"Naisulat: {rep['output']}\n{rep['object']}\n{rep['from']} -> {rep['to']}", 0.4)
                dialog.dismiss()
                popup.dismiss()
                self.run_bg(lambda: scenetool.move_object(path, row["name"], out, dx, dy, dz, scne=row["scne"]), done, "Moving object ...")
            inner.add_widget(make_btn("APPLY (bagong kopya)", apply, 50, "primary"))
            dialog.open()

        def refill(*_args) -> None:
            listing.clear_widgets()
            try:
                pat = re.compile(filt.text.strip(), re.I) if filt.text.strip() else None
            except re.error:
                pat = None
            shown = 0
            for row in rows:
                if pat and not (pat.search(row["name"]) or pat.search(row["target"])):
                    continue
                listing.add_widget(make_btn(f"{row['name']}  ({row['x']:.1f}, {row['y']:.1f}, {row['z']:.1f})",
                                            (lambda r=row: move_dialog(r)), 44))
                shown += 1
                if shown >= 80:
                    break
            if not shown:
                listing.add_widget(make_label("Walang tugma sa filter.", 13, MUTED, size_hint_y=None, height=dp(40)))
        filt.bind(on_text_validate=refill, text=refill)
        refill()
        popup.open()

    def blender_export(self) -> None:
        folder = output_root() / "blender" / (self.ws.opened.path.stem if self.ws.opened else "iff")

        def done(info) -> None:
            note = (
                f"Blender package ready:\n{info['folder']}\n\n"
                f"{len(info['models'])} model(s), {info['textures']} PNG texture(s)"
                + (", UV included." if info["uv"] else ".")
                + "\n\nOpen model_XX.obj in Blender (or run import_to_blender.py). "
                "Read README_BLENDER.txt. Keep the vertex count the same."
            )
            if info["texture_errors"]:
                note += "\n\nSkipped textures: " + ", ".join(map(str, info["texture_errors"][:5]))
            show_message("Blender export", note, 0.6)

        self.run_bg(lambda: self.ws.export_blender_package(folder), done, "Exporting Blender package ...")

    def blender_import(self) -> None:
        def picked(folder: Path) -> None:
            def done(report) -> None:
                lines = []
                if report["textures"] is not None:
                    lines.append(f"Textures imported: {len(report['textures']['changes'])}")
                if report["texture_error"]:
                    lines.append(f"Texture error: {report['texture_error']}")
                for name, result in report["meshes"]:
                    lines.append(f"{name}: {result}")
                lines.append("\nNow use Actions > Stage / Save.")
                show_message("Blender import", "\n".join(lines), 0.6)

            self.run_bg(lambda: self.ws.import_blender_package(folder), done, "Importing from Blender ...")

        PickerPopup("Choose the Blender package folder", "dir", (), picked,
                    start=output_root() / "blender").open()

    # ------------------------------------------------------------------ AI
    def _ai_settings(self) -> dict:
        try:
            return json.loads((Path(self.user_data_dir) / "ai.json").read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _ai_save(self, data: dict) -> None:
        try:
            (Path(self.user_data_dir) / "ai.json").write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass

    def ai_assist_popup(self) -> None:
        number = self.selected_texture
        if number is None or self.ws.opened is None:
            show_message("AI Assist", "Tap a colour texture in the Textures tab first "
                         "(example: HI - FACE DIFFUSE).", 0.35)
            return
        settings = self._ai_settings()
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
        info = make_label(
            "AUTO - works offline, walang API key at walang internet. Mag-tap ng chip o "
            "i-type ang gusto mo (English / Tagalog). Maglagay ng reference photo para "
            "ma-match ang skin tone.",
            12, MUTED, halign="left", valign="top", text_size=(Window.width * 0.84, None),
            size_hint_y=None,
        )
        info.bind(texture_size=lambda w, size: setattr(w, "height", size[1]))
        ask = make_input("Ano ang babaguhin? hal. mas maputi, warmer, center", 44)
        ask.text = settings.get("ask", "")
        key = make_input("Anthropic API key (optional)", 40)
        key.password = True
        key.text = settings.get("key", "")
        model = make_input("Model", 40)
        model.text = settings.get("model", ai_assist.DEFAULT_MODEL)
        state = {"reference": None, "result": None, "image": None, "adv": False}
        view = Image(fit_mode="contain")
        view_card = Card(kind="bar", padding=dp(4))
        view_card.add_widget(view)
        notes = left_label("", 12, MUTED, height=54)
        notes.shorten = False
        popup = make_popup("AI Assist  (auto, offline)", box, (0.97, 0.95))
        adv_box = BoxLayout(orientation="vertical", size_hint_y=None, height=0,
                            spacing=dp(4), opacity=0)

        def remember() -> None:
            self._ai_save({"key": key.text.strip(), "model": model.text.strip(), "ask": ask.text})

        def pick_reference() -> None:
            def picked(path: Path) -> None:
                state["reference"] = path
                notes.text = escape_markup(f"Reference photo: {path.name}")
                run()

            PickerPopup("Reference photo (optional)", "file", (".png", ".jpg", ".jpeg"), picked,
                        start=output_root() / "png").open()

        def run() -> None:
            remember()
            api_key = key.text.strip() if state["adv"] else ""

            def work():
                return self.ws.ai_adjust_texture(
                    number, ask.text, api_key, model.text.strip() or ai_assist.DEFAULT_MODEL,
                    state["reference"],
                )

            def done(result) -> None:
                params, _original, adjusted = result
                state["result"], state["image"] = params, adjusted
                buffer = io.BytesIO()
                adjusted.convert("RGB").save(buffer, format="PNG")
                view.texture = CoreImage(io.BytesIO(buffer.getvalue()), ext="png").texture
                changed = ", ".join(
                    f"{k} {v:.2f}" for k, v in params.items()
                    if k != "notes" and abs(v - ai_assist.PARAMS[k][0]) > 1e-6
                )
                notes.text = escape_markup(f"{params.get('notes', '')}\n{changed}".strip())

            self.run_bg(work, done, "AI Assist ...")

        def add_word(word: str) -> None:
            ask.text = f"{ask.text.strip().rstrip(',')}, {word}".strip(", ")
            run()

        def toggle_adv() -> None:
            state["adv"] = not state["adv"]
            adv_box.clear_widgets()
            if state["adv"]:
                adv_box.add_widget(key)
                adv_box.add_widget(model)
                adv_box.height, adv_box.opacity = dp(84), 1
            else:
                adv_box.height, adv_box.opacity = 0, 0

        def apply() -> None:
            if state["image"] is None:
                notes.text = "Wait for the preview first (tap Run)."
                return

            def done(_report) -> None:
                self.set_status(f"AI result imported into texture #{number} - use Actions > Stage / Save")
                popup.dismiss()
                self.refresh_preview()

            self.run_bg(lambda: self.ws.apply_texture_image(number, state["image"]), done,
                        "Encoding texture ...")

        chips = GridLayout(cols=4, size_hint_y=None, height=dp(84), spacing=dp(4))
        for label, word in (
            ("Lighter", "lighter"), ("Darker", "darker"), ("Warmer", "warmer"),
            ("Cooler", "cooler"), ("Contrast", "more contrast"), ("Center", "center"),
            ("Bigger", "bigger"), ("Smaller", "smaller"),
        ):
            chips.add_widget(make_btn(label, lambda w=word: add_word(w), 40, "ghost", font_size=sp(12)))
        for widget in (info, ask, chips, view_card, notes):
            box.add_widget(widget)
        box.add_widget(make_btn("Online AI (optional API key)", toggle_adv, 34, "ghost",
                                font_size=sp(11)))
        box.add_widget(adv_box)
        row = GridLayout(cols=4, size_hint_y=None, height=dp(48), spacing=dp(6))
        row.add_widget(make_btn("Reference", pick_reference, 48, "ghost", font_size=sp(13)))
        row.add_widget(make_btn("Run", run, 48, "primary", font_size=sp(13)))
        row.add_widget(make_btn("Import", apply, 48, "primary", font_size=sp(13)))
        row.add_widget(make_btn("Close", popup.dismiss, 48, "ghost", font_size=sp(13)))
        box.add_widget(row)
        popup.open()
        Clock.schedule_once(lambda _dt: run(), 0.3)

    # ------------------------------------------------------------ UV editor
    def uv_editor(self) -> None:
        number = self.selected_texture
        if number is None or self.ws.opened is None:
            show_message("UV Editor", "Tap a colour texture in the Textures tab first "
                         "(example: HI - FACE DIFFUSE).", 0.35)
            return
        self.run_bg(
            lambda: self.ws.texture_image(number).convert("RGBA"),
            lambda base: self._uv_editor_open(number, base),
            "Loading texture ...",
        )

    def preview_tapped(self) -> None:
        number = self.selected_texture
        if number is None:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
        popup = make_popup(f"Texture #{number}", box, (0.88, 0.5))

        def go(fn):
            popup.dismiss()
            Clock.schedule_once(lambda _dt: fn(), 0.1)

        if getattr(self, "cyberface_mode", False):
            box.add_widget(make_btn("EDIT  (CYBERFACE EDITOR 3D)", lambda: go(self.cyberface_workshop), 50, "primary"))
            box.add_widget(make_btn("UV Editor (tattoo)", lambda: go(self.uv_editor), 46, "ghost"))
            box.add_widget(make_btn("AI Assist", lambda: go(self.ai_assist_popup), 46, "ghost"))
        box.add_widget(make_btn("Export PNG", lambda: go(self.export_png), 46, "ghost"))
        box.add_widget(make_btn("Cancel", popup.dismiss, 46, "danger"))
        popup.open()

    def beard_here(self) -> None:
        """v273: GENERATE 3D BEARD on the IFF that is OPEN (the face / head / textures stay yours); only when the open IFF has no
        strand-card buffer does it fall back to the built-in template."""
        from nba2k20 import headhair
        if self.ws.opened is not None:
            try:
                headhair.beard_status(self.ws)
            except Exception:  # noqa: BLE001
                pass
            else:
                show_message("GENERATE 3D BEARD", "Sa IFF na bukas ito gagawin (hindi magbabago ang mukha mo). Pagkatapos ng "
                             "GENERATE: isara at buksan ulit ang CYBERFACE EDITOR para makita at ma-resize ang bagong beard.", 0.4)
                self.beard_generator_dialog(self.ws)
                return
        # v274: NO silent switch to the built-in template (that is what changed the face): tell instead
        show_message("GENERATE 3D BEARD", "Ang bukas na IFF ay walang 3D beard cards, kaya hindi ito mapapalitan dito.\n"
                     "I-port muna ang 2K14 (may kasamang 3D beard base) o buksan ang cyberface na may 3D beard. "
                     "Hindi na gagamit ng ibang IFF para hindi magbago ang mukha mo.", 0.45)

    def mesh_tool_beard(self) -> None:
        """Mesh Tool > 3D Hair: GENERATE 3D BEARD / HAIR / BRAIDS from the built-in 3213 template (no IFF needs to be open)."""
        from nba2k20 import headhair
        out_dir = output_root() / "iff" / "3D"
        template = headhair.builtin_beard_template()

        def done(res):
            ws2, out = res
            self.beard_generator_dialog(ws2, out)
        self.run_bg(lambda: headhair.open_template_workspace(self.ws, template, out_dir), done, "Ginagawang 3D ...")

    def mesh_tool(self) -> None:
        """Home 'Mesh Tool' (v249)."""
        from nba2k20 import meshtool
        meshtool.open_mesh_tool(self, UI)

    def head_sculpt(self) -> None:
        """Home 'Head Sculpt': the separate OBJ head editor (no IFF, no face PNG needed)."""
        headsculpt.open_head_sculpt(self, UI)

    def pick_face_png(self) -> None:
        """Home 'Open OBJ': pick an exported face PNG (e.g. texture_01_HI_FACE_DIFFUSE_256x256_fmt16.png)
        and edit it in the Cyberface Workshop (beard / hair / tattoo / paint + any OBJ) without opening an IFF."""
        def chosen(path: Path) -> None:
            def load():
                from PIL import Image as PILImage
                with PILImage.open(path) as im:
                    return im.convert("RGBA")
            self.run_bg(load, lambda base: workshop.open_workshop(self, UI, 0, base, standalone_name=Path(path).stem),
                        "Opening workshop ...")

        PickerPopup("Pumili ng face PNG", "file", (".png", ".jpg", ".jpeg"), chosen,
                    start=output_root() / "png").open()

    def cyberface_workshop(self) -> None:
        number = self.selected_texture
        if self.ws.opened is None:
            show_message("Cyberface Workshop", "Mag-open muna ng IFF.", 0.3)
            return
        if number is None or (self.ws.is_cyberface() and number == self.ws.hair_texture_number()):
            # v251: walang napili, o ang HAIR (1 MB) ang napili -> ang FACE map ang bubuksan, hindi ang buhok
            face = self.ws.face_diffuse_texture_number()
            if face is not None:
                number = face
                self.select_texture(number)
        if number is None:
            show_message("Cyberface Workshop", "Pumili muna ng texture sa Textures tab "
                         "(halimbawa HI - FACE DIFFUSE), tapos pindutin ulit.", 0.38)
            return
        if any(str(x.location) == "2k14" for x in self.ws.opened.textures):
            show_message("Cyberface Workshop", "Ito ay 2K14 IFF (read-only view): puwede mong i-preview at "
                         "i-Export PNG, pero hindi ito i-eedit dito.\n\nPara ilipat ang mukha sa 2K20: "
                         "Open OBB (2K20) -> 2K14 Converter -> FACE (2K14 IFF) -> 2K20 CYBERFACE.", 0.5)
            return
        if getattr(self, "cyberface_mode", False):
            face_number = self.ws.face_diffuse_texture_number()
            if face_number is None:
                show_message("Cyberface Workshop", "Walang FACE DIFFUSE o SKIN / FACE MAP texture sa IFF na ito. "
                             "Hindi maisusulat dito ang game-visible na beard/hair face layers.", 0.4)
                return
            if face_number != number:
                number = face_number
                self.select_texture(number)
                self.set_status(f"Workshop target: FACE DIFFUSE (texture #{number})")
        if self.ws.texture_is_normal(number):
            show_message("Cyberface Workshop", "Normal map ito. Piliin ang FACE DIFFUSE o SKIN texture.", 0.35)
            return
        self.run_bg(
            lambda: self.ws.texture_image(number).convert("RGBA"),
            lambda base: workshop.open_workshop(self, UI, number, base),
            "Opening workshop ...",
        )

    # ------------------------------------------------------------ HEAD / HAIR (v218)
    def head_hair_dialog(self) -> None:
        """Java 'HEAD / HAIR' screen: EDIT OBJ, EXPORT / REPLACE HEAD, HAIR and FULL OBJ for the open cyberface IFF."""
        from nba2k20 import headhair, objmesh as objmesh_core
        if self.ws.opened is None:
            show_message("HEAD / HAIR", "Mag-open muna ng IFF (HIHEAD / LOHEAD / cyberface).", 0.3)
            return
        try:
            info = headhair.report(self.ws)
        except Exception as error:  # noqa: BLE001
            show_message("HEAD / HAIR", friendly_error(error), 0.4)
            return
        slot = info["hair_slot"]
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
        box.add_widget(make_label(f"{info['name']}  \u2022  {info['vertices']:,} verts  \u2022  0x{info['offset']:x}  \u2022  "
                                  f"{info['bytes'] // 1024} KB", 12, MUTED, size_hint_y=None, height=dp(24)))
        box.add_widget(make_label((("3D STRAND CARDS \u2022 BEARD + BRAIDS (3213)" if info.get("cards") else "HAIR SLOT \u2022 READY")
                                   if slot else "HAIR SLOT \u2022 NONE (HEAD ONLY)"), 13,
                                  ACCENT if slot else MUTED, size_hint_y=None, height=dp(26)))
        popup = make_popup("HEAD / HAIR", box, (0.94, 0.86))

        def pick_export(part):
            def go():
                name = {"HEAD": "head", "HAIR": "hair", "FULL": "full", "BLENDER": "blender"}[part]
                dest = output_root() / "obj" / f"{info['name']}_{name}.obj"
                self.run_bg(lambda: headhair.export_obj(self.ws, dest, part),
                            lambda p: show_message("EXPORT " + part, f"Na-save: {p}", 0.35), "Exporting OBJ ...")
            return go

        def pick_replace(part):
            def go():
                def chosen(path):
                    def work():
                        rep = headhair.replace_obj(self.ws, objmesh_core.resolve_model_path(Path(path)), part)
                        ws = self.ws
                        if getattr(ws, "session", None) is not None and getattr(ws, "current_index", None) is not None:
                            ws.stage_current()
                            return rep, None
                        src = ws.opened.path
                        out = output_root() / "iff" / f"{src.stem}_EDITED{src.suffix}"
                        return rep, ws.save_iff(out, allow_overwrite=True)["output"]

                    def done(res):
                        rep, saved = res
                        note = ("\n(3213-vertex OBJ ito - galing marahil sa 3D BEARD cards head; ang HEAD lang ang nilagay, "
                               "hindi ang cards.)" if rep.get("head_only_fallback") else "")
                        if rep.get("conformed"):
                            note = (f"\n(Ibang topology ang OBJ: {rep['source_vertices']:,} vertices / {rep['source_faces']:,} faces. "
                                    f"Na-project sa native head: {rep['projected']:,} skin vertices sumunod sa surface, "
                                    f"{rep['followed']:,} (mata / bibig / malayo) sumunod sa kapitbahay. Hindi nagalaw ang UV, "
                                    "faces, hair at weights - kaya buo ang mukha.)")
                        show_message("REPLACE " + rep["part"], f"Naisulat: {rep['written']:,} vertices (match {rep['correlation']})."
                                     + note + "\n"
                                     + (f"Na-save ang kopya: {saved}" if saved else "Naka-stage na. Gamitin ang SAVE OBB."), 0.4)
                    self.run_bg(work, done, "Replacing ...")
                PickerPopup("Pumili ng OBJ (" + part + ")", "file", (".obj", ".n2km", ".model"), chosen,
                            start=output_root() / "obj").open()
            return go

        def edit_obj():
            popup.dismiss()
            self.cyberface_workshop()

        def row(*buttons):
            r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            for text, cb, enabled in buttons:
                b = make_btn(text, cb, 48, "primary" if enabled else "ghost", font_size=sp(12))
                b.disabled = not enabled
                r.add_widget(b)
            box.add_widget(r)

        def split_obj():
            from nba2k20 import objsplit

            def chosen(path):
                dest = output_root() / "obj" / f"{Path(path).stem}_split.obj"
                self.run_bg(lambda: objsplit.split_file(Path(path), dest),
                            lambda rep: show_message("SPLIT OBJ", "ONE OBJ: " + ", ".join(f"{k} {v}" for k, v in rep["faces"].items())
                                                     + f" faces ({rep['how']}).\n" + rep["output"], 0.4), "Splitting OBJ ...")
            PickerPopup("Pumili ng combined OBJ", "file", (".obj", ".n2km", ".model"), chosen, start=output_root() / "obj").open()

        def copy_from_iff(part):
            def go():
                def chosen(path):
                    def done(rep):
                        self.refresh_textures()
                        if rep.get("built"):
                            show_message("3D BEARD + BRAIDS IFF", f"Nagawa ang bagong IFF (head mo + 3D cards ng {rep['donor']}):\n{rep['output']}\n\n"
                                         "Ilagay sa OBB: Import IFF (replace this entry) sa entry na ito, tapos SAVE OBB COPY at subukan sa game.\n"
                                         "Face skin ay galing sa donor; ang hugis ng head ay sa iyo.", 0.5)
                        else:
                            show_message("COPY " + part, f"{rep['written']} vertices ng {rep['part']} mula sa {rep['donor']} ang nilagay sa head na ito."
                                         + ("\nKasama ang strand texture (HAIR / BACK OF HEAD) at faces. Beard + braids ay magkasama."
                                            "\nTingnan sa editor / Textures, tapos SAVE OBB COPY." if rep.get("used_cards") is not None else
                                            "\nTingnan sa editor, tapos SAVE. (Texture ng beard hindi kasama.)"), 0.4)
                    out_dir = output_root() / "iff" / "3D"
                    self.run_bg(lambda: headhair.transfer_part(self.ws, Path(path), part, out_dir), done, "Copying ...")
                PickerPopup("Pumili ng IFF na may 3D beard / braids (3168 o 3213 head)", "file", (".iff",), chosen).open()
            return go

        def copy_textures():
            def chosen(path):
                self.run_bg(lambda: headhair.transfer_textures(self.ws, Path(path)),
                            lambda rep: (self.refresh_textures(), show_message(
                                "COPY BEARD TEXTURES", "Nakopya: " + ", ".join(rep["textures"]) + f"\nmula sa {rep['donor']}.\n"
                                "Tingnan sa Textures, tapos Save OBB COPY at subukan sa game.", 0.4)),
                            "Copying textures ...")
            PickerPopup("Pumili ng IFF na may 3D beard (donor)", "file", (".iff",), chosen).open()

        def resize_dialog():
            """BEARD / HAIR (braids) LENGTH and WIDTH: stretches the 3D mesh vertices of the open cyberface IFF."""
            state = {"BEARD": [1.0, 1.0], "HAIR": [1.0, 1.0]}
            rbox = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
            status = make_label("Pindutin ang + / - . Ang 1.00 ay orihinal na laki.", 12, MUTED, size_hint_y=None, height=dp(56),
                                halign="left", valign="top", text_size=(Window.width * 0.8, None))
            rbox.add_widget(status)
            rpop = make_popup("RESIZE BEARD / HAIR", rbox, (0.94, 0.78))

            def show():
                status.text = (f"BEARD  haba {state['BEARD'][0]:.2f}  \u2022  lapad {state['BEARD'][1]:.2f}\n"
                               f"HAIR (braids)  haba {state['HAIR'][0]:.2f}  \u2022  lapad {state['HAIR'][1]:.2f}")

            def step(part, index, factor):
                def go():
                    state[part][index] *= factor
                    try:
                        rep = headhair.resize_part(self.ws, part, state[part][0], state[part][1])
                    except Exception as error:  # noqa: BLE001
                        show_message("RESIZE " + part, friendly_error(error), 0.4)
                        return
                    state[part] = [rep["length"], rep["width"]]
                    show()
                return go

            def reset():
                for part in ("BEARD", "HAIR"):
                    try:
                        headhair.reset_part(self.ws, part)
                    except Exception:  # noqa: BLE001
                        pass
                    state[part] = [1.0, 1.0]
                show()

            def save():
                def work():
                    ws = self.ws
                    if getattr(ws, "session", None) is not None and getattr(ws, "current_index", None) is not None:
                        ws.stage_current()
                        return None
                    src = ws.opened.path
                    out = output_root() / "iff" / f"{src.stem}_EDITED{src.suffix}"
                    return ws.save_iff(out, allow_overwrite=True)["output"]
                self.run_bg(work, lambda saved: show_message(
                    "RESIZE", (f"Na-save ang kopya: {saved}" if saved else "Naka-stage na. Gamitin ang SAVE OBB.")
                    + "\nSubukan sa kopya ng OBB.", 0.4), "Saving ...")

            def pair(label, part, index):
                r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
                r.add_widget(make_btn(label + " -", step(part, index, 0.92), 48, "primary", font_size=sp(12)))
                r.add_widget(make_btn(label + " +", step(part, index, 1.08), 48, "primary", font_size=sp(12)))
                rbox.add_widget(r)

            pair("BEARD HABA", "BEARD", 0)
            pair("BEARD LAPAD", "BEARD", 1)
            pair("HAIR HABA", "HAIR", 0)
            pair("HAIR LAPAD", "HAIR", 1)
            r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
            r.add_widget(make_btn("RESET", reset, 48, "ghost", font_size=sp(12)))
            r.add_widget(make_btn("SAVE", save, 48, "primary", font_size=sp(12)))
            rbox.add_widget(r)
            rbox.add_widget(make_label("Positions lang ng beard / hair vertices ang binabago. Hindi pa nasubukan sa game.",
                                       11, MUTED, halign="left", valign="top", text_size=(Window.width * 0.8, None)))
            rbox.add_widget(BoxLayout())
            rbox.add_widget(make_btn("CLOSE", rpop.dismiss, 46, "ghost"))
            show()
            rpop.open()

        def gen_beard():
            """GENERATE 3D BEARD (v239): procedural strand cards with DENSITY / LENGTH / THICKNESS / CURL / DROOP sliders.

            v239: hindi na kailangan pumili ng template IFF - gamit na agad ang built-in na 3213 template (nba2k20/assets/
            beard_template_3213.iff) para gawing 3D ang head mo, deretso na sa GENERATE dialog."""
            if info.get("cards"):
                popup.dismiss()
                self.beard_generator_dialog(self.ws)
                return
            out_dir = output_root() / "iff" / "3D"
            template = headhair.builtin_beard_template()

            def done(res):
                ws2, out = res
                popup.dismiss()
                self.beard_generator_dialog(ws2, out)
            self.run_bg(lambda: headhair.open_template_workspace(self.ws, template, out_dir), done, "Ginagawang 3D ...")

        box.add_widget(make_label("HEAD / HAIR REPLACEMENT", 11, MUTED, size_hint_y=None, height=dp(22)))
        row(("GENERATE 3D BEARD / HAIR / BRAIDS  \u2022  SLIDERS  \u2022  AUTO KAPAL", gen_beard, True))
        row(("SPLIT HEAD + HAIR + MOUTH + EYES \u2022 ONE OBJ", split_obj, True))
        def edit_cards():
            """v240: the 3D editor of the generated BEARD / HAIR / BRAIDS (Cyberface Editor with the cards, BEARD already locked)."""
            if not info.get("cards"):
                show_message("EDIT 3D BEARD / HAIR / BRAIDS", "Wala pang 3D cards ang IFF na ito. GENERATE 3D BEARD muna, i-SAVE, "
                             "tapos 'BUKSAN ANG 3D IFF PARA I-EDIT'.", 0.45)
                return
            number = self.selected_texture
            if number is None:
                number = self.ws.face_diffuse_texture_number()
            if number is None:
                rows = [r for r in self.ws.texture_rows() if r["decodable"] and not r.get("runtime")]
                number = rows[0]["number"] if rows else None
            if number is None:
                show_message("EDIT 3D BEARD / HAIR / BRAIDS", "Walang texture na mabuksan sa IFF na ito.", 0.35)
                return
            self.select_texture(number)
            self.start_part = "BEARD"
            popup.dismiss()
            self.cyberface_workshop()
        row(("EDIT OBJ", edit_obj, True), ("EDIT 3D BEARD / HAIR / BRAIDS", edit_cards, True))
        row(("EXPORT FULL OBJ", pick_export("FULL"), True), ("REPLACE OBJ", pick_replace("FULL"), True))
        row(("EXPORT FOR BLENDER (FACE/HAIR/BEARD)", pick_export("BLENDER"), True))
        row(("COPY BEARD FROM IFF", copy_from_iff("BEARD"), slot), ("COPY HAIR FROM IFF", copy_from_iff("HAIR"), slot))
        row(("COPY BEARD TEXTURES FROM IFF", copy_textures, slot), ("RESIZE BEARD / HAIR (HABA)", resize_dialog, slot))
        row(("EXPORT HAIR", pick_export("HAIR"), slot), ("REPLACE HAIR", pick_replace("HAIR"), slot))
        row(("EXPORT HEAD", pick_export("HEAD"), True), ("REPLACE HEAD", pick_replace("HEAD"), True))
        box.add_widget(make_label("EDIT OBJ = buksan ang HEAD sa Cyberface Editor (APPLY ang magsusulat).\n"
                                  "REPLACE = positions lang ang isusulat; mali ang vertex order = tatanggihan, walang masisira.",
                                  11, MUTED, halign="left", valign="top", text_size=(Window.width * 0.8, None)))
        box.add_widget(BoxLayout())
        box.add_widget(make_btn("CLOSE", popup.dismiss, 46, "ghost"))
        popup.open()

    # ------------------------------------------------------------ GENERATE 3D BEARD (v232)
    def beard_generator_dialog(self, target, out_path=None) -> None:
        """One-press 3D beard (hair cards) with live preview.  ``target`` = the Workspace whose 3213 IFF is changed (the open one,
        or the 3D IFF that was just built from a template); ``out_path`` = where SAVE writes it for a template build."""
        from nba2k20 import headhair
        try:
            status = headhair.beard_status(target)
        except Exception as error:  # noqa: BLE001
            show_message("GENERATE 3D BEARD", friendly_error(error), 0.4)
            return
        colors = {"BLACK": (20, 15, 13), "DARK BROWN": (46, 30, 20), "BROWN": (84, 55, 34), "GRAY": (120, 118, 116)}
        state = {"density": 0.9, "length": 1.0, "thickness": 1.5, "curl": 0.3, "droop": 0.75, "color": colors["BLACK"],
                 "seed": 1, "yaw": 0.0, "pitch": 0.0, "busy": False, "again": False, "timer": None,
                 "kind": "beard", "take_hair": False, "base_paint": False, "shape": "cards"}   # v278: real strand cards by default
        root = BoxLayout(orientation="vertical", spacing=dp(5), padding=dp(4))
        info_label = make_label("", 12, MUTED, size_hint_y=None, height=dp(34), halign="left", valign="middle",
                                text_size=(Window.width * 0.88, None))
        root.add_widget(info_label)
        picture = DragImage(lambda dx, dy: turn(dx / dp(3), -dy / dp(6)), fit_mode="contain", size_hint_y=0.28)
        root.add_widget(picture)
        popup = make_popup("GENERATE 3D BEARD", root, (0.97, 0.95))

        def params() -> dict:
            return {k: state[k] for k in ("density", "length", "thickness", "curl", "droop", "color", "seed", "kind", "take_hair", "base_paint", "shape")}

        def show(res) -> None:
            state["busy"] = False
            png, rep, error = res
            if error is not None:
                info_label.text = "Preview error: " + friendly_error(error)
            else:
                picture.texture = CoreImage(io.BytesIO(png), ext="png").texture
                note = ("  " + rep["notes"][0]) if rep["notes"] else ""
                if rep.get("braids_removed"):
                    note += "  (Walang free na lugar sa atlas: aalisin ang braids / hair cards.)"
                limit = status["max_cards_all"] if state["take_hair"] else status["max_cards"]
                info_label.text = (f"{rep['cards']} cards  \u2022  hanggang {limit} ang kasya sa IFF na ito.{note}\n"
                                   "I-drag ang larawan para iikot.")
            if state["again"]:
                state["again"] = False
                render()

        def render(*_a) -> None:
            if state["busy"]:
                state["again"] = True
                return
            state["busy"] = True
            snapshot, yaw, pitch = params(), state["yaw"], state["pitch"]

            def work():
                try:
                    image, rep = headhair.preview_beard(target, snapshot, yaw, pitch, 360)
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    res = (buffer.getvalue(), rep, None)
                except Exception as exc:  # noqa: BLE001
                    log_error("beard preview", exc)
                    res = (None, None, exc)
                Clock.schedule_once(lambda _dt: show(res), 0)
            threading.Thread(target=work, daemon=True).start()

        def later(*_a) -> None:
            if state["timer"] is not None:
                state["timer"].cancel()
            state["timer"] = Clock.schedule_once(render, 0.35)

        def turn(dyaw: float, dpitch: float) -> None:
            state["yaw"] = (state["yaw"] + dyaw) % 360.0
            state["pitch"] = max(-60.0, min(60.0, state["pitch"] + dpitch))
            render()

        def view(yaw: float, pitch: float = 0.0):
            def go():
                state["yaw"], state["pitch"] = yaw, pitch
                render()
            return go

        def slider_row(label, key, lo, hi):
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            name = make_label(f"{label} {state[key]:.2f}", 13, TEXT, size_hint_x=0.34, halign="left", valign="middle",
                              text_size=(Window.width * 0.3, None))
            slider = Slider(min=lo, max=hi, value=state[key], cursor_size=(dp(26), dp(26)))

            def changed(_w, value) -> None:
                state[key] = float(value)
                name.text = f"{label} {value:.2f}"
                later()
            slider.bind(value=changed)
            row.add_widget(name)
            row.add_widget(slider)
            root.add_widget(row)

        shapes = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        shape_buttons = {}
        shape_names = {"shell": "3D (tuloy-tuloy: beard shell, hair cap, braid tubes)", "cards": "CARDS (hiwa-hiwalay na strips)"}

        def pick_shape(shape):
            def go():
                state["shape"] = shape
                for name, button in shape_buttons.items():
                    button.text = ("[x] " if name == shape else "") + shape_names[name]
                render()
            return go

        for name in ("shell", "cards"):
            shape_buttons[name] = make_btn(("[x] " if name == state["shape"] else "") + shape_names[name], pick_shape(name), 40, "ghost",
                                           font_size=sp(10))
            shapes.add_widget(shape_buttons[name])
        root.add_widget(shapes)
        kinds = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        kind_buttons = {}

        def pick_kind(kind):
            def go():
                state["kind"] = kind
                for name, button in kind_buttons.items():
                    button.text = ("[x] " if name == kind else "") + {"beard": "BEARD", "hair": "HAIR", "braids": "BRAIDS"}[name]
                state["yaw"] = 180.0 if kind == "braids" else 0.0
                render()
            return go

        for name, text in (("beard", "[x] BEARD"), ("hair", "HAIR"), ("braids", "BRAIDS")):
            kind_buttons[name] = make_btn(text, pick_kind(name), 40, "ghost", font_size=sp(12))
            kinds.add_widget(kind_buttons[name])
        root.add_widget(kinds)

        def toggle_all():
            state["take_hair"] = not state["take_hair"]
            all_button.text = ("[x] " if state["take_hair"] else "") + "GAMITIN LAHAT NG SLOTS (mas maraming cards, aalisin ang kabilang hair / beard)"
            render()
        all_button = make_btn("GAMITIN LAHAT NG SLOTS (mas maraming cards, aalisin ang kabilang hair / beard)", toggle_all, 40, "ghost",
                              font_size=sp(10))
        root.add_widget(all_button)

        def toggle_paint():
            state["base_paint"] = not state["base_paint"]
            paint_button.text = ("[x] " if state["base_paint"] else "") + "PINTURA SA MUKHA (OPTIONAL - babaguhin ang face texture, kaya naka-OFF)"
        paint_button = make_btn("PINTURA SA MUKHA (OPTIONAL - babaguhin ang face texture, kaya naka-OFF)", toggle_paint, 40, "ghost", font_size=sp(10))
        root.add_widget(paint_button)

        views = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        for text, yaw, pitch in (("HARAP", 0.0, 0.0), ("3/4", 40.0, 0.0), ("GILID", 90.0, 0.0), ("BABA", 0.0, -35.0)):
            views.add_widget(make_btn(text, view(yaw, pitch), 40, "ghost", font_size=sp(12)))
        root.add_widget(views)
        slider_row("KAPAL (DENSITY)", "density", 0.0, 1.0)
        slider_row("HABA", "length", 0.4, 2.2)
        slider_row("LAPAD NG HIBLA", "thickness", 0.4, 2.5)
        slider_row("KULOT (CURL)", "curl", 0.0, 1.0)
        slider_row("BAGSAK (DROOP)", "droop", 0.0, 1.0)

        palette = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))

        def set_color(rgb):
            def go():
                state["color"] = rgb
                render()
            return go

        def reshuffle():
            state["seed"] += 1
            render()

        for text, rgb in colors.items():
            palette.add_widget(make_btn(text, set_color(rgb), 40, "ghost", font_size=sp(11)))
        palette.add_widget(make_btn("SHUFFLE", reshuffle, 40, "ghost", font_size=sp(11)))
        root.add_widget(palette)

        def generate() -> None:
            def done(rep):
                self.refresh_textures()
                extra = ("\nInalis ang kabilang hair / beard cards para magkasya ito." if rep.get("braids_removed") else "")
                if rep["notes"]:
                    extra += "\n" + rep["notes"][0]
                kind_name = rep.get("kind", "beard")
                what = (f"3D {kind_name.upper()} SHELL {rep['grid'][0]} x {rep['grid'][1]}" if rep.get("shape") == "shell" and rep.get("grid")
                        else f"{rep['cards']} 3D braid tubes" if rep.get("shape") == "tubes"
                        else f"{rep['cards']} cards")
                show_message("GENERATE 3D " + rep.get("kind", "beard").upper(), f"{what} ({rep['vertices']} vertices) ang nilagay sa IFF.{extra}\n"
                             "Ayusin pa ang sliders at pindutin ulit ang GENERATE (laging mula sa orihinal, hindi nag-iipon).\n"
                             "Kapag ok na: SAVE.", 0.45)
            self.run_bg(lambda: headhair.generate_beard(target, params()), done, "Generating 3D beard ...")

        def reset() -> None:
            self.run_bg(lambda: headhair.reset_generated_beard(target),
                        lambda _r: (self.refresh_textures(), render()), "Restoring ...")

        def rebase() -> None:
            def done(_r):
                show_message("GENERATE 3D BEARD", "Ang kasalukuyang beard (kasama ang anumang na-edit mo sa CYBERFACE EDITOR "
                             "/ OBJ) ay bago nang base. RESET at ang susunod na GENERATE ay dito na mag-uumpisa, hindi na sa "
                             "dating beard.", 0.4)
                render()
            self.run_bg(lambda: headhair.rebase_beard(target), done, "Marking base ...")

        def save() -> None:
            def work():
                if out_path is not None:
                    return target.save_iff(out_path, allow_overwrite=True)["output"]
                if getattr(target, "session", None) is not None and getattr(target, "current_index", None) is not None:
                    target.stage_current()
                    return None
                src = target.opened.path
                out = output_root() / "iff" / f"{src.stem}_EDITED{src.suffix}"
                return target.save_iff(out, allow_overwrite=True)["output"]

            def done(saved):
                if out_path is not None:
                    show_message("SAVE 3D BEARD", f"Na-save ang 3D IFF:\n{saved}\n\nIlagay sa OBB: Import IFF (replace this entry), "
                                 "tapos SAVE OBB COPY at subukan sa game.\n\nPara i-edit ang beard sa CYBERFACE EDITOR: pindutin ang "
                                 "'BUKSAN ANG 3D IFF PARA I-EDIT' (nasa baba ng dialog).", 0.5)
                else:
                    show_message("SAVE 3D BEARD", (f"Na-save ang kopya: {saved}" if saved else "Naka-stage na. Gamitin ang SAVE OBB.")
                                 + "\nSubukan sa kopya ng OBB.", 0.4)
            self.run_bg(work, done, "Saving ...")

        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        actions.add_widget(make_btn("GENERATE", generate, 48, "primary", font_size=sp(13)))
        actions.add_widget(make_btn("RESET", reset, 48, "ghost", font_size=sp(12)))
        actions.add_widget(make_btn("SAVE", save, 48, "primary", font_size=sp(13)))
        actions.add_widget(make_btn("CLOSE", popup.dismiss, 48, "ghost", font_size=sp(12)))
        root.add_widget(actions)
        def open_3d() -> None:
            """v240: make the saved 3D IFF the OPEN IFF, so the Cyberface Editor / OBJ editor / EXPORT-REPLACE OBJ see the head AND the
            generated cards (the editor of a 3213 IFF shows and sculpts the beard cards: lock BEARD, GRAB / SMOOTH / SIZE ...)."""
            if out_path is None:
                show_message("3D IFF", "Ang IFF na ito ay 3D na (3213) at bukas na: gamitin ang EDIT: CYBERFACE EDITOR "
                             "(piliin ang BEARD sa PART LOCK).", 0.4)
                return

            def work():
                if not Path(out_path).is_file():
                    target.save_iff(out_path, allow_overwrite=True)
                return str(out_path)

            def done(path):
                popup.dismiss()
                self.ws.open_iff(Path(path))
                self.refresh_textures()
                show_message("3D IFF", "Bukas na ang 3D IFF. Pumili ng texture, pindutin ang EDIT: CYBERFACE EDITOR, "
                             "tapos BEARD sa PART LOCK para i-sculpt ang beard cards (APPLY ang magsusulat).", 0.45)
            self.run_bg(work, done, "Opening 3D IFF ...")
        root.add_widget(make_btn("BUKSAN ANG 3D IFF PARA I-EDIT (CYBERFACE / OBJ EDITOR)", open_3d, 40, "ghost", font_size=sp(10)))
        root.add_widget(make_btn("I-EDIT SA CYBERFACE / OBJ EDITOR, TAPOS: GAMITIN ITO BILANG BAGONG BASE", rebase, 40,
                                 "ghost", font_size=sp(10)))
        popup.open()
        render()

    # ------------------------------------------------------------ OBJ Creator
    def obj_creator(self) -> None:
        """Hair / beard shells fitted to a head mesh -> OBJ for Blender.  Not written into the game IFF."""
        import io
        import math
        from nba2k20 import objcreator
        from nba2k20 import objmesh as objmesh_core

        state = {"creator": None, "yaw": 20.0, "pitch": 3.0, "zoom": 1.0, "source": ""}
        root = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
        root.add_widget(make_label("HAIR  \u2022  BEARD  \u2022  EXPORT OBJ", 11, MUTED, size_hint_y=None, height=dp(18)))
        card = Card(kind="bar", padding=dp(4))

        def drag(dx: float, dy: float) -> None:
            state["yaw"] += dx / dp(4)
            state["pitch"] = max(-85.0, min(85.0, state["pitch"] - dy / dp(5)))
            render()

        image = DragImage(drag, fit_mode="contain")
        card.add_widget(image)
        root.add_widget(card)
        status = make_label("Loading ...", 12, MUTED, size_hint_y=None, height=dp(34))
        root.add_widget(status)

        def render(*_a) -> None:
            creator = state["creator"]
            if creator is None:
                return

            def work():
                img = creator.preview((420, 420), yaw=math.radians(state["yaw"]),
                                      pitch=math.radians(state["pitch"]), zoom=state["zoom"])
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                return buffer.getvalue()

            def done(data):
                image.texture = CoreImage(io.BytesIO(data), ext="png").texture
                status.text = escape_markup(f"{state['source']}   |   {creator.status()}")

            self.run_bg(work, done, "Rendering ...")

        def load_mesh(path, label: str) -> None:
            def done(creator):
                state.update(creator=creator, source=label)
                render()

            self.run_bg(lambda: objcreator.Creator(objmesh_core.load_obj(Path(path))), done, "Loading head ...")

        def part_row(title, styles, first, add, remove, grow):
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(92), spacing=dp(4))
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            drop = Drop(text=first, values=list(styles), size_hint_x=0.34)
            row.add_widget(drop)
            row.add_widget(make_btn(f"ADD {title}", lambda: add(drop.text), 44, "primary", font_size=sp(12)))
            row.add_widget(make_btn(f"REMOVE {title}", remove, 44, font_size=sp(12)))
            box.add_widget(row)
            row2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            row2.add_widget(make_btn(f"{title} LONGER  +", lambda: grow(objcreator.LENGTH_STEP), 44, "primary",
                                     font_size=sp(12)))
            row2.add_widget(make_btn(f"{title} SHORTER  -", lambda: grow(-objcreator.LENGTH_STEP), 44,
                                     font_size=sp(12)))
            box.add_widget(row2)
            return box

        def grow(which: str, delta: float) -> None:
            creator = state["creator"]
            if creator is None:
                return
            ok = (creator.grow_hair if which == "hair" else creator.grow_beard)(delta)
            if not ok:
                show_message("Haba", "Mag-ADD muna ng buhok / balbas bago pahabain.", 0.3)
            render()

        def add_hair(style: str) -> None:
            creator = state["creator"]
            if creator is None:
                return
            if not creator.add_hair(style):
                show_message("Hair", "Walang nahanap na bahagi ng ulo para sa buhok sa mesh na ito.", 0.35)
            render()

        def add_beard(style: str) -> None:
            creator = state["creator"]
            if creator is None:
                return
            if not creator.add_beard(style):
                show_message("Beard", "Walang nahanap na bahagi ng mukha para sa balbas sa mesh na ito.", 0.35)
            render()

        def remove(which: str) -> None:
            creator = state["creator"]
            if creator is not None:
                (creator.remove_hair if which == "hair" else creator.remove_beard)()
                render()

        root.add_widget(part_row("HAIR", objcreator.HAIR_STYLES, "Caesar", add_hair, lambda: remove("hair"),
                                 lambda d: grow("hair", d)))
        root.add_widget(part_row("BEARD", objcreator.BEARD_STYLES, "Goatee", add_beard, lambda: remove("beard"),
                                 lambda d: grow("beard", d)))

        def view(yaw=0.0, pitch=0.0, zoom=1.0) -> None:
            state["yaw"] += yaw
            state["pitch"] = max(-85.0, min(85.0, state["pitch"] + pitch))
            state["zoom"] = max(0.3, min(6.0, state["zoom"] * zoom))
            render()

        views = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for text, kw in (("Left", {"yaw": -25}), ("Right", {"yaw": 25}), ("Up", {"pitch": -15}),
                         ("Down", {"pitch": 15}), ("Zoom -", {"zoom": 0.8}), ("Zoom +", {"zoom": 1.25})):
            views.add_widget(make_btn(text, partial(view, **kw), 40, font_size=sp(11)))
        root.add_widget(views)

        def from_iff() -> None:
            if self.ws.opened is None:
                show_message("IFF > OBJ", "Buksan muna ang isang IFF (Models tab), tapos pindutin ulit.", 0.35)
                return

            def work():
                info = self.ws.head_mesh_obj()
                if info is None:
                    raise RuntimeError("Walang head mesh na nakita sa IFF na ito (texture-only ang file).")
                return info

            self.run_bg(work, lambda info: load_mesh(info["path"], f"IFF mesh #{info['number']}"),
                        "Reading IFF mesh ...")

        def open_obj() -> None:
            PickerPopup("Piliin ang head OBJ / N2KM", "file", (".obj", ".n2km", ".model"),
                        lambda chosen: load_mesh(objmesh_core.resolve_model_path(chosen), Path(chosen).name),
                        start=output_root()).open()

        def recent_obj() -> None:
            import json
            try:
                items = json.loads((output_root() / "workshop_recent_obj.json").read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                items = []
            items = [e for e in items if isinstance(e, dict) and Path(str(e.get("path", ""))).is_file()]
            if not items:
                show_message("Recent OBJ", "Wala pang recent. Mag-open o mag-save ng OBJ sa Workshop muna.", 0.3)
                return
            box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
            rp = make_popup("Recent OBJ / IFF-OBJ", box, (0.94, 0.7))
            for e in items:
                tag = {"iff": "IFF-OBJ", "saved": "SAVED"}.get(e.get("kind"), "OBJ")
                box.add_widget(make_btn(f"[{tag}] {Path(e['path']).name}",
                                        lambda p=e["path"]: (rp.dismiss(), load_mesh(p, Path(p).name)), 44,
                                        font_size=sp(11)))
            box.add_widget(make_btn("Close", rp.dismiss, 42))
            rp.open()

        def save_obj() -> None:
            creator = state["creator"]
            if creator is None:
                return

            def work():
                return creator.export(output_root() / "obj" / "head_hair_beard.obj")

            self.run_bg(work, lambda path: show_message(
                "OBJ saved",
                f"{path}\n\nHiwalay na group ang head / hair / beard. Para sa Blender ito - HINDI maisusulat "
                "sa game IFF ang dagdag na mesh (kailangan ng parehong vertex count).", 0.55), "Saving OBJ ...")

        bottom = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        bottom.add_widget(make_btn("IFF > OBJ", from_iff, 46, font_size=sp(12)))
        bottom.add_widget(make_btn("OPEN OBJ", open_obj, 46, font_size=sp(12)))
        bottom.add_widget(make_btn("RECENT", recent_obj, 46, font_size=sp(12)))
        bottom.add_widget(make_btn("SAVE OBJ", save_obj, 46, "primary", font_size=sp(12)))
        root.add_widget(bottom)
        popup = make_popup("OBJ CREATOR", root, (0.98, 0.96))
        root.add_widget(make_btn("Close", popup.dismiss, 42))
        popup.open()
        default = ASSETS / "head_default.obj"
        if default.is_file():
            load_mesh(default, "Default head")
        else:
            status.text = "Walang default head: pindutin ang OPEN OBJ o IFF > OBJ."

    def _uv_editor_open(self, number: int, base) -> None:
        if self.ws.texture_is_normal(number):
            show_message("UV Editor", "Pang-kulay na texture lang ito (Face Diffuse, Skin), "
                         "hindi para sa normal map.", 0.35)
            return
        small_base = base.copy()
        small_base.thumbnail((512, 512))
        state = {"overlay": None, "opacity": 1.0, "mode": "Normal", "name": "", "ink": facelab.DEFAULT_INK}
        box = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(4))
        popup = make_popup("UV Editor", box, (0.98, 0.96))

        def render(_dt=None) -> None:
            image = small_base
            if state["overlay"] is not None:
                image = overlay_core.composite_overlay(
                    small_base, facelab.ink_boost(state["overlay"], state["ink"]), canvas.cx, canvas.cy, canvas.size_frac,
                    canvas.rot, state["opacity"],
                    facelab.ink_mode({"ink": state["ink"], "mode": state["mode"]}),
                )
            texture = Texture.create(size=image.size, colorfmt="rgba")
            texture.blit_buffer(image.convert("RGBA").tobytes(), colorfmt="rgba", bufferfmt="ubyte")
            texture.flip_vertical()
            canvas.set_texture(texture)

        def changed(final: bool) -> None:
            Clock.unschedule(render)
            Clock.schedule_once(render, 0 if final else 0.06)

        canvas = OverlayCanvas(changed)
        hint = left_label("I-drag para ilipat  |  Pinch para i-resize at ikutin  |  "
                          "Hilahin ang kanto para i-resize", 12, MUTED, height=34)
        status = left_label("Pindutin ang Add overlay at pumili ng PNG (tattoo / logo).", 12, MUTED, height=24)

        def add_overlay() -> None:
            def picked(path: Path) -> None:
                try:
                    with Image.open(path) as source:
                        src = source.convert("RGBA")
                        src.thumbnail((1024, 1024))
                        state["overlay"] = facelab.auto_transparent(src)   # JPG / opaque PNG -> background removed
                except Exception as error:  # noqa: BLE001
                    show_message("Overlay", friendly_error(error), 0.35)
                    return
                state["name"] = path.name
                canvas.has_overlay = True
                canvas.aspect = state["overlay"].height / max(1, state["overlay"].width)
                canvas.cx = canvas.cy = 0.5
                canvas.size_frac, canvas.rot = 0.2, 0.0
                status.text = escape_markup(f"Overlay: {path.name}")
                canvas._redraw()
                render()

            PickerPopup("Pumili ng overlay PNG", "file", (".png", ".jpg", ".jpeg", ".webp"), picked,
                        start=output_root() / "png").open()

        def reset() -> None:
            canvas.cx = canvas.cy = 0.5
            canvas.size_frac, canvas.rot, canvas.zoom = 0.2, 0.0, 1.0
            opacity.value = 1.0
            canvas._redraw()
            render()

        def zoom(factor: float) -> None:
            canvas.zoom = max(1.0, min(4.0, canvas.zoom * factor))
            canvas._redraw()

        def set_size(fraction: float) -> None:
            canvas.size_frac = fraction
            canvas._changed(True)

        def turn(delta: float) -> None:
            canvas.rot = 0.0 if delta == 0 else (canvas.rot + delta + 180) % 360 - 180
            canvas._changed(True)

        def next_ink() -> None:
            state["ink"] = (state["ink"] + 1) % len(facelab.INK_LEVELS)
            ink_btn.text = "Ink: " + facelab.INK_LEVELS[state["ink"]]
            render()

        ink_btn = make_btn("Ink: " + facelab.INK_LEVELS[facelab.DEFAULT_INK], next_ink, 42, "ghost", font_size=sp(12))
        top = GridLayout(cols=5, size_hint_y=None, height=dp(42), spacing=dp(4))
        top.add_widget(make_btn("Add overlay", add_overlay, 42, "primary", font_size=sp(12)))
        top.add_widget(ink_btn)
        top.add_widget(make_btn("+ Zoom", lambda: zoom(1.4), 42, "ghost", font_size=sp(12)))
        top.add_widget(make_btn("- Zoom", lambda: zoom(1 / 1.4), 42, "ghost", font_size=sp(12)))
        top.add_widget(make_btn("Reset", reset, 42, "danger", font_size=sp(12)))

        sizes = GridLayout(cols=4, size_hint_y=None, height=dp(44), spacing=dp(4))
        for label, fraction in overlay_core.SIZE_PRESETS:
            sizes.add_widget(make_btn(label, lambda f=fraction: set_size(f), 44, "ghost", font_size=sp(12)))

        opacity_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        opacity_row.add_widget(left_label("Opacity", 13, MUTED, size_hint_x=0.22))
        opacity = Slider(min=0.05, max=1.0, value=1.0, cursor_size=(dp(26), dp(26)))

        def on_opacity(_w, value) -> None:
            state["opacity"] = value
            changed(False)

        opacity.bind(value=on_opacity)
        opacity_row.add_widget(opacity)

        mode_buttons: dict = {}

        def set_mode(name: str) -> None:
            state["mode"] = name
            for key, button in mode_buttons.items():
                button.kind = "primary" if key == name else "ghost"
            render()

        blends = GridLayout(cols=4, size_hint_y=None, height=dp(44), spacing=dp(4))
        for name in overlay_core.BLEND_MODES:
            button = make_btn(name, lambda n=name: set_mode(n), 44,
                              "primary" if name == "Normal" else "ghost", font_size=sp(12))
            mode_buttons[name] = button
            blends.add_widget(button)

        rotate = GridLayout(cols=3, size_hint_y=None, height=dp(40), spacing=dp(4))
        rotate.add_widget(make_btn("Rotate -5", lambda: turn(-5), 40, "ghost", font_size=sp(12)))
        rotate.add_widget(make_btn("Rotate 0", lambda: turn(0), 40, "ghost", font_size=sp(12)))
        rotate.add_widget(make_btn("Rotate +5", lambda: turn(5), 40, "ghost", font_size=sp(12)))

        def apply() -> None:
            if state["overlay"] is None:
                status.text = "Magdagdag muna ng overlay."
                return
            placement = (canvas.cx, canvas.cy, canvas.size_frac, canvas.rot, state["opacity"],
                         facelab.ink_mode({"ink": state["ink"], "mode": state["mode"]}))

            def work():
                result = overlay_core.composite_overlay(base, facelab.ink_boost(state["overlay"], state["ink"]), *placement)
                return self.ws.apply_texture_image(number, result)

            def done(_report) -> None:
                self.set_status(f"Overlay applied to texture #{number} - use Actions > Stage / Save")
                popup.dismiss()
                self.refresh_preview()

            self.run_bg(work, done, "Applying overlay ...")

        bottom = GridLayout(cols=2, size_hint_y=None, height=dp(48), spacing=dp(6))
        bottom.add_widget(make_btn("APPLY", apply, 48, "primary"))
        bottom.add_widget(make_btn("CANCEL", popup.dismiss, 48, "ghost"))

        for widget in (top, hint, canvas, status, sizes, opacity_row, blends, rotate, bottom):
            box.add_widget(widget)
        popup.open()
        Clock.schedule_once(render, 0.1)

    # resources tab
    def _build_resources_tab(self):
        box = BoxLayout(orientation="vertical", spacing=dp(6))
        self.res_filter = make_input("Filter kind / name / extension", 42)
        self.res_filter.bind(text=lambda *_: self.refresh_resources())
        self.res_list = RowList(size_hint_y=0.45)
        self.res_text = Label(
            text="", halign="left", valign="top", size_hint_y=None, font_name=MONO_FONT,
            font_size=sp(12), color=TEXT,
        )
        self.res_text.bind(
            width=lambda w, v: setattr(w, "text_size", (v, None)),
            texture_size=lambda w, s: setattr(w, "height", s[1]),
        )
        scroll = ScrollView(size_hint_y=0.3)
        scroll.add_widget(self.res_text)
        text_card = Card(kind="bar", size_hint_y=0.3, padding=dp(8))
        text_card.add_widget(scroll)
        grid = GridLayout(cols=2, size_hint_y=None, height=dp(104), spacing=dp(6))
        grid.add_widget(make_btn("Export raw", self.export_resource, 48))
        grid.add_widget(make_btn("Import raw", self.import_resource, 48, "primary"))
        grid.add_widget(make_btn("Export all resources", self.export_all_resources, 48))
        for widget in (self.res_filter, self.res_list, text_card, grid):
            box.add_widget(widget)
        self.refresh_resources()
        return box

    def refresh_resources(self) -> None:
        rows = self.ws.resource_rows(self.res_filter.text)
        self.res_list.set_rows(
            [
                row_entry(
                    f"#{r['number']}   {r['kind']}   {r['extension']}",
                    f"{r['size']:,} B  |  {r['offset']}",
                    partial(self.select_resource, r["number"]),
                    key=r["number"],
                )
                for r in rows
            ]
        )

    def select_resource(self, number: int, *_args) -> None:
        self.selected_resource = number
        self.res_list.mark_selected(number)
        self.res_text.text = self.ws.resource_text(number)

    def export_resource(self) -> None:
        if self.selected_resource is None:
            show_message("Resource", "Tap a resource first.", 0.3)
            return
        number = self.selected_resource
        folder = output_root() / "resources"
        self.run_bg(
            lambda: self.ws.export_resource(number, folder),
            lambda path: self.set_status(f"Saved {path}"),
            "Exporting ...",
        )

    def import_resource(self) -> None:
        if self.selected_resource is None:
            show_message("Resource", "Tap a resource first.", 0.3)
            return
        number = self.selected_resource

        def picked(path: Path) -> None:
            self.run_bg(
                lambda: self.ws.import_resource(number, path),
                lambda _r: self.set_status("Imported (same size required) - now use Actions > Save"),
                "Importing ...",
            )

        PickerPopup("Choose replacement file", "file", (), picked,
                    start=output_root() / "resources").open()

    def export_all_resources(self) -> None:
        folder = output_root() / "resources_all" / Path(self.ws.current_label).stem
        self.run_bg(
            lambda: self.ws.export_all_resources(folder),
            lambda result: show_message(
                "Export all resources", f"{result[0]} file(s) saved to:\n{folder}"
            ),
            "Exporting all resources ...",
        )

    # ------------------------------------------------------------- actions
    def show_actions(self) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
        popup = make_popup("Actions", box, (0.92, None))
        actions: list[tuple[str, str, object]] = []
        if self.ws.session is not None:
            actions += [
                ("Stage this entry (Save IFF)", "primary", self.stage_entry),
                ("Save OBB copy", "ghost", self.save_obb_copy),
                ("Save OBB (overwrite original)", "danger", self.save_obb_overwrite),
                ("Export IFF (save complete IFF)", "ghost", self.export_complete_iff),
                ("Import IFF (replace this entry)", "ghost", self.replace_complete_iff),
            ]
        else:
            actions += [
                ("Save IFF copy", "primary", self.save_iff_copy),
                ("Save IFF (overwrite original)", "danger", self.save_iff_overwrite),
            ]
        actions.append(("Scoreboard preview", "primary", self.show_scoreboard_preview))
        actions.append(("Texture scan report", "ghost", self.show_scan_report))
        for text, kind, callback in actions:
            box.add_widget(
                make_btn(text, lambda cb=callback: (popup.dismiss(), cb()), 50, kind)
            )
        box.add_widget(make_btn("Close", popup.dismiss, 50))
        popup.height = dp(70 + 58 * (len(actions) + 1))
        popup.open()

    def show_scoreboard_preview(self) -> None:
        """Rebuild the in-game scorebug look from this IFF's plate texture (placeholders for
        team logos / scores / clock, which the game draws at runtime)."""
        from nba2k20 import scoreboard

        def done(png):
            view = Image(fit_mode="contain")
            view.texture = CoreImage(io.BytesIO(png), ext="png").texture
            box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(4))
            box.add_widget(view)
            popup = make_popup("Scoreboard preview (logos/score/clock = placeholders)", box, (0.96, 0.42))
            box.add_widget(make_btn("Close", popup.dismiss, 48))
            popup.open()

        self.run_bg(
            lambda: scoreboard.preview_png(self.ws._need_iff()),
            done,
            "Building scoreboard preview ...",
        )

    def show_scan_report(self) -> None:
        self.run_bg(
            self.ws.texture_scan_report,
            lambda text: show_message("Texture scan report", text, 0.6),
            "Scanning ...",
        )

    def stage_entry(self) -> None:
        def done(result):
            self.set_status(f"Entry {result['index']} staged ({result['staged_total']} total)")
            show_message(
                "Staged",
                "The OBB is not changed yet.\nPick another IFF from 'IFF List' to keep editing,\n"
                "or Back, then 'Save OBB copy'.",
                0.36,
            )

        self.run_bg(self.ws.stage_current, done, "Rebuilding entry ...")

    def save_iff_copy(self) -> None:
        source = self.ws.opened.path
        destination = copy_with_suffix(output_root() / source.name, "_EDITED")
        self.run_bg(
            lambda: self.ws.save_iff(destination),
            lambda r: show_message("IFF saved", r["output"], 0.3),
            "Saving IFF ...",
        )

    def save_iff_overwrite(self) -> None:
        source = self.ws.opened.path
        confirm(
            "Overwrite IFF?",
            f"This replaces:\n{source}",
            lambda: self.run_bg(
                lambda: self.ws.save_iff(source, allow_overwrite=True),
                lambda r: show_message("IFF saved", r["output"], 0.3),
                "Saving IFF ...",
            ),
        )

    def export_complete_iff(self) -> None:
        folder = output_root() / "iff"
        self.run_bg(
            lambda: self.ws.export_obb_iff(folder),
            lambda path: show_message("Exported", str(path), 0.3),
            "Exporting IFF ...",
        )

    def replace_complete_iff(self) -> None:
        """Import IFF: replace the open OBB entry with a complete IFF file (any .iff file name)."""
        expected = self.ws.session.entry_name(self.ws.current_index)

        def run(path: Path) -> None:
            self.run_bg(
                lambda: self.ws.replace_obb_iff(path, check_name=False),
                lambda r: show_message(
                    "IFF imported",
                    f"{r['label']} staged ({r['mode']}).\nThe OBB is not changed until you 'Save OBB copy'.",
                    0.36,
                ) or self.show_iff_screen(r["label"], f"OBB #{r['index']}"),
                "Validating replacement ...",
            )

        def picked(path: Path) -> None:
            if path.name.lower() == expected.lower():
                run(path)
            else:  # allowed (renamed export), but say so: the size check still protects the OBB
                confirm(
                    "Different file name",
                    f"Open entry: {expected}\nChosen file: {path.name}\n\n"
                    "Import it into this entry anyway? (The decompressed size must match exactly.)",
                    lambda: run(path),
                )

        PickerPopup(
            f"Import IFF into {expected}", "file", (".iff",), picked, start=output_root() / "iff"
        ).open()


if __name__ == "__main__":
    ToolApp().run()
