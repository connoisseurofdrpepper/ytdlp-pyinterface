import subprocess, threading, queue
from typing import List, Optional, Callable

class Task:
    def __init__(self, label: str, cmd: List[str], cwd: Optional[str] = None):
        self.label = label
        self.cmd = cmd
        self.cwd = cwd
        self.process: Optional[subprocess.Popen] = None
        self.status = "queued"
        self.returncode: Optional[int] = None

class Runner:
    def __init__(self, on_log: Callable[[str], None], on_task: Callable[[Task], None]):
        self.on_log = on_log
        self.on_task = on_task
        self.q: "queue.Queue[Task]" = queue.Queue()
        self._stop = threading.Event()
        self.current: Optional[Task] = None
        threading.Thread(target=self._loop, daemon=True).start()

    def enqueue(self, task: Task):
        self.q.put(task)
        self.on_log(f"[QUEUE] {task.label}\n")

    def stop_all(self):
        self._stop.set()
        if self.current and self.current.process:
            try: self.current.process.terminate()
            except Exception: pass

    def _loop(self):
        while not self._stop.is_set():
            try:
                task = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            self.current = task
            self._run_task(task)
            self.current = None

    def _run_task(self, task: Task):
        task.status = "running"
        self.on_task(task)
        self.on_log(f"[RUN] {task.label}\n")
        try:
            task.process = subprocess.Popen(
                task.cmd,
                cwd=task.cwd or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert task.process.stdout is not None
            for line in task.process.stdout:
                self.on_log(line)
                if self._stop.is_set():
                    break
            task.process.wait()
            task.returncode = task.process.returncode
            task.status = "done" if task.returncode == 0 else "error"
        except Exception as e:
            self.on_log(f"[ERROR] {e}\n")
            task.status = "error"
            task.returncode = -1
        finally:
            self.on_task(task)
            self.on_log(f"[END] {task.label} (status={task.status}, code={task.returncode})\n")
