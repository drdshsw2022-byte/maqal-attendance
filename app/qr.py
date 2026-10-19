"""رسم رمز QR (بدون Pillow) + مسح الرمز بكاميرا الهاتف عبر Google Code Scanner على أندرويد."""
import segno
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import StringProperty
from kivy.uix.widget import Widget
from kivy.utils import platform


class QRView(Widget):
    payload = StringProperty("")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, payload=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        if not self.payload or self.width < 10:
            return
        m = [list(r) for r in segno.make(self.payload, error="m", micro=False).matrix]
        n = len(m)
        quiet = 2
        cells = n + quiet * 2
        side = min(self.width, self.height)
        cell = int(side / cells) or 1
        total = cell * cells
        ox = self.x + (self.width - total) / 2
        oy = self.y + (self.height - total) / 2
        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=(ox, oy), size=(total, total))
            Color(0.08, 0.06, 0.2, 1)
            for r, row in enumerate(m):
                c = 0
                while c < n:  # ندمج الخلايا المظلمة المتجاورة في مستطيل واحد
                    if row[c]:
                        start = c
                        while c < n and row[c]:
                            c += 1
                        Rectangle(pos=(ox + (start + quiet) * cell, oy + (n - 1 - r + quiet) * cell),
                                  size=((c - start) * cell, cell))
                    else:
                        c += 1


def parse_payload(text):
    """MQL|<session_id>|<code6> -> (session_id, code) أو None"""
    parts = (text or "").strip().split("|")
    if len(parts) == 3 and parts[0] == "MQL" and parts[1].isdigit() and parts[2].isdigit() and len(parts[2]) == 6:
        return int(parts[1]), parts[2]
    return None


def scanner_available():
    return platform == "android"


_keep = []  # نحتفظ بالمراجع حتى لا يحذفها جامع النفايات أثناء عمل الماسح


def scan(on_text, on_error):
    """يفتح ماسح Google (ML Kit). on_text(str) / on_error(str) تُستدعى على خيط Kivy."""
    if platform != "android":
        on_error("المسح بالكاميرا متاح على أندرويد فقط. أدخل الرمز يدوياً.")
        return
    try:
        from jnius import PythonJavaClass, autoclass, cast, java_method

        class _OnOk(PythonJavaClass):
            __javainterfaces__ = ["com/google/android/gms/tasks/OnSuccessListener"]
            __javacontext__ = "app"

            @java_method("(Ljava/lang/Object;)V")
            def onSuccess(self, result):
                try:
                    bc = cast("com.google.mlkit.vision.barcode.common.Barcode", result)
                    val = bc.getRawValue()
                except Exception as e:  # pragma: no cover
                    Clock.schedule_once(lambda dt: on_error(str(e)), 0)
                    return
                Clock.schedule_once(lambda dt: on_text(str(val) if val is not None else ""), 0)

        class _OnFail(PythonJavaClass):
            __javainterfaces__ = ["com/google/android/gms/tasks/OnFailureListener"]
            __javacontext__ = "app"

            @java_method("(Ljava/lang/Exception;)V")
            def onFailure(self, e):
                msg = "تعذّر فتح الماسح. تأكد من تحديث خدمات Google Play أو أدخل الرمز يدوياً."
                Clock.schedule_once(lambda dt: on_error(msg), 0)

        class _OnCancel(PythonJavaClass):
            __javainterfaces__ = ["com/google/android/gms/tasks/OnCanceledListener"]
            __javacontext__ = "app"

            @java_method("()V")
            def onCanceled(self):
                pass

        Activity = autoclass("org.kivy.android.PythonActivity").mActivity
        Scanning = autoclass("com.google.mlkit.vision.codescanner.GmsBarcodeScanning")
        client = Scanning.getClient(Activity)
        task = client.startScan()
        listeners = [_OnOk(), _OnFail(), _OnCancel()]
        _keep[:] = listeners + [client, task]
        task.addOnSuccessListener(listeners[0])
        task.addOnFailureListener(listeners[1])
        task.addOnCanceledListener(listeners[2])
    except Exception as e:  # pragma: no cover
        on_error("تعذّر تشغيل الماسح: " + str(e)[:80])


def open_url(url):
    """يفتح رابطاً في متصفح الهاتف (لتنزيل ملف Excel)."""
    if platform == "android":
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        activity.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    else:
        import webbrowser
        webbrowser.open(url)
