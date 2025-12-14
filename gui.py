# gui.py

# ==========================================================
# [重要] 桌面版不再使用 eventlet 补丁，避免与 GUI 线程冲突
# ==========================================================
# 移除 import eventlet 和 monkey_patch

import sys
import os
import io

# ==========================================================
# ⚠️ 重定向标准输出，解决 GBK 报错和无控制台崩溃
# ==========================================================
# 定义一个什么都不做的“黑洞”，或者将输出重定向到文件
class NullWriter(io.TextIOBase):
    def write(self, s):
        pass # 吃掉所有 print 输出，防止 GBK 报错
    def flush(self):
        pass

import time
import threading
import socket
import traceback
import webview
import logging

# 如果是打包后的环境 (没有控制台)
if getattr(sys, 'frozen', False):
    # 将 stdout 和 stderr 替换为 utf-8 的空写入器
    # 这样代码里的 print("中文") 就不会因为 GBK 编码问题报错了
    sys.stdout = NullWriter()
    sys.stderr = NullWriter()

# 引入 main 中的 app 和 socketio
from main import app, socketio

# [核心修复] 强制将 SocketIO 切换为 'threading' 模式
# 这样它就会使用原生线程，而不是 eventlet 协程，从而避免死锁
socketio.async_mode = 'threading'

# 设置日志路径
def get_log_path():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, 'crash.log')

# 全局异常捕获
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    with open(get_log_path(), 'a', encoding='utf-8') as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] CRASH:\n")
        f.write(error_msg)
    print("Crash log saved.", file=sys.stderr)

sys.excepthook = handle_exception

def wait_for_server(port=5000):
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', port))
            return True
        except ConnectionRefusedError:
            time.sleep(0.2)
    return False

def start_flask():
    try:
        # 移除了 async_mode 参数
        # 模式已经在 main.py 初始化 SocketIO 时通过 if IS_FROZEN 判断好了
        socketio.run(app, host='127.0.0.1', port=5000, 
                     debug=False, use_reloader=False, 
                     allow_unsafe_werkzeug=True)
    except Exception as e:
        with open(get_log_path(), 'a', encoding='utf-8') as f:
            f.write(f"\n[Flask Error] {str(e)}\n")
            f.write(traceback.format_exc())
            
if __name__ == '__main__':
    # 1. 启动后台线程
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()

    # 2. 等待服务启动
    if not wait_for_server():
        raise Exception("Server failed to start")

    # 3. 启动 GUI
    # 建议加上 http_server=True (PyWebview 5.0+ 特性，如果你的版本支持)
    # 这里保持稳妥写法
    webview.create_window(
        title='电影分镜 AI 助手',
        url='http://127.0.0.1:5000',
        width=1280,
        height=800,
        resizable=True
    )
    
    webview.start(debug=False)