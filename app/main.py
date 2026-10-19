"""نظام الحضور والغياب — جامعة المعقل الأهلية (البصرة)"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.config import Config

if os.environ.get("MAQAL_DESKTOP"):  # للتجربة على الحاسوب بحجم هاتف
    Config.set("graphics", "width", os.environ.get("MAQAL_W", "405"))
    Config.set("graphics", "height", os.environ.get("MAQAL_H", "820"))
Config.set("input", "mouse", "mouse,disable_multitouch")

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager

import config
from api import Api
from screens.admin import AdminDash, AssignScreen
from screens.auth import ActivateScreen, LoginScreen
from screens.common import change_password_dialog
from screens.doctor import DoctorDash, ReportScreen, SessionScreen
from screens.student import HistoryScreen, ScanScreen, StudentDash
from theme import C, register_fonts
from widgets import ALabel, Btn, Dialog, Field, message, toast


class MaqalApp(App):
    title = "نظام الحضور – جامعة المعقل الأهلية"

    def build(self):
        register_fonts()
        Window.clearcolor = C.bg
        Window.softinput_mode = "below_target"
        self.store = JsonStore(os.path.join(self.user_data_dir, "maqal.json"))
        cfg = self.store.get("cfg") if self.store.exists("cfg") else {}
        self.server_url = os.environ.get("MAQAL_SERVER") or cfg.get("server") or config.DEFAULT_SERVER
        self.device_id = cfg.get("device") or uuid.uuid4().hex
        self.user, self.stack = None, []
        self.api = Api(self)
        self._save_cfg()
        sm = ScreenManager(transition=FadeTransition(duration=0.12))
        for s in (LoginScreen(), ActivateScreen(), StudentDash(), DoctorDash(), AdminDash(), HistoryScreen(),
                  ScanScreen(), SessionScreen(), ReportScreen(), AssignScreen()):
            sm.add_widget(s)
        sm.current = "login"
        self.sm = sm
        Window.bind(on_keyboard=self._key)
        return sm

    # ------------------------------------------------------------ التخزين
    def _save_cfg(self, token=None):
        old = self.store.get("cfg") if self.store.exists("cfg") else {}
        self.store.put("cfg", server=self.server_url, device=self.device_id,
                       token=old.get("token") if token is None else token)

    def on_start(self):
        cfg = self.store.get("cfg")
        if cfg.get("token") and self.server_url:
            self.api.token = cfg["token"]
            self.api.get("/api/me", self._resume, fail=lambda e: self._to_login(), quiet=True)
        elif not self.server_url:
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.server_dialog(first=True), 0.6)

    def _resume(self, user):
        self.user = user
        self.enter_role(user)

    # ------------------------------------------------------------ الدخول والخروج
    def on_login(self, res):
        self.api.token = res["token"]
        self.user = res["user"]
        self._save_cfg(token=res["token"])
        self.enter_role(self.user)

    def enter_role(self, user):
        self.stack = []
        dash = self.sm.get_screen(user["role"])
        dash.enter(user)
        self.sm.current = user["role"]
        if user.get("must_change"):
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: change_password_dialog(forced=True), 0.4)

    def _to_login(self):
        self.api.token = None
        self.user = None
        self.stack = []
        self.sm.current = "login"

    def logout(self):
        self._save_cfg(token="")
        self._to_login()

    def session_expired(self):
        self._save_cfg(token="")
        self._to_login()
        toast("انتهت الجلسة، سجّل الدخول من جديد", "err")

    # ------------------------------------------------------------ التنقل
    def open(self, name, **kw):
        scr = self.sm.get_screen(name)
        if hasattr(scr, "setup"):
            scr.setup(**kw)
        self.stack.append(self.sm.current)
        self.sm.current = name

    def back(self):
        if not self.stack:
            return False
        prev = self.stack.pop()
        self.sm.current = prev
        scr = self.sm.get_screen(prev)
        if hasattr(scr, "refresh") and prev in ("student", "doctor", "admin"):
            scr.refresh()
        return True

    def _key(self, _w, key, *_):
        if key == 27:  # زر الرجوع في أندرويد
            return self.back()
        return False

    def toast(self, text, kind="info"):
        toast(text, kind)

    # ------------------------------------------------------------ إعدادات الخادم
    def server_dialog(self, first=False):
        f = Field("عنوان الخادم", icon="dns", input_type="url")
        f.text = self.server_url
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(76 + 56 + 36), spacing=dp(6))
        box.add_widget(f)
        box.add_widget(ALabel("مثال: https://attendance.university.edu.iq", color=C.muted, font_size=sp(12),
                              size_hint_y=None, height=dp(24), wrap=False))
        box.add_widget(Btn("اختبار الاتصال", icon="refresh", kind="soft", height=48,
                           on_release=lambda *_: self._test(f.text)))

        def save():
            url = f.text.strip().rstrip("/")
            if url and "://" not in url:
                url = "http://" + url
            self.server_url = url
            self._save_cfg()
            toast("تم حفظ عنوان الخادم", "ok")
            return True
        Dialog("إعدادات الخادم", box, [("حفظ", "primary", save), ("إغلاق", "soft", None)], icon="dns").open()

    def _test(self, url):
        url = url.strip().rstrip("/")
        if url and "://" not in url:
            url = "http://" + url
        old, self.server_url = self.server_url, url
        self.api.get("/api/ping", lambda r: toast("الاتصال ناجح ✓", "ok"), fail=lambda e: toast(e["message"], "err"))
        self.server_url = old if not old else self.server_url


if __name__ == "__main__":
    MaqalApp().run()
