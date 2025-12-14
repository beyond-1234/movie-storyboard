import uuid
import time
from concurrent.futures import ThreadPoolExecutor

class TaskQueue:
    def __init__(self, max_workers=2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = {}

    def submit(self, worker_func, *args, **kwargs):
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "id": task_id, "status": "pending", 
            "created_at": time.strftime('%H:%M:%S'),
            "desc": kwargs.pop('desc', 'AI任务')
        }
        self.executor.submit(self._runner, task_id, worker_func, args, kwargs)
        return task_id

    def _runner(self, task_id, func, args, kwargs):
        self.tasks[task_id]["status"] = "processing"
        try:
            # 执行传入的函数
            func(*args, **kwargs)
            self.tasks[task_id]["status"] = "success"
        except Exception as e:
            print(f"Task Error: {e}")
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = str(e)
    
    def get_list(self):
        return sorted(self.tasks.values(), key=lambda x: x['created_at'], reverse=True)

queue = TaskQueue()