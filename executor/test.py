from bl import helpers
from bl.context import context
from bl.executor.result import Result

from bl.log import getLogger

log = getLogger(__name__)


class State:
    NOT_STARTED = 'NOT_STARTED'
    RUNNING = 'RUNNING'
    FINISHED = 'FINISHED'


class Test:

    class Factory:

        def __init__(self, storage, result_factory):
            self.storage = storage
            self.result_factory = result_factory

        def __call__(self, testcase_id, load_generator, arguments):
            return Test(testcase_id=testcase_id,
                        arguments=arguments,
                        storage=self.storage,
                        load_generator=load_generator,
                        result_factory=self.result_factory)

    _next_run_id = 0

    @staticmethod
    def get_next_run_id():
        next_run_id = Test._next_run_id
        Test._next_run_id += 1
        return 'test-%d' % next_run_id

    def __init__(self, testcase_id, storage, load_generator, result_factory, arguments=None):
        self.storage = storage
        self.load_generator = load_generator
        self.testcase_id, self.arguments = self._parse_testcase_id(testcase_id)
        self.arguments.update(arguments or {})
        self.class_name = 'unknown class'
        self.state = State.NOT_STARTED
        self.run_id = Test.get_next_run_id()
        self.on_started = lambda test: None
        self.on_finished = lambda test: None
        self.result_factory = result_factory

    def __str__(self):
        return 'Test[%s:%s]' % (self.testcase_id, self.run_id)

    def __repr__(self):
        return str(self)

    def run(self):
        self.state = State.RUNNING
        context().thread_data.test = self
        log.info('Start test %s with id %s' % (self.testcase_id, self.run_id))

        self.on_started(self)
        try:
            with self.result_factory() as result:
                testcase = self.storage.get(self.testcase_id)
                result.testcase_id = self.testcase_id
                result.run_id = self.run_id
                result.arguments = self.arguments
                if not testcase:
                    result.class_name = 'not found'
                    result.exception_message = 'Test not found'
                    result.result = Result.Skip
                    return

                result.class_name = testcase.testclass.__name__
                result.group_name = testcase.group_name()

                arguments_str = ', '.join(['%s=%s' % (k, v) for k, v in self.arguments.items()])
                if arguments_str:
                    arguments_str = '(%s)' % arguments_str
                log.info('%-9.9s:%-40.40s started%s' % (self.testcase_id, result.class_name, arguments_str), extra={'to_console': True})
                testcase.run(arguments=self.arguments)
        finally:
            self.on_finished(self)
            log.info('%-9.9s:%-40.40s %s %s/%s' % (self.testcase_id,
                                                   result.class_name,
                                                   result.get_result().console_format,
                                                   self.load_generator.finished_count or '?',
                                                   self.load_generator.total_count or '?'),
                     extra={'to_console': True})
            self.state = State.FINISHED
            context().thread_data.test = None

    def on_fork(self, arguments):
        self.load_generator.add_test(testcase_id=self.testcase_id, arguments=arguments)

    @staticmethod
    @helpers.describe('Parse testcase id')
    def _parse_testcase_id(testcase_id):
        # 'TBB-38370(ibo_country=FRA, l10n=US)' -> ('TBB-38370', dict(ibo_country=FRA, l10n=US))
        arguments = {}
        id, parenthis, arguments_str = testcase_id.partition('(')
        if arguments_str:
            arguments_str = arguments_str[:-1]  # remove last (
            for key_value in arguments_str.split(','):
                key, value = key_value.split('=')
                arguments[key.strip(' ')] = value.strip(' ')
        return id, arguments
