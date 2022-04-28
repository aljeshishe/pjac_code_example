import ctypes
import threading

from bl.log import getLogger

log = getLogger(__name__)


class Worker:
    """
    Worker is wrapper around Thread. It is intended to run tests.
    """
    def __init__(self, workers):
        self.stopped = False
        self.workers_pool = workers
        self.thread = threading.Thread(target=self.thread_func, name=self._worker_name())
        self.thread.start()

    def __str__(self):
        return 'Worker[%s]' % self.thread.ident

    def __repr__(self):
        return str(self)

    def thread_func(self):
        log.info('Worker %s started' % self.thread.ident)
        from bl import pycrashrpt
        holder = pycrashrpt.install_thread()

        self.thread.name = self._worker_name(self.thread.ident)
        while not self.stopped:
            try:
                if self.workers_pool.cpu_monitor.throttle():
                    continue
                test = self.workers_pool.pop()
                log.info('Worker.thread_func: got test %s' % test)
                test.run()

            except KeyboardInterrupt:
                log.info('Worker.thread_func: %s got KeyboardInterrupt' % self.thread.ident)
                break
            except Exception as e:
                log.exception('Worker.thread_func: exception', extra={'to_console': True})
        self.workers_pool.on_worker_finished(self)

    def finished(self):
        return not self.thread.is_alive()

    def stop(self):
        self.stopped = True
        result = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.thread.ident), ctypes.py_object(KeyboardInterrupt))
        log.info('Worker.stop: raised KeyboardInterrupt exception in thread %d (%d threads affected)' % (self.thread.ident, result))
        if result == 0:
            log.warn('Worker.stop: invalid thread id')
        elif result != 1:
            log.warn('Worker.stop: invalid return value, resetting exception in thread %d' % self.thread.ident)
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(self.thread.ident), 0)

    def _worker_name(self, thread_id=None):
        return 'WorkerThread:%s' % thread_id if thread_id else 'unknown'
