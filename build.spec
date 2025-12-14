# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules # 如果之前用了这个也保留

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 格式: ('源码里的路径', '打包后的文件夹名')

        # 1. 网页文件 (放根目录)
        ('index.html', '.'),
        ('series.html', '.'),
        
        # 2. 静态资源 -> 复制到 EXE/static
        ('static', 'static'),
        
        # 3. 数据文件 -> 复制到 EXE/data
        # 注意：这里会把开发环境的 json 复制过去作为“初始数据”
        ('data', 'data'),
    ]+ collect_data_files('pyJianYingDraft'),
    hiddenimports=[
        'socketio',
        'flask_socketio',
        'webview',
        'webview.platforms.winforms',
        'engineio.async_drivers.threading',
        'pyJianYingDraft',
        
        # === 修复 Eventlet 打包报错 ===
        # 即使我们运行时不用它，PyInstaller 扫描时也需要这些
        # 确保这些都在，防止各种奇怪的 ModuleNotFound
        'engineio.async_drivers.threading', 
        'eventlet.hubs.epolls',
        'eventlet.hubs.kqueue',
        'eventlet.hubs.selects',
        'dns',
    ],    
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True, # 开启文件夹模式
    name='StoryboardAI',   # 程序名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # <--- 建议先设为 True，方便看后台报错。发布时改为 False 隐藏黑框
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StoryboardAI', # 最终文件夹名称
)