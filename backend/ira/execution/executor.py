from datetime import datetime
from typing import Callable, Any
from .task import Task, TaskStatus
from .queue import TaskQueue

class TaskExecutor:
    def __init__(self, handler: Callable[[str], Any]) -> None:
        self.handler = handler

    def execute(self, commands: list[str]) -> TaskQueue:
        queue = TaskQueue()
        
        for cmd in commands:
            queue.add(Task(command=cmd))
            
        while True:
            task = queue.next()
            if not task:
                break
                
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            try:
                response = self.handler(task.command)
                task.status = TaskStatus.COMPLETED
                task.result = getattr(response, 'text', str(response))
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                
            task.finished_at = datetime.now()
            
        return queue
