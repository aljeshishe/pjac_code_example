import errno
import time

import bl.log

log = bl.log.getLogger(__name__)


class MainLoop:
    """
    Mainloop is helper class. It simply blocks execution of main
        thread until Ctrl+C is pressed or stop is called
    """
    def __init__(self):
        self.running = True

    def run(self):
        # this method shouldn't raise anything. In any case it should just exit
        while self.running:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                log.info('Ctrl+C was pressed', extra={'to_console': True})
                break
            except IOError as e:
                if e.errno == errno.EINTR:  # after Ctrl+C sometimes IOError[4] is raised. We ignore it because
                    continue                # KeyboardInterrupt will arrive anyway. So better catch it here, not somewhere else
            except Exception as e:
                log.exception('Unexpected exception in mainloop', extra={'to_console': True})
                break
        log.info('Mainloop stopped')

    def stop(self):
        log.info('Stopping mainloop')
        self.running = False
