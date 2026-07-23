from collections import deque
from .task import Task, TaskStatus

class TaskQueue:
    def __init__(self) -> None:
        self._all_tasks: list[Task] = []
        self._queue: deque[Task] = deque()

    def add(self, task: Task) -> None:
        self._all_tasks.append(task)
        self._queue.append(task)

    def next(self) -> Task | None:
        if self._queue:
            return self._queue.popleft()
        return None

    def peek(self) -> Task | None:
        if self._queue:
            return self._queue[0]
        return None

    def clear(self) -> None:
        self._all_tasks.clear()
        self._queue.clear()

    def remaining(self) -> list[Task]:
        return [t for t in self._all_tasks if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING)]

    def completed(self) -> list[Task]:
        return [t for t in self._all_tasks if t.status == TaskStatus.COMPLETED]

    def failed(self) -> list[Task]:
        return [t for t in self._all_tasks if t.status == TaskStatus.FAILED]

    def all(self) -> list[Task]:
        return list(self._all_tasks)
