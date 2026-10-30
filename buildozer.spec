[app]

# (str) Title of your application
title = PathPresenterDownloader

# (str) Package name
package.name = pathpresenter

# (str) Package domain (needed for android packaging)
package.domain = org.pathpresenter

# (list) Source files to include (let it include python files and requirements)
source.include_exts = py,png,jpg,kv,atlas,txt

# (list) Source files to exclude (optional)
source.exclude_exts = spec

# (list) List of inclusion patterns
source.include_patterns = assets/*,images/*.png

# (list) Application requirements
requirements = python3,requests,pillow,kivy

# (str) Supported orientations
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (str) Custom python main script
android.entrypoint = main.py

# (bool) Automatically accept SDK licenses
android.accept_sdk_license = True

# (str) Supported Android architectures
android.archs = arm64-v8a, armeabi-v7a

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
