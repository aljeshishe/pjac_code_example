from bl.executor.test import Test
from unittest.mock import Mock


def test_simple_test():
    testcase = Mock()
    testcase.testclass.__name__ = 'TBB-1'
    result_mock = Mock()
    result_factory = Mock()
    result_factory.return_value.__enter__ = Mock(return_value=result_mock)
    result_factory.return_value.__exit__ = Mock(return_value=result_mock)

    storage = Mock()
    storage.get = Mock(return_value=testcase)
    load_generator = Mock()
    test = Test(testcase_id='TBB-1(x=0,y="something_else")',
                result_factory=result_factory,
                storage=storage,
                load_generator=load_generator)

    arguments = dict(x='0', y='"something_else"')

    assert test.run_id == 'test-0'
    assert test.class_name == 'unknown class'
    assert test.testcase_id == 'TBB-1'
    assert test.arguments == arguments

    test.run()
    testcase.run.assert_called_with(arguments=arguments)
    test.state = 'FINISHED'

    fork_arguments = dict(arguments='value')
    test.on_fork(fork_arguments)
    load_generator.add_test.assert_called_with(testcase_id='TBB-1', arguments=fork_arguments)
    result_factory().__exit__.assert_called()


def test_not_found_write_exception():
    result_mock = Mock()
    result_factory = Mock()
    result_factory.return_value.__enter__ = Mock(return_value=result_mock)
    result_factory.return_value.__exit__ = Mock(return_value=result_mock)
    storage = Mock()
    storage.get = Mock(return_value=None)
    load_generator = Mock()
    test = Test(testcase_id='TBB-1(x=0,y="something_else")',
                result_factory=result_factory,
                storage=storage,
                load_generator=load_generator)
    test.run()
    assert result_mock.class_name == 'not found'
    assert result_mock.exception_message == 'Test not found'
    result_factory().__exit__.assert_called()
