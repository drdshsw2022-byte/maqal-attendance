import os, sys, time, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import pytest
import app as core
import importer

SEED = os.path.join(os.path.dirname(__file__), "..", "seed")


@pytest.fixture()
def env(tmp_path):
    path = str(tmp_path / "t.db")
    application = core.create_app(db_path=path, secret="test-secret")
    core.import_courses(path, importer.parse_courses(f"{SEED}/courses.xlsx"))
    core.import_students(path, importer.parse_students(f"{SEED}/students.xlsx"))
    core.create_admin(path, "admin@x.com", "مدير", "adminpass")
    return application.test_client(), path


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def login(c, ident, pw, device="dev1"):
    r = c.post("/api/auth/login", json={"identifier": ident, "password": pw, "device_id": device})
    return r


def test_full_flow(env):
    c, path = env
    # --- المدير
    adm = login(c, "admin@x.com", "adminpass").get_json()["token"]
    ov = c.get("/api/admin/overview", headers=H(adm)).get_json()
    assert ov["students"] == 538
    # دكتور
    r = c.post("/api/admin/doctors", headers=H(adm), json={"name": "د. تجربة", "email": "Doc@Gmail.com", "password": "temp123"})
    assert r.status_code == 200
    did = r.get_json()["id"]
    assert c.post("/api/admin/doctors", headers=H(adm), json={"name": "x y z", "email": "doc@gmail.com", "password": "temp123"}).status_code == 409
    # مواد الفصل الأول للقسم ai المرحلة 2
    courses = c.get("/api/admin/courses", headers=H(adm)).get_json()
    cs = [x for x in courses if x["dept"] == "ai" and x["stage"] == 2]
    assert cs, "no ai stage-2 season-1 courses"
    cid = cs[0]["id"]
    assert c.post("/api/admin/assign", headers=H(adm), json={"doctor_id": did, "course_id": cid, "assigned": True}).status_code == 200
    # --- الدكتور
    d = login(c, "doc@gmail.com", "temp123").get_json()
    assert d["user"]["must_change"] is True
    dt = d["token"]
    assert c.post("/api/auth/change-password", headers=H(dt), json={"old": "temp123", "new": "newpass1"}).status_code == 200
    mine = c.get("/api/doctor/courses", headers=H(dt)).get_json()
    assert [m["id"] for m in mine] == [cid]
    assert c.post("/api/doctor/sessions", headers=H(dt), json={"course_id": cs[1]["id"]}).status_code == 403
    # --- طالبان من المرحلة 2
    with sqlite3.connect(path) as con:
        studs = con.execute("SELECT uid FROM users WHERE role='student' AND stage=2 AND shift='morning' LIMIT 2").fetchall()
    u1, u2 = studs[0][0], studs[1][0]
    assert login(c, u1, "123456").status_code == 409  # غير مفعّل
    assert c.post("/api/auth/activate", json={"uid": "0000000000", "password": "abcdef", "department": "ai", "device_id": "A"}).status_code == 404
    r = c.post("/api/auth/activate", json={"uid": u1, "password": "abcdef", "department": "ai", "email": "s1@gmail.com", "device_id": "A"})
    assert r.status_code == 200, r.get_json()
    s1 = r.get_json()["token"]
    s2 = c.post("/api/auth/activate", json={"uid": u2, "password": "abcdef", "department": "ai", "device_id": "B"}).get_json()["token"]
    assert c.post("/api/auth/activate", json={"uid": u1, "password": "zzzzzz", "department": "ai", "device_id": "Z"}).status_code == 409
    # ربط الجهاز
    assert login(c, u1, "abcdef", "OTHER").status_code == 403
    assert login(c, "s1@gmail.com", "abcdef", "A").status_code == 200
    home = c.get("/api/student/home", headers=H(s1)).get_json()
    assert any(x["id"] == cid for x in home["courses"])
    # --- بدء محاضرة
    sid = c.post("/api/doctor/sessions", headers=H(dt), json={"course_id": cid}).get_json()["session_id"]
    assert c.post("/api/doctor/sessions", headers=H(dt), json={"course_id": cid}).get_json()["resumed"] is True
    st = c.get(f"/api/doctor/sessions/{sid}", headers=H(dt)).get_json()
    assert st["qr"]["payload"] == f"MQL|{sid}|{st['qr']['code']}"
    code = st["qr"]["code"]
    # رمز خاطئ
    assert c.post("/api/attendance/checkin", headers=H(s1), json={"code": "000000" if code != "000000" else "111111", "device_id": "A"}).status_code == 400
    # جهاز خاطئ
    assert c.post("/api/attendance/checkin", headers=H(s1), json={"code": code, "device_id": "EVIL"}).status_code == 403
    r = c.post("/api/attendance/checkin", headers=H(s1), json={"code": code, "session_id": sid, "device_id": "A"})
    assert r.status_code == 200 and r.get_json()["status"] == "present", r.get_json()
    assert c.post("/api/attendance/checkin", headers=H(s1), json={"code": code, "device_id": "A"}).get_json()["already"] is True
    # دخول بدون session_id (إدخال يدوي)
    r = c.post("/api/attendance/checkin", headers=H(s2), json={"code": code, "device_id": "B"})
    assert r.status_code == 200
    st = c.get(f"/api/doctor/sessions/{sid}", headers=H(dt)).get_json()
    assert st["counts"]["present"] == 2
    # تعديل يدوي
    stu = [x for x in st["roster"] if x["uid"] == u2][0]
    assert c.post(f"/api/doctor/sessions/{sid}/mark", headers=H(dt), json={"student_id": stu["student_id"], "status": "excused"}).status_code == 200
    assert c.post(f"/api/doctor/sessions/{sid}/end", headers=H(dt)).status_code == 200
    # بعد الإنهاء لا يقبل الرمز
    assert c.post("/api/attendance/checkin", headers=H(s1), json={"code": code, "device_id": "A"}).status_code == 400
    rep = c.get(f"/api/doctor/courses/{cid}/report", headers=H(dt)).get_json()
    row1 = [r for r in rep["rows"] if r["uid"] == u1][0]
    row2 = [r for r in rep["rows"] if r["uid"] == u2][0]
    assert row1["present"] == 1 and row1["pct"] == 100
    assert row2["excused"] == 1
    assert rep["unassigned"] > 100
    with sqlite3.connect(path) as con:
        third = con.execute("SELECT id FROM users WHERE role='student' AND stage=2 AND shift='morning' AND department IS NULL LIMIT 1").fetchone()[0]
    assert c.post(f"/api/admin/students/{third}/department", headers=H(adm), json={"department": "ai"}).status_code == 200
    rep = c.get(f"/api/doctor/courses/{cid}/report", headers=H(dt)).get_json()
    absent_row = [r for r in rep["rows"] if r["uid"] not in (u1, u2)][0]
    assert absent_row["absent"] == 1 and absent_row["pct"] == 0 and absent_row["warn"] is True
    # تاريخ الطالب
    h = c.get(f"/api/student/courses/{cid}/history", headers=H(s1)).get_json()
    assert h["rows"][0]["status"] == "present"
    # تصدير
    link = c.post("/api/export-link", headers=H(dt), json={"course_id": cid}).get_json()["path"]
    x = c.get(link)
    assert x.status_code == 200 and x.data[:2] == b"PK"
    assert c.get(f"/export/course/{cid}.xlsx?t=bad").status_code == 403
    # الصلاحيات
    assert c.get("/api/admin/overview", headers=H(dt)).status_code == 403
    assert c.get("/api/doctor/courses", headers=H(s1)).status_code == 403
    # فك ربط الجهاز
    sid1 = [x for x in c.get("/api/admin/students?q=" + u1, headers=H(adm)).get_json()["rows"]][0]["id"]
    assert c.post(f"/api/admin/students/{sid1}/reset", headers=H(adm), json={"what": "device"}).status_code == 200
    assert login(c, u1, "abcdef", "NEW").status_code == 200


def test_late_and_rate_limit(env):
    c, path = env
    adm = login(c, "admin@x.com", "adminpass").get_json()["token"]
    did = c.post("/api/admin/doctors", headers=H(adm), json={"name": "د. ب ت", "email": "d2@x.com", "password": "temp123"}).get_json()["id"]
    cid = [x for x in c.get("/api/admin/courses", headers=H(adm)).get_json() if x["dept"] == "ai" and x["stage"] == 3][0]["id"]
    c.post("/api/admin/assign", headers=H(adm), json={"doctor_id": did, "course_id": cid, "assigned": True})
    dt = login(c, "d2@x.com", "temp123").get_json()["token"]
    sid = c.post("/api/doctor/sessions", headers=H(dt), json={"course_id": cid, "late_after": 1}).get_json()["session_id"]
    with sqlite3.connect(path) as con:
        con.execute("UPDATE sessions SET started_at=started_at-300 WHERE id=?", (sid,))
        uid = con.execute("SELECT uid FROM users WHERE role='student' AND stage=3 LIMIT 1").fetchone()[0]
    tok = c.post("/api/auth/activate", json={"uid": uid, "password": "abcdef", "department": "ai", "device_id": "D"}).get_json()["token"]
    code = c.get(f"/api/doctor/sessions/{sid}", headers=H(dt)).get_json()["qr"]["code"]
    assert c.post("/api/attendance/checkin", headers=H(tok), json={"code": code, "device_id": "D"}).get_json()["status"] == "late"
    # تحديد المحاولات
    for _ in range(6):
        login(c, "nobody@x.com", "bad")
    assert login(c, "nobody@x.com", "bad").status_code == 429
