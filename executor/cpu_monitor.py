import time
from threading import Thread

import psutil
from bl.log import getLogger
from bl.settings import Settings

log = getLogger(__name__)


class CPUMonitor:
    """
    Class for monitoring CPU loading and throttling process
    """
    def __init__(self, threshold: int = None):
        self._threshold = threshold or Settings.get('cpu_throtlng_percent', with_type=int)
        self._load = 0.0
        self.running = True

        log.info(f'Starting CPU monitoring thread with {self._threshold}% threshold')

        self.thread = Thread(target=self.monitor)
        self.thread.start()

    def monitor(self):
        while self.running:
            self._load = psutil.cpu_percent(interval=1)
            if self._load > self._threshold:
                log.debug(f'CPU overloaded ({self._load}%), waiting for an update ...')

    def throttle(self):
        """
        Return True if current CPU load < treshhold value
        """
        throttled = self._load > self._threshold
        if throttled:
            time.sleep(1)
        return throttled

    def stop(self):
        """
        Stop CPU monitoring
        """
        log.info('Stopping CPU monitoring thread')

        self.running = False
        self.thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
