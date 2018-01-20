#!/usr/bin/python
import sys
from argparse import ArgumentParser, SUPPRESS, Namespace
from os.path import isdir
from versions import Redirector, IOC, SupportModule, Config
from versions import SITE_LIST, AREA_LIST, AREA_SUPPORT, AREA_IOC
from versions import MATURITY_PROD
from versions import get_ioc_name, default_version
from versions import get_ioc_list, get_ioc_versions
from versions import get_support_module_list, get_support_module_versions


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


def print_active_ioc_summary(argv):
    """
    Print version information for all IOC's in the redirector directory.
    There "links" output is the same as the 'configure-ioc -L' output.
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


def print_active_ioc_dependencies(argv):
    """
    Print the dependency information of the IOC's in the redirector directory.
    For each IOC, it prints the IOC version, EPICS version and EPICS BSP for the IOC,
    and the list of support modules that the IOC depends on.
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


def print_active_support_module_dependencies(argv):
    """
    Print the support module dependencies that are used by one or more IOC's.
    The report includes dependencies with other support modules and the IOC's that depend on them.
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
            for dep in sup.get_support_module_dependencies():  # print dependencies
                assert (isinstance(dep, SupportModule))
                print '   {0:16} {1:16} {2}'.format(dep.name, default_version(dep.version, dep.maturity), dep.epics)
            for ioc in ioc_dict[sup_id]:  # print ioc's
                assert (isinstance(ioc, IOC))
                print '   {0:16} {1:16} {2}'.format(ioc.name, default_version(ioc.version, ioc.maturity), ioc.epics)
            print
    else:
        print 'support module \'' + argv.name + '\'' + \
              ' does not exist or is not used by any IOC\'s in the redirector directory'


def print_ioc_dependencies(args):
    """
    :param args:
    :return:
    """
    epics_version = args.epics
    ioc_list = get_ioc_list(epics_version, MATURITY_PROD)
    dep_list = {}
    len_name_max = 0
    len_version_max = 0

    # Loop over all IOC's, sites and versions for a given EPICS version.
    # Create a dictionary indexed by the tuple (name, version), where each
    # element of the dictionary is a list of the dependencies for the given ioc.
    # Only ioc's for MATURITY_PROD are considered since versions numbers
    # don't make sense in MATURITY_WORK or MATURITY_TEST.
    for ioc_target_name in ioc_list:
        for site in SITE_LIST:
            for ioc_version in get_ioc_versions(ioc_target_name, epics_version, site):
                ioc_name = get_ioc_name(ioc_target_name, site)
                # print ioc_name, ioc_version
                ioc = IOC(ioc_name)
                ioc.set_attributes(MATURITY_PROD, epics_version, site, ioc_target_name, ioc_version)
                # print ioc
                dep_list[(ioc_name, ioc_version)] = ioc.get_ioc_dependencies()
                len_name_max = max(len_name_max, len(ioc_name))
                len_version_max = max(len_version_max, len(ioc_version))

    print_aux(dep_list, epics_version, len_name_max, len_version_max)


def print_support_module_dependencies(args):
    """
    :param args:
    :return:
    """
    epics_version = args.epics
    support_module_list = get_support_module_list(epics_version, MATURITY_PROD)
    dep_list = {}
    dep_names = {}
    dep_versions = {}
    len_name_max = 0
    len_version_max = 0
    referenced_names = set()

    # Loop over all support modules and versions for a given EPICS version.
    # Create a dictionary indexed by the tuple (name, version), where each
    # element of the dictionary is a list of the dependencies for the given module.
    # Only support modules for MATURITY_PROD are considered since versions numbers
    # don't make sense in MATURITY_WORK or MATURITY_TEST.
    for support_name in support_module_list:
        for support_version in get_support_module_versions(support_name, epics_version):
            # key = (support_name, support_version)
            sup = SupportModule(support_name, support_version, epics_version, MATURITY_PROD)
            dep_list[(support_name, support_version)] = sup.get_support_module_dependencies()
            # print sup, len(dep_list[key]), dep_list
            # dep_names[key] = [x.name for x in dep_list[key]]
            # dep_versions[key] = [x.version for x in dep_list[key]]
            # calculate the max lengths
            len_name_max = max(len_name_max, len(support_name))
            len_version_max = max(len_version_max, len(support_version))
            # referenced_names.update(dep_names[key])
            # print dep_names[key]

    print_aux(dep_list, epics_version, len_name_max, len_version_max)
    # return
    #
    # # Sort the list (set) of support module names that are referenced by other modules.
    # # This is the list that will be used later in the report colums; we don't want empty
    # # columns that make the report unnecessarily wider.
    # referenced_names = sorted(referenced_names)
    #
    # # Calculate the maximum length between the support module name and version.
    # # This number will be used when formatting output.
    # len_max = max(len_name_max, len_version_max)
    #
    # # Print title. Leave empty space for the name and version at the beginning.
    # print fmt([epics_version], len_name_max) + fmt(' ', len_version_max) + fmt(referenced_names, len_max)
    #
    # # Print support modules. There will be one line per support module starting
    # # the name and version, and then followed by the versions of the dependencies.
    # # Only support modules with dependencies will be listed in the output.
    # for support_name, support_version in sorted(dep_list):
    #
    #     # print support_name, support_version
    #     key = (support_name, support_version)
    #
    #     # Skip modules with no dependencies
    #     if len(dep_names[key]) == 0:  # no dependencies
    #         continue
    #
    #     # Loop over the referenced dependencies (the report columns).
    #     # Trap those that are not a dependency.
    #     column_list = []
    #     for dep in referenced_names:
    #         try:
    #             idx = dep_names[key].index(dep)
    #             column_list.append(dep_versions[key][idx])
    #         except ValueError:
    #             column_list.append('-')  # not a dependency
    #     print fmt([support_name], len_name_max) + fmt([support_version], len_version_max) + fmt(column_list, len_max)


def print_aux(dep_list, epics_version, len_name_max, len_version_max):
    """

    :param dep_list:
    :param epics_version:
    :param len_name_max:
    :param len_version_max:
    :return:
    """
    dep_names = {}
    dep_versions = {}
    referenced_names = set()

    for key in dep_list:
        dep_names[key] = [x.name for x in dep_list[key]]
        dep_versions[key] = [x.version for x in dep_list[key]]
        referenced_names.update(dep_names[key])

    # Sort the list (set) of support module names that are referenced by other modules.
    # This is the list that will be used later in the report colums; we don't want empty
    # columns that make the report unnecessarily wider.
    referenced_names = sorted(referenced_names)
    # print referenced_names

    # Calculate the maximum length between the support module name and version.
    # This number will be used when formatting output.
    len_max = max(len_name_max, len_version_max)

    # Print title. Leave empty space for the name and version at the beginning.
    print fmt([epics_version], len_name_max) + fmt(' ', len_version_max) + fmt(referenced_names, len_max)

    # Print support modules. There will be one line per support module starting
    # the name and version, and then followed by the versions of the dependencies.
    # Only support modules with dependencies will be listed in the output.
    for name, version in sorted(dep_list):

        # print support_name, support_version
        key = (name, version)

        # Skip modules with no dependencies
        if len(dep_names[key]) == 0:  # no dependencies
            continue

        # Loop over the referenced dependencies (the report columns).
        # Trap those that are not a dependency.
        column_list = []
        for dep in referenced_names:
            try:
                idx = dep_names[key].index(dep)
                column_list.append(dep_versions[key][idx])
            except ValueError:
                column_list.append('-')  # not a dependency
        print fmt([name], len_name_max) + fmt([version], len_version_max) + fmt(column_list, len_max)


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

    args = command_line_arguments(['-r', 'gem_sw_cp_2', '-e', 'R3.14.12.7'])
    Config.set_root_directory(args.root[0])
    # print_ioc_dependencies(args)
    print_support_module_dependencies(args)
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
            print_active_ioc_dependencies(args)
        else:
            print_active_support_module_dependencies(args)
    else:
        print_active_ioc_summary(args)

    exit(0)
