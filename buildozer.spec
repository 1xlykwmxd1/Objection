[app]
title = David2k Tool
package.name = pro
package.domain = com.david2ktool
version = 2.0

source.dir = .
source.include_exts = py,png,jpg,json,obj,txt,bin,objtopo,iff
source.exclude_dirs = tests,recipes,bin,.buildozer,.github,__pycache__

# v192: etcpak included (fast ETC2 encoder: needed for 2048 face slots; recipe in ./recipes patches its build).
requirements = python3,numpy,kivy==2.3.0,pillow,sqlite3,etcpak,texture2ddecoder,certifi
p4a.local_recipes = ./recipes

orientation = portrait
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/presplash.png
android.presplash_color = #12131A
fullscreen = 0

# MANAGE_EXTERNAL_STORAGE = "All files access" (Android 11+), requested at runtime.
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,REQUEST_INSTALL_PACKAGES


android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = False
p4a.branch = v2024.01.21
android.enable_androidx = False

[buildozer]
log_level = 2
warn_on_root = 1
