#!/usr/bin/python
import sys
# import re
from argparse import ArgumentParser, SUPPRESS, Namespace
from os.path import isdir
from versions import Redirector, IOC, SupportModule, Config
from versions import SITE_LIST, AREA_LIST, AREA_SUPPORT, AREA_IOC
from versions import MATURITY_PROD
from versions import get_ioc_name, default_version
from versions import get_epics_versions, get_latest_epics_version
from versions import get_ioc_list, get_ioc_versions
from versions import get_support_module_list, get_support_module_versions

EPICS_ALL = 'all'

NOT_FOUND = (-1)


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
    else:
        format_string = ('{:' + str(width + 1) + 's} ') * len(item_list)
    # print format_string
    return format_string.format(*item_list)


def skip_name(name, match_list):
    """
    :param name:
    :type name: str
    :param match_list:
    :type match_list: list
    :return:
    :rtype: bool
    """
    if match_list:
        for s in match_list:
            # print 'm', 's=', s, 'n=', name, s.find(name)
            if name.find(s) != NOT_FOUND:
                # print 'match'
                return False
        return True
    else:
        return False


def skip_exclude(name, exclude_list):
    """
    :param name:
    :type name: str
    :param exclude_list:
    :type exclude_list: list
    :return:
    """
    for s in exclude_list:
        if name.find(s) != NOT_FOUND:
            return True
    return False


def skip_epics(epics_version, epics_version_list):
    """
    :param epics_version:
    :type epics_version: str
    :param epics_version_list:
    :type epics_version_list: list
    :return: skip EPICS version?
    :rtype: bool
    """
    # print epics_version, epics_version_list
    if epics_list:
        for s in epics_version_list:
            if epics_version.find(s) != NOT_FOUND:
                return False
        return True
    else:
        return False


# def print_active_ioc_summary(argv):
#     """
#     Print version information for all IOC's in the redirector directory.
#     There "links" output is the same as the 'configure-ioc -L' output.
#     :param argv: command line arguments
#     :type argv: Namespace
#     :return None
#     """
#     rd = Redirector(argv.exclude, argv.epics)
#     len_max = len(max(rd.get_ioc_names(), key=len))  # for formatting
#     # print '-', rd.get_ioc_names()
#     format_string_links = '{0:' + str(len_max) + '}  {1}'
#     format_string_details = '{0:' + str(len_max) + '}  {1:5} {2:14} {3:15} {4:13} {5}'
#     for ioc in rd.get_ioc_list():
#         # print ioc
#         if argv.links:
#             print format_string_links.format(ioc.name, ioc.link)
#         else:
#             print format_string_details.format(ioc.name, ioc.maturity, ioc.epics, ioc.bsp, ioc.version, ioc.boot)


def print_active_ioc_summary(exclude_list, epics_version_list, print_links):
    """
    Print version information for all IOC's in the redirector directory.
    There "links" output is the same as the 'configure-ioc -L' output.
    :param exclude_list: list of IOC's (words) to exclude from the list
    :type exclude_list: list
    :param epics_version_list:
    :param print_links: print links instead of formatted table (same as configure-ioc -L)
    :type print_links: bool
    :return None
    """
    # rd = Redirector(argv.exclude, argv.epics)
    rd = Redirector()
    len_max = len(max(rd.get_ioc_names(), key=len))  # for formatting
    # print '-', rd.get_ioc_names()
    format_string_links = '{0:' + str(len_max) + '}  {1}'
    format_string_details = '{0:' + str(len_max) + '}  {1:5} {2:14} {3:15} {4:13} {5}'
    for ioc in rd.get_ioc_list():
        assert (isinstance(ioc, IOC))
        if skip_exclude(ioc.name, exclude_list) or skip_epics(ioc.epics, epics_version_list):
            continue
        # print ioc
        if print_links:
            print format_string_links.format(ioc.name, ioc.link)
        else:
            print format_string_details.format(ioc.name, ioc.maturity, ioc.epics, ioc.bsp, ioc.version, ioc.boot)


# def print_active_ioc_dependencies(argv):
#     """
#     Print the dependency information of the IOC's in the redirector directory.
#     For each IOC, it prints the IOC version, EPICS version and EPICS BSP for the IOC,
#     and the list of support modules that the IOC depends on.
#     :param argv: command line arguments
#     :type argv: Namespace
#     :return None
#     """
#     # print 'print_ioc_dependencies', argv.name
#     rd = Redirector(argv.exclude, argv.epics)
#     if argv.name in rd.get_ioc_names():
#         ioc = rd.get_ioc(argv.name)
#         assert (isinstance(ioc, IOC))
#         print '{0} {1} {2} {3} {4}'.format(ioc.name, default_version(ioc.version, ioc.maturity),
#                                            ioc.boot, ioc.epics, ioc.bsp)
#         for support_module in ioc.get_ioc_dependencies():
#             print '   {0:16} {1}'.format(support_module.name, support_module.version)
#     else:
#         print argv.name + ' not found'

def print_active_ioc_dependencies(ioc_name_list, exclude_list, epics_version_list):
    """
    Print the dependency information of IOC's in the redirector directory.
    For each IOC, it prints the IOC version, EPICS version and EPICS BSP for the IOC,
    and the list of support modules that the IOC depends on.
    :param ioc_name_list: list of strings IOC names to include in the output
    :type ioc_name_list: list
    :param exclude_list: list of strings in IOC names to exclude from the output
    :type exclude_list: list
    :param epics_version_list: list of strings to match against IOC EPICS versions
    :type epics_version_list: list
    :return None
    """
    # print 'print_ioc_dependencies', argv.name
    # rd = Redirector(argv.exclude, argv.epics)
    rd = Redirector()
    for ioc in rd.get_ioc_list():
        # print match_list
        # print ioc
        assert (isinstance(ioc, IOC))
        if skip_name(ioc.name, ioc_name_list) or \
                skip_exclude(ioc.name, exclude_list) or \
                skip_epics(ioc.epics, epics_version_list):
            continue
        print '{} {} {} {} {}'.format(ioc.name, default_version(ioc.version, ioc.maturity),
                                      ioc.boot, ioc.epics, ioc.bsp)
        for support_module in ioc.get_ioc_dependencies():
            print '   {:16} {}'.format(support_module.name, support_module.version)
        print


# def print_active_support_module_dependencies(argv):
#     """
#     Print the support module dependencies that are used by one or more IOC's.
#     The report includes dependencies with other support modules and the IOC's that depend on them.
#     :param argv: command line arguments
#     :type argv: Namespace
#     :return None
#     """
#     # print 'print_support_module_dependencies', support_module_name
#
#     # The ioc dictionary is used to create a cross reference between support modules and IOC objects.
#     # Each entry is indexed by the support module id and contains the list of IOC's using the support module.
#     # Repeated dependencies are prevented by not appending them to the list.
#     ioc_dict = {}
#
#     # The support module dictionary is used to map support module id's with SupportModule objects.
#     # Repeated dependencies will be discarded.
#     sup_dict = {}
#
#     # Populate the two dictionaries. We loop over all the ioc's in the redirector directory
#     # and then iterate over the dependencies for each ioc.
#     rd = Redirector(argv.exclude, argv.epics)
#     for ioc in rd.get_ioc_list():
#         # print '-', ioc
#         for sup in ioc.get_ioc_dependencies():
#             sup_dict[sup.id] = sup  # repeated entries are discarded at this point
#             assert (isinstance(sup, SupportModule))
#             # print '  ', sup
#             if sup.name == argv.name:
#                 if sup.id in ioc_dict:
#                     ioc_dict[sup.id].append(ioc)
#                 else:
#                     ioc_dict[sup.id] = [ioc]
#
#     # Check whether there are any ioc's that depend of the support module we are looking for.
#     # An empty dictionary means either that no ioc's depend on the support module, or that
#     # the support module doesn't exist at all.
#     if ioc_dict:
#         # Print the support module dependencies first, followed by the ioc's that use the support module
#         for sup_id in sorted(ioc_dict):
#             sup = sup_dict[sup_id]
#             # print '--', sup
#             assert (isinstance(sup, SupportModule))
#             print sup.name, sup.version, sup.epics
#             # print support module dependencies
#             for dep in sup.get_support_module_dependencies():
#                 assert (isinstance(dep, SupportModule))
#                 print '   {0:16} {1:16} {2}'.format(dep.name, default_version(dep.version, dep.maturity), dep.epics)
#             # print ioc's that depend on the support module
#             for ioc in ioc_dict[sup_id]:
#                 assert (isinstance(ioc, IOC))
#                 print '   {0:16} {1:16} {2}'.format(ioc.name, default_version(ioc.version, ioc.maturity), ioc.epics)
#             print
#     else:
#         print 'support module(s) \'' + str(argv.name) + '\'' + \
#               ' does not exist or is not used by any IOC\'s in the redirector directory'

def print_active_support_module_dependencies(support_name_list, exclude_list, epics_version_list):
    """
    Print the support module dependencies that are used by one or more IOC's.
    The report includes dependencies with other support modules and the IOC's that depend on them.
    :param support_name_list: list of strings to match against support module names
    :type support_name_list: list
    :param exclude_list: TODO
    :type exclude_list: list
    :param epics_version_list: list of strings to match against support module EPICS versions
    :type epics_version_list: list
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
    # rd = Redirector(argv.exclude, argv.epics)
    rd = Redirector()
    for ioc in rd.get_ioc_list():
        if skip_exclude(ioc.name, exclude_list) or skip_epics(ioc.epics, epics_version_list):
            continue
        # print '-', ioc
        for sup in ioc.get_ioc_dependencies():
            sup_dict[sup.id] = sup  # repeated entries are discarded at this point
            assert (isinstance(sup, SupportModule))
            # print '  ', sup
            if skip_name(sup.name, support_name_list):
                continue
            # if sup.name == argv.name:
            #     if sup.id in ioc_dict:
            #         ioc_dict[sup.id].append(ioc)
            #     else:
            #         ioc_dict[sup.id] = [ioc]
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
                print '   {0:16} {1:16} {2}'.format(dep.name, default_version(dep.version, dep.maturity), dep.epics)
            # print ioc's that depend on the support module
            for ioc in ioc_dict[sup_id]:
                assert (isinstance(ioc, IOC))
                print '   {0:16} {1:16} {2}'.format(ioc.name, default_version(ioc.version, ioc.maturity), ioc.epics)
            print
    else:
        print 'support module(s) \'' + str(support_name_list) + '\'' + \
              ' does not exist or is not used by any IOC\'s in the redirector directory'


def print_epics_version_list():
    """
    List all EPICS versions available in prod.
    :return: None
    """
    for epics in get_epics_versions(MATURITY_PROD):
        print epics


def print_ioc_list(epics_version_list):
    """
    List all the IOC's available in prod for the given EPICS version(s).
    :param epics_version_list: list of EPICS versions to search for IOC's
    :type epics_version_list: list
    :return: None
    """
    ioc_dict = {}
    len_max = 0

    # Loop over all EPICS versions and IOC's.
    # Build a dictionary where each entry is the list containing the different EPICS
    # version(s) for each IOC.
    # EPICS versions are listed in reverse order.
    for epics_version in sorted(epics_version_list, reverse=True):
        for ioc_name in get_ioc_list(epics_version, MATURITY_PROD):
            len_max = max(len_max, len(ioc_name))
            if ioc_name in ioc_dict:
                ioc_dict[ioc_name].append(epics_version)
            else:
                ioc_dict[ioc_name] = [epics_version]

    # Print the dictionary (formatted).
    format_string = '{:' + str(len_max) + '}    {}'
    for ioc_name in sorted(ioc_dict):
        print format_string.format(ioc_name, ioc_dict[ioc_name])


def print_support_module_list(epics_version_list):
    """
    List all the support modules available in prod for the given EPICS version(s).
    :param epics_version_list: list of EPICS versions to search for support modules.
    :type epics_version_list: list
    :return: None
    """
    support_dict = {}
    len_max = 0

    # Loop over all EPICS versions and support modules.
    # Build a dictionary where each entry is the list containing the different
    # EPICS version(s) for each IOC.
    # EPICS versions are listed in reverse order.
    for epics_version in sorted(epics_version_list, reverse=True):
        for support_name in get_support_module_list(epics_version, MATURITY_PROD):
            len_max = max(len_max, len(support_name))
            if support_name in support_dict:
                support_dict[support_name].append(epics_version)
            else:
                support_dict[support_name] = [epics_version]

    # Print the dictionary (formatted).
    format_string = '{:' + str(len_max) + '}    {}'
    for support_name in sorted(support_dict):
        print format_string.format(support_name, support_dict[support_name])


def print_ioc_dependency_report(match_list, exclude_list, epics_version_list, csv_output):
    """
    Print a matrix (table) with the dependencies for each IOC.
    The match list can be used to select IOC's matching a list of strings.
    The exclude list can be used to skip IOC's matching a list of strings.

    Create a dictionary indexed by the tuple (name, version), where each
    element of the dictionary is a list of the dependencies for the given ioc.
    Only IOC's for MATURITY_PROD are considered since versions numbers
    don't make sense in maturities other than prod.
    :param match_list:
    :type match_list: list
    :param exclude_list:
    :type exclude_list: list
    :param epics_version_list:
    :type epics_version_list: list
    :param csv_output: CSV output?
    :type csv_output: bool
    :return:
    """
    for epics_version in epics_version_list:
        ioc_list = get_ioc_list(epics_version, MATURITY_PROD)
        dep_list = {}

        # Maximum length of an IOC name and version (used later for formatting)
        len_name_max = 0
        len_version_max = 0

        # Loop over all IOC's, sites and versions for a given EPICS version.
        # Create a dictionary indexed by the tuple (ioc name, ioc version), where each
        # element of the dictionary is a list of the dependencies for the given IOC.
        # IOC's are matched and excluded at this point.
        for ioc_target_name in ioc_list:
            for site in SITE_LIST:
                for ioc_version in get_ioc_versions(ioc_target_name, epics_version, site):
                    ioc_name = get_ioc_name(ioc_target_name, site)
                    if skip_name(ioc_name, match_list) or skip_exclude(ioc_name, exclude_list):
                        continue
                    # print ioc_name, ioc_version
                    ioc = IOC(ioc_name)
                    ioc.set_attributes(MATURITY_PROD, epics_version, site, ioc_target_name, ioc_version)
                    # print ioc
                    dep_list[(ioc_name, ioc_version)] = ioc.get_ioc_dependencies()
                    len_name_max = max(len_name_max, len(ioc_name))
                    len_version_max = max(len_version_max, len(ioc_version))

        _print_dependency_report(dep_list, epics_version, len_name_max, len_version_max, csv_output)

        if len(epics_list) > 1:
            print '\n'


def print_support_module_dependency_report(match_list, exclude_list, epics_version_list, csv_output):
    """
    Loop over all support modules and versions for all EPICS versions in the EPICS list
    Create a dictionary indexed by the tuple (name, version), where each
    element of the dictionary is a list of the dependencies for the given module.
    Only support modules for MATURITY_PROD are considered since versions numbers
    don't make sense in maturities other than prod.
    :param match_list:
    :type match_list: list
    :param exclude_list:
    :type exclude_list: list
    :param epics_version_list:
    :type epics_version_list: list
    :param csv_output: CSV output?
    :type csv_output: bool
    :return: None
    """
    for epics_version in epics_version_list:
        support_module_list = get_support_module_list(epics_version, MATURITY_PROD)
        dep_list = {}
        len_name_max = 0
        len_version_max = 0

        for support_name in support_module_list:
            if skip_name(support_name, match_list) or skip_exclude(support_name, exclude_list):
                continue
            for support_version in get_support_module_versions(support_name, epics_version):
                sup = SupportModule(support_name, support_version, epics_version, MATURITY_PROD)
                dep_list[(support_name, support_version)] = sup.get_support_module_dependencies()
                len_name_max = max(len_name_max, len(support_name))
                len_version_max = max(len_version_max, len(support_version))

        # print dep_list
        _print_dependency_report(dep_list, epics_version, len_name_max, len_version_max, csv_output)

        if len(epics_list) > 1:
            print '\n'


def _print_dependency_report(dep_list, epics_version, len_name_max, len_version_max, csv_output):
    """
    Auxiliary routine used by print_ioc_dependencies and print_support_module_dependencies
    to do the actual formatting of the dependency table report.
    :param dep_list: dependency dictionary, indexed by a (name, version) tuple
    :type dep_list: dict
    :param epics_version: EPICS version
    :type epics_version: str
    :param len_name_max: max length of a support module or IOC name
    :type len_name_max: int
    :param len_version_max: max length of a support module or IOC version
    :type len_version_max: int
    :return:
    """
    # These two variables are used to store the list of dependency names and versions
    # in two separate dictionaries indexed by the same index used in dep_list.
    dep_names = {}
    dep_versions = {}
    len_dep_name_max = 0
    len_dep_version_max = 0

    # The reference names set is used to build a list of unique dependency names.
    referenced_names = set()

    for key in dep_list:
        dep_names[key] = [x.name for x in dep_list[key]]
        dep_versions[key] = [x.version for x in dep_list[key]]
        referenced_names.update(dep_names[key])

        # Keep track of the maximum name and version length for the dependency
        # Ignore those cases that don't have dependencies.
        try:
            len_dep_name_max = max(len_dep_name_max, len(max(dep_names[key], key=len)))
            len_dep_version_max = max(len_dep_version_max, len(max(dep_versions[key], key=len)))
        except ValueError:
            pass

    # Sort the list (set) of support module names that are actually used.
    # Support modules that are not used won't be included in this list.
    # Therefore, the report will include columns of relevant dependencies.
    referenced_names = sorted(referenced_names)
    # print referenced_names

    # Calculate the maximum length between the all the names and versions.
    # This number will be used when formatting output.
    # TODO improve the way the maximum lengths are calculated. Right now, there's a single one (easiest, but not optimal)
    len_max = max(len_name_max, len_version_max, len_dep_name_max, len_dep_version_max, len(epics_version))

    # Print title. The EPICS version will show up in the leftmost columns. This column will be
    # wide enough for the name and version of the support module or ioc.
    print fmt([epics_version], len_max, csv_output) + \
          fmt([' '], len_max, csv_output) + \
          fmt(referenced_names, len_max, csv_output)

    # Print support modules pr IOC's. There will be one line per item. The first two columns
    # will have the name and version, followed by the versions of the dependency versions.
    # Only support modules and IOC's with dependencies will be listed in the output.
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
        print fmt([name], len_max, csv_output) + \
              fmt([version], len_max, csv_output) + \
              fmt(column_list, len_max, csv_output)


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

    parser.add_argument(action='store',
                        nargs='*',
                        dest='name',
                        default=[],
                        help='IOC or support module name')

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
                        default=[],
                        help='exclude matching items from the output')

    parser.add_argument('-e', '--epics',
                        action='store',
                        nargs='*',
                        dest='epics',
                        default=[],
                        help='Restrict output to EPICS version(s)')

    parser.add_argument('-r', '--report',
                        action='store_true',
                        dest='report',
                        default=False,
                        help='print dependency report (support module or IOC')
    parser.add_argument('--csv',
                        action='store_true',
                        dest='csv',
                        default=False,
                        help='print report in csv format')

    parser.add_argument('--qe',
                        action='store_true',
                        dest='query_epics',
                        default=False,
                        help='list all available EPICS versions in prod')
    parser.add_argument('--qs',
                        action='store_true',
                        dest='query_support',
                        default=False,
                        help='list all available support packages in prod/.../support')
    parser.add_argument('--qi',
                        action='store_true',
                        dest='query_ioc',
                        default=False,
                        help='list all available ioc\'s in prod/.../ioc')

    parser.add_argument('-t', '--test',
                        action='store',
                        nargs=1,
                        dest='test',
                        default=[],
                        help=SUPPRESS)

    return parser.parse_args(argv)


# def skip_name(name, match_list, exclude_list):
#     """
#     :param name:
#     :type name: str
#     :param match_list:
#     :type match_list: list
#     :param exclude_list:
#     :type exclude_list: list
#     :return:
#     """
#     # First check the list of strings to exclude.
#     for s in exclude_list:
#         if name.find(s) != NOT_FOUND:
#             return True
#
#     # Then check the list of matching words.
#     if match_list:
#         for s in match_list:
#             # print 'm', 's=', s, 'n=', name, s.find(name)
#             if name.find(s) != NOT_FOUND:
#                 # print 'match'
#                 return False
#         return True
#     else:
#         return False

if __name__ == '__main__':

    # args = command_line_arguments(['-t', 'gem_sw_cp_2', '-r', 'lib'])
    # Config.set_root_directory(args.test[0])
    # print args

    args = command_line_arguments(sys.argv[1:])

    # Override the data directory (testing)
    if args.test:
        Config.set_root_directory(args.test[0])

    # Abort if the redirector, production and work directories are not found
    if not (isdir(Config.redirector_dir()) and isdir(Config.prod_dir()) and isdir(Config.work_dir())):
        print 'Redirector, prod or work directory not found'
        exit(1)

    if args.query_epics or args.query_support or args.query_ioc or args.report:
        if args.epics:
            if EPICS_ALL in args.epics:
                epics_list = get_epics_versions(MATURITY_PROD)
            else:
                epics_list = args.epics
        else:
            epics_list = [get_latest_epics_version(MATURITY_PROD)]
    else:
        epics_list = args.epics

    # Sort the EPICS list in reverse order since we want to the the newest version of EPICS first
    epics_list = sorted(epics_list, reverse=True)

    # Decide what report to print based on the command line options.
    if args.query_epics:
        print_epics_version_list()

    elif args.query_support:
        print_support_module_list(epics_list)

    elif args.query_ioc:
        print_ioc_list(epics_list)

    elif args.report:
        if args.area == AREA_IOC:
            print_ioc_dependency_report(args.name, args.exclude, epics_list, args.csv)
        else:
            print_support_module_dependency_report(args.name, args.exclude, epics_list, args.csv)

    elif args.name:
        if args.area == AREA_IOC:
            print_active_ioc_dependencies(args.name, args.exclude, epics_list)
        else:
            print_active_support_module_dependencies(args.name, args.exclude, args.epics)

    else:
        print_active_ioc_summary(args.exclude, epics_list, args.links)

    exit(0)
