import json
from bl.executor.html_report import HtmlReport, BEFORE_JSON_LOG, AFTER_JSON_LOG
from unittest.mock import patch
from bl.helpers import uniq_file_name


@patch('bl.executor.html_report.HtmlReport.current_time', side_effect=['1', '2', '3', '4', '5'])
def test_level(current_time_patch):
    log_file = uniq_file_name(postfix='_unittest.html')
    report = HtmlReport()
    report.write_log(module_name='html_loger', level='INFO', message='Parent message')

    report.level_down()
    report.write_log(module_name='html_loger', level='INFO', message='Child message')

    report.level_up()
    report.write_log(module_name='html_loger', level='INFO', message='Parent message again')
    report.write_log(module_name='html_loger', level='DEBUG', message='Some\nmultiline\nmessage')

    report.save(filename=log_file,
                testcase_id='TEST-1',
                result='PASS',
                class_name='logging')

    json_log = {"testcase_id": "TEST-1", "result": "PASS", "class_name": "logging", "log": [
        {"time": "1", "msg": "Parent message", "lvl": "INFO", "module": "html_loger",
         "log": [{"time": "2", "msg": "Child message", "lvl": "INFO", "module": "html_loger"}]},
        {"time": "3", "msg": "Parent message again", "lvl": "INFO", "module": "html_loger"},
        {"time": "4", "msg": "Some", "lvl": "DEBUG", "module": "html_loger",
         "log": [{"time": "5", "msg": "multiline\nmessage", "lvl": "DEBUG", "module": "html_loger"}]}]}

    html_content = f'{BEFORE_JSON_LOG}{json.dumps(json_log)}{AFTER_JSON_LOG}'
    with open(log_file) as file:
        content = file.read()
    assert content == html_content
