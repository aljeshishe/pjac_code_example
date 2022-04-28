from bl.executor.result import Result
from unittest.mock import patch
from bl.paths import Paths
import os
from xml.etree import ElementTree as ET


@patch('bl.executor.result.Result.current_time', return_value='1')
@patch('bl.executor.result.Settings')
@patch('bl.executor.result.step')
@patch('bl.executor.result.context')
def test_result_log(current_time, context_mock, step_mock, settings_mock):
    xml_report = os.path.join(Paths.reports(), 'TBB-0___1.xml')
    html_report = os.path.join(Paths.html_reports(), 'TBB-0___1.html')

    with Result(run_number=1) as result:
        result.testcase_id = 'TBB-0'
        result.add_log(id='test', message='hello world', level='INFO')
        result.attach('test/test.mp3')

    assert os.path.exists(xml_report)
    assert os.path.exists(html_report)
    with open(xml_report) as file:
        xml_content = ET.parse(file).getroot()

    files = xml_content.find('testcase/files')
    xml_attach = files[0].attrib
    html_attach = files[1].attrib

    assert '\n1 [test                     ] INFO - hello world\n' == xml_content.find('testcase/system-out').text
    assert xml_attach['name'] == 'test.mp3'
    assert xml_attach['path'] == 'test/test.mp3'
    assert xml_attach['type'] == '0'

    assert html_attach['name'] == 'TBB-0___1.html'
    assert html_attach['path'] == html_report
    assert html_attach['type'] == '5'
