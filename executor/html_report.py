import datetime
import json
from os import remove, path

from .html_parts import *


class SavedReport:
    """
    Storing info about saved html report
    """

    def __init__(self, full_path):
        self.full_path = full_path

    @property
    def filename(self):
        return path.basename(self.full_path)

    @property
    def content(self):
        with open(self.full_path) as file:
            return file.read()

    def delete(self):
        remove(self.full_path)


class HtmlReport:
    """
    Class for creating HTML reports
    """

    def __init__(self):
        self.log = []
        self.levels = []
        self.cursor = self.log
        self.levels.append(self.cursor)

    def write_log(self, module_name, level, message):
        """
        Write line to html file
        :param module_name: name related to class or file
        :param level: logging level
        :param message: log_message
        """
        messages = message.split('\n')
        if len(messages) > 1:
            self._write(module_name, level, messages[0])
            self.level_down()
            self._write(module_name, level, '\n'.join(messages[1:]))
            self.level_up()
        else:
            self._write(module_name, level, message)

    def _write(self, module_name, level, message):
        self.cursor.append(dict(time=HtmlReport.current_time(),
                                msg=message,
                                lvl=level,
                                module=module_name))

    @staticmethod
    def current_time():
        return datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]

    def level_up(self):
        """
        Close current level and up
        """
        if len(self.levels) > 1:
            self.cursor = self.levels.pop()

    def level_down(self):
        """
        Create new log level
        """
        if 'log' not in self.cursor[-1]:
            self.cursor[-1]['log'] = []

        self.levels.append(self.cursor)
        self.cursor = self.cursor[-1]['log']

    def save(self, filename, **kwargs):
        """
        Append required testcase params and dump to file file
        :param filename: path to store HTML report
        :param testcase_id: Testcase id
        :param result: status of test
        :param class_name: Python class of test
        :param groups: Directories, where test located
        :param arguments: run args
        :param exception: Exception message (if exist)
        :param traceback: Traceback of exception (if exist)
        """
        with open(filename, 'w') as file:
            file.write(BEFORE_JSON_LOG)
            kwargs['log'] = self.log
            file.write(json.dumps(kwargs))
            file.write(AFTER_JSON_LOG)
        return SavedReport(filename)
