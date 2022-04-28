import datetime
import os
import sys
import unittest
import zlib
from traceback import format_exception
from urllib.parse import urljoin
from xml.sax.saxutils import escape as sax_escape

import bl.log
import requests
from bl import helpers
from bl.accountpool import AccountPoolException
from bl.assertions import Assert
from bl.assertions import PjacAssertion, LogFileFoundOnRemoteServerAssertion
from bl.context import context
from bl.helpers import correct_file_path
from bl.paths import Paths
from bl.settings import Settings
from bl.step import step
from bl.utils.ignore_exception import SuppressExceptions

from .html_report import HtmlReport

log = bl.log.getLogger(__name__)


class ReportType:
    XML = 'xml'
    HTML = 'html'


def escape(text):
    return sax_escape(text, entities={"'": '&#39;', '"': '&#34;', '\n': '&#10;'})


class Attachment:
    """
    Attachment represents files attached to test result
    """
    def __init__(self, path):
        self.path = path

    # make object hashable(so we can use it in set) with __hash__ and __eq__
    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return self.path == other

    def _prepare(self, need_attachment):
        from bl.telco.voice_file import Lame
        original_file_name = self.path
        path_base, ext = os.path.splitext(original_file_name)
        if ext.lower() == '.wav':
            if need_attachment:
                with SuppressExceptions():
                    self.path = Lame.encode(input_file_name=original_file_name)
            self.remove(original_file_name)

    def remove(self, file_name=None):
        file_name = file_name or self.path
        # we should not delete files from data dir for example
        if not file_name.startswith(Paths.artifacts()):
            return
        with SuppressExceptions():
            os.remove(file_name)

    def as_xml(self, need_attachment):
        self._prepare(need_attachment)
        if not need_attachment:
            return ''
        return '      <file name=\"%s\" path=\"%s\" type=\"%s\"/>\n' % (escape(os.path.basename(self.path)),
                                                                        escape(self.path),
                                                                        Attachment.get_type(self.path))

    @staticmethod
    def get_type(path):
        if path.endswith(".jpg"):
            return 1
        elif path.endswith(".txt"):
            return 2
        elif path.endswith(".xml"):
            return 3
        elif path.endswith(".har"):
            return 4
        elif path.endswith(".html"):
            return 5
        elif path.endswith(".png"):
            return 6
        elif path.endswith(".ini"):
            return 7
        elif path.endswith(".gzip"):
            return 8
        elif path.endswith(".pcapng"):
            return 9
        elif path.endswith(".zip"):
            return 10
        elif path.endswith(".tiff"):
            return 11
        elif path.endswith(".pdf"):
            return 12
        else:
            return 0


class ResultType:
    """
    Type of result
    """
    def __init__(self, report_format, console_format):
        self.report_format = report_format
        self.console_format = console_format


class Result:
    """
    Result of test executions
    """
    Unknown = ResultType('unknown', 'NONE')
    Error = ResultType('error', 'FAIL')
    Success = ResultType('success', 'PASS')
    Skip = ResultType('skipped', 'SKIP')
    Failure = ResultType('failure', 'FAIL')

    class Factory:

        def __init__(self, run_number):
            self.run_number = run_number

        def __call__(self):
            result = Result(run_number=self.run_number)
            return result

    def __init__(self, run_number):
        context().result = self
        self.result = Result.Unknown
        self.log = []
        self.start_time = datetime.datetime.now()
        self.stop_time = datetime.datetime.now()
        self.attachments = set()
        self.group_name = 'GROUP_NAME'
        self.exception_message = ''
        self.exception_traceback = ''
        self.failure_group_type = ''
        self.class_name = ''
        self.testcase_id = ''
        self.run_id = ''
        self.run_number = run_number
        self.arguments = {}
        self.call_ids = set()
        self.current_step = None
        self.html_report = HtmlReport()
        step(0, f'Starting test on %s[%s]' % (helpers.get_hostname(), helpers.local_ip_address()))

    def stop_report(self, result, exc_info=None):
        self.stop_time = datetime.datetime.now()
        self.result = result
        if exc_info:
            type, value, traceback = exc_info
            self.exception_message = Assert.format_exception_message(value)
            self.exception_traceback = ''.join(format_exception('', None, traceback)[:-1])
            self.failure_group_type, _, _ = self.exception_message.partition('.')

    def get_result(self):
        return self.result

    def add_log(self, id, level, message):
        self.log.append('%s [%-25.25s] %s - %s\n' % (Result.current_time(),
                                                     id,
                                                     level,
                                                     message.replace('\n',
                                                                     '\n                                                ')))

        self.html_report.write_log(module_name=id, level=level, message=message)

    @staticmethod
    def current_time():
        return datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]

    def attach(self, path):
        log.info('Attaching %s' % path)
        self.attachments.add(Attachment(path))

    def _report_file_name(self, report_type=ReportType.XML):
        directory = Paths.html_reports() if report_type == ReportType.HTML else Paths.reports()
        arguments = '_'.join(sorted(self.arguments.values()))
        return os.path.join(directory, correct_file_path('%s_%s_%s_%s.%s' %
                                                         (self.testcase_id, arguments, self.run_id, self.run_number,
                                                          report_type)))

    def create_report(self):
        saved_report = self._create_html_report()
        self._create_xml_report(saved_report.full_path)

    def _create_html_report(self):
        return self.html_report.save(filename=self._report_file_name(report_type=ReportType.HTML),
                                     test_id=self.testcase_id,
                                     arguments=['%s=%s' % (key, value) for key, value in list(self.arguments.items())],
                                     class_name=self.class_name,
                                     groups=[self.group_name],
                                     result=self.result.console_format,
                                     exception=self.exception_message,
                                     start_time=self.start_time.isoformat(timespec='microseconds'),
                                     traceback=self.exception_traceback,
                                     call_ids=list(self.call_ids),
                                     short_exception_message=self.short_exception_message)

    def _create_xml_report(self, html_attachment):
        failure_text = ''
        if self.result != Result.Success:
            failure_content = '    <%(result_type)s type=\"%(result_type)s\" message=\"%(message)s\"><![CDATA[\n%(trace_back)s]]></%(result_type)s>'
            failure_text = failure_content % dict(result_type=escape(self.result.report_format),
                                                  message=escape(self.exception_message),
                                                  trace_back=self.exception_traceback)
        properties_text = ''
        if self.arguments:
            properties_text = '<properties>%s</properties>' % ''.join(
                ['<property name="%s" value="%s"/>' % (k, v) for k, v in self.arguments.items()])

        xml_attachments = [attach.as_xml(self.need_attachment()) for attach in self.attachments]
        xml_attachments.append(Attachment(html_attachment).as_xml(need_attachment=True))
        files_text = '<files>%s</files>' % '\n'.join(xml_attachments)

        xml_template = '''<?xml version="1.0" encoding="UTF-8"?>
        <testsuite errors=\"%(errors)d\" failures=\"%(failures)d\" skipped=\"%(skipped)d\"  name=\"bl.infra.testcase.common.PjacTestSuite\" tests=\"1\" time=\"%(time)d\">
  <testcase classname=\"%(classname)s\" name=\"%(testcaseid)s\" testcaseid=\"%(testcaseid)s\" testrun=\"%(testrun)s\" timestamp=\"%(start_time)s\" time=\"%(time)s\" groups=\"%(groups)s\" run=\"%(run)s\">
    %(properties)s
    %(failure_text)s<system-out><![CDATA[\n%(log)s]]></system-out>
    <system-err><![CDATA[]]></system-err>
    %(files_text)s
  </testcase>
</testsuite>
'''
        log = ''.join(self.log)
        xml_content = xml_template % dict(errors=int(self.result == Result.Error),
                                          failures=int(self.result == Result.Failure),
                                          skipped=int(self.result == Result.Skip),
                                          time=(datetime.datetime.now() - self.start_time).total_seconds(),
                                          classname=escape(self.class_name),
                                          testcaseid=escape(self.testcase_id),
                                          testrun=escape(self.run_id),
                                          start_time=escape(self.start_time.strftime('%Y-%m-%d_%H-%M-%S')),
                                          groups=self.group_name,
                                          run=self.run_number,
                                          failure_text=failure_text,
                                          log=log,
                                          files_text=files_text,
                                          properties=properties_text)
        filename = self._report_file_name(report_type=ReportType.XML)
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(xml_content)

    def need_attachment(self):
        # If test fails store attachments. If test pass store only if Settings.attachments_in_passed is enabled
        # HTML report attachment mandatory
        return self.get_result() != Result.Success or Settings.get('attachments_in_passed', with_type=bool)

    def _remove_attachments(self):
        log.info('Removing attachments')
        if not self.need_attachment():
            for attachment in self.attachments:
                attachment.remove()

    @property
    def short_exception_message(self):
        return self.exception_message.split('\n')[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.result != Result.Unknown:
            self.stop_report(result=self.result)

        elif not exc_type:
            self.stop_report(result=Result.Success)

        elif exc_type in (LogFileFoundOnRemoteServerAssertion, unittest.SkipTest, AccountPoolException):
            self.stop_report(result=Result.Skip, exc_info=sys.exc_info())

        elif exc_type == KeyboardInterrupt:
            type, value, traceback = sys.exc_info()
            self.stop_report(result=Result.Skip,
                             exc_info=(type, KeyboardInterrupt('Execution interrupted'), traceback))

        elif exc_type == PjacAssertion:
            self.stop_report(result=Result.Failure, exc_info=sys.exc_info())
        else:
            self.stop_report(result=Result.Error, exc_info=sys.exc_info())
        self.create_report()
        self._remove_attachments()
        return True


class ServiceResult(Result):
    class Factory:
        def __init__(self, run_number):
            self.run_number = run_number

        def __call__(self):
            return ServiceResult(run_number=self.run_number)

    def _report_file_name(self, report_type=ReportType.XML):
        return '%s_%s.%s' % (self.testcase_id, self.run_id, report_type)


class StressResult(Result):
    class Factory(Result.Factory):

        def __init__(self, *args, **kwargs):
            super(StressResult.Factory, self).__init__(*args, **kwargs)
            self.stress_run_id = None

        def __call__(self):
            result = StressResult(run_number=self.run_number, stress_run_id=self.stress_run_id)
            return result

    def __init__(self, run_number, stress_run_id):
        super(StressResult, self).__init__(run_number=run_number)
        self.stress_run_id = stress_run_id

    def create_report(self):
        try:
            result = self.result.console_format.lower()
            saved_html_report = self._create_html_report()

            response = requests.post(urljoin(Settings.manager_url, '/reports'),
                                     data={'message': self.short_exception_message,
                                           'result_type': result,
                                           'run_id': self.stress_run_id,
                                           'testcase_id': self.testcase_id,
                                           'finished_time': self.stop_time.isoformat()},
                                     files=[('content', (saved_html_report.filename,
                                                         zlib.compress(saved_html_report.content.encode()),
                                                         'application/gzip'))])
            response.raise_for_status()
            saved_html_report.delete()
        except Exception as e:
            log.exception('Warning: Cant upload report %s to manager' % saved_html_report.full_path)
            log.warning('Warning: Cant upload report %s to manager)' % saved_html_report.full_path,
                        {'to_console': True})

