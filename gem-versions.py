#!/usr/bin/python
import sys
from argparse import ArgumentParser, SUPPRESS, Namespace
from os.path import isdir

from versions import Redirector, IOC, SupportModule, Config
from versions import AREA_LIST, AREA_SUPPORT, AREA_IOC, EPICS_ALL
from versions import default_ioc_version
from versions import skip_name, skip_exclude, skip_epics
from versions import fmt_list


def print_active_ioc_summary(exclude_list, epics_version_list, print_links, csv_output):
    """
    Print version information for all ioc's in the redirector directory.
    There "links" output is the same as the 'configure-ioc -L' output.
    :param exclude_list: list of ioc's (substrings) to exclude from the list
    :type exclude_list: list
    :param epics_version_list: list of epics versions to show in the output
    :param print_links: print links instead of formatted table (same as configure-ioc -L)
    :type print_links: bool
    param csv_output: csv output?
    :type csv_output: bool
    :return None
    """
    rd = Redirector()
    len_max = len(max(rd.get_ioc_names(), key=len))  # for formatting
    for ioc in rd.get_ioc_list():
        assert (isinstance(ioc, IOC))
        if skip_exclude(ioc.name, exclude_list) or skip_epics(ioc.epics, epics_version_list):
            continue
        if print_links:
            # print format_string_links.format(ioc.name, ioc.link)
            print fmt_list([ioc.name, ioc.link], [len_max, None], csv_output)
        else:
            # print format_string_details.format(ioc.name, ioc.maturity, ioc.epics, ioc.bsp, ioc.version, ioc.boot)
            print fmt_list([ioc.name, ioc.maturity, ioc.epics, ioc.bsp, ioc.version, ioc.boot],
                           [len_max, 5, 14, 15, 13, None], csv_output)


def print_active_ioc_dependencies(ioc_name_list, exclude_list, epics_version_list):
    """
    Print the dependency information of ioc's in the redirector directory.
    For each ioc, it prints the ioc version, EPICS version and EPICS BSP for the ioc,
    and the list of support modules that the ioc depends on.
    :param ioc_name_list: list of strings ioc names to include in the output
    :type ioc_name_list: list
    :param exclude_list: list of strings in ioc names to exclude from the output
    :type exclude_list: list
    :param epics_version_list: list of strings to match against ioc EPICS versions
    :type epics_version_list: list
    :return None
    """
    rd = Redirector()
    for ioc in rd.get_ioc_list():
        # print ioc
        assert (isinstance(ioc, IOC))
        if skip_name(ioc.name, ioc_name_list) or \
                skip_exclude(ioc.name, exclude_list) or \
                skip_epics(ioc.epics, epics_version_list):
            continue
        print '{} {} {} {} {}'.format(ioc.name, default_ioc_version(ioc.version, ioc.maturity),
                                           ioc.boot, ioc.epics, ioc.bsp)
        for support_module in ioc.get_ioc_dependencies():
            print '   {:16} {}'.format(support_module.name, support_module.version)
        print


def print_active_support_module_dependencies(support_name_list, exclude_list, epics_version_list):
    """
    Print the support module dependencies that are used by one or more ioc's.
    The report includes dependencies with other support modules and the ioc's that depend on them.
    :param support_name_list: list of strings to match against support module names
    :type support_name_list: list
    :param exclude_list: list of items to exclude (no regular expressions)
    :type exclude_list: list
    :param epics_version_list: list of strings to match against support module EPICS versions
    :type epics_version_list: list
    :return None
    """
    # print 'print_support_module_dependencies', support_module_name

    # The ioc dictionary is used to create a cross reference between support modules and ioc objects.
    # Each entry is indexed by the support module id and contains the list of ioc's using the support module.
    # Repeated dependencies are prevented by not appending them to the list.
    ioc_dict = {}

    # The support module dictionary is used to map support module id's with SupportModule objects.
    # Repeated dependencies will be discarded.
    sup_dict = {}

    # Populate the two dictionaries. We loop over all the ioc's in the redirector directory
    # and then iterate over the dependencies for each ioc.
    rd = Redirector()
    for ioc in rd.get_ioc_list():
        if skip_exclude(ioc.name, exclude_list) or skip_epics(ioc.epics, epics_version_list):
            continue
        for sup in ioc.get_ioc_dependencies():
            sup_dict[sup.id] = sup  # repeated entries are discarded at this point
            assert (isinstance(sup, SupportModule))
            # print '  ', sup
            if skip_name(sup.name, support_name_list):
                continue
            if sup.id in ioc_dict:
                ioc_dict[sup.id].append(ioc)
            else:
                ioc_dict[sup.id] = [ioc]

    # Check whether there are any ioc's that depend of the support module we are looking for.
    # An empty dictionary means either that no ioc's depend on the support module, or that
    # the support module doesn't exist at all.
    if ioc_dict:
        # Print the support module dependencies first, followed by the ioc's that use the support module
        for sup_id in sorted(ioc_dict):
            sup = sup_dict[sup_id]
            # print '--', sup
            assert (isinstance(sup, SupportModule))
            print sup.name, sup.version, sup.epics
            # print support module dependencies
            for dep in sup.get_support_module_dependencies():
                assert (isinstance(dep, SupportModule))
                print '   {:16} {:16} {}'.format(dep.name, default_ioc_version(dep.version, dep.maturity), dep.epics)
            # print ioc's that depend on the support module
            for ioc in ioc_dict[sup_id]:
                assert (isinstance(ioc, IOC))
                print '   {:16} {:16} {}'.format(ioc.name, default_ioc_version(ioc.version, ioc.maturity), ioc.epics)
            print
    else:
        print 'support module(s) \'' + str(support_name_list) + '\'' + \
              ' does not exist or is not used by any ioc\'s in the redirector directory'


def command_line_arguments(argv):
    """
    Process command line arguments
    :param argv: command line arguments from sys.argv[1:]
    :type argv: list
    :return: argparse Namespace
    :rtype: Namespace
    """

    # Define text that will be printed at the end of the '-h' option
    epilog_text = """Print ioc version information of ioc\'s that are listed in the redirector directory.""" \
                  """ It is also possible to get information about active support modules.""" \
                  """ If no arguments are supplied, the versions of all ioc's in the """ + \
                  """ redirector directory will be printed."""

    parser = ArgumentParser(epilog=epilog_text)

    parser.add_argument(action='store',
                        nargs='*',
                        dest='name',
                        default=[],
                        help='ioc or support module name(s)')

    parser.add_argument('-l', '--links',
                        action='store_true',
                        dest='links',
                        default=False,
                        help='print raw links (same output as configure-ioc -L)')

    parser.add_argument('-a', '--area',
                        action='store',
                        nargs=1,
                        dest='area',
                        choices=AREA_LIST,
                        default=AREA_SUPPORT,
                        help='set <area> to \'' + AREA_SUPPORT + '\' or \'' + AREA_IOC +
                             '\' [default=' + AREA_SUPPORT + ']')

    parser.add_argument('-i', '--ioc',
                        action='store_const',
                        dest='area',
                        const=AREA_IOC,
                        help='set <area>=' + AREA_IOC)

    parser.add_argument('-x', '--exclude',
                        action='store',
                        nargs='+',
                        dest='exclude',
                        default=[],
                        help='exclude matching ioc\'s from the output')

    parser.add_argument('-e', '--epics',
                        action='store',
                        nargs='*',
                        dest='epics',
                        default=[],
                        help='Restrict output to EPICS version(s) (\'' + EPICS_ALL + '\' for all versions)')

    parser.add_argument('--csv',
                        action='store_true',
                        dest='csv',
                        default=False,
                        help='print output in csv format')

    parser.add_argument('-t', '--test',
                        action='store',
                        nargs=1,
                        dest='test',
                        default=[],
                        help=SUPPRESS)

    return parser.parse_args(argv)


if __name__ == '__main__':

    # Test code
    # test_dir = '/Users/pgigoux/PycharmProjects/ade/gem_sw_cp_2'
    # args = command_line_arguments(['-h'])
    # args = command_line_arguments(['-t', test_dir])
    # args = command_line_arguments(['-t', test_dir, '--csv'])
    # args = command_line_arguments(['-t', test_dir, '-l', '--csv'])
    # args = command_line_arguments(['-t', test_dir, '-i', 'tcs', 'mcs'])
    # args = command_line_arguments(['-t', test_dir, 'slalib', 'timelib', 'astlib'])
    # args = command_line_arguments(['-t', test_dir, 'lib'])

    args = command_line_arguments(sys.argv[1:])

    # Override the data directory (testing)
    if args.test:
        Config.set_root_directory(args.test[0])

    # Abort if the redirector, production and work directories do not exist.
    if not (isdir(Config.redirector_dir()) and isdir(Config.prod_dir()) and isdir(Config.work_dir())):
        print 'Redirector, prod and/or work directories do not exist'
        exit(1)

    # Print the active ioc or support module information.
    # Use a 'configure-ioc -L' like output if no names are specified
    if args.name:
        # report entries in the redirector directory (i.e. in use)
        if args.area == AREA_IOC:
            print_active_ioc_dependencies(args.name, args.exclude, args.epics)
        else:
            print_active_support_module_dependencies(args.name, args.exclude, args.epics)

    else:
        # 'configure-ioc -L' like output if no options are specified
        print_active_ioc_summary(args.exclude, args.epics, args.links, args.csv)

    exit(0)
