import os
import weakref
from unittest.mock import Mock, call

import pytest
from bl.executor.local_load_generator import LocalLoadGenerator
from bl.executor.result import Result


def test_testcase_split():
    assert LocalLoadGenerator.split_tests_string('') == []
    with pytest.raises(TypeError):
        LocalLoadGenerator.split_tests_string(1)

    assert LocalLoadGenerator.split_tests_string('T-1') == ['T-1']
    assert LocalLoadGenerator.split_tests_string('T-1,T-2;T-3(x=0) T-4') == ['T-1', 'T-2', 'T-3(x=0)', 'T-4']


def test_local_load_generator():
    class TestMock(Mock):
        def __init__(self, result):
            super().__init__()
            _result = lambda: None
            _result.get_result = lambda: result
            self.result = _result

    tests = [TestMock(Result.Error), TestMock(Result.Failure), TestMock(Result.Skip), TestMock(Result.Success)]
    workers = Mock()
    main_loop = Mock()
    test_factory = Mock(side_effect=tests)
    load_generator = Mock()

    local_load_generator = LocalLoadGenerator(workers=workers,
                                              main_loop=main_loop,
                                              test_factory=test_factory,
                                              testcase_args=['T-1,T-2'],
                                              repeat_count=2,
                                              load_generator=load_generator)

    assert local_load_generator.total_count == len(tests)
    assert local_load_generator.finished_count == 0
    assert sorted(local_load_generator.testcases) == ['T-1', 'T-1', 'T-2', 'T-2']
    test_factory.assert_has_calls(
        [call(arguments=None, load_generator=weakref.proxy(local_load_generator), testcase_id='T-2'),
         call(arguments=None, load_generator=weakref.proxy(local_load_generator), testcase_id='T-2'),
         call(arguments=None, load_generator=weakref.proxy(local_load_generator), testcase_id='T-1'),
         call(arguments=None, load_generator=weakref.proxy(local_load_generator), testcase_id='T-1')],
        any_order=True)

    workers.push.assert_has_calls([call(test) for test in tests], any_order=True)
    for test in tests:
        test.on_finished(test)

    assert local_load_generator.finished_count == len(tests)
    main_loop.stop.assert_called()


@pytest.fixture
def csv_resource():
    with open('test.csv', 'w+') as file:
        file.write('T-1;T-2,T-3\n#comment\nT-4')
    pytest.csv_file = file.name
    yield
    if os.path.exists(pytest.csv_file):
        os.remove(pytest.csv_file)


def test_load_from_csv(csv_resource):
    local = LocalLoadGenerator(workers=Mock(),
                               main_loop=Mock(),
                               test_factory=Mock(),
                               testcase_args=[pytest.csv_file],
                               repeat_count=2,
                               load_generator=Mock())
    assert sorted(local.testcases) == ['T-1', 'T-1', 'T-2', 'T-2', 'T-3', 'T-3', 'T-4', 'T-4']
