"""شاشات الدخول وتفعيل حساب الطالب."""
import os

from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen

from screens.common import app
from theme import ASSETS, C, GRAD
from widgets import ALabel, Btn, Card, Field, GradBox, Icon, IconBtn, RBox, Spacer, VScroll, toast


class ChoiceList(BoxLayout):
    """قائمة اختيار مفرد (أزرار عمودية)."""

    def __init__(self, options, color=C.indigo, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(8), **kw)
        self.options, self.value, self.color = options, None, color
        self.height = dp(46) * len(options) + dp(8) * max(0, len(options) - 1)
        self._build()

    def _build(self):
        self.clear_widgets()
        for key, text in self.options:
            b = Btn(text, kind="primary" if key == self.value else "soft", color=self.color, height=46)
            b.bind(on_release=lambda _b, k=key: self.pick(k))
            self.add_widget(b)

    def pick(self, k):
        self.value = k
        self._build()


def header_block(title, subtitle):
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(190), padding=[0, dp(40), 0, 0], spacing=dp(2))
    logo = os.path.join(ASSETS, "logo.png")
    box.add_widget(Image(source=logo, size_hint=(1, None), height=dp(74)))
    box.add_widget(ALabel(title, color=C.white, font_name="TajX", font_size=sp(27), halign="center", wrap=False,
                          size_hint_y=None, height=dp(44)))
    box.add_widget(ALabel(subtitle, color=(1, 1, 1, 0.9), font_size=sp(14), halign="center", wrap=False,
                          size_hint_y=None, height=dp(26)))
    return box


class LoginScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="login", **kw)
        bg = GradBox(stops=GRAD["login"], vertical=True)
        sc = VScroll(padding=0, spacing=0)
        sc.add(header_block("جامعة المعقل الأهلية", "البصرة · نظام الحضور والغياب الذكي"))
        card = Card(size_hint_y=None, height=dp(430), padding=[dp(20), dp(22)], spacing=dp(6), radius=dp(30))
        card.add_widget(ALabel("تسجيل الدخول", bold=True, font_size=sp(21), size_hint_y=None, height=dp(34), wrap=False))
        self.ident = Field("الرقم الجامعي أو البريد الإلكتروني (Gmail)", icon="person")
        self.pw = Field("كلمة المرور", icon="lock", password=True)
        card.add_widget(self.ident)
        card.add_widget(self.pw)
        self.go = Btn("دخول", icon="check", on_release=lambda *_: self.submit())
        card.add_widget(self.go)
        card.add_widget(ALabel("طالب جديد؟ فعّل حسابك بالرقم المعرفي أول مرة", color=C.muted, font_size=sp(13),
                               halign="center", size_hint_y=None, height=dp(30)))
        card.add_widget(Btn("تفعيل حساب الطالب", icon="reg", kind="soft", on_release=lambda *_: app().open("activate")))
        card.add_widget(Btn("إعدادات الخادم", icon="dns", kind="soft", color=C.muted, height=44,
                            on_release=lambda *_: app().server_dialog()))
        wrap = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(14), 0, dp(14), dp(24)])
        wrap.height = card.height + dp(24)
        wrap.add_widget(card)
        sc.add(wrap)
        bg.add_widget(sc)
        self.add_widget(bg)

    def on_pre_enter(self, *_):
        self.pw.text = ""

    def submit(self):
        ident, pw = self.ident.text, self.pw.input.text
        if not ident or not pw:
            toast("أدخل الرقم الجامعي أو البريد وكلمة المرور", "err")
            return
        a = app()
        a.api.post("/api/auth/login", {"identifier": ident, "password": pw, "device_id": a.device_id}, a.on_login)


class ActivateScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="activate", **kw)
        bg = GradBox(stops=GRAD["login"], vertical=True)
        sc = VScroll(padding=0, spacing=0)
        top = RBox(size_hint_y=None, height=dp(70), padding=[dp(10), dp(26), dp(10), 0])
        top.add_widget(IconBtn("back", C.white, on_release=lambda *_: app().back()))
        top.add_widget(ALabel("تفعيل حساب الطالب", color=C.white, bold=True, font_size=sp(20), wrap=False))
        sc.add(top)
        self.card = Card(size_hint_y=None, padding=[dp(20), dp(20)], spacing=dp(6), radius=dp(30))
        wrap = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(14), dp(6), dp(14), dp(24)])
        wrap.add_widget(self.card)
        self.wrap = wrap
        sc.add(wrap)
        bg.add_widget(sc)
        self.add_widget(bg)
        self.depts = []

    def on_pre_enter(self, *_):
        app().api.get("/api/meta/departments", self.build)
        self.card.clear_widgets()
        self.card.add_widget(ALabel("جارٍ التحميل…", color=C.muted, halign="center"))
        self.card.height = dp(100)
        self.wrap.height = dp(130)

    def build(self, depts):
        c = self.card
        c.clear_widgets()
        c.add_widget(ALabel("اكتب الرقم المعرفي المسجل لك في الجامعة، ثم اختر قسمك وكلمة مرور. يرتبط حسابك بهاتفك هذا.",
                            color=C.muted, font_size=sp(13), autoh=True))
        self.uid_f = Field("الرقم المعرفي (10 أرقام)", icon="badge", input_type="number")
        c.add_widget(self.uid_f)
        c.add_widget(ALabel("القسم", color=C.muted, font_size=sp(13), size_hint_y=None, height=dp(20), wrap=False))
        self.dept = ChoiceList([(d["key"], d["name"]) for d in depts])
        c.add_widget(self.dept)
        self.email = Field("بريد Gmail (اختياري — للدخول به لاحقاً)", icon="mail", input_type="mail")
        self.pw = Field("كلمة المرور (6 أحرف فأكثر)", icon="lock", password=True)
        self.pw2 = Field("تأكيد كلمة المرور", icon="lock", password=True)
        for w in (self.email, self.pw, self.pw2):
            c.add_widget(w)
        c.add_widget(Spacer(6))
        c.add_widget(Btn("تفعيل وتسجيل الدخول", icon="check", on_release=lambda *_: self.submit()))
        n = len(depts)
        c.height = dp(60) + dp(76) * 4 + self.dept.height + dp(54) + dp(60) + dp(30)
        self.wrap.height = c.height + dp(32)

    def submit(self):
        uid = self.uid_f.text
        if len(uid) != 10 or not uid.isdigit():
            toast("الرقم المعرفي يجب أن يكون 10 أرقام", "err")
            return
        if not self.dept.value:
            toast("اختر القسم", "err")
            return
        if len(self.pw.input.text) < 6:
            toast("كلمة المرور يجب ألا تقل عن 6 أحرف", "err")
            return
        if self.pw.input.text != self.pw2.input.text:
            toast("كلمتا المرور غير متطابقتين", "err")
            return
        a = app()
        a.api.post("/api/auth/activate", {
            "uid": uid, "department": self.dept.value, "email": self.email.text or None,
            "password": self.pw.input.text, "device_id": a.device_id}, a.on_login)
