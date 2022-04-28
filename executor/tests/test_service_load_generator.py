from bl.executor.service_load_generator import StressLoadGenerator
from unittest.mock import Mock, patch


@patch('bl.executor.service_load_generator.Stresser')
def test_service_load_generator(stresser_mock):
    test_factory = Mock()
    workers = Mock()
    load_generator = Mock()
    service_load = StressLoadGenerator(test_factory=test_factory, workers=workers, load_generator=load_generator)

    run_response = service_load._run_tests(create_request({
        'run_id': 1,
        'threads': 20,
        'testcases': [{'id': 'TBB-1', 'percent': 10},
                      {'id': 'TBB-2', 'percent': 40},
                      {'id': 'TBB-3', 'percent': 50}]
    }))
    assert run_response.status_code == 200
    assert run_response.buffer[0].decode() == '{"result":"ok"}'
    stresser_mock.return_value.run_tests.assert_called_with(run_id=1,
                                                            testcases_percents=[('TBB-1', 10),
                                                                                ('TBB-2', 40),
                                                                                ('TBB-3', 50)],
                                                            threads=20)

    set_threads_response = service_load._set_threads(create_request(dict(threads=30)))
    assert set_threads_response.status_code == 200
    assert set_threads_response.buffer[0].decode() == '{"result":"ok"}'
    stresser_mock.return_value.set_threads.assert_called_with(30)

    set_threads_response = service_load._stop_tests(create_request())
    assert set_threads_response.status_code == 200
    assert set_threads_response.buffer[0].decode() == '{"result":"ok"}'
    stresser_mock.return_value.stop_tests.assert_called()

    stresser_mock.return_value.get_status.return_value = ('Running', 123, 20)
    get_status_response = service_load._get_status(create_request())
    assert get_status_response.status_code == 200
    assert get_status_response.buffer[0].decode() == '{"result":"ok","status":"Running","run_seconds":123,"threads":20}'


def create_request(body={}):
    run_request = Mock()
    run_request.form = body
    return run_request
