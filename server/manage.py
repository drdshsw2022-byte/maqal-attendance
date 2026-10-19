"""أوامر إدارة الخادم.

  python manage.py init --admin-email you@gmail.com      # تهيئة كاملة (تولّد كلمة مرور للمدير)
  python manage.py run  --port 8000                      # تشغيل الخادم
  python manage.py import-students ملف.xlsx               # تحديث قاعدة الطلاب لاحقاً
  python manage.py import-courses  ملف.xlsx
  python manage.py import-departments ملف.xlsx           # أعمدة: الرقم المعرفي | القسم (ai / control / cyber)
  python manage.py create-admin --email a@b.com --password ******
"""
import argparse
import os
import secrets
import string
import sys

import app as core
import importer

BASE = os.path.dirname(os.path.abspath(__file__))


def db_path():
    return os.environ.get("MAQAL_DB") or os.path.join(BASE, "instance", "attendance.db")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init")
    a.add_argument("--admin-email", required=True)
    a.add_argument("--admin-name", default="مدير النظام")
    a.add_argument("--admin-password")
    a.add_argument("--students", default=os.path.join(BASE, "seed", "students.xlsx"))
    a.add_argument("--courses", default=os.path.join(BASE, "seed", "courses.xlsx"))
    r = sub.add_parser("run")
    r.add_argument("--host", default="0.0.0.0")
    r.add_argument("--port", type=int, default=8000)
    for name in ("import-students", "import-courses", "import-departments"):
        s = sub.add_parser(name)
        s.add_argument("file")
    c = sub.add_parser("create-admin")
    c.add_argument("--email", required=True)
    c.add_argument("--name", default="مدير النظام")
    c.add_argument("--password", required=True)
    args = p.parse_args()

    os.makedirs(os.path.dirname(db_path()), exist_ok=True)
    core.init_db(db_path())
    if args.cmd == "init":
        courses = importer.parse_courses(args.courses)
        students = importer.parse_students(args.students)
        core.import_courses(db_path(), courses)
        core.import_students(db_path(), students)
        pw = args.admin_password or "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        core.create_admin(db_path(), args.admin_email, args.admin_name, pw)
        print(f"تم استيراد {len(courses)} مادة و{len(students)} طالباً.")
        print(f"حساب المدير:  {args.admin_email}\nكلمة المرور:  {pw}\n(احفظها الآن، ولن تظهر مرة أخرى)")
    elif args.cmd == "import-courses":
        courses = importer.parse_courses(args.file)
        core.import_courses(db_path(), courses)
        print(f"تم استيراد {len(courses)} مادة")
    elif args.cmd == "import-students":
        students = importer.parse_students(args.file)
        core.import_students(db_path(), students)
        print(f"تم استيراد {len(students)} طالباً")
    elif args.cmd == "import-departments":
        import openpyxl
        ws = openpyxl.load_workbook(args.file, read_only=True, data_only=True).worksheets[0]
        pairs = [(str(r[0]).strip(), str(r[1]).strip()) for r in ws.iter_rows(min_row=2, values_only=True) if r[0] and r[1]]
        print(f"تم تحديث قسم {core.import_departments(db_path(), pairs)} طالباً")
    elif args.cmd == "create-admin":
        core.create_admin(db_path(), args.email, args.name, args.password)
        print("تم")
    elif args.cmd == "run":
        core.create_app().run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    sys.exit(main())
