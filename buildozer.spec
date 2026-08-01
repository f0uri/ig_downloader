[app]

title = Save Insta
package.name = saveinsta
package.domain = com.youssefmansouri

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,json,ttf

version = 1.0

requirements = python3,kivy==2.2.1,requests,yt-dlp

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 21
android.ndk = 25b

android.archs = arm64-v8a

android.permissions = INTERNET

presplash.color = #ffffff

[buildozer]

log_level = 2
warn_on_root = 1
