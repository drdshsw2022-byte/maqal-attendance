"""الألوان والخطوط والأيقونات."""
import os

from kivy.core.text import LabelBase
from kivy.utils import get_color_from_hex as hx

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def register_fonts():
    f = os.path.join(ASSETS, "fonts")
    LabelBase.register(
        name="Taj",
        fn_regular=os.path.join(f, "IBMPlexSansArabic-Regular.ttf"),
        fn_bold=os.path.join(f, "IBMPlexSansArabic-Bold.ttf"),
    )
    LabelBase.register(name="TajM", fn_regular=os.path.join(f, "IBMPlexSansArabic-Medium.ttf"))
    LabelBase.register(name="TajX", fn_regular=os.path.join(f, "IBMPlexSansArabic-Bold.ttf"))
    LabelBase.register(name="Icons", fn_regular=os.path.join(f, "MaterialIcons-Regular.ttf"))


class C:
    bg = hx("#F3F4FB")
    card = hx("#FFFFFF")
    text = hx("#1E1B4B")
    muted = hx("#6B7280")
    line = hx("#E5E7EB")
    white = (1, 1, 1, 1)
    # ألوان زاهية
    indigo = hx("#4F46E5")
    violet = hx("#7C3AED")
    purple = hx("#A855F7")
    teal = hx("#0D9488")
    emerald = hx("#10B981")
    sky = hx("#0EA5E9")
    amber = hx("#F59E0B")
    orange = hx("#F97316")
    rose = hx("#F43F5E")
    pink = hx("#EC4899")
    red = hx("#DC2626")
    green = hx("#16A34A")


def tint(color, a=0.12):
    return (color[0], color[1], color[2], a)


# تدرجات الرأس لكل دور
GRAD = {
    "login": ["#4F46E5", "#7C3AED", "#EC4899"],
    "student": ["#4F46E5", "#7C3AED"],
    "doctor": ["#0D9488", "#0EA5E9"],
    "admin": ["#E11D48", "#F97316"],
}

STATUS = {  # حالة الحضور: (نص، لون)
    "present": ("حاضر", C.green),
    "late": ("متأخر", C.amber),
    "excused": ("بعذر", C.sky),
    "absent": ("غائب", C.rose),
}

ICON = {
    "home": "", "person": "", "school": "", "groups": "", "scan": "",
    "qr": "", "chart": "", "settings": "", "logout": "", "check": "",
    "book": "", "add": "", "delete": "", "search": "", "lock": "",
    "mail": "", "badge": "", "play": "", "stop": "", "download": "",
    "key": "", "devices": "", "cancel": "", "clock": "", "people": "",
    "dash": "", "admin": "", "history": "", "refresh": "", "back": "",
    "visibility": "", "info": "", "warning": "", "edit": "", "calendar": "",
    "account": "", "fact": "", "done_all": "", "timer": "", "pie": "",
    "assign": "", "reg": "", "manage": "", "dns": "", "keyboard": "",
    "close": "", "class": "", "local_library": "",
}
