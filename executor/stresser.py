import datetime
import random
import threading
import weakref


class Status:
    IDLE = 'idle'
    RUNNING = 'running'


class Stresser:
    """
    Stresser implements stress test execution logic
    """
    def __init__(self, test_factory, workers):
        self.status = Status.IDLE
        self.started = None
        self.workers = workers
        self.testcases_percents = None
        self.test_factory = test_factory
        self._finished_count = 0
        self._counters_lock = threading.RLock()

    def set_threads(self, threads):
        self.workers.set_threads(threads)

    def run_tests(self, run_id, testcases_percents, threads=None):
        self.test_factory.result_factory.stress_run_id = run_id
        self.status = Status.RUNNING
        self.started = datetime.datetime.now()
        self.testcases_percents = testcases_percents

        self.workers.set_threads(threads)
        self._adjust_running_test(threads)

    def get_status(self):
        """
        returns:
        status,
        run_seconds
        threads
        """
        run_seconds = 0
        if self.status == Status.RUNNING:
            run_seconds = (datetime.datetime.now() - self.started).total_seconds()
        return (self.status,
                run_seconds,
                self.workers.workers_count())

    def stop_tests(self):
        self.workers.reset()

    def add_test(self, testcase_id, arguments=None):
        if self.status != Status.RUNNING:
            return
        test = self.test_factory(testcase_id=testcase_id, arguments=arguments, load_generator=weakref.proxy(self))
        test.on_started = self._on_started
        test.on_finished = self._on_finished
        self.workers.push(test)

    def _on_started(self, test):
        pass

    def _on_finished(self, test):
        with self._counters_lock:
            self._finished_count += 1
        self.add_test(testcase_id=self.get_next_testcase_id())

    def get_next_testcase_id(self):
        chance = random.random() * 100
        current_percent = 0
        for testcase, percent in self.testcases_percents:
            current_percent += percent
            if chance < current_percent:
                return testcase

    def _adjust_running_test(self, count=None):
        count = count or self.workers.workers_count()
        for i in range(count):
            self.add_test(testcase_id=self.get_next_testcase_id())

    @property
    def total_count(self):
        return None

    @property
    def finished_count(self):
        with self._counters_lock:
            return self._finished_count
