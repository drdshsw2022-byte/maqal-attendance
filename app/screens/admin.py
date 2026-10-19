"""لوحة المدير: نظرة عامة وإعدادات، الدكاترة وإسناد المواد، الطلاب."""
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from screens.auth import ChoiceList
from screens.common import (Dash, DEPT_AR, SHIFT_AR, STAGE_AR, TapCard, app, chip, empty_note, section, tiles_row)
from theme import C, GRAD
from widgets import (ALabel, Btn, Card, Chips, Dialog, Field, GradBox, Icon, IconBtn, RBox, Spacer, VScroll, ar,
                     message, toast)

VIOLET = ["#7C3AED", "#A855F7"]
SKY = ["#0EA5E9", "#6366F1"]
GREEN = ["#10B981", "#0D9488"]
ORANGE = ["#F59E0B", "#F97316"]
ROSE = ["#F43F5E", "#EC4899"]


class ArField(Field):
    """حقل لنص عربي مع معاينة سليمة تحته (شاشة الإدخال في Kivy لا تربط الحروف العربية)."""

    def __init__(self, label, **kw):
        super().__init__(label, ltr=False, height=100, **kw)
        self.prev = ALabel("", color=C.indigo, bold=True, font_size=sp(15), size_hint_y=None, height=dp(22), wrap=False)
        self.add_widget(self.prev)
        self.input.bind(text=lambda _w, v: setattr(self.prev, "atext", v))


def load(sc, url, build):
    sc.clear()
    sc.add(ALabel("جارٍ التحميل…", color=C.muted, halign="center", size_hint_y=None, height=dp(60)))
    app().api.get(url, lambda d: (sc.clear(), build(sc, d)))


class AdminDash(Dash):
    role = "admin"
    accent = C.rose
    tabs = [("overview", "dash", "الرئيسية"), ("doctors", "people", "الدكاترة"), ("students", "school", "الطلاب"),
            ("profile", "person", "حسابي")]

    def subtitle(self, u):
        return "مدير النظام · " + (u.get("email") or "")

    # ------------------------------------------------------------------ الرئيسية
    def tab_overview(self, sc):
        load(sc, "/api/admin/overview", self._overview)

    def _overview(self, sc, d):
        sc.add(tiles_row([(d["students"], "الطلاب", VIOLET), (d["activated"], "مفعّلون", GREEN),
                          (d["doctors"], "الدكاترة", SKY)]))
        sc.add(tiles_row([(d["courses"], "مواد الفصل", ORANGE), (d["sessions_today"], "محاضرات اليوم", SKY),
                          (d["checkins_today"], "تسجيلات اليوم", GREEN)]))
        if d["live_sessions"]:
            sc.add(ALabel(f"{d['live_sessions']} محاضرة جارية الآن", color=C.rose, bold=True, halign="center",
                          size_hint_y=None, height=dp(26), wrap=False))
        s = d["settings"]
        card = Card(size_hint_y=None, height=dp(250), spacing=dp(4))
        card.add_widget(ALabel("إعدادات النظام", bold=True, font_size=sp(17), size_hint_y=None, height=dp(30),
                               wrap=False))
        for label, val in [("الفصل الحالي", "الأول" if s["current_season"] == 1 else "الثاني"),
                           ("التأخر بعد", f"{s['late_minutes']} دقيقة"), ("إنذار الغياب عند", f"{s['absence_limit_pct']}%"),
                           ("تجدد رمز QR كل", f"{s['qr_step']} ثانية")]:
            row = RBox(size_hint_y=None, height=dp(30))
            row.add_widget(ALabel(label, color=C.muted, wrap=False))
            row.add_widget(ALabel(val, bold=True, halign="left", wrap=False))
            card.add_widget(row)
        card.add_widget(Btn("تعديل الإعدادات", icon="edit", kind="soft", color=C.rose, height=46,
                            on_release=lambda *_: self.edit_settings(s)))
        sc.add(card)
        sc.add(ALabel("الفصل الحالي يحدد المواد التي تظهر للطلاب والدكاترة.", color=C.muted, font_size=sp(12),
                      autoh=True))

    def edit_settings(self, s):
        season = Chips([(1, "الفصل الأول"), (2, "الفصل الثاني")], s["current_season"], color=C.rose)
        late = Field("التأخر بعد (دقيقة)", input_type="number")
        late.text = str(s["late_minutes"])
        lim = Field("إنذار الغياب عند نسبة (%)", input_type="number")
        lim.text = str(s["absence_limit_pct"])
        step = Field("تجدد رمز QR كل (ثانية: 10–60)", input_type="number")
        step.text = str(s["qr_step"])
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(44 + 76 * 3 + 8 * 3), spacing=dp(8))
        for w in (season, late, lim, step):
            box.add_widget(w)

        def save():
            app().api.post("/api/admin/settings", {"current_season": season.selected, "late_minutes": late.text,
                                                   "absence_limit_pct": lim.text, "qr_step": step.text},
                           lambda _r: (toast("تم حفظ الإعدادات", "ok"), self.refresh(), dlg.dismiss()))
            return False
        dlg = Dialog("إعدادات النظام", box, [("حفظ", "primary", save), ("إلغاء", "soft", None)], icon="settings",
                     color=C.rose)
        dlg.open()

    # ------------------------------------------------------------------ الدكاترة
    def tab_doctors(self, sc):
        load(sc, "/api/admin/doctors", self._doctors)

    def _doctors(self, sc, rows):
        sc.add(Btn("إضافة دكتور", icon="add", color=C.rose, on_release=lambda *_: self.add_doctor()))
        sc.add(section(f"الدكاترة ({len(rows)})"))
        if not rows:
            sc.add(empty_note("لا يوجد دكاترة بعد. أضف أول دكتور.", "people"))
        for r in rows:
            card = Card(size_hint_y=None, height=dp(176), spacing=dp(6))
            top = RBox(size_hint_y=None, height=dp(28), spacing=dp(8))
            top.add_widget(ALabel(r["name"], bold=True, font_size=sp(16), wrap=False))
            top.add_widget(chip("فعّال" if r["active"] else "موقوف", C.green if r["active"] else C.rose))
            card.add_widget(top)
            card.add_widget(ALabel(r["email"] or "", color=C.muted, font_size=sp(12), wrap=False, size_hint_y=None,
                                   height=dp(20)))
            card.add_widget(ALabel(f"{r['courses']} مادة مسندة", color=C.muted, font_size=sp(12), wrap=False,
                                   size_hint_y=None, height=dp(20)))
            row = RBox(size_hint_y=None, height=dp(46), spacing=dp(8))
            row.add_widget(Btn("المواد", icon="book", color=C.rose, height=46,
                               on_release=lambda *_, r=r: app().open("assign", doctor=r)))
            row.add_widget(Btn("كلمة مرور", kind="soft", color=C.indigo, height=46,
                               on_release=lambda *_, r=r: self.reset_pw(r)))
            row.add_widget(Btn("إيقاف" if r["active"] else "تفعيل", kind="soft",
                               color=C.rose if r["active"] else C.green, height=46,
                               on_release=lambda *_, r=r: self.toggle(r)))
            card.add_widget(row)
            sc.add(card)

    def add_doctor(self):
        name = ArField("اسم الدكتور", icon="person")
        email = Field("البريد الإلكتروني (Gmail)", icon="mail", input_type="mail")
        pw = Field("كلمة مرور مؤقتة (6 أحرف فأكثر)", icon="key")
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(100 + 76 + 76 + 16), spacing=dp(8))
        for w in (name, email, pw):
            box.add_widget(w)

        def save():
            app().api.post("/api/admin/doctors", {"name": name.text, "email": email.text, "password": pw.text},
                           lambda _r: (toast("تمت إضافة الدكتور", "ok"), self.refresh(), dlg.dismiss()))
            return False
        dlg = Dialog("إضافة دكتور", box, [("إضافة", "primary", save), ("إلغاء", "soft", None)], icon="add",
                     color=C.rose)
        dlg.open()

    def reset_pw(self, r):
        pw = Field("كلمة المرور المؤقتة الجديدة", icon="key")

        def save():
            app().api.post(f"/api/admin/doctors/{r['id']}/reset-password", {"password": pw.text},
                           lambda _r: (toast("تم تغيير كلمة المرور، سيُطلب من الدكتور تغييرها", "ok"), dlg.dismiss()))
            return False
        dlg = Dialog("كلمة مرور " + r["name"], pw, [("حفظ", "primary", save), ("إلغاء", "soft", None)], icon="key")
        dlg.open()

    def toggle(self, r):
        app().api.post(f"/api/admin/doctors/{r['id']}/active", {"active": not r["active"]},
                       lambda _r: self.refresh())

    # ------------------------------------------------------------------ الطلاب
    def tab_students(self, sc):
        self._q, self._stage, self._shift = "", "", ""
        top = Card(size_hint_y=None, height=dp(206), spacing=dp(6))
        self.q = Field("بحث بالاسم أو الرقم المعرفي", icon="search", ltr=False)
        top.add_widget(self.q)
        self.stage_chips = Chips([("", "كل المراحل"), (2, "المرحلة 2"), (3, "المرحلة 3")], "", color=C.rose,
                                 on_select=lambda k: None)
        self.shift_chips = Chips([("", "كل الدوام"), ("morning", "صباحي"), ("evening", "مسائي")], "", color=C.rose,
                                 on_select=lambda k: None)
        top.add_widget(self.stage_chips)
        top.add_widget(self.shift_chips)
        sc.add(top)
        sc.add(Btn("بحث", icon="search", color=C.rose, on_release=lambda *_: self.search()))
        sc.add(Btn("تعيين قسم جماعي للطلاب", icon="manage", kind="soft", color=C.indigo, height=46,
                   on_release=lambda *_: self.bulk_dept()))
        self.res = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(10))
        self.res.bind(minimum_height=self.res.setter("height"))
        sc.add(self.res)
        self.search()

    def search(self):
        from urllib.parse import quote
        url = "/api/admin/students?q=" + quote(self.q.text)
        for key, ch in (("stage", self.stage_chips), ("shift", self.shift_chips)):
            if ch.selected != "":
                url += f"&{key}={ch.selected}"
        self.res.clear_widgets()

        def ok(d):
            self.res.clear_widgets()
            self.res.add_widget(ALabel(f"النتائج: {d['total']} طالب" + (" (يظهر أول 40)" if d["total"] > 40 else ""),
                                       color=C.muted, size_hint_y=None, height=dp(24), wrap=False))
            for r in d["rows"]:
                card = TapCard(size_hint_y=None, height=dp(78), padding=[dp(14), dp(8)], spacing=dp(2), radius=dp(16))
                top = RBox(size_hint_y=None, height=dp(26), spacing=dp(8))
                top.add_widget(ALabel(r["name"], bold=True, font_size=sp(14), wrap=False))
                top.add_widget(chip("مفعّل" if r["activated"] else "غير مفعّل", C.green if r["activated"] else C.muted))
                card.add_widget(top)
                dept = DEPT_AR.get(r["department"], "بلا قسم").replace("هندسة ", "")
                card.add_widget(ALabel(f"{r['uid']}  ·  المرحلة {r['stage']}  ·  {SHIFT_AR.get(r['shift'])}  ·  {dept}",
                                       color=C.muted, font_size=sp(11), wrap=False, size_hint_y=None, height=dp(20)))
                card.bind(on_release=lambda _w, r=r: self.student_actions(r))
                self.res.add_widget(card)
        app().api.get(url, ok)

    def student_actions(self, r):
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(48) * 3 + dp(8) * 2, spacing=dp(8))

        def do(path, data, msg):
            def f(*_):
                dlg.dismiss()
                app().api.post(path, data, lambda _r: (toast(msg, "ok"), self.search()))
            return f
        box.add_widget(Btn("فك ارتباط الهاتف", icon="devices", kind="soft", color=C.sky, height=48,
                           on_release=do(f"/api/admin/students/{r['id']}/reset", {"what": "device"},
                                         "تم فك الارتباط، يسجّل الطالب دخوله بهاتفه الجديد")))
        box.add_widget(Btn("إعادة تعيين الحساب", icon="refresh", kind="soft", color=C.amber, height=48,
                           on_release=do(f"/api/admin/students/{r['id']}/reset", {"what": "account"},
                                         "تمت إعادة التعيين، يفعّل الطالب حسابه من جديد")))
        box.add_widget(Btn("تعيين القسم", icon="school", kind="soft", color=C.indigo, height=48,
                           on_release=lambda *_: (dlg.dismiss(), self.pick_dept(r))))
        dlg = Dialog(r["name"], box, [("إغلاق", "soft", None)], icon="person", color=C.rose)
        dlg.open()

    def _depts(self, cb):
        app().api.get("/api/meta/departments", lambda ds: cb([(d["key"], d["name"]) for d in ds]))

    def pick_dept(self, r):
        def show(opts):
            lst = ChoiceList(opts, color=C.indigo)

            def save():
                if not lst.value:
                    toast("اختر القسم", "err")
                    return False
                app().api.post(f"/api/admin/students/{r['id']}/department", {"department": lst.value},
                               lambda _r: (toast("تم تعيين القسم", "ok"), self.search(), dlg.dismiss()))
                return False
            dlg = Dialog("قسم الطالب", lst, [("حفظ", "primary", save), ("إلغاء", "soft", None)], icon="school")
            dlg.open()
        self._depts(show)

    def bulk_dept(self):
        def show(opts):
            stage = Chips([("", "كل المراحل"), (2, "المرحلة 2"), (3, "المرحلة 3")], "", color=C.indigo)
            shift = Chips([("", "كل الدوام"), ("morning", "صباحي"), ("evening", "مسائي")], "", color=C.indigo)
            lst = ChoiceList(opts, color=C.indigo)
            box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8),
                            height=dp(40) * 2 + lst.height + dp(8) * 2 + dp(44))
            box.add_widget(ALabel("يُطبَّق فقط على الطلاب الذين لم يُحدَّد قسمهم بعد.", color=C.muted,
                                  font_size=sp(12), size_hint_y=None, height=dp(44)))
            for w in (stage, shift, lst):
                box.add_widget(w)

            def save():
                if not lst.value:
                    toast("اختر القسم", "err")
                    return False
                app().api.post("/api/admin/students/bulk-department",
                               {"department": lst.value, "stage": stage.selected or None,
                                "shift": shift.selected or None},
                               lambda r: (toast(f"تم تحديث {r['updated']} طالباً", "ok"), self.search(), dlg.dismiss()))
                return False
            dlg = Dialog("تعيين قسم جماعي", box, [("تطبيق", "primary", save), ("إلغاء", "soft", None)], icon="manage")
            dlg.open()
        self._depts(show)


class AssignScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="assign", **kw)
        self.doctor, self.courses, self.dept, self.stage = None, [], "", ""
        root = BoxLayout(orientation="vertical")
        bar = GradBox(stops=GRAD["admin"], radius=[0, 0, dp(26), dp(26)], size_hint_y=None, height=dp(104),
                      padding=[dp(10), dp(30), dp(14), dp(6)])
        r = RBox()
        r.add_widget(IconBtn("back", C.white, on_release=lambda *_: app().back()))
        col = BoxLayout(orientation="vertical")
        self.title = ALabel("", color=C.white, font_name="TajX", font_size=sp(19), wrap=False)
        col.add_widget(self.title)
        col.add_widget(ALabel("إسناد المواد (الفصل الحالي)", color=(1, 1, 1, 0.9), font_size=sp(12), wrap=False,
                              size_hint_y=None, height=dp(20)))
        r.add_widget(col)
        bar.add_widget(r)
        root.add_widget(bar)
        self.sc = VScroll(spacing=10)
        root.add_widget(self.sc)
        self.add_widget(root)

    def setup(self, doctor):
        self.doctor, self.dept, self.stage = doctor, "", ""
        self.title.atext = doctor["name"]
        self.fetch()

    def fetch(self):
        self.sc.clear()
        app().api.get(f"/api/admin/courses?doctor_id={self.doctor['id']}", self.build)

    def build(self, courses):
        self.courses = courses
        self.render()

    def render(self):
        sc = self.sc
        sc.clear()
        depts = sorted({(c["dept"], c["dept_name"]) for c in self.courses}, key=lambda x: x[1])
        sc.add(Chips([("", "كل الأقسام")] + [(k, n.replace("هندسة ", "")) for k, n in depts], self.dept,
                     on_select=self.set_dept, color=C.rose))
        sc.add(Chips([("", "كل المراحل")] + [(i, f"المرحلة {i}") for i in (1, 2, 3, 4)], self.stage,
                     on_select=self.set_stage, color=C.rose))
        shown = [c for c in self.courses if (not self.dept or c["dept"] == self.dept)
                 and (self.stage == "" or c["stage"] == self.stage)]
        sc.add(ALabel(f"{len(shown)} مادة", color=C.muted, size_hint_y=None, height=dp(22), wrap=False))
        for c in shown:
            card = TapCard(size_hint_y=None, height=dp(74), padding=[dp(14), dp(8)], radius=dp(16))
            row = RBox(spacing=dp(10))
            ic = Icon("check" if c["assigned"] else "add", 28, C.green if c["assigned"] else C.muted,
                      size_hint=(None, 1))
            row.add_widget(ic)
            col = BoxLayout(orientation="vertical")
            col.add_widget(ALabel(c["name"], bold=True, font_size=sp(14), wrap=False))
            col.add_widget(ALabel(f"{c['code']} · {c['dept_name'].replace('هندسة ', '')} · مرحلة {c['stage']}",
                                  color=C.muted, font_size=sp(11), wrap=False))
            row.add_widget(col)
            card.add_widget(row)
            card.bind(on_release=lambda _w, c=c: self.toggle(c))
            sc.add(card)

    def set_dept(self, k):
        self.dept = k
        self.render()

    def set_stage(self, k):
        self.stage = k
        self.render()

    def toggle(self, c):
        new = not c["assigned"]

        def ok(_):
            c["assigned"] = new
            self.render()
        app().api.post("/api/admin/assign", {"doctor_id": self.doctor["id"], "course_id": c["id"], "assigned": new}, ok)
