#!/usr/bin/python
import sys
from argparse import ArgumentParser, SUPPRESS, Namespace
from os.path import isdir
from versions import Redirector, IOC, SupportModule, Config
from versions import AREA_LIST, AREA_SUPPORT, AREA_IOC
from versions import MATURITY_PROD
from versions import default_version
from versions import get_support_module_list, get_support_module_versions


def print_ioc_summary(argv):
    """
    Print version information for all IOC's in the redirector directory
    :param argv: command line arguments
    :type argv: Namespace
    :return None
    """
    rd = Redirector(argv.exclude, argv.epics)
    len_max = len(max(rd.get_ioc_names(), key=len))  # for formatting
    # print '-', rd.get_ioc_names()
    format_string_links = '{0:' + str(len_max) + '}  {1}'
    format_string_details = '{0:' + str(len_max) + '}  {1:5} {2:14} {3:15} {4:13} {5}'
    for ioc in rd.get_ioc_list():
        # print ioc
        if argv.links:
            print format_string_links.format(ioc.name, ioc.link)
        else:
            print format_string_details.format(ioc.name, ioc.maturity, ioc.epics, ioc.bsp, ioc.version, ioc.boot)


def print_ioc_dependencies(argv):
    """
    Print IOC and dependency information. It will print the IOC version, EPICS version
    and EPICS BSP for the IOC, and the list of support modules and versions.
    :param argv: command line arguments
    :type argv: Namespace
    :return None
    """
    # print 'print_ioc_dependencies', argv.name
    rd = Redirector(argv.exclude, argv.epics)
    if argv.name in rd.get_ioc_names():
        ioc = rd.get_ioc(argv.name)
        assert (isinstance(ioc, IOC))
        print '{0} {1} {2} {3} {4}'.format(ioc.name, default_version(ioc.version, ioc.maturity),
                                           ioc.boot, ioc.epics, ioc.bsp)
        for support_module in ioc.get_ioc_dependencies():
            print '   {0:16} {1}'.format(support_module.name, support_module.version)
    else:
        print argv.name + ' not found'


def print_support_module_dependencies(argv):
    """
    Print the support module dependencies to other support modules, as well as the IOC's
    that depend on the support module.
    :param argv: command line arguments
    :type argv: Namespace
    :return None
    """
    # print 'print_support_module_dependencies', support_module_name

    # The ioc dictionary is used to create a cross reference between support modules and IOC objects.
    # Each entry is indexed by the support module id and contains the list of IOC's using the support module.
    # Repeated dependencies are prevented by not appending them to the list.
    ioc_dict = {}

    # The support module dictionary is used to map support module id's with SupportModule objects.
    # Repeated dependencies will be discarded.
    sup_dict = {}

    # Populate the two dictionaries. We loop over all the ioc's in the redirector directory
    # and then iterate over the dependencies for each ioc.
    rd = Redirector(argv.exclude, argv.epics)
    for ioc in rd.get_ioc_list():
        # print '-', ioc
        for sup in ioc.get_ioc_dependencies():
            sup_dict[sup.id] = sup  # repeated entries are discarded at this point
            assert (isinstance(sup, SupportModule))
            # print '  ', sup
            if sup.name == argv.name:
                if sup.id in ioc_dict:
                    ioc_dict[sup.id].append(ioc)
                else:
                    ioc_dict[sup.id] = [ioc]

    if ioc_dict:
        # Print the support module dependencies first, followed by the ioc's that use the support module
        for sup_id in sorted(ioc_dict):
            sup = sup_dict[sup_id]
            # print '--', sup
            assert (isinstance(sup, SupportModule))
            print sup.name, sup.version, sup.epics
            for dep in sup.get_support_module_dependencies():
                assert (isinstance(dep, SupportModule))
                print '   {0:16} {1:16} {2}'.format(dep.name, default_version(dep.version, dep.maturity), dep.epics)
            for ioc in ioc_dict[sup_id]:
                assert (isinstance(ioc, IOC))
                print '   {0:16} {1:16} {2}'.format(ioc.name, default_version(ioc.version, ioc.maturity), ioc.epics)
            print
    else:
        print 'support module \"' + argv.name + '\" does not exist or is not used by any (active) IOC\'s'


def print_report(args):
    epics_version = args.epics

    # Build dictionary with...
    support_module_list = get_support_module_list(epics_version, MATURITY_PROD)
    dep_list = {}
    dep_names = {}
    dep_versions = {}
    len_name_max = 0
    len_version_max = 0

    # Loop over all support modules and versions for a given EPICS version.
    # Create a dictionary indexed by the tuple (name, version), where each
    # element of the dictionary is a list of the dependencies for the given module.
    # Only support modules for MATURITY_PROD are considered since versions numbers
    # don't make sense in MATURITY_WORK or MATURITY_TEST.
    for support_name in support_module_list:
        for support_version in get_support_module_versions(support_name, epics_version):
            key = (support_name, support_version)
            sup = SupportModule(support_name, support_version, epics_version, MATURITY_PROD)
            dep_list[key] = sup.get_support_module_dependencies()
            # print sup, len(dep_list[key]), dep_list
            dep_names[key] = [x.name for x in dep_list[key]]
            dep_versions[key] = [x.version for x in dep_list[key]]
            # calculate the max lengths
            len_name_max = max(len_name_max, len(support_name))
            len_version_max = max(len_version_max, len(support_version))

    len_max = max(len_name_max, len_version_max)

    print fmt([' '], len_name_max) + fmt(' ', len_version_max) + fmt(support_module_list, len_max)
    for support_name, support_version in sorted(dep_list):
        key = (support_name, support_version)
        if len(dep_names[key]) == 0:
            continue
        l = []
        # print support_name, support_version
        for col in support_module_list:
            try:
                idx = dep_names[key].index(col)
                l.append(dep_versions[key][idx])
            except ValueError:
                l.append('-')
        print fmt([support_name], len_name_max) + fmt([support_version], len_version_max) + fmt(l, len_max)
        # print key, dep_names[key], dep_versions[key]


def fmt(item_list, width, csv=False, csv_delimiter=','):
    """
    Format a list of items in "columns" of at least width characters, or using CSV format.
    :param item_list: list of items to format
    :type item_list: list
    :param width: column width
    :type width: int
    :param csv: format as csv output
    :type csv: bool
    :param csv_delimiter: delimiter to use in csv output
    :type csv_delimiter: str
    :return: formatted line
    :rtype: str
    """
    # print 'fmt', len(args), args
    if csv:
        format_string = ('{:s}' + csv_delimiter) * len(item_list)
        format_string = format_string[:-1]
    else:
        format_string = ('{:' + str(width + 1) + 's} ') * len(item_list)
    # print format_string
    return format_string.format(*item_list)


def command_line_arguments(argv):
    """
    Process command line arguments
    :param argv: command line arguments from sys.argv[1:]
    :type argv: list
    :return: argparse Namespace
    :rtype: Namespace
    """

    # Define text that will be printed at the end of the '-h' option
    epilog_text = """The default area is '""" + AREA_SUPPORT + """'""" + \
                  """. The list of all IOC's in the redirector directory will be printed if no module is specified."""

    parser = ArgumentParser(epilog=epilog_text)

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
                        help='set <area> to \'' + AREA_SUPPORT + '\' or \'' + AREA_IOC + '\'')
    parser.add_argument('-i',
                        '--ioc',
                        action='store_const',
                        dest='area',
                        const=AREA_IOC,
                        help='set <area>=' + AREA_IOC)
    parser.add_argument('-x', '--exclude',
                        action='store',
                        nargs='+',
                        dest='exclude',
                        help='',
                        default=[])
    parser.add_argument('-e', '--epics',
                        action='store',
                        dest='epics',
                        help='',
                        default='')
    parser.add_argument(action='store',
                        nargs='?',
                        dest='name',
                        help='',
                        default=[])
    parser.add_argument('-r', '--root',
                        action='store',
                        nargs=1,
                        dest='root',
                        default='',
                        help=SUPPRESS)

    return parser.parse_args(argv)


if __name__ == '__main__':

    print fmt(['a', 'b', 'c'], 10)
    print fmt(['a', 'b', 'c'], 10, True)
    exit(0)
    args = command_line_arguments(['-r', 'gem_sw_cp', '-e', 'R3.14.12.6'])
    Config.set_root_directory(args.root[0])
    print_report(args)
    exit(0)

    args = command_line_arguments(sys.argv[1:])

    if args.root:
        Config.set_root_directory(args.root[0])

    # Abort if the redirector, production and work directories are not found
    if not (isdir(Config.redirector_dir()) and isdir(Config.prod_dir()) and isdir(Config.work_dir())):
        print 'No redirector, prod or work directory found'
        exit(1)

    if args.name:
        if args.area == AREA_IOC:
            print_ioc_dependencies(args)
        else:
            print_support_module_dependencies(args)
    else:
        print_ioc_summary(args)

    exit(0)
