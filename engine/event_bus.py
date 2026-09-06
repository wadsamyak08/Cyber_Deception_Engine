"""Thread-safe publish/consume queue connecting decoys to the engine."""

import queue


class EventBus:
    def __init__(self):
        self._q = queue.Queue()

    def publish(self, event):
        self._q.put(event)

    def consume(self, timeout=1.0):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def depth(self):
        return self._q.qsize()
