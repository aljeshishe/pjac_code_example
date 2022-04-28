from .cpu_monitor import CPUMonitor
from mock import patch
import pytest
import time
from bl.timer import Stopwatch

def test_overloaded():
    with patch('psutil.cpu_percent', return_value=11):
        with CPUMonitor(threshold=10) as monitor:

            stopwatch = Stopwatch()
            throttled = monitor.throttle()
            assert stopwatch.stop() == pytest.approx(1, 0.01)

            assert throttled is True

def test_acceptable_cpu():
    with patch('psutil.cpu_percent', return_value=10):
        with CPUMonitor(threshold=80) as monitor:
            stopwatch = Stopwatch()
            assert monitor.throttle() is False
            assert stopwatch.stop() == pytest.approx(0, 0.01)



def test_dynamic_change():
    with patch('psutil.cpu_percent', return_value=49) as cpu_patched:
        with CPUMonitor(threshold=50) as monitor:
            stopwatch = Stopwatch()
            assert monitor.throttle() is False
            assert stopwatch.stop() == pytest.approx(0, 0.01)

            cpu_patched.return_value = 51
            time.sleep(1) # CPU monitor renew load value every second

            stopwatch = Stopwatch()
            throttled = monitor.throttle()
            assert throttled is True

            assert stopwatch.stop() == pytest.approx(1, 0.01)