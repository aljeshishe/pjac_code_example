import weakref
from importlib import import_module
from urllib.parse import urljoin

from bl.executor.load_generator import LoadGenerator
from bl.executor.result import ReportType
from bl.executor.test import State
from bl.log import getLogger
from wheezy.core.json import json_encode
from wheezy.http import HTTPResponse
from wheezy.routing import url

log = getLogger(__name__)


def instantiate(classname, parameters):
    """
    Method for creation class object by classname
    :param classname: fullname of class (for example: bl.phone_numbers.PstnNumber)
    :param parameters: dict parameters for object
    :return: Initialized object with parameters
    """
    from_, import_ = classname.rsplit('.', 1)
    class_ = getattr(import_module(from_), import_)
    return class_(**parameters)


def create_response(data, status_code):
    response = HTTPResponse('application/json; charset=UTF-8')
    response.status_code = status_code
    response.write(json_encode(data))
    return response


class ServiceLoadGenerator(LoadGenerator):
    """
    ServiceLoadGenerator generates load for service mode
    """
    def __init__(self, test_factory, workers, load_generator):
        super(ServiceLoadGenerator, self).__init__()
        self.workers = workers
        self.test_factory = test_factory
        self.load_generator = load_generator
        self.running_tests = {}
        self.load_generator.path_router.add_routes([url('actions', self.on_post_action),
                                                    url('actions/{action_id}', self.on_get_action),
                                                    url('actions/{action_id}/report', self.on_get_action_report)])

    def on_get_action_report(self, request):
        run_id = request.environ['route_args'].action_id
        test = self.running_tests.get(run_id)
        filename = test.result._report_file_name(report_type=ReportType.XML)
        with open(filename, 'r', encoding='utf-8') as file:
            response = HTTPResponse('text/xml; charset=UTF-8')
            response.write(file.read())
        return response

    def on_post_action(self, request):
        log.info('ServiceLoadGenerator.on_post_action: %s' % request)
        testcase_id = request.form.get('testcase_id')
        arguments = {}

        for argument_name, pjac_object in request.form.get('args', {}).items():
            classname, parameters = pjac_object.popitem()
            arguments[argument_name] = instantiate(classname, parameters)

        if not testcase_id:
            return create_response(data=dict(result='ERROR',
                                             error_description='No testcase_id parameter'),
                                   status_code=400)

        log.info('New test %s args[%s]' % (testcase_id, arguments))
        test = self.test_factory(testcase_id=testcase_id, arguments=arguments, load_generator=weakref.proxy(self))
        self.workers.push(test)
        self.running_tests[test.run_id] = test
        return create_response(data=dict(result='OK',
                                         status_url=urljoin(self.load_generator.address, 'actions/%s' % test.run_id),
                                         report_url=urljoin(self.load_generator.address, 'actions/%s/report' % test.run_id)),
                               status_code=201)

    def on_get_action(self, request):
        log.info('ServiceLoadGenerator.on_get_action: %s' % request)
        run_id = request.environ['route_args'].action_id
        if not run_id:
            return create_response(data=dict(result='ERROR',
                                             error_description='No action_id parameter'),
                                   status_code=400)

        test = self.running_tests.get(run_id)
        if not test:
            return create_response(data=dict(result='ERROR',
                                             error_description='Action not found'),
                                   status_code=404)

        if test.state == State.NOT_STARTED:
            return create_response(data=dict(result='OK',
                                             status='NOT_STARTED'),
                                   status_code=200)

        if test.state == State.RUNNING:
            return create_response(data=dict(status='RUNNING',
                                             result='OK',
                                             current_step_number=test.result.current_step.number,
                                             current_step_description=test.result.current_step.description),
                                   status_code=200)

        if test.state == State.FINISHED:
            return create_response(data=dict(result='OK',
                                             status=test.result.result.console_format),
                                   status_code=200)

    @property
    def total_count(self):
        return None

    @property
    def finished_count(self):
        return None


