from os.path import join
from versions import MATURITY_PROD, MATURITY_WORK
from versions import Config, Redirector
from versions import default_version, get_epics_versions, get_dependencies, get_support_module_list
from gem_versions import command_line_arguments
from gem_versions import print_active_ioc_summary, print_ioc_dependencies, print_support_module_dependencies


def print_separator(text):
    print '\n' + '-' * 3 + ' ' + text + ' ' + '-' * 40


def test_command_line(argv):
    args = command_line_arguments(argv)
    print args


def test_config():
    print_separator('test_config')
    for directory in (Config.ROOT_DIR_CP, Config.ROOT_DIR_MK):
        Config.set_root_directory(directory)
        print 'redirector dir', Config.redirector_dir()
        print 'prod dir', Config.prod_dir()
        print 'work dir', Config.work_dir()
        print 'mat_dir prod', Config.maturity_directory(MATURITY_PROD)
        print 'mat_dir work', Config.maturity_directory(MATURITY_WORK)


def test_default_version():
    print_separator('test_default_version')
    print 'default_version, 1.0', default_version('1.0', MATURITY_PROD)
    print 'default_version, empty', default_version('test', MATURITY_WORK)


def test_epics_versions():
    print_separator('test_epics_versions')
    print 'get_epics_versions, prod', get_epics_versions(MATURITY_PROD)
    print 'get_epics_versions, work', get_epics_versions(MATURITY_WORK)


def test_module_list():
    print_separator('test_module_list')
    print 'get_support_module_list', get_support_module_list('R3.14.12.6', MATURITY_PROD)
    print 'get_support_module_list', get_support_module_list('R3.14.12.4', MATURITY_WORK)


def test_get_dependencies():
    print_separator('test_get_dependencies')

    release_file = join(Config.root_dir, 'prod/R3.14.12.6/ioc/mcs/cp/1-2-BR314/configure/RELEASE')
    print 'get_dependencies', \
        get_dependencies(release_file,
                         get_support_module_list('R3.14.12.6', MATURITY_PROD),
                         get_support_module_list('R3.14.12.6', MATURITY_WORK))

    release_file = join(Config.root_dir, 'prod/R3.14.12.6/support/iocStats/3-1-14-3-BR314/configure/RELEASE')
    print 'get_dependencies', \
        get_dependencies(release_file,
                         get_support_module_list('R3.14.12.6', MATURITY_PROD),
                         get_support_module_list('R3.14.12.6', MATURITY_WORK))


def test_redirector():
    print_separator('test_redirector')
    print Redirector()
    print Redirector([])

    rd = Redirector()
    print 'get_ioc_names', rd.get_ioc_names()
    print 'get_ioc_list', rd.get_ioc_list()
    print 'get_ioc', rd.get_ioc('mcs-cp-ioc')


def test_ioc():

    pass


def test_support_module():
    pass


def test_print_summary():
    for directory in [Config.ROOT_DIR_CP, Config.ROOT_DIR_MK]:

        Config.set_root_directory(directory)

        print_separator('test_print_summary, no links, no exclude ' + directory)
        args = command_line_arguments([])
        print_active_ioc_summary(args)

        print_separator('test_print_summary, no links, exclude lab/sim ' + directory)
        args = command_line_arguments(['-x', 'lab', 'sim'])
        print_active_ioc_summary(args)

        print_separator('test_print_summary, links ' + directory)
        args = command_line_arguments(['-l'])
        print_active_ioc_summary(args)


def test_print_ioc_dependencies():

    Config.set_root_directory(Config.ROOT_DIR_CP)

    print_separator('test_print_ioc_dependencies, production')
    args = command_line_arguments(['-i', 'mcs-cp-ioc'])
    print_ioc_dependencies(args)

    print_separator('test_print_ioc_dependencies, lab')
    args = command_line_arguments(['-i', 'labcp1-cp-ioc'])
    print_ioc_dependencies(args)


def test_print_support_module_dependencies():

    Config.set_root_directory(Config.ROOT_DIR_CP)

    print_separator('test_print_support_module_dependencies, no epics')
    args = command_line_arguments(['whoami'])
    print_support_module_dependencies(args)

    print_separator('test_print_support_module_dependencies, epics R3.14.12.6-1')
    args = command_line_arguments(['iocStats', '-e', 'R3.14.12.6-1'])
    print_support_module_dependencies(args)


if __name__ == '__main__':
    Config.root_dir = './gem_sw_cp_2'
    # test_command_line(['-h'])
    # test_config()
    # test_get_dependencies()
    test_redirector()
    # test_default_version()
    # test_epics_versions()
    # test_get_dependencies()

    # test_print_summary()
    # test_print_ioc_dependencies()
    # test_print_support_module_dependencies()
