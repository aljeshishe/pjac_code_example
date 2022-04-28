import argparse
import socket

from bl.assertions import Assert, PjacError
from bl.log import getLogger
from bl.paths import Paths

log = getLogger(__name__)


def parse(args=None):
    """
    Parse arguments related to testcase run
    :return: arguments
    """
    parser = argparse.ArgumentParser(prog='run.py',
                                     add_help=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description='Example: run.py -n dev-aut-50x TBB-12345',
                                     epilog='''Usage examples:
- Run single test
    python run.py -n DEV-AUT-AMS TBB-8445
- Run multiple tests
    python run.py -n DEV-AUT-AMS TBB-8445 TBB-12999 TBB-13002
- Run multiple tests from file
    python run.py -n DEV-AUT-AMS sets\smoke.csv sets\p0.csv
- Run stress tests (140 threads)
    python run.py --work_threads=140 --stress-settings=sets/stress.conf -s resources/DEV-TEL-SV7.ini --subset telco-stress --release-dirty 0 --reuse-accounts 1
- Run service mode
    python run.py --service-mode -s resources\DEV-AUT-AMS.ini

Home page: https://wiki.ringcentral.com/display/ARC/PJAC+Framework
Skype: alexey.grachev
Glip: Alexey Grachev''')
    # parser.add_argument('--service-mode', action='store_true', default=False, help='service mode - stay alive to execute tests requested via HTTP interface till exit command is received')
    parser.add_argument('--service-mode', default=0, help='service mode - stay alive to execute tests requested via HTTP interface till exit command is received')
    parser.add_argument('-s', '--setting', default='', help='settings file')
    parser.add_argument('-w', '--work_threads', default=10, type=int, help='number of threads to run tests')
    parser.add_argument('-t', '--trace_enable', action='store_true', help='Use collete tracer for call flow in reports')
    parser.add_argument('-r', '--repeat', default=1, type=int, help='how much times repeat tests')
    parser.add_argument('-o', '--workspace', default=Paths.pjac_fw(), help='output directory for run(downloads, screenshots, reports, logs)')
    parser.add_argument('-n', '--environment', default='', help='environment name. Specify pod unit if needed (e.g. gci-aqa-ams unit 1 pod 2). If not specified unit 1 pod 1 is used.')
    parser.add_argument('-b', '--subset', default=socket.gethostname(), help='Subset where to get accoount(usefull, if you generate account manually)')
    parser.add_argument('-c', '--release_clean', action='store_true', default=False, help='accounts are release as CLEAN and could be reused')
    parser.add_argument('-u', '--run', default=1, help='Run number(only for report)')
    parser.add_argument('-h', '--help', action='store_true', help='show this help message and exit')
    parser.add_argument('-P', '--param', nargs='*', default='', help='Additional resources parameters(no spaces allowed). Example: -P Sip_Proxy=sip.lab.nordigy.ru Connector_StartWaveRecording=0')
    parser.add_argument('testcases', nargs='*', default='', help='testcase ids or CSV files with testcases')
    args = parser.parse_args(args)
    args.param = _parse_overrides(args.param)
    log.info('Parsed arguments: %s' % args)

    Assert.greater(args.repeat, 0, PjacError('Repeat count greater then 0', verbose=False))
    Assert.greater(args.work_threads, 0, PjacError('Work threads greater then 0', verbose=False))

    return args, parser


def _parse_overrides(overrides):
    overrides_dict = dict()
    if overrides:
        for param_str in overrides:
            key, eq_char, value = param_str.partition('=')
            if key and value:
                overrides_dict[key] = value
            else:
                log.warning('Ignoring resource parameter "%s" (valid format: -P Parameter=Value)'
                            % param_str, extra={'to_console': True})
    return overrides_dict
