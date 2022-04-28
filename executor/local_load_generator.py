import random
import threading
import weakref

from bl.assertions import Assert, PjacError
from bl.log import getLogger

from .load_generator import LoadGenerator
from .result import Result

log = getLogger(__name__)


class LocalLoadGenerator(LoadGenerator):
    """
    LocalLoadGenerator implements generation of test load for local mode.
    In this mode all tests are added to queue and executed by workers
    """
    TC_SEPARATORS = ',|;| |\t'

    def __init__(self, workers, main_loop, test_factory, testcase_args, repeat_count, load_generator):
        super(LocalLoadGenerator, self).__init__()
        self.test_factory = test_factory
        self.workers = workers
        self.main_loop = main_loop
        self.testcases = []
        self.load_generator = load_generator
        for arg in self.split_tests_string(' '.join(testcase_args)):
            try:
                with open(arg, 'r') as file:
                    for line in file:
                        line, _, _ = line.partition('#')  # cut off comments
                        testcases = self.split_tests_string(line.strip('\n '))
                        if testcases:
                            self.testcases += testcases
            except IOError:
                self.testcases.append(arg)
        Assert.not_empty(self.testcases, PjacError('Testcase list not empty', verbose=False))
        log.info('Running: %s (%d times)' % (' '.join(self.testcases), repeat_count), extra={'to_console': True})
        self.testcases = self.testcases * repeat_count
        random.shuffle(self.testcases)
        self._left_count = 0
        self._failed_count = 0
        self._success_count = 0
        self._skipped_count = 0
        self._counters_lock = threading.RLock()
        self.start()

    # 'test1(param1=1, param2=2) test2 test3' -> ['test1(param1=1, param2=2)', 'test2', 'test3']
    @staticmethod
    def split_tests_string(str):
        result = []
        level = 0
        current = []
        for c in (str + ' '):
            if c in ' ,;' and level == 0 and current:
                result.append(''.join(current))
                current = []
            else:
                if c == '(':
                    level += 1
                elif c == ')':
                    level -= 1
                if current or c != ' ':
                    current.append(c)
        return result

    def start(self):
        for testcase in self.testcases:
            self.add_test(testcase)

    def add_test(self, testcase_id, arguments=None):
        test = self.test_factory(testcase_id=testcase_id, arguments=arguments, load_generator=weakref.proxy(self))
        test.on_started = self._on_started
        test.on_finished = self._on_finished
        self.workers.push(test)
        with self._counters_lock:
            self._left_count += 1

    def stop(self):
        log.info('Ran %d tests' % self.total_count, extra={'to_console': True})
        log.info('failed: %d skipped: %d success: %d' % (self._failed_count, self._skipped_count, self._success_count),
                 extra={'to_console': True})
        self.load_generator.stop()

    def _on_started(self, test):
        log.debug('LocalLoadGenerator._on_started %s' % test)

    def _on_finished(self, test):
        log.debug('LocalLoadGenerator._on_finished %s' % test)
        with self._counters_lock:
            result = test.result.get_result()
            if result == Result.Error or result == Result.Failure:
                self._failed_count += 1
            if result == Result.Success:
                self._success_count += 1
            if result == Result.Skip:
                self._skipped_count += 1

            self._left_count -= 1
            if self._left_count == 0:
                self.main_loop.stop()
            log.debug('LocalLoadGenerator._on_finished success[%s] failed[%s] skipped[%s] left[%s]' % (self._success_count,
                                                                                                       self._failed_count,
                                                                                                       self._skipped_count,
                                                                                                       self._left_count))

    @property
    def total_count(self):
        with self._counters_lock:
            return self._left_count + self.finished_count

    @property
    def finished_count(self):
        with self._counters_lock:
            return self._failed_count + self._success_count + self._skipped_count
