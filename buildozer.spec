[app]
title = حضور المعقل
package.name = maqalattendance
package.domain = iq.edu.almaaqal
source.dir = app
source.include_exts = py,png,ttf,txt,json
source.exclude_dirs = __pycache__
version = 1.0.0

requirements = python3,kivy==2.3.0,pyjnius,android,openssl,certifi,segno,arabic-reshaper==3.0.0,python-bidi==0.4.2,six

orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #4F46E5

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
p4a.branch = v2024.01.21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.enable_androidx = True
# ماسح QR الرسمي من Google (لا يحتاج صلاحية الكاميرا في التطبيق)
android.gradle_dependencies = com.google.android.gms:play-services-code-scanner:16.1.0

[buildozer]
log_level = 2
warn_on_root = 1
