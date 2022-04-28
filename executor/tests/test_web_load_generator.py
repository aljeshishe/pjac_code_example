from bl.executor.web_load_generator import WebLoadGenerator
from unittest.mock import Mock, patch
from bl.helpers import next_free_port
import logging
import os


@patch('bl.executor.web_load_generator.Settings')
@patch('bl.executor.web_load_generator.launch_memory_usage_server')
def test_web_load_generator(dowser_mock, settings_mock, caplog):
    main_loop = Mock()
    settings_mock.Sip_OutboundPstnProxy = 'google.com'
    caplog.set_level(logging.CRITICAL)
    port = next_free_port('0.0.0.0', 8000, protocol='tcp')
    caplog.set_level(logging.INFO)

    with WebLoadGenerator(main_loop=main_loop, port=port) as web_load_generator:
        assert 'Pjac web ui is waiting requests on' in caplog.messages[0]

        root_response = web_load_generator.on_root(request=None)
        assert root_response.status_code == 200
        assert root_response.buffer == []

        trace_response = web_load_generator.on_trace(request=None)
        stacktraces = trace_response.buffer[0].decode()
        assert 'STACKTRACE - START' in stacktraces
        assert os.path.abspath(__file__) in stacktraces

        request = lambda: None
        request.host = 'host:0'

        dowser_response = web_load_generator.on_dowser(request=request)
        assert dowser_response.status_code == 302
        dowser_mock.assert_called()
        assert ('Location', f'http://host:1?floor=10') in dowser_response.headers

        exit_response = web_load_generator.on_exit_cmd(request=None)
        assert exit_response.status_code == 200
        main_loop.stop.assert_called()