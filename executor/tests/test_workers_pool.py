import threading
import time

from bl.settings import Settings

from bl.executor import WorkersPool, WarmupWorkersPool
from bl.unittest_testcase import PjacUnitTestCase
from mock import patch, Mock


class Tests(PjacUnitTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        Settings.set('cpu_throtlng_percent', 100)

    def tearDown(self):
        super(Tests, self).tearDown()
        Settings.reset()

    def test_workers_pool_init(self):
        with WorkersPool(count=10) as pool:
            time.sleep(1)  # wait all workers started
            self.assertEqual(pool.workers_count(), 10)
        self.assertEqual(pool.workers_count(), 0)

    def test_workers_pool_set_threads(self):
        with WorkersPool() as pool:
            time.sleep(1)  # wait all workers started
            self.assertEqual(pool.workers_count(), 0)
            pool.set_threads(10)
            self.assertEqual(pool.workers_count(), 10)
        self.assertEqual(pool.workers_count(), 0)

    def test_warmup_workers_pool_init(self):
        with WarmupWorkersPool(count=10, warm_up_speed=120) as pool:
            self.assertEqual(pool.workers_count(), 0)

            time.sleep(2.5)
            self.assertGreaterEqual(pool.workers_count(), 5)

            time.sleep(5)
            self.assertEqual(pool.workers_count(), 10)

        self.assertEqual(pool.workers_count(), 0)

    def test_warmup_workers_pool_set_threads(self):
        with WarmupWorkersPool(warm_up_speed=120) as pool:
            self.assertEqual(pool.workers_count(), 0)
            pool.set_threads(10)
            self.assertEqual(pool.workers_count(), 0)

            time.sleep(2.5)
            self.assertGreaterEqual(pool.workers_count(), 5)

            time.sleep(2.5)
            self.assertEqual(pool.workers_count(), 10)

        self.assertEqual(pool.workers_count(), 0)

    def test_warmup_workers_pool_stop_during_warmup(self):
        with WarmupWorkersPool(count=10, warm_up_speed=120) as pool:
            self.assertEqual(pool.workers_count(), 0)

            time.sleep(2.5)
            self.assertGreaterEqual(pool.workers_count(), 5)

        self.assertEqual(pool.workers_count(), 0)

    def test_warmup_workers_pool_decrease_threads_during_warmup(self):
        with WarmupWorkersPool(count=10, warm_up_speed=120) as pool:
            self.assertEqual(pool.workers_count(), 0)

            time.sleep(2.5)
            self.assertGreaterEqual(pool.workers_count(), 5)

            pool.set_threads(2)
            time.sleep(2)
            self.assertEqual(pool.workers_count(), 2)
        self.assertEqual(pool.workers_count(), 0)

    def test_worker_tasts(self):
        with WorkersPool() as pool:

            mock = Mock(return_value=None)

            for i in range(10):
                pool.push(mock)

            self.assertEqual(pool.workers_count(), 0)
            pool.set_threads(10)
            self.assertEqual(pool.workers_count(), 10)

            time.sleep(2)
            self.assertEqual(mock.run.call_count, 10)

        self.assertEqual(pool.workers_count(), 0)

    def test_on_worker_finished(self):
        with WorkersPool() as pool:

            lock = threading.Lock()
            count = [0]

            pool_handler = pool.on_worker_finished

            def wrapper(worker):
                pool_handler(worker)
                with lock:
                    count[0] += 1

            with patch.object(pool, 'on_worker_finished', wraps=wrapper) as mock:
                pool.set_threads(10)
                pool.stop()
                time.sleep(1)
                self.assertEqual(count[0], 10)

    def test_stop_bottom_count(self):
        with WorkersPool() as pool:
            self.assertEqual(pool.workers_count(), 0)
            pool.set_threads(10)
            self.assertEqual(pool.workers_count(), 10)

            pool.stop(bottom_count=5)
            self.assertEqual(pool.workers_count(), 5)
        self.assertEqual(pool.workers_count(), 0)

    def test_stop_warm_up_bottom_count(self):
        with WarmupWorkersPool(count=10, warm_up_speed=120) as pool:
            self.assertEqual(pool.workers_count(), 0)
            pool.set_threads(10)

            time.sleep(2.5)
            self.assertGreaterEqual(pool.workers_count(), 5)

            pool.stop(bottom_count=2)
            self.assertEqual(pool.workers_count(), 2)

        self.assertEqual(pool.workers_count(), 0)
