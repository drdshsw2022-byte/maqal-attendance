"""مكونات مشتركة بين اللوحات: الرأس، شريط التبويب، الملف الشخصي، التنسيق."""
import time

from kivy.app import App
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from theme import C, GRAD, STATUS, tint
from widgets import (ALabel, Btn, Card, Dialog, Field, GradBox, Icon, IconBtn, RBox, Spacer, VScroll, ar, message,
                     toast)

ROLE_AR = {"student": "طالب", "doctor": "دكتور", "admin": "مدير النظام"}
STAGE_AR = {1: "الأولى", 2: "الثانية", 3: "الثالثة", 4: "الرابعة", 5: "الخامسة"}
SHIFT_AR = {"morning": "صباحي", "evening": "مسائي", "all": "الكل"}
DEPT_AR = {"ai": "هندسة الذكاء الاصطناعي", "control": "هندسة السيطرة والحاسبات", "cyber": "هندسة الأمن السيبراني"}


def app():
    return App.get_running_app()


def fmt_dt(ts):
    return time.strftime("%Y/%m/%d  %H:%M", time.localtime(ts)) if ts else "—"


def fmt_t(ts):
    return time.strftime("%H:%M", time.localtime(ts)) if ts else ""


def pct_color(pct, warn=False):
    if pct is None:
        return C.muted
    if warn:
        return C.rose
    return C.green if pct >= 85 else C.amber


class TapCard(ButtonBehavior, Card):
    pass


def chip(text, color, h=24, size=12):
    """وسم صغير ملوّن (شكل حبة)."""
    c = Card(bg=tint(color, 0.14), radius=dp(h / 2), shadow=False, padding=[dp(10), 0], size_hint=(None, None),
             height=dp(h), pos_hint={"center_y": 0.5})
    lbl = ALabel(text, color=color, bold=True, font_size=sp(size), wrap=False, halign="center")
    from widgets import _width
    lbl.width = _width(ar(text), "Taj", sp(size), True) + dp(8)
    lbl.size_hint_x = None
    c.add_widget(lbl)
    c.width = lbl.width + dp(20)
    return c


def tile(value, label, stops):
    t = GradBox(stops=stops, radius=[dp(18)], padding=[dp(10), dp(8)], spacing=0, size_hint_y=None, height=dp(86))
    t.add_widget(ALabel(str(value), color=C.white, font_name="TajX", font_size=sp(26), halign="center", wrap=False))
    t.add_widget(ALabel(label, color=(1, 1, 1, 0.9), font_size=sp(12), halign="center", wrap=False,
                        size_hint_y=None, height=dp(20)))
    return t


def tiles_row(items):
    """items: [(قيمة، عنوان، (لونا التدرج))]"""
    row = RBox(size_hint_y=None, height=dp(86), spacing=dp(10))
    for v, l, s in items:
        row.add_widget(tile(v, l, s))
    return row


def section(text):
    return ALabel(text, bold=True, font_size=sp(17), size_hint_y=None, height=dp(30), wrap=False)


def empty_note(text, icon="info"):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(120), spacing=dp(6))
    box.add_widget(Icon(icon, 40, C.muted, size_hint=(1, 1)))
    box.add_widget(ALabel(text, color=C.muted, halign="center", size_hint_y=None, height=dp(40)))
    return box


# ---------------------------------------------------------------- شريط التبويب
class TabItem(ButtonBehavior, BoxLayout):
    def __init__(self, key, icon, label, accent, **kw):
        super().__init__(orientation="vertical", padding=[0, dp(6)], spacing=dp(2), **kw)
        self.key, self.accent = key, accent
        self.icon = Icon(icon, 26, C.muted, size_hint=(1, 1))
        self.lbl = ALabel(label, color=C.muted, font_size=sp(11), halign="center", wrap=False, size_hint_y=None,
                          height=dp(16))
        self.add_widget(self.icon)
        self.add_widget(self.lbl)

    def set_active(self, on):
        col = self.accent if on else C.muted
        self.icon.color = col
        self.lbl.color = col
        self.lbl.bold = on


class TabBar(Card):
    def __init__(self, items, accent, on_select, **kw):
        super().__init__(orientation="horizontal", padding=[dp(6), 0], spacing=0, radius=dp(0), size_hint_y=None,
                         height=dp(66), **kw)
        self.items = {}
        self.on_select = on_select
        row = RBox()
        for key, icon, label in items:
            it = TabItem(key, icon, label, accent)
            it.bind(on_release=lambda w: self.on_select(w.key))
            self.items[key] = it
            row.add_widget(it)
        self.add_widget(row)

    def mark(self, key):
        for k, it in self.items.items():
            it.set_active(k == key)


# ---------------------------------------------------------------- لوحة عامة
class Dash(Screen):
    role = ""
    tabs = []
    accent = C.indigo

    def __init__(self, **kw):
        super().__init__(name=self.role, **kw)
        self.user, self.current = {}, None
        root = BoxLayout(orientation="vertical")
        self.header = GradBox(stops=GRAD[self.role], radius=[0, 0, dp(30), dp(30)], size_hint_y=None, height=dp(142),
                              padding=[dp(18), dp(28), dp(18), dp(14)], spacing=dp(2))
        self.h_uni = ALabel("جامعة المعقل الأهلية – البصرة", color=(1, 1, 1, 0.88), font_size=sp(13),
                            size_hint_y=None, height=dp(22), wrap=False)
        self.h_name = ALabel("", color=C.white, font_name="TajX", font_size=sp(24), size_hint_y=None, height=dp(38),
                             wrap=False)
        self.h_sub = ALabel("", color=(1, 1, 1, 0.92), font_size=sp(13), size_hint_y=None, height=dp(22), wrap=False)
        for w in (self.h_uni, self.h_name, self.h_sub):
            self.header.add_widget(w)
        self.body = BoxLayout()
        self.tabbar = TabBar(self.tabs, self.accent, self.select)
        for w in (self.header, self.body, self.tabbar):
            root.add_widget(w)
        self.add_widget(root)

    def enter(self, user):
        self.user = user
        self.h_name.atext = user["name"]
        self.h_sub.atext = self.subtitle(user)
        self.select(self.tabs[0][0])

    def subtitle(self, u):
        return ROLE_AR[self.role]

    def select(self, key):
        self.current = key
        self.tabbar.mark(key)
        self.body.clear_widgets()
        sc = VScroll()
        self.body.add_widget(sc)
        getattr(self, "tab_" + key)(sc)

    def refresh(self):
        if self.current:
            self.select(self.current)

    # --- الملف الشخصي (مشترك)
    def tab_profile(self, sc):
        u = self.user
        a = app()
        card = Card(size_hint_y=None, height=dp(150), spacing=dp(6))
        top = RBox(size_hint_y=None, height=dp(64), spacing=dp(12))
        badge = GradBox(stops=GRAD[self.role], radius=[dp(32)], size_hint=(None, None), size=(dp(60), dp(60)))
        badge.add_widget(Icon("person", 34, C.white, size_hint=(1, 1)))
        top.add_widget(badge)
        col = BoxLayout(orientation="vertical")
        col.add_widget(ALabel(u["name"], bold=True, font_size=sp(18), wrap=False))
        col.add_widget(ALabel(ROLE_AR[u["role"]], color=C.muted, wrap=False))
        top.add_widget(col)
        card.add_widget(top)
        ident = u.get("uid") or u.get("email") or ""
        card.add_widget(ALabel(("الرقم الجامعي: " if u.get("uid") else "البريد: ") + ident, color=C.muted, wrap=False,
                               size_hint_y=None, height=dp(24)))
        if u.get("uid") and u.get("email"):
            card.add_widget(ALabel("البريد المرتبط: " + u["email"], color=C.muted, wrap=False, size_hint_y=None,
                                   height=dp(24)))
        sc.add(card)
        sc.add(Btn("تغيير كلمة المرور", icon="key", kind="soft", color=self.accent,
                   on_release=lambda *_: change_password_dialog()))
        if u["role"] == "student":
            sc.add(Btn("ربط بريد Gmail بحسابي", icon="mail", kind="soft", color=C.sky,
                       on_release=lambda *_: set_email_dialog(self)))
        sc.add(Btn("إعدادات الخادم", icon="dns", kind="soft", color=C.muted,
                   on_release=lambda *_: a.server_dialog()))
        sc.add(Btn("تسجيل الخروج", icon="logout", kind="danger", on_release=lambda *_: a.logout()))
        sc.add(ALabel("جامعة المعقل الأهلية – البصرة\nنظام الحضور والغياب الذكي · الإصدار 1.0", color=C.muted,
                      font_size=sp(12), halign="center", autoh=True))


def change_password_dialog(forced=False):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(86 * 2), spacing=dp(4))
    old = Field("كلمة المرور الحالية", icon="lock", password=True)
    new = Field("كلمة المرور الجديدة (6 أحرف فأكثر)", icon="key", password=True)
    box.add_widget(old)
    box.add_widget(new)

    def save():
        if len(new.text) < 6:
            toast("كلمة المرور الجديدة قصيرة", "err")
            return False

        def ok(_):
            toast("تم تغيير كلمة المرور", "ok")
            dlg.dismiss()
            app().user["must_change"] = False

        app().api.post("/api/auth/change-password", {"old": old.input.text, "new": new.input.text}, ok)
        return False

    btns = [("حفظ", "primary", save)]
    if not forced:
        btns.append(("إلغاء", "soft", None))
    dlg = Dialog("تغيير كلمة المرور", box, btns, dismissable=not forced, icon="key")
    dlg.open()


def set_email_dialog(dash):
    f = Field("بريد Gmail", icon="mail", input_type="mail")

    def save():
        def ok(r):
            toast("تم ربط البريد، يمكنك الدخول به", "ok")
            app().user["email"] = r["email"]
            dash.user["email"] = r["email"]
            dash.refresh()
            dlg.dismiss()

        app().api.post("/api/auth/set-email", {"email": f.text}, ok)
        return False

    dlg = Dialog("ربط البريد", f, [("حفظ", "primary", save), ("إلغاء", "soft", None)], icon="mail")
    dlg.open()
