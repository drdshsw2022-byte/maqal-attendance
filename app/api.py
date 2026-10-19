"""عميل الخادم: طلبات JSON غير حاجبة عبر UrlRequest."""
import json

from kivy.network.urlrequest import UrlRequest

try:
    import certifi
    CA = certifi.where()
except Exception:  # pragma: no cover
    CA = None

NET_ERR = "تعذّر الاتصال بالخادم. تحقق من الإنترنت أو من عنوان الخادم في الإعدادات."


class Api:
    def __init__(self, app):
        self.app = app
        self.token = None

    @property
    def base(self):
        return (self.app.server_url or "").rstrip("/")

    def call(self, method, path, data=None, ok=None, fail=None, quiet=False):
        if not self.base:
            self._failed(fail, {"error": "no_server", "message": "اضبط عنوان الخادم أولاً"}, quiet)
            return None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token

        def on_ok(_req, res):
            if ok:
                ok(res)

        def on_bad(req, res):
            if req.resp_status == 401 and self.token:
                self.app.session_expired()
                return
            if not isinstance(res, dict):
                res = {"error": "http", "message": f"خطأ من الخادم ({req.resp_status})"}
            self._failed(fail, res, quiet)

        def on_err(_req, _e):
            self._failed(fail, {"error": "network", "message": NET_ERR}, quiet)

        return UrlRequest(
            self.base + path, req_body=json.dumps(data) if data is not None else None, req_headers=headers,
            method=method, on_success=on_ok, on_failure=on_bad, on_error=on_err, timeout=15, ca_file=CA,
        )

    def _failed(self, fail, res, quiet):
        if fail:
            fail(res)
        elif not quiet:
            self.app.toast(res.get("message", "حدث خطأ"), "err")

    def get(self, path, ok=None, fail=None, quiet=False):
        return self.call("GET", path, None, ok, fail, quiet)

    def post(self, path, data=None, ok=None, fail=None):
        return self.call("POST", path, data or {}, ok, fail)
