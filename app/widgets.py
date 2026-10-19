"""عناصر الواجهة المشتركة: نصوص عربية RTL، بطاقات، أزرار، حقول، حوارات."""
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import (BooleanProperty, ColorProperty, ListProperty, NumericProperty, ObjectProperty,
                             StringProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hx

import arabic_reshaper
from bidi.algorithm import get_display

from theme import C, GRAD, ICON, tint

_reshaper = arabic_reshaper.ArabicReshaper(configuration={"delete_harakat": False, "support_ligatures": True})


def ar(text):
    """تشكيل الحروف العربية وترتيبها بصرياً (Kivy لا يدعم RTL بنفسه)."""
    if not text:
        return ""
    return get_display(_reshaper.reshape(str(text)))


_measure_cache = {}


def _width(shaped, font, size, bold=False):
    key = (shaped, font, round(size, 1), bold)
    w = _measure_cache.get(key)
    if w is None:
        w = CoreLabel(font_name=font, font_size=size, bold=bold).get_extents(shaped)[0]
        if len(_measure_cache) > 4000:
            _measure_cache.clear()
        _measure_cache[key] = w
    return w


def wrap_ar(text, font, size, max_w, bold=False):
    """يلفّ النص العربي منطقياً ثم يشكّل كل سطر على حدة، فتبقى الأسطر بالترتيب الصحيح."""
    out = []
    for para in str(text).split("\n"):
        words, cur = para.split(" "), []
        for w in words:
            trial = " ".join(cur + [w])
            if cur and _width(ar(trial), font, size, bold) > max_w:
                out.append(ar(" ".join(cur)))
                cur = [w]
            else:
                cur.append(w)
        out.append(ar(" ".join(cur)))
    return "\n".join(out)


# ---------------------------------------------------------------- تدرجات
_grad_cache = {}


def gradient(stops, vertical=False):
    key = (tuple(stops), vertical)
    tex = _grad_cache.get(key)
    if tex:
        return tex
    cols = [hx(s) for s in stops]
    n = 96
    data = bytearray()
    for i in range(n):
        t = i / (n - 1) * (len(cols) - 1)
        a = min(int(t), len(cols) - 2)
        f = t - a
        px = [int((cols[a][k] * (1 - f) + cols[a + 1][k] * f) * 255) for k in range(4)]
        data += bytes(px)
    if vertical:  # الصف الأول في Kivy هو الأسفل
        rows = [bytes(data[i * 4:(i + 1) * 4]) for i in range(n)]
        data = b"".join(reversed(rows))
    tex = Texture.create(size=(1, n) if vertical else (n, 1), colorfmt="rgba")
    tex.blit_buffer(bytes(data), colorfmt="rgba", bufferfmt="ubyte")
    tex.mag_filter = "linear"
    tex.min_filter = "linear"
    tex.wrap = "clamp_to_edge"
    _grad_cache[key] = tex
    return tex


# ---------------------------------------------------------------- نص
class ALabel(Label):
    """نص عربي (يمين) مع التفاف صحيح. استخدم atext بدل text."""
    atext = StringProperty("")
    wrap = BooleanProperty(True)
    autoh = BooleanProperty(False)

    def __init__(self, atext="", **kw):
        kw.setdefault("font_name", "Taj")
        kw.setdefault("halign", "right")
        kw.setdefault("valign", "middle")
        kw.setdefault("color", C.text)
        kw.setdefault("font_size", sp(15))
        auto = kw.pop("autoh", False)
        super().__init__(**kw)
        self.autoh = auto
        if auto:
            self.size_hint_y = None
            self.height = self.font_size * 1.6
        self.bind(atext=self._upd, width=self._upd, font_size=self._upd, font_name=self._upd, bold=self._upd)
        if auto:
            self.bind(texture_size=self._fit)
        self.atext = atext
        self._upd()

    def _fit(self, *_):
        self.height = max(self.texture_size[1] + dp(2), self.font_size * 1.5)

    def _upd(self, *_):
        w = self.width
        if self.wrap and w > dp(30):
            self.text = wrap_ar(self.atext, self.font_name, self.font_size, w - dp(2), self.bold)
        else:
            self.text = ar(self.atext)
        self.text_size = (w, None if self.autoh else self.height) if self.wrap else (None, None)
        if not self.wrap:
            self.text_size = (w, self.height)


class Icon(Label):
    def __init__(self, name="home", size=22, color=None, **kw):
        kw.setdefault("font_name", "Icons")
        kw.setdefault("size_hint", (None, None))
        super().__init__(text=ICON.get(name, name), font_size=sp(size), color=color or C.text, **kw)
        self.size = (dp(size + 6), dp(size + 6))
        self.halign = self.valign = "center"
        self.text_size = self.size
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


class RBox(BoxLayout):
    """صف أفقي يبدأ من اليمين (RTL): أول عنصر يُضاف يظهر في أقصى اليمين."""

    def __init__(self, **kw):
        kw.setdefault("orientation", "horizontal")
        super().__init__(**kw)

    def add_widget(self, widget, index=0, canvas=None):
        super().add_widget(widget, len(self.children), canvas)


def Spacer(h=8):
    return Widget(size_hint_y=None, height=dp(h))


# ---------------------------------------------------------------- حاويات
class Card(BoxLayout):
    bg = ColorProperty(C.card)
    radius = NumericProperty(dp(20))
    shadow = BooleanProperty(True)

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("padding", dp(14))
        kw.setdefault("spacing", dp(8))
        super().__init__(**kw)
        with self.canvas.before:
            self._sh = [Color(0.2, 0.2, 0.5, 0.05), RoundedRectangle(), Color(0.2, 0.2, 0.5, 0.06), RoundedRectangle()]
            self._c = Color(*self.bg)
            self._r = RoundedRectangle()
        self.bind(pos=self._draw, size=self._draw, bg=self._draw, radius=self._draw)

    def _draw(self, *_):
        x, y, w, h = *self.pos, *self.size
        r = self.radius
        self._c.rgba = self.bg
        self._r.pos, self._r.size, self._r.radius = (x, y), (w, h), [r]
        on = 1 if self.shadow else 0
        self._sh[0].a = 0.05 * on
        self._sh[2].a = 0.06 * on
        self._sh[1].pos, self._sh[1].size, self._sh[1].radius = (x - dp(2), y - dp(5)), (w + dp(4), h + dp(2)), [r + dp(2)]
        self._sh[3].pos, self._sh[3].size, self._sh[3].radius = (x, y - dp(2)), (w, h), [r]


class GradBox(BoxLayout):
    """خلفية متدرجة."""
    stops = ListProperty(GRAD["login"])
    radius = ListProperty([0])
    vertical = BooleanProperty(False)

    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        super().__init__(**kw)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._r = RoundedRectangle()
        self.bind(pos=self._draw, size=self._draw, stops=self._draw, radius=self._draw)
        self._draw()

    def _draw(self, *_):
        self._r.texture = gradient(self.stops, self.vertical)
        self._r.pos, self._r.size, self._r.radius = self.pos, self.size, self.radius


class Progress(Widget):
    value = NumericProperty(0)
    color = ColorProperty(C.indigo)

    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(8))
        super().__init__(**kw)
        with self.canvas:
            Color(*tint(C.indigo, 0.12))
            self._bg = RoundedRectangle()
            self._c = Color(*self.color)
            self._fg = RoundedRectangle()
        self.bind(pos=self._draw, size=self._draw, value=self._draw, color=self._draw)

    def _draw(self, *_):
        h = self.height
        self._bg.pos, self._bg.size, self._bg.radius = self.pos, self.size, [h / 2]
        w = max(h, self.width * max(0.0, min(1.0, self.value)))
        # التعبئة من اليمين لتناسب RTL
        self._fg.pos = (self.x + self.width - w, self.y)
        self._fg.size = (w, h)
        self._fg.radius = [h / 2]
        self._c.rgba = self.color


# ---------------------------------------------------------------- أزرار
class Btn(ButtonBehavior, BoxLayout):
    """زر: primary (متدرج) | soft (ملوّن خفيف) | ghost | danger"""

    def __init__(self, text="", icon=None, kind="primary", color=None, height=52, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(height))
        kw.setdefault("padding", [dp(14), 0])
        kw.setdefault("spacing", dp(8))
        super().__init__(orientation="horizontal", **kw)
        self.kind = kind
        self.accent = color or (C.rose if kind == "danger" else C.indigo)
        fg = C.white if kind in ("primary", "danger") else self.accent
        with self.canvas.before:
            self._c = Color(1, 1, 1, 1)
            self._r = RoundedRectangle()
        self.bind(pos=self._draw, size=self._draw, state=self._draw)
        row = RBox(size_hint=(None, 1), spacing=dp(8))
        self.lbl = ALabel(text, wrap=False, color=fg, bold=True, font_size=sp(16), halign="center",
                          size_hint=(None, 1))
        self.lbl.width = max(dp(20), _width(ar(text), "Taj", sp(16), True) + dp(8))
        if icon:
            row.add_widget(Icon(icon, 22, fg, size_hint=(None, 1)))
        row.add_widget(self.lbl)
        row.width = self.lbl.width + (dp(36) if icon else 0)
        self._row = row
        self.add_widget(Widget())
        self.add_widget(row)
        self.add_widget(Widget())
        self._draw()

    def set_text(self, text):
        self.lbl.atext = text
        self.lbl.width = _width(ar(text), "Taj", sp(16), True) + dp(10)
        self._row.width = self.lbl.width + dp(36)

    def _draw(self, *_):
        a = 0.85 if self.state == "down" else 1
        if self.kind == "primary":
            self._r.texture = gradient([self._hex(self.accent, 1), self._hex(self.accent, 0.82)])
            self._c.rgba = (1, 1, 1, a)
        elif self.kind == "danger":
            self._r.texture = None
            self._c.rgba = (*self.accent[:3], a)
        elif self.kind == "white":
            self._r.texture = None
            self._c.rgba = (1, 1, 1, 0.88 if self.state == "down" else 1)
        else:
            self._r.texture = None
            self._c.rgba = tint(self.accent, 0.22 if self.state == "down" else 0.12)
        self._r.pos, self._r.size, self._r.radius = self.pos, self.size, [self.height / 2.6]

    @staticmethod
    def _hex(c, k):
        return "#%02x%02x%02x" % tuple(int(min(1, v * k) * 255) for v in c[:3])


class IconBtn(ButtonBehavior, BoxLayout):
    def __init__(self, icon, color=None, size=44, bg=None, **kw):
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("pos_hint", {"center_y": 0.5})
        super().__init__(**kw)
        self.size = (dp(size), dp(size))
        self.bgc = bg
        with self.canvas.before:
            self._c = Color(*(bg or (0, 0, 0, 0)))
            self._r = RoundedRectangle()
        self.bind(pos=self._d, size=self._d)
        self.add_widget(Icon(icon, 24, color or C.text, size_hint=(1, 1)))
        self._d()

    def _d(self, *_):
        self._r.pos, self._r.size, self._r.radius = self.pos, self.size, [self.height / 2]


# ---------------------------------------------------------------- حقول
class Field(BoxLayout):
    """حقل إدخال بعنوان عربي. ltr=True للأرقام والبريد."""

    def __init__(self, label, icon=None, ltr=True, password=False, input_type="text", multiline=False, hint="",
                 height=76, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(height))
        kw.setdefault("spacing", dp(4))
        super().__init__(**kw)
        self.add_widget(ALabel(label, size_hint_y=None, height=dp(20), font_size=sp(13), color=C.muted, wrap=False))
        box = RBox(size_hint_y=None, height=dp(48), padding=[dp(10), 0], spacing=dp(6))
        with box.canvas.before:
            self._bg = Color(0.96, 0.96, 0.99, 1)
            self._rr = RoundedRectangle()
            self._ln = Color(*C.line)
            self._ll = Line(width=dp(1))
        self._box = box
        box.bind(pos=self._d, size=self._d)
        if icon:
            box.add_widget(Icon(icon, 20, C.muted, size_hint=(None, 1)))
        self.input = TextInput(
            multiline=multiline, password=password, input_type=input_type, font_name="Taj", font_size=sp(16),
            halign="left" if ltr else "right", background_color=(0, 0, 0, 0), background_normal="",
            background_active="", foreground_color=C.text, cursor_color=C.indigo, padding=[dp(4), dp(13), dp(4), dp(8)],
            write_tab=False, hint_text=ar(hint) if hint else "", hint_text_color=(0.6, 0.6, 0.7, 1),
        )
        self.input.bind(focus=self._focus)
        box.add_widget(self.input)
        self.add_widget(box)
        self._d()

    def _d(self, *_):
        b = self._box
        self._rr.pos, self._rr.size, self._rr.radius = b.pos, b.size, [dp(14)]
        self._ll.rounded_rectangle = (*b.pos, *b.size, dp(14))

    def _focus(self, _w, f):
        self._ln.rgba = C.indigo if f else C.line

    @property
    def text(self):
        return self.input.text.strip()

    @text.setter
    def text(self, v):
        self.input.text = v


# ---------------------------------------------------------------- خيارات
class Chips(ScrollView):
    """شرائح اختيار مفرد تمرَّر أفقياً عند الحاجة. options = [(key, نص)]"""

    def __init__(self, options, selected=None, on_select=None, color=None, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(44))
        kw.setdefault("bar_width", 0)
        kw.setdefault("do_scroll_y", False)
        super().__init__(**kw)
        self.options, self.on_select, self.color = options, on_select, color or C.indigo
        self.selected = selected if selected is not None else (options[0][0] if options else None)
        self.inner = RBox(size_hint=(None, 1), spacing=dp(8), padding=[0, dp(2)])
        self.inner.bind(minimum_width=self._fit)
        super().add_widget(self.inner)
        self.bind(width=self._fit)
        self._build()

    def _fit(self, *_):
        self.inner.width = max(self.inner.minimum_width, self.width)
        self.scroll_x = 1  # RTL: نبدأ من اليمين

    def _build(self):
        self.inner.clear_widgets()
        for key, text in self.options:
            on = key == self.selected
            b = Btn(text, kind="primary" if on else "soft", color=self.color, height=40)
            b.size_hint_x = None
            b.width = max(dp(70), b.lbl.width + dp(34))
            b.bind(on_release=lambda _b, k=key: self.pick(k))
            self.inner.add_widget(b)
        self.inner.add_widget(Widget())

    def pick(self, key):
        self.selected = key
        self._build()
        if self.on_select:
            self.on_select(key)


# ---------------------------------------------------------------- قائمة قابلة للتمرير
class VScroll(ScrollView):
    def __init__(self, padding=16, spacing=12, **kw):
        kw.setdefault("bar_width", 0)
        kw.setdefault("scroll_type", ["content"])
        super().__init__(**kw)
        self.body = GridLayout(cols=1, size_hint_y=None, padding=dp(padding), spacing=dp(spacing))
        self.body.bind(minimum_height=self.body.setter("height"))
        super().add_widget(self.body)

    def add(self, w):
        self.body.add_widget(w)
        return w

    def clear(self):
        self.body.clear_widgets()


# ---------------------------------------------------------------- نوافذ وتنبيهات
def toast(text, kind="info"):
    col = {"ok": C.green, "err": C.rose, "info": C.indigo}.get(kind, C.indigo)
    card = Card(bg=col, size_hint=(None, None), padding=[dp(18), dp(10)], radius=dp(24), shadow=True)
    lbl = ALabel(text, color=C.white, bold=True, halign="center", wrap=True, autoh=True,
                 size_hint_x=None)
    w = min(Window.width - dp(40), dp(340))
    lbl.width = w - dp(36)
    card.add_widget(lbl)
    card.width = w
    Clock.schedule_once(lambda dt: _place_toast(card, lbl), 0)
    Window.add_widget(card)
    card.opacity = 0
    from kivy.animation import Animation
    Animation(opacity=1, d=0.2).start(card)
    Clock.schedule_once(lambda dt: Animation(opacity=0, d=0.3).start(card), 2.8)
    Clock.schedule_once(lambda dt: Window.remove_widget(card), 3.2)


def _place_toast(card, lbl):
    card.height = lbl.height + dp(22)
    card.pos = ((Window.width - card.width) / 2, dp(96))


class Dialog(ModalView):
    def __init__(self, title, content=None, buttons=(), dismissable=True, icon=None, color=None, **kw):
        super().__init__(auto_dismiss=dismissable, background="", background_color=(0.1, 0.08, 0.25, 0.55),
                         size_hint=(None, None), **kw)
        w = min(Window.width - dp(32), dp(400))
        self.width = w
        card = Card(padding=dp(18), spacing=dp(10), radius=dp(26), size_hint=(1, None))
        head = RBox(size_hint_y=None, height=dp(36), spacing=dp(8))
        if icon:
            head.add_widget(Icon(icon, 26, color or C.indigo, size_hint=(None, 1)))
        head.add_widget(ALabel(title, bold=True, font_size=sp(19), wrap=False))
        card.add_widget(head)
        if content is not None:
            card.add_widget(content)
        if buttons:
            row = RBox(size_hint_y=None, height=dp(48), spacing=dp(10))
            for text, kind, cb in buttons:
                b = Btn(text, kind=kind, height=48)
                b.size_hint_x = 1
                b.bind(on_release=lambda _b, cb=cb: self._run(cb))
                row.add_widget(b)
            card.add_widget(row)
        def _fit(*_):
            card.height = card.minimum_height
            self.height = card.minimum_height
        card.bind(minimum_height=_fit)
        _fit()
        self.add_widget(card)

    def _run(self, cb):
        if cb is None:
            self.dismiss()
        elif cb() is not False:
            self.dismiss()


def message(title, text, icon="info", color=None, ok="حسناً"):
    lbl = ALabel(text, autoh=True, color=C.muted)
    d = Dialog(title, lbl, [(ok, "primary", None)], icon=icon, color=color)
    d.open()
    return d
