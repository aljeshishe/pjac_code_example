from bl.executor.stresser import Stresser, Status
from mock import Mock, patch
import pytest


@patch('bl.executor.stresser.Stresser.add_test')
def test_percent_regular(add_test_mock):
    run_count = 10000
    stresser = Stresser(test_factory=Mock(), workers=Mock())
    stresser.run_tests(run_id=1, testcases_percents=[('TBB-1', 10), ('TBB-2', 20), ('TBB-3', 70)], threads=run_count)

    tbb_1_add_tests = len([add_test for add_test in add_test_mock.mock_calls if add_test[2] == dict(testcase_id='TBB-1')])
    tbb_2_add_tests = len([add_test for add_test in add_test_mock.mock_calls if add_test[2] == dict(testcase_id='TBB-2')])
    tbb_3_add_tests = len([add_test for add_test in add_test_mock.mock_calls if add_test[2] == dict(testcase_id='TBB-3')])

    assert tbb_1_add_tests / run_count == pytest.approx(0.1, abs=0.02)
    assert tbb_2_add_tests / run_count == pytest.approx(0.2, abs=0.02)
    assert tbb_3_add_tests / run_count == pytest.approx(0.7, abs=0.02)


def test_percent_zero():
    stresser = Stresser(test_factory=Mock(), workers=Mock())
    stresser.testcases_percents = [('TBB-1', 0), ('TBB-2', 100)]
    assert stresser.get_next_testcase_id() == 'TBB-2'


def test_percent_all_zeroes():
    stresser = Stresser(test_factory=Mock(), workers=Mock())
    stresser.testcases_percents = [('TBB-1', 0), ('TBB-2', 0)]
    assert stresser.get_next_testcase_id() is None


def test_run_stop_tests():
    thread_count = 3
    worker_mock = Mock()
    stresser = Stresser(test_factory=Mock(), workers=worker_mock)
    stresser.run_tests(run_id=1, testcases_percents=[('TBB-1', 10), ('TBB-2', 20), ('TBB-3', 70)], threads=thread_count)
    worker_mock.set_threads.assert_called_with(thread_count)
    assert len(worker_mock.push.mock_calls) == 3

    status, run_seconds, workers_count = stresser.get_status()
    assert status == Status.RUNNING
    assert run_seconds == pytest.approx(0, abs=0.01)
    assert workers_count == worker_mock.workers_count()

    stresser.stop_tests()
    worker_mock.reset.assert_called_with()


