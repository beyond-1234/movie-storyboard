# task_queue.py
import uuid
import time
import logging
from concurrent.futures import ThreadPoolExecutor

# 引入 Flask 的 current_app (虽然线程里用不了，但作为类型提示)
# 关键：不要在这里直接 import socketio 实例，避免循环引用

logger = logging.getLogger("TaskQueue")
socketio_instance = None # 全局变量存储

def init_socketio(sio):
    """接收 main.py 传来的 socketio 对象"""
    global socketio_instance
    socketio_instance = sio

class TaskQueue:
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}

    def submit(self, worker_func, *args, **kwargs):
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "id": task_id, "status": "pending", 
            "created_at": time.strftime('%H:%M:%S'),
            "desc": kwargs.pop('desc', 'AI任务'),
            "progress": 0
        }
        self._emit_update() # 提交时广播
        self.executor.submit(self._runner, task_id, worker_func, args, kwargs)
        return task_id

    def _runner(self, task_id, func, args, kwargs):
        self.tasks[task_id]["status"] = "processing"
        self._emit_update() # 开始时广播
        
        try:
            func(*args, **kwargs)
            self.tasks[task_id]["status"] = "success"
            self.tasks[task_id]["progress"] = 100
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = str(e)
        
        self._emit_update() # 结束时广播

    def _emit_update(self):
        """
        移除 broadcast=True 参数，因为在新版 Flask-SocketIO 中，
        上下文之外的 emit 默认就是广播。
        """
        if socketio_instance:
            try:
                task_list = self.get_list()
                
                # === 修改这里：删掉 broadcast=True ===
                socketio_instance.emit(
                    'task_update', 
                    task_list, 
                    namespace='/'
                )
                
            except Exception as e:
                logger.error(f"Socket emit failed: {e}")

    def get_list(self):
        return sorted(self.tasks.values(), key=lambda x: x['created_at'], reverse=True)

queue = TaskQueue()