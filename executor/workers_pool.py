import queue
import threading
import time
import weakref
from queue import Empty
from threading import Lock

from bl.assertions import Assert, PjacError
from bl.executor import debugger
from bl.executor.worker import Worker
from bl.log import getLogger
from bl.settings import Settings
from bl.timer import Timer
from bl.utils.ignore_exception import SuppressExceptions

from .cpu_monitor import CPUMonitor

log = getLogger(__name__)


class MyQueue(queue.Queue):
    """
    Enhanced version of queue.Queue which supports clear method
    """
    def clear(self):
        with self.mutex:
            self.queue.clear()


class WorkersPool:
    """
    Pool of workers which run tests
    """
    def __init__(self, count=0):
        self.tasks = MyQueue()
        self.workers = set()
        self.workers_lock = Lock()
        self.set_threads(count)
        self.cpu_monitor = CPUMonitor()

    def push(self, task):
        self.tasks.put(task)

    def pop(self):
        # we need to poll, or KeyboardInterrupt will not be raised in time
        while True:
            with SuppressExceptions(Empty, verbose=False):
                return self.tasks.get(timeout=1)

    def set_threads(self, thread_count):
        with self.workers_lock:
            total_count = len(self.workers)
            create_count = thread_count - total_count

        if create_count > 0:
            log.info('WorkersPool.set_threads Starting new workers count %d(current_count=%d)' % (create_count, total_count))
            new_workers = ([Worker(weakref.proxy(self)) for _ in range(create_count)])
            with self.workers_lock:
                self.workers.update(new_workers)
        if create_count < 0:
            self.stop(bottom_count=thread_count)

    def stop(self, bottom_count=0):
        # debugger.log_all_stacks()
        self.cpu_monitor.stop()
        with debugger.check_interval(0):  # all threads should get KeyboardInterrupt without delay
            timer = Timer(60)
            try_timer = Timer(0)
            iteration = 0
            while not timer.fired():
                workers_to_stop, total_workers = self._workers_to_stop(bottom_count)
                if not workers_to_stop:
                    return
                if try_timer.fired():
                    iteration += 1
                    log.info('WorkersPool.stop stopping %s(current_count=%s) workers iteration %s ' % (len(workers_to_stop), total_workers, iteration))
                    for worker in workers_to_stop:
                        worker.stop()
                    try_timer = Timer(20)
                time.sleep(1)
            log.warn('WorkersPool.stop cant stop %s(current_count=%s) workers' % (len(workers_to_stop), total_workers))

    def _workers_to_stop(self, bottom_count):
        with self.workers_lock:
            total_workers = len(self.workers)
            workers_to_stop = list(self.workers.copy())[:total_workers - bottom_count]
            return workers_to_stop, total_workers

    def reset(self):
        log.info('WorkersPool.reset Test queue size is %d clearing' % self.tasks.qsize())
        self.tasks.clear()
        self.stop()

    def on_worker_finished(self, worker):
        with self.workers_lock:
            self.workers.remove(worker)
            workers_left = len(self.workers)
        log.info('WorkersPool.on_worker_finished: %s finished left %s' % (worker, workers_left))

    def workers_count(self):
        with self.workers_lock:
            return len(self.workers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class WarmupWorkersPool(WorkersPool):
    """
    Pool of workers which support gradual warmup.
    It is necessary to avoid load spike on backend
    """
    def __init__(self, count=0, warm_up_speed=None):
        self._threads_count_target = 0

        warm_up_speed = warm_up_speed or Settings.get('warmup_speed', with_type=int)
        Assert.greater(warm_up_speed, 0, PjacError('warmup_speed should be greater 0', verbose=False))

        self._warm_up_delay = 60 / float(warm_up_speed)
        self._cond = threading.Condition()

        super(WarmupWorkersPool, self).__init__(count=count)

        self._work_thread = threading.Thread(target=self._thread_func)
        self._work_thread.daemon = True
        self._work_thread.start()

    def _thread_func(self):
        while True:
            with self._cond:
                if self.workers_count() >= self._threads_count_target:
                    super(WarmupWorkersPool, self).set_threads(self._threads_count_target)
                    self._cond.wait()
                    continue
                super(WarmupWorkersPool, self).set_threads(self.workers_count() + 1)
                self._cond.wait(timeout=self._warm_up_delay)

    def set_threads(self, threads):
        with self._cond:
            self._threads_count_target = threads
            self._cond.notify()

    def stop(self, bottom_count=0):
        with self._cond:
            self._threads_count_target = bottom_count
            super(WarmupWorkersPool, self).stop(bottom_count)
