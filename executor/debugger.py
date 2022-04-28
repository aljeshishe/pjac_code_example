import gc
import os
import socket
import sys
import traceback
from contextlib import contextmanager
from typing import Iterator

from bl.log import getLogger
from bl.paths import Paths
from bl.settings import Settings

log = getLogger(__name__)


def start() -> None:
    """
    Starts inprocess debugger. It will connect to pycharm
    """
    if Settings.get('use_tracer', with_type=bool, default=False):
        return

    debugger = Settings.get('Debugger', default='pycharm173').lower()
    host = Settings.get('Debug_Host', default='127.0.0.1')
    port = Settings.get('Debug_Port', with_type=int, default=55555)

    _start(debugger=debugger, host=host, port=port)


def _start(debugger: str, host: str, port: int) -> None:
    def start_client_hack(host:, port):
        log_func(1, "Connecting to ", host, ":", str(port))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((host, port))
        log_func(1, "Connected.")
        return s

    if debugger in ('pycharm3', 'pycharm4', 'pycharm5', 'pycharm16', 'pycharm17', 'pycharm173', 'pycharm183'):
        debugger_addon_path = os.path.join(Paths.site_packages(), '%s-debug.egg' % debugger)
        sys.path.append(debugger_addon_path)

        import pydevd
        if debugger in ('pycharm16', 'pycharm17', 'pycharm173', 'pycharm183'):
            log_func = pydevd.pydevd_log
            pydevd.start_client = start_client_hack
        else:
            log_func = pydevd.PydevdLog
            pydevd.StartClient = start_client_hack

        try:
            pydevd.settrace(host,
                            port=port,
                            stdoutToServer=True,
                            stderrToServer=True,
                            suspend=True)
        except socket.error as e:
            msg = 'Unable to connect to debugging server: %s' % str(e)
            log.warning(msg, extra={'to_console': True})


@contextmanager
def check_interval(value) -> Iterator[None]:
    """
    Context manager for modifying sys.setcheckinterval value
    :param value: new value of check interval
    :return:
    """
    old = sys.getcheckinterval()
    log.info('Setting checkinterval[%s] old[%s]' % (value, old))
    sys.setcheckinterval(value)

    yield
    log.info('Restoring checkinterval[%s] old[%s]' % (old, value))
    sys.setcheckinterval(old)


def log_all_stacks() -> str:
    """
    Logs all stacks for all threads
    """
    with check_interval(10000):  # disable thread switching
        lines = ['*** STACKTRACE - START ***']
        for threadId, stack in list(sys._current_frames().items()):
            lines.append('\n')
            lines.append('# ThreadID: %s' % threadId)
            for filename, lineno, name, line in traceback.extract_stack(stack):
                lines.append('File: %s, line %d, in %s' % (filename, lineno, name))
                if line:
                    lines.append('  %s' % (line.strip()))
        lines.append('*** STACKTRACE - END ***')
        log.info('\n'.join(lines))
        return '<br>'.join(lines)


def log_leaks() -> None:
    """
    Collects garbage and logs warning if there were ancollcetable garbage
    """
    log.debug('Collecting garbage')
    gc.collect()
    garbage_size = len(gc.garbage)
    if garbage_size > 10:
        log.warning('WARNING: too much garbage %s' % garbage_size, extra={'to_console': True})

    if garbage_size:
        log.info('Cleaning uncollectable garbage %s' % garbage_size)
        del gc.garbage[:]
