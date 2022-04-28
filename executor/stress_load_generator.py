from bl.executor.load_generator import LoadGenerator
from bl.executor.stresser import Stresser
from bl.log import getLogger
from wheezy.http import json_response
from wheezy.routing import url

log = getLogger(__name__)


class StressLoadGenerator(LoadGenerator):
    """
    StressLoadGenerator implements logic for stress mode
    """
    def __init__(self, test_factory, workers, load_generator):
        super(StressLoadGenerator, self).__init__()
        self.load_generator = load_generator
        self.stresser = Stresser(test_factory=test_factory, workers=workers)
        self.load_generator.path_router.add_routes([url('run_tests', self._run_tests),
                                                    url('set_threads', self._set_threads),
                                                    url('get_status', self._get_status)])

    def _run_tests(self, request):
        log.info('ServiceLoadGenerator._run_tests: %s' % request)

        run_id = request.form['run_id']
        threads = request.form['threads']
        tests = request.form['testcases']
        testcases_percents = [(test['id'], test['percent']) for test in tests]
        self.stresser.run_tests(run_id=run_id, testcases_percents=testcases_percents, threads=threads)
        return json_response(dict(result='ok'))

    def _set_threads(self, request):
        log.info('ServiceLoadGenerator._set_threads: %s' % request)

        self.stresser.set_threads(request.form['threads'])
        return json_response(dict(result='ok'))

    def _stop_tests(self, request):
        log.info('ServiceLoadGenerator._stop_tests: %s' % request)
        self.stresser.stop_tests()
        return json_response(dict(result='ok'))

    def _get_status(self, request):
        log.info('ServiceLoadGenerator._get_status: %s' % request)
        status, run_seconds, threads = self.stresser.get_status()
        return json_response(dict(result='ok',
                                  status=status,
                                  run_seconds=run_seconds,
                                  threads=threads))
