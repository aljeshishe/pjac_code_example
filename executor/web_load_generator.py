import warnings
from multiprocessing.pool import ThreadPool
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

from bl import helpers
from bl.executor import debugger
from bl.executor.load_generator import LoadGenerator
from bl.log import getLogger
from bl.settings import Settings
from wheezy.http import HTTPResponse, redirect
from wheezy.http import WSGIApplication
from wheezy.routing import url, PathRouter
from wheezy.web.middleware import bootstrap_defaults
from wheezy.web.middleware import path_routing_middleware_factory

log = getLogger(__name__)


class ServerWithIncreasedConnections(WSGIServer):
    request_queue_size = 100


class MyWSGIRequestHandler(WSGIRequestHandler):

    def log_message(self, format, *args):
        log.info('%s - - [%s] %s' % (self.client_address[0],
                                     self.log_date_time_string(),
                                     format % args), extra={'to_console': False})


class MyPathRouter(PathRouter):

    def match(self, path):
        handler, kwargs = super(MyPathRouter, self).match(path)
        log.info('Calling handler: %s with %s' % (handler, kwargs))
        return handler, kwargs


def launch_memory_usage_server(port=8080, show_trace=False):
    import cherrypy
    from dowser import Root
    config = {}
    config['global'] = {
        'environment': 'embedded',
        'server.socket_port': port,
        'server.socket_host': '0.0.0.0'
    }
    if show_trace:
        config['global']['request.show_tracebacks'] = True
    cherrypy.tree.mount(Root())
    cherrypy.config.update(config)
    cherrypy.engine.start()


class WebLoadGenerator(LoadGenerator):
    """
    WebLoadGenerator implements helper handers like / trace/ dowser/ terminate/
    """
    def __init__(self, main_loop, port):
        super(WebLoadGenerator, self).__init__()
        self.main_loop = main_loop
        self.running_tests = {}
        self.thread_pool = ThreadPool(10)
        self.path_router = MyPathRouter()

        self.path_router.add_routes([url('', self.on_root),
                                     url('trace', self.on_trace),
                                     url('dowser', self.on_dowser),
                                     url('terminate', self.on_exit_cmd)])

        from wheezy.security.crypto import Ticket
        from wheezy.web import templates
        from wheezy.security.crypto.comp import sha1
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ticket = Ticket(digestmod=sha1)
        options = dict(path_router=self.path_router,
                       render_template=templates.MakoTemplate,
                       ticket=ticket)
        main = WSGIApplication(middleware=[bootstrap_defaults(), path_routing_middleware_factory], options=options)
        self.server = make_server('', port, main, server_class=ServerWithIncreasedConnections, handler_class=MyWSGIRequestHandler)
        host = helpers.local_ip_address(Settings.Sip_OutboundPstnProxy)
        self.address = 'http://%s:%s' % (host, self.server.server_port)
        self.start()

    def start(self):
        log.info(f'Pjac web ui is waiting requests on {self.address}', extra={'to_console': True})
        self.thread_pool.apply_async(self.server.serve_forever)

    def stop(self):
        log.info('Stopping pjac web ui ')
        self.thread_pool.apply_async(self.server.shutdown)
        self.thread_pool.close()
        self.thread_pool.join()
        log.info('Pjac web ui stopped')

    def on_trace(self, request):
        response = HTTPResponse()
        response.write(debugger.log_all_stacks())
        return response

    def on_root(self, request):
        return HTTPResponse()

    def on_dowser(self, request):
        host,_ , port = request.host.partition(':')
        port = helpers.next_free_port('0.0.0.0', int(Settings.Port), protocol='tcp')
        address = f'http://{host}:{port}?floor=10'
        log.info(f'Starting dowser at {address}')
        launch_memory_usage_server(port=port, show_trace=True)
        return redirect(address)

    def on_exit_cmd(self, request):
        log.info('WebLoadGenerator.on_exit_cmd: %s' % request)
        log.info('Terminate request received', extra={'to_console': True})
        self.main_loop.stop()
        return HTTPResponse()

    @property
    def total_count(self):
        return None

    @property
    def finished_count(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
