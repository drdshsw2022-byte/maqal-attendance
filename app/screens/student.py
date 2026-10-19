"""لوحة الطالب: الرئيسية، المواد، الملف الشخصي + شاشة المسح وسجل المادة."""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

import qr
from screens.common import (Dash, STAGE_AR, SHIFT_AR, TapCard, app, chip, empty_note, fmt_dt, fmt_t, pct_color,
                            section, tile, tiles_row)
from theme import C, GRAD, ICON, STATUS, tint
from widgets import (ALabel, Btn, Card, Dialog, Field, GradBox, Icon, IconBtn, Progress, RBox, Spacer, VScroll, toast)

ST = ["#4F46E5", "#7C3AED"]
GREEN = ["#10B981", "#0D9488"]
ORANGE = ["#F59E0B", "#F97316"]
ROSE = ["#F43F5E", "#EC4899"]
SKY = ["#0EA5E9", "#6366F1"]


def course_card(c, on_tap=None):
    card = TapCard(size_hint_y=None, height=dp(142), spacing=dp(6))
    top = RBox(size_hint_y=None, height=dp(28), spacing=dp(8))
    top.add_widget(ALabel(c["name"], bold=True, font_size=sp(16), wrap=False))
    pct = c["pct"]
    top.add_widget(chip("—" if pct is None else f"{pct}%", pct_color(pct, c["warn"]), h=26, size=13))
    card.add_widget(top)
    sub = RBox(size_hint_y=None, height=dp(22), spacing=dp(8))
    sub.add_widget(ALabel(f"{c['code']}  ·  الفصل {c['semester']}", color=C.muted, font_size=sp(12), wrap=False))
    if c.get("live"):
        sub.add_widget(chip("محاضرة جارية الآن", C.rose, h=22, size=11))
    card.add_widget(sub)
    card.add_widget(Progress(value=(pct or 0) / 100, color=pct_color(pct, c["warn"])))
    card.add_widget(ALabel(
        f"حضور {c['present']} · تأخر {c['late']} · بعذر {c['excused']} · غياب {c['absent']}   (من {c['total']} محاضرة)",
        color=C.muted, font_size=sp(12), size_hint_y=None, height=dp(34)))
    if c["warn"]:
        card.add_widget(ALabel("تنبيه: نسبة غيابك تجاوزت الحد المسموح", color=C.rose, bold=True, font_size=sp(12),
                               wrap=False, size_hint_y=None, height=dp(20)))
        card.height = dp(160)
    if on_tap:
        card.bind(on_release=lambda *_: on_tap(c))
    return card


class StudentDash(Dash):
    role = "student"
    accent = C.violet
    tabs = [("home", "home", "الرئيسية"), ("courses", "book", "موادي"), ("profile", "person", "حسابي")]

    def subtitle(self, u):
        from screens.common import DEPT_AR
        st = STAGE_AR.get(u.get("stage"), "")
        return f"طالب · المرحلة {st} · {SHIFT_AR.get(u.get('shift'), '')}"

    def _load(self, sc, build):
        sc.clear()
        sc.add(ALabel("جارٍ التحميل…", color=C.muted, halign="center", size_hint_y=None, height=dp(60)))
        app().api.get("/api/student/home", lambda d: (sc.clear(), build(sc, d)))

    def tab_home(self, sc):
        self._load(sc, self._home)

    def _home(self, sc, d):
        hero = GradBox(stops=ST, radius=[dp(24)], size_hint_y=None, height=dp(150), padding=dp(16), spacing=dp(8))
        hero.add_widget(ALabel("سجّل حضورك الآن", color=C.white, font_name="TajX", font_size=sp(20), wrap=False,
                               size_hint_y=None, height=dp(32)))
        hero.add_widget(ALabel("امسح رمز QR الظاهر على شاشة الدكتور، أو اكتب الرمز المكوّن من 6 أرقام.",
                               color=(1, 1, 1, 0.92), font_size=sp(13)))
        b = Btn("مسح رمز الحضور", icon="scan", kind="white", color=C.violet, height=48)
        b.bind(on_release=lambda *_: app().open("scan"))
        hero.add_widget(b)
        sc.add(hero)
        ov = d["overall_pct"]
        sc.add(tiles_row([
            ("—" if ov is None else f"{ov}%", "نسبة حضورك", GREEN if (ov or 100) >= 80 else ORANGE),
            (len(d["courses"]), "المواد", SKY),
            (d["absences"], "مرات الغياب", ROSE),
        ]))
        if d.get("needs_department"):
            sc.add(ALabel("لم يُحدَّد قسمك بعد، راجع إدارة الجامعة.", color=C.rose, bold=True, autoh=True))
        live = [c for c in d["courses"] if c["live"]]
        if live:
            sc.add(section("محاضرات جارية الآن"))
            for c in live:
                sc.add(course_card(c, lambda c: app().open("scan")))
        sc.add(section("موادي هذا الفصل"))
        if not d["courses"]:
            sc.add(empty_note("لا توجد مواد لهذا الفصل", "book"))
        for c in d["courses"]:
            sc.add(course_card(c, lambda c: app().open("history", course=c)))

    def tab_courses(self, sc):
        def build(sc, d):
            sc.add(section("تفاصيل الحضور لكل مادة"))
            sc.add(ALabel("اضغط على المادة لعرض سجل محاضراتها", color=C.muted, font_size=sp(12), wrap=False,
                          size_hint_y=None, height=dp(22)))
            if not d["courses"]:
                sc.add(empty_note("لا توجد مواد لهذا الفصل", "book"))
            for c in d["courses"]:
                sc.add(course_card(c, lambda c: app().open("history", course=c)))
        self._load(sc, build)


class HistoryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="history", **kw)
        root = BoxLayout(orientation="vertical")
        self.bar = GradBox(stops=GRAD["student"], radius=[0, 0, dp(26), dp(26)], size_hint_y=None, height=dp(110),
                           padding=[dp(10), dp(30), dp(14), dp(8)])
        row = RBox()
        row.add_widget(IconBtn("back", C.white, on_release=lambda *_: app().back()))
        self.title = ALabel("", color=C.white, font_name="TajX", font_size=sp(20), wrap=False)
        row.add_widget(self.title)
        self.bar.add_widget(row)
        self.sc = VScroll()
        root.add_widget(self.bar)
        root.add_widget(self.sc)
        self.add_widget(root)

    def setup(self, course):
        self.title.atext = course["name"]
        self.sc.clear()
        self.sc.add(ALabel("جارٍ التحميل…", color=C.muted, halign="center", size_hint_y=None, height=dp(60)))
        app().api.get(f"/api/student/courses/{course['id']}/history", self.build)

    def build(self, d):
        sc = self.sc
        sc.clear()
        s = d["summary"]
        sc.add(tiles_row([
            ("—" if s["pct"] is None else f"{s['pct']}%", "نسبة الحضور", GREEN),
            (s["present"] + s["late"], "حضور", SKY),
            (s["absent"], "غياب", ROSE),
        ]))
        sc.add(section("سجل المحاضرات"))
        if not d["rows"]:
            sc.add(empty_note("لم تُعقد محاضرات بعد", "history"))
        for r in d["rows"]:
            label, col = STATUS[r["status"]]
            card = Card(size_hint_y=None, height=dp(58), padding=[dp(14), dp(8)])
            row = RBox(spacing=dp(10))
            row.add_widget(Icon("check" if r["status"] in ("present", "late") else "cancel", 26, col,
                                size_hint=(None, 1)))
            row.add_widget(ALabel(fmt_dt(r["date"]), wrap=False))
            row.add_widget(chip(label, col, h=26, size=13))
            card.add_widget(row)
            sc.add(card)


class ScanScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="scan", **kw)
        bg = GradBox(stops=GRAD["student"], vertical=True)
        sc = VScroll(padding=0, spacing=0)
        top = RBox(size_hint_y=None, height=dp(72), padding=[dp(10), dp(28), dp(10), 0])
        top.add_widget(IconBtn("back", C.white, on_release=lambda *_: app().back()))
        top.add_widget(ALabel("تسجيل الحضور", color=C.white, font_name="TajX", font_size=sp(21), wrap=False))
        sc.add(top)
        card = Card(size_hint_y=None, height=dp(432), padding=[dp(20), dp(16)], spacing=dp(8), radius=dp(30))
        card.add_widget(Icon("qr", 64, C.violet, size_hint=(1, None), height=dp(72)))
        card.add_widget(ALabel("وجّه الكاميرا نحو رمز QR الظاهر على شاشة الدكتور", bold=True, halign="center",
                               autoh=True))
        self.cam = Btn("فتح الكاميرا ومسح الرمز", icon="scan", on_release=lambda *_: self.scan())
        card.add_widget(self.cam)
        card.add_widget(ALabel("— أو أدخل الرمز المكوّن من 6 أرقام —", color=C.muted, halign="center",
                               size_hint_y=None, height=dp(30), wrap=False))
        self.code = Field("رمز المحاضرة", icon="key", input_type="number")
        card.add_widget(self.code)
        card.add_widget(Btn("تسجيل الحضور", icon="check", kind="soft", color=C.violet,
                            on_release=lambda *_: self.manual()))
        card.add_widget(ALabel("يتغيّر الرمز كل بضع ثوانٍ؛ إن لم يُقبل فاقرأ الرمز الحالي من جديد.", color=C.muted,
                               font_size=sp(12), halign="center", autoh=True))
        wrap = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(14), dp(10), dp(14), dp(24)])
        wrap.height = card.height + dp(34)
        wrap.add_widget(card)
        sc.add(wrap)
        bg.add_widget(sc)
        self.add_widget(bg)

    def on_pre_enter(self, *_):
        self.code.text = ""
        self.cam.opacity = 1 if qr.scanner_available() else 0.45

    def scan(self):
        qr.scan(self.got_text, lambda m: toast(m, "err"))

    def got_text(self, text):
        p = qr.parse_payload(text)
        if not p:
            toast("هذا ليس رمز حضور صالحاً", "err")
            return
        self.send(*p)

    def manual(self):
        c = "".join(ch for ch in self.code.text if ch.isdigit())
        if len(c) != 6:
            toast("الرمز يتكون من 6 أرقام", "err")
            return
        self.send(None, c)

    def send(self, sid, code):
        a = app()
        a.api.post("/api/attendance/checkin", {"session_id": sid, "code": code, "device_id": a.device_id}, self.done)

    def done(self, r):
        late = r["status"] == "late"
        if r.get("already"):
            title, text, icon, col = "مسجّل مسبقاً", f"حضورك في مادة «{r['course']}» مسجّل من قبل.", "info", C.sky
        elif late:
            title, text, icon, col = "تم التسجيل (متأخر)", f"سُجّل حضورك في «{r['course']}» بحالة تأخر.", "clock", C.amber
        else:
            title, text, icon, col = "تم تسجيل حضورك", f"مادة «{r['course']}» — حاضر ✓", "check", C.green
        from widgets import message
        message(title, text, icon=icon, color=col)
        self.code.text = ""
