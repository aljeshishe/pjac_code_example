import pytest
from bl.executor.arguments import parse
from bl.assertions import PjacError


def test_params(caplog):
    params, _ = parse(args=['-n', 'dev-aut-ams',
                            'call_op_to_op',
                            '--run=1',
                            '-w', '30',
                            '-s', 'test.ini',
                            '-c',
                            '-b', 'tester',
                            '-o', 'some_path',
                            '-r', '20',
                            '-P', 'SipProxy=126', 'trace_enable=False', 'SomeInvalidResource'])
    assert params.environment == 'dev-aut-ams'
    assert params.testcases == ['call_op_to_op']
    assert params.run == '1'
    assert params.work_threads == 30
    assert params.setting == 'test.ini'
    assert params.service_mode == 0
    assert params.trace_enable is False
    assert params.workspace == 'some_path'
    assert params.subset == 'tester'
    assert params.help is False
    assert params.param == dict(SipProxy='126', trace_enable='False')
    assert caplog.messages[0] == 'Ignoring resource parameter "SomeInvalidResource" (valid format: -P Parameter=Value)'


@pytest.mark.parametrize('param,value,exception_message',
                         [('-r', '-1', 'Repeat count greater then 0'),
                          ('-w', '0', 'Work threads greater then 0')])
def test_invalid_args(param, value, exception_message):
    with pytest.raises(PjacError) as error:
        params, _ = parse(args=['call_op_to_op', param, value])

    assert error.value.message == exception_message

