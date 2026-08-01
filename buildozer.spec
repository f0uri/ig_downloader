[app]
title = Save Insta
package.name = saveinsta
package.domain = com.youssefmansouri
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,db,ttf
version = 1.0
requirements = python3,kivy==2.2.1,requests,yt-dlp,sqlite3,urllib3,charset_normalizer,certifi,idna,chardet
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.accept_sdk_license = True
android.arch = arm64-v8a
[buildozer]
log_level = 2
warn_on_root = 1
