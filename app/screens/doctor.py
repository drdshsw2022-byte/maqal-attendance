"""لوحة الدكتور: المواد، التقارير، + شاشة المحاضرة الحية (QR دوّار) وشاشة التقرير."""
import time

from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from qr import QRView, open_url
from screens.common import (Dash, STAGE_AR, SHIFT_AR, TapCard, app, chip, empty_note, fmt_dt, fmt_t, pct_color,
                            section, tiles_row)
from theme import C, GRAD, ICON, STATUS, tint
from widgets import (ALabel, Btn, Card, Chips, Dialog, GradBox, Icon, IconBtn, Progress, RBox, Spacer, VScroll,
                     message, toast)

GREEN = ["#10B981", "#0D9488"]
SKY = ["#0EA5E9", "#6366F1"]
ORANGE = ["#F59E0B", "#F97316"]
ROSE = ["#F43F5E", "#EC4899"]
TEAL = ["#0D9488", "#0EA5E9"]


class DoctorDash(Dash):
    role = "doctor"
    accent = C.teal
    tabs = [("courses", "class", "موادي"), ("reports", "chart", "التقارير"), ("profile", "person", "حسابي")]

    def subtitle(self, u):
        return "دكتور · " + (u.get("email") or "")

    def _courses(self, sc, build):
        sc.clear()
        sc.add(ALabel("جارٍ التحميل…", color=C.muted, halign="center", size_hint_y=None, height=dp(60)))
        app().api.get("/api/doctor/courses", lambda d: (sc.clear(), build(sc, d)))

    def tab_courses(self, sc):
        def build(sc, d):
            live = sum(1 for c in d if c["active_session"])
            sc.add(tiles_row([(len(d), "موادي", TEAL), (sum(c["students"] for c in d), "الطلاب", SKY),
                              (live, "جارية الآن", ROSE if live else GREEN)]))
            sc.add(section("المواد المسندة إليك"))
            if not d:
                sc.add(empty_note("لم تُسند إليك مواد بعد. راجع مدير النظام.", "class"))
            for c in d:
                sc.add(self.course_card(c))
        self._courses(sc, build)

    def course_card(self, c):
        card = Card(size_hint_y=None, height=dp(176), spacing=dp(6))
        card.add_widget(ALabel(c["name"], bold=True, font_size=sp(17), wrap=False, size_hint_y=None, height=dp(28)))
        row = RBox(size_hint_y=None, height=dp(24), spacing=dp(6))
        row.add_widget(chip(c["code"], C.teal))
        row.add_widget(chip(f"المرحلة {STAGE_AR.get(c['stage'], c['stage'])}", C.indigo))
        row.add_widget(chip(c["dept_name"].replace("هندسة ", ""), C.violet))
        row.add_widget(Widget())
        card.add_widget(row)
        card.add_widget(ALabel(f"{c['students']} طالباً مسجلاً  ·  {c['sessions']} محاضرة منتهية", color=C.muted,
                               font_size=sp(13), wrap=False, size_hint_y=None, height=dp(24)))
        if c["active_session"]:
            b = Btn("متابعة المحاضرة الجارية", icon="qr", kind="danger", on_release=lambda *_: app().open(
                "session", session_id=c["active_session"]))
        else:
            b = Btn("بدء محاضرة جديدة", icon="play", color=C.teal, on_release=lambda *_: self.start(c))
        card.add_widget(b)
        return card

    def start(self, c):
        shift = Chips([("all", "كل الطلاب"), ("morning", "صباحي فقط"), ("evening", "مسائي فقط")], "all",
                      color=C.teal)
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(86), spacing=dp(6))
        box.add_widget(ALabel("لمن تُعقد هذه المحاضرة؟", color=C.muted, font_size=sp(13), size_hint_y=None,
                              height=dp(22), wrap=False))
        box.add_widget(shift)

        def go():
            app().api.post("/api/doctor/sessions", {"course_id": c["id"], "shift": shift.selected},
                           lambda r: app().open("session", session_id=r["session_id"]))
            return True
        Dialog("بدء محاضرة", box, [("ابدأ", "primary", go), ("إلغاء", "soft", None)], icon="play", color=C.teal).open()

    def tab_reports(self, sc):
        def build(sc, d):
            sc.add(section("اختر مادة لعرض تقرير الحضور"))
            if not d:
                sc.add(empty_note("لا توجد مواد", "chart"))
            for c in d:
                card = TapCard(size_hint_y=None, height=dp(78), padding=[dp(14), dp(10)])
                row = RBox(spacing=dp(10))
                row.add_widget(Icon("chart", 30, C.teal, size_hint=(None, 1)))
                col = BoxLayout(orientation="vertical")
                col.add_widget(ALabel(c["name"], bold=True, font_size=sp(16), wrap=False))
                col.add_widget(ALabel(f"{c['sessions']} محاضرة · {c['students']} طالباً", color=C.muted,
                                      font_size=sp(12), wrap=False))
                row.add_widget(col)
                card.add_widget(row)
                card.bind(on_release=lambda _w, c=c: app().open("report", course=c))
                sc.add(card)
        self._courses(sc, build)


# ====================================================================== المحاضرة الحية
class StatusRow(ButtonBehavior, Card):
    def __init__(self, r, on_tap, **kw):
        super().__init__(size_hint_y=None, height=dp(62), padding=[dp(12), dp(6)], radius=dp(16), **kw)
        self.r = r
        self.bind(on_release=lambda *_: on_tap(self.r))
        self.row = RBox(spacing=dp(10))
        self.dot = Icon("check", 26, C.rose, size_hint=(None, 1))
        col = BoxLayout(orientation="vertical")
        col.add_widget(ALabel(r["name"], bold=True, font_size=sp(14), wrap=False))
        self.sub = ALabel("", color=C.muted, font_size=sp(11), wrap=False)
        col.add_widget(self.sub)
        self.chipbox = BoxLayout(size_hint=(None, 1), width=dp(84), padding=[0, dp(16)])
        for w in (self.dot, col, self.chipbox):
            self.row.add_widget(w)
        self.add_widget(self.row)
        self.apply(r)

    def apply(self, r):
        self.r = r
        label, col = STATUS[r["status"]]
        self.dot.color = col
        self.dot.text = ICON["check" if r["status"] in ("present", "late") else ("info" if r["status"] == "excused" else "cancel")]
        self.sub.atext = r["uid"] + (("  ·  " + fmt_t(r["at"])) if r["at"] else "")
        self.chipbox.clear_widgets()
        c = chip(label, col, h=28, size=13)
        c.pos_hint = {"center_y": 0.5}
        self.chipbox.add_widget(c)


class SessionScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="session", **kw)
        self.sid, self.rows, self.exp_at, self.step, self.filter = None, {}, 0, 20, "all"
        self._poll_ev = self._tick_ev = None
        root = BoxLayout(orientation="vertical")
        bar = GradBox(stops=GRAD["doctor"], radius=[0, 0, dp(26), dp(26)], size_hint_y=None, height=dp(104),
                      padding=[dp(10), dp(30), dp(14), dp(6)])
        r = RBox()
        r.add_widget(IconBtn("back", C.white, on_release=lambda *_: app().back()))
        col = BoxLayout(orientation="vertical")
        self.title = ALabel("", color=C.white, font_name="TajX", font_size=sp(19), wrap=False)
        self.sub = ALabel("", color=(1, 1, 1, 0.9), font_size=sp(12), wrap=False, size_hint_y=None, height=dp(20))
        col.add_widget(self.title)
        col.add_widget(self.sub)
        r.add_widget(col)
        bar.add_widget(r)
        root.add_widget(bar)
        self.sc = VScroll(spacing=10)
        root.add_widget(self.sc)
        foot = Card(size_hint_y=None, height=dp(72), radius=0, padding=[dp(14), dp(10)])
        foot.add_widget(Btn("إنهاء المحاضرة", icon="stop", kind="danger", on_release=lambda *_: self.confirm_end()))
        root.add_widget(foot)
        self.add_widget(root)
        self._build_static()

    def _build_static(self):
        sc = self.sc
        qrc = Card(size_hint_y=None, height=dp(430), padding=[dp(16), dp(14)], spacing=dp(6), radius=dp(26))
        qrc.add_widget(ALabel("اعرض الرمز على الشاشة ليمسحه الطلاب", bold=True, halign="center", size_hint_y=None,
                              height=dp(26), wrap=False))
        self.qr = QRView(size_hint=(1, 1))
        qrc.add_widget(self.qr)
        self.code = ALabel("", font_name="TajX", font_size=sp(38), halign="center", wrap=False, size_hint_y=None,
                           height=dp(52), color=C.teal)
        qrc.add_widget(self.code)
        self.bar = Progress(color=C.teal, height=dp(10))
        qrc.add_widget(self.bar)
        self.qr_note = ALabel("", color=C.muted, font_size=sp(12), halign="center", wrap=False, size_hint_y=None,
                              height=dp(20))
        qrc.add_widget(self.qr_note)
        sc.add(qrc)
        self.tiles = BoxLayout(size_hint_y=None, height=dp(86))
        sc.add(self.tiles)
        self.warn = ALabel("", color=C.amber, bold=True, font_size=sp(12), autoh=True)
        sc.add(self.warn)
        self.chips = Chips([("all", "الكل"), ("present", "الحاضرون"), ("absent", "لم يحضروا")], "all",
                           on_select=self.set_filter, color=C.teal)
        sc.add(self.chips)
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.list.bind(minimum_height=self.list.setter("height"))
        sc.add(self.list)

    # ------------------------------------------------------------------ دورة الحياة
    def setup(self, session_id):
        self.sid = session_id
        self.rows.clear()
        self.list.clear_widgets()
        self.exp_at = 0
        self.qr.payload = ""
        self.title.atext = "المحاضرة"
        self.sc.scroll_y = 1

    def on_enter(self, *_):
        self.poll()
        self._poll_ev = Clock.schedule_interval(self.poll, 3)
        self._tick_ev = Clock.schedule_interval(self.tick, 0.25)

    def on_leave(self, *_):
        for ev in (self._poll_ev, self._tick_ev):
            if ev:
                ev.cancel()
        self._poll_ev = self._tick_ev = None

    def poll(self, *_):
        if self.sid:
            app().api.get(f"/api/doctor/sessions/{self.sid}", self.update, quiet=True,
                          fail=lambda e: None)

    def tick(self, _dt):
        if not self.exp_at:
            return
        left = self.exp_at - time.time()
        self.bar.value = max(0.0, left / self.step)
        self.qr_note.atext = f"يتجدد الرمز بعد {max(0, int(left) + 1)} ثانية"
        if left < -0.2:
            self.exp_at = 0
            self.poll()

    # ------------------------------------------------------------------ تحديث البيانات
    def update(self, d):
        c = d["course"]
        self.title.atext = c["name"]
        ended = d["ended_at"] is not None
        self.sub.atext = ("انتهت  ·  " if ended else "جارية منذ ") + fmt_t(d["started_at"]) + \
            f"  ·  {SHIFT_AR.get(d['shift'])}"
        q = d.get("qr")
        if q:
            self.step = q["step"]
            self.exp_at = time.time() + q["expires_in"]
            if self.qr.payload != q["payload"]:
                self.qr.payload = q["payload"]
            self.code.atext = q["code"][:3] + " " + q["code"][3:]
        else:
            self.qr.payload = ""
            self.code.atext = "انتهت المحاضرة"
            self.qr_note.atext = ""
            self.exp_at = 0
        k = d["counts"]
        absent = k["total"] - k["present"] - k["late"] - k["excused"]
        self.tiles.clear_widgets()
        self.tiles.add_widget(tiles_row([(k["present"], "حاضر", GREEN), (k["late"], "متأخر", ORANGE),
                                         (absent, "لم يحضر", ROSE), (k["total"], "الإجمالي", SKY)]))
        un = d.get("unassigned", 0)
        self.warn.atext = (f"ملاحظة: {un} طالباً من هذه المرحلة لم يختاروا قسمهم بعد، ولن يظهروا في الكشف "
                           f"حتى يفعّلوا حساباتهم.") if un else ""
        self.warn.height = dp(8) if not un else self.warn.height
        for r in d["roster"]:
            row = self.rows.get(r["student_id"])
            if row is None:
                row = StatusRow(r, self.edit)
                self.rows[r["student_id"]] = row
                self.list.add_widget(row)
            elif row.r["status"] != r["status"] or row.r["at"] != r["at"]:
                row.apply(r)
        self.apply_filter()

    def set_filter(self, key):
        self.filter = key
        self.apply_filter()

    def apply_filter(self):
        for row in self.rows.values():
            st = row.r["status"]
            show = self.filter == "all" or (self.filter == "present" and st in ("present", "late")) or \
                (self.filter == "absent" and st == "absent")
            row.height = dp(62) if show else 0
            row.opacity = 1 if show else 0
            row.disabled = not show

    # ------------------------------------------------------------------ إجراءات
    def edit(self, r):
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        box.height = dp(50) * 4 + dp(8) * 3

        def setter(status):
            def f(*_):
                dlg.dismiss()
                app().api.post(f"/api/doctor/sessions/{self.sid}/mark",
                               {"student_id": r["student_id"], "status": status}, lambda _r: self.poll())
            return f
        for st in ("present", "late", "excused", "absent"):
            label, col = STATUS[st]
            box.add_widget(Btn(label, kind="primary" if r["status"] == st else "soft", color=col, height=50,
                               on_release=setter(st)))
        dlg = Dialog(r["name"], box, [("إغلاق", "soft", None)], icon="edit", color=C.teal)
        dlg.open()

    def confirm_end(self):
        def go():
            def ok(_):
                toast("تم إنهاء المحاضرة وحفظ الحضور", "ok")
                app().back()
            app().api.post(f"/api/doctor/sessions/{self.sid}/end", {}, ok)
        lbl = ALabel("سيتوقف قبول الرمز، وكل من لم يسجّل حضوره يُحتسب غائباً.", color=C.muted, autoh=True)
        Dialog("إنهاء المحاضرة؟", lbl, [("إنهاء", "danger", go), ("متابعة", "soft", None)], icon="stop",
               color=C.rose).open()


# ====================================================================== التقرير
class ReportScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="report", **kw)
        self.course = None
        root = BoxLayout(orientation="vertical")
        bar = GradBox(stops=GRAD["doctor"], radius=[0, 0, dp(26), dp(26)], size_hint_y=None, height=dp(104),
                      padding=[dp(10), dp(30), dp(14), dp(6)])
        r = RBox()
        r.add_widget(IconBtn("back", C.white, on_release=lambda *_: app().back()))
        self.title = ALabel("", color=C.white, font_name="TajX", font_size=sp(19), wrap=False)
        r.add_widget(self.title)
        bar.add_widget(r)
        root.add_widget(bar)
        self.sc = VScroll(spacing=10)
        root.add_widget(self.sc)
        foot = Card(size_hint_y=None, height=dp(72), radius=0, padding=[dp(14), dp(10)])
        foot.add_widget(Btn("تصدير كشف Excel", icon="download", color=C.teal, on_release=lambda *_: self.export()))
        root.add_widget(foot)
        self.add_widget(root)

    def setup(self, course):
        self.course = course
        self.title.atext = course["name"]
        self.sc.clear()
        self.sc.add(ALabel("جارٍ التحميل…", color=C.muted, halign="center", size_hint_y=None, height=dp(60)))
        app().api.get(f"/api/doctor/courses/{course['id']}/report", self.build)

    def build(self, d):
        sc = self.sc
        sc.clear()
        rows = d["rows"]
        warn = sum(1 for r in rows if r["warn"])
        pcts = [r["pct"] for r in rows if r["pct"] is not None]
        avg = round(sum(pcts) / len(pcts)) if pcts else None
        sc.add(tiles_row([(d["sessions"], "محاضرات", SKY), ("—" if avg is None else f"{avg}%", "متوسط الحضور", GREEN),
                          (warn, f"تجاوزوا {d['limit_pct']}% غياب", ROSE)]))
        if d.get("unassigned"):
            sc.add(ALabel(f"{d['unassigned']} طالباً من المرحلة لم يختاروا قسمهم بعد ولا يظهرون هنا.",
                          color=C.amber, bold=True, font_size=sp(12), autoh=True))
        sc.add(section("الطلاب"))
        if not rows:
            sc.add(empty_note("لا يوجد طلاب مسجلون في هذه المادة بعد", "people"))
        for r in sorted(rows, key=lambda x: (x["pct"] is None, x["pct"] if x["pct"] is not None else 0)):
            card = Card(size_hint_y=None, height=dp(86), padding=[dp(14), dp(8)], spacing=dp(4), radius=dp(16))
            top = RBox(size_hint_y=None, height=dp(26), spacing=dp(8))
            top.add_widget(ALabel(r["name"], bold=True, font_size=sp(14), wrap=False))
            top.add_widget(chip("—" if r["pct"] is None else f"{r['pct']}%", pct_color(r["pct"], r["warn"]), h=24))
            card.add_widget(top)
            card.add_widget(Progress(value=(r["pct"] or 0) / 100, color=pct_color(r["pct"], r["warn"])))
            card.add_widget(ALabel(f"{r['uid']}  ·  حضور {r['present']}  تأخر {r['late']}  بعذر {r['excused']}  "
                                   f"غياب {r['absent']}", color=C.muted, font_size=sp(11), wrap=False,
                                   size_hint_y=None, height=dp(20)))
            sc.add(card)

    def export(self):
        def ok(r):
            url = app().api.base + r["path"]
            try:
                open_url(url)
                toast("يُفتح المتصفح لتنزيل الملف…", "ok")
            except Exception:
                message("رابط التصدير", url, icon="download")
        app().api.post("/api/export-link", {"course_id": self.course["id"]}, ok)
