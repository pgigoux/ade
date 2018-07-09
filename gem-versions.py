#!/usr/bin/python
import sys
from argparse import ArgumentParser, SUPPRESS, Namespace
from os.path import isdir

from versions import Redirector, IOC, SupportModule, Config
from versions import SITE_LIST, AREA_LIST, AREA_SUPPORT, AREA_IOC
from versions import MATURITY_PROD
from versions import get_ioc_name, default_version
from versions import get_epics_versions, get_latest_epics_version
from versions import get_ioc_list, get_ioc_versions
from versions import get_support_module_list, get_support_module_versions

# Value used to indicate all versions of EPICS in reports
EPICS_ALL = 'all'

# Value returned by str.find() where there's no match
NOT_FOUND = -1


def fmt(item_list, width, csv=False, csv_delimiter=','):
    """
    Format a list of items in columns of at least width characters. Use CSV format if csv=True
    The for loops in this routine are needed to be compatible with Python 2.6.
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
    format_string = ''
    if csv:
        for n in range(len(item_list)):
            format_string += '{' + str(n) + ':s}' + csv_delimiter
    else:
        for n in range(len(item_list)):
            format_string += '{' + str(n) + ':' + str(width + 1) + 's} '
    return format_string.format(*item_list)


def fmt_list(item_list, width_list, csv=False, csv_delimiter=','):
    """
    Format a list of items in columns of at least width characters. Use CSV format if csv=True
    The for loops in this routine are needed to be compatible with Python 2.6.
    :param item_list: list of items to format
    :type item_list: list
    :param width_list: list of column width
    :type width_list: list
    :param csv: format as csv output
    :type csv: bool
    :param csv_delimiter: delimiter to use in csv output
    :type csv_delimiter: str
    :return: formatted line
    :rtype: str
    """

    # The two lists must be of the same size
    if len(item_list) != len(width_list):
        raise IndexError

    format_string = ''
    if csv:
        return fmt(item_list, 0, csv, csv_delimiter)
    else:
        for n in range(len(item_list)):
            format_string += '{' + str(n) + ':' + str(width_list[n] + 1) + 's} '
    return format_string.format(*item_list)


def skip_name(name, match_list):
    """
    Auxiliary routine used to skip (ignore) an IOC or support module from the output.
    A name won't be skipped if any string in the match list is a substring of the name.
    No items will be ignored if the match list is empty.
    :param name: name to check
    :type name: str
    :param match_list: list of strings that should be allowed in the output
    :type match_list: list
    :return: boolean value indicating whether the name should be included or not
    :rtype: bool
    """
    skip = True
    # print name, match_list
    if match_list:
        for s in match_list:
            if name.find(s) != NOT_FOUND:
                skip = False
        return skip
    else:
        return False


def skip_exclude(name, exclude_list):
    """
    Auxiliary routine used to skip (exclude) an IOC or support module from the output.
    No items will be excluded if the exclude list is empty.
    :param name: name to check
    :type name: str
    :param exclude_list: list of strings that should be excluded from the output
    :type exclude_list: list
    :return: boolean value indicating whether the name should be excluded or not
    :rtype: bool
    """
    for s in exclude_list:
        if name.find(s) != NOT_FOUND:
            return True
    return False


def skip_epics(epics_version, epics_version_list):
    """
    Auxiliary routine used to skip (exclude) an IOC or support module from the output based on its EPICS version.
    No items will be excluded if the epics list is empty.
    :param epics_version: EPICS version to check against the list
    :type epics_version: str
    :param epics_version_list: list
    :type epics_version_list: list
    :return: boolean value indicating whether the epics version should be excluded or not
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


def print_active_ioc_summary(exclude_list, epics_version_list, print_links):
    """
    Print version information for all IOC's in the redirector directory.
    There "links" output is the same as the 'configure-ioc -L' output.
    :param exclude_list: list of IOC's (substrings) to exclude from the list
    :type exclude_list: list
    :param epics_version_list:
    :param print_links: print links instead of formatted table (same as configure-ioc -L)
    :type print_links: bool
    :return None
    """
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
    # print 'print_ioc_dependencies'
    rd = Redirector()
    for ioc in rd.get_ioc_list():
        # print ioc
        assert (isinstance(ioc, IOC))
        if skip_name(ioc.name, ioc_name_list) or \
                skip_exclude(ioc.name, exclude_list) or \
                skip_epics(ioc.epics, epics_version_list):
            continue
        print '{0} {1} {2} {3} {4}'.format(ioc.name, default_version(ioc.version, ioc.maturity),
                                           ioc.boot, ioc.epics, ioc.bsp)
        for support_module in ioc.get_ioc_dependencies():
            print '   {0:16} {1}'.format(support_module.name, support_module.version)
        print


def print_active_support_module_dependencies(support_name_list, exclude_list, epics_version_list):
    """
    Print the support module dependencies that are used by one or more IOC's.
    The report includes dependencies with other support modules and the IOC's that depend on them.
    :param support_name_list: list of strings to match against support module names
    :type support_name_list: list
    :param exclude_list: list of items to exclude (no regular expressions)
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
    for epics in sorted(get_epics_versions(MATURITY_PROD)):
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
    format_string = '{0:' + str(len_max) + '}    {1}'
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

    # Loop over all EPICS versions and support modules (listed in reverse order).
    # Build a dictionary where each entry is the list containing the different EPICS version(s) for each IOC.
    for epics_version in sorted(epics_version_list, reverse=True):
        for support_name in get_support_module_list(epics_version, MATURITY_PROD):
            len_max = max(len_max, len(support_name))
            if support_name in support_dict:
                support_dict[support_name].append(epics_version)
            else:
                support_dict[support_name] = [epics_version]

    # Print the dictionary
    format_string = '{0:' + str(len_max) + '}    {1}'
    for support_name in sorted(support_dict):
        print format_string.format(support_name, support_dict[support_name])


def print_ioc_dependency_report(ioc_name_list, exclude_list, epics_version_list, csv_output):
    """
    Print a matrix (table) with the dependencies for each IOC.
    The match list can be used to select ioc's matching a list of substrings.
    The exclude list can be used to skip ioc's matching a list of substrings.

    Create a dictionary indexed by the tuple (name, version), where each
    element of the dictionary is a list of the dependencies for the given ioc.
    Only ioc's with MATURITY_PROD are considered since versions numbers
    don't make sense in maturities other than production.
    :param ioc_name_list: list of ioc names to include in the output
    :type ioc_name_list: list
    :param exclude_list: list of strings to match ioc names to exclude from the output
    :type exclude_list: list
    :param epics_version_list: list of EPICS versions to include in the output
    :type epics_version_list: list
    :param csv_output: CSV output?
    :type csv_output: bool
    :return:
    """
    for epics_version in epics_version_list:

        # List of all IOC (target) names for the EPICS version
        ioc_list = get_ioc_list(epics_version, MATURITY_PROD)

        # Loop over all ioc's, sites and versions for a given EPICS version.
        # Create a dictionary indexed by the tuple (ioc name, ioc version), where each
        # element of the dictionary is a list of the dependencies for the given ioc.
        # IOC's are "matched" and "excluded" at this point.
        dep_dict = {}
        for ioc_target_name in ioc_list:
            for site in SITE_LIST:
                for ioc_version in get_ioc_versions(ioc_target_name, epics_version, site):
                    ioc_name = get_ioc_name(ioc_target_name, site)
                    if skip_name(ioc_name, ioc_name_list) or skip_exclude(ioc_name, exclude_list):
                        continue
                    # print ioc_name, ioc_version
                    ioc = IOC(ioc_name)
                    ioc.set_attributes(MATURITY_PROD, epics_version, site, ioc_target_name, ioc_version)
                    # print ioc
                    dep_dict[(ioc_name, ioc_version)] = ioc.get_ioc_dependencies()

        _print_dependency_report(dep_dict, epics_version, csv_output)

        if len(epics_list) > 1:
            print '\n'


def print_support_module_dependency_report(support_name_list, exclude_list, epics_version_list, csv_output):
    """
    Loop over all support modules and versions for all EPICS versions in the EPICS list
    Create a dictionary indexed by the tuple (name, version), where each
    element of the dictionary is a list of the dependencies for the given module.
    Only support modules for MATURITY_PROD are considered since versions numbers
    don't make sense for other software maturities.
    :param support_name_list: list of support module names to include in the output
    :type support_name_list: list
    :param exclude_list: list of support module names to exclude from the output
    :type exclude_list: list
    :param epics_version_list: list of EPICS versions to include in the output
    :type epics_version_list: list
    :param csv_output: csv output?
    :type csv_output: bool
    :return: None
    """
    for epics_version in epics_version_list:
        support_module_list = get_support_module_list(epics_version, MATURITY_PROD)

        # Loop over all support module and versions for a given EPICS version.
        # Create a dictionary indexed by the tuple (support module name, support module version),
        # where each element of the dictionary is a list of the dependencies for the support module.
        # Support modules are "matched" and "excluded" at this point.
        dep_dict = {}
        for support_name in support_module_list:
            if skip_name(support_name, support_name_list) or skip_exclude(support_name, exclude_list):
                continue
            for support_version in get_support_module_versions(support_name, epics_version):
                sup = SupportModule(support_name, support_version, epics_version, MATURITY_PROD)
                dep_dict[(support_name, support_version)] = sup.get_support_module_dependencies()

        # print dep_list
        _print_dependency_report(dep_dict, epics_version, csv_output)

        if len(epics_list) > 1:
            print '\n'


def _print_dependency_report(dep_dict, epics_version, csv_output):
    """
    Auxiliary routine used by print_ioc_dependencies and print_support_module_dependencies
    to do the actual formatting of the dependency table report.
    :param dep_dict: dependency dictionary, indexed by a (name, version) tuple
    :type dep_dict: dict
    :param epics_version: EPICS version
    :type epics_version: str
    :return None
    """
    # These two variables are used to store the list of dependency names and versions
    # in two separate dictionaries indexed by the same index used in dep_list.
    dep_names = {}
    dep_versions = {}

    # Variables used to store name, version and column lengths
    len_name_max = 0
    len_version_max = 0
    len_dep_name_max = 0
    len_dep_version_max = 0
    column_lengths = {}

    # The reference names set is used to build a list of unique dependency names.
    referenced_names = set()

    # Iterate over all the elements in the dictionary. Each element is indexed by the name and the
    # version number, and the contents of each element is the list of supports modules it depends on.
    for key in dep_dict:

        # The key is a tuple consisting of the name and version indexing the dictionary.
        # This will printed in the first and second column of the report.
        len_name_max = max(len_name_max, len(key[0]))
        len_version_max = max(len_version_max, len(key[1]))

        # Split the dependency names and versions in two separate list.
        # The module name is stored in one list and the versions in the other.
        dep_names[key] = [x.name for x in dep_dict[key]]
        dep_versions[key] = [x.version for x in dep_dict[key]]

        # Store the names into a set. This eliminates duplicate and empty names.
        referenced_names.update(dep_names[key])

        # Create a list of the maximum (column) length for each dependency.
        # The list will be used when formatting the output.
        for name, version in zip(dep_names[key], dep_versions[key]):
            # print name, version
            if name in column_lengths:
                column_lengths[name] = max(column_lengths[name], max(len(name), len(version)))
            else:
                column_lengths[name] = max(len(name), len(version))
                # print '-', name, column_lengths[name]

        # Keep track of the maximum name and version length for the dependency
        # Ignore those cases that don't have dependencies.
        try:
            len_dep_name_max = max(len_dep_name_max, len(max(dep_names[key], key=len)))
            len_dep_version_max = max(len_dep_version_max, len(max(dep_versions[key], key=len)))
        except ValueError:
            pass

    # Sort the set of support module names that are actually used.
    # Support modules that are not used are not included in this set.
    # Thus, the report will only include columns of relevant dependencies.
    referenced_names = sorted(referenced_names)
    # print referenced_names

    column_length_list = [column_lengths[x] for x in referenced_names]
    # print column_length_list

    # The length of the first column will also depend on the EPICS version length
    first_column_length = max(len_name_max, len(epics_version))

    # Print title. The EPICS version will show up in the leftmost columns. This column will be
    # wide enough for the name and version of the support module or ioc.
    print fmt([epics_version], first_column_length, csv_output) + \
          fmt([' '], len_version_max, csv_output) + \
          fmt_list(referenced_names, column_length_list, csv_output)

    # Print support modules pr ioc's. There will be one line per item. The first two columns
    # will have the name and version, followed by the versions of the dependency versions.
    # Only support modules and ioc's with dependencies will be listed in the output.
    for name, version in sorted(dep_dict):

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

        print fmt([name], first_column_length, csv_output) + \
              fmt([version], len_version_max, csv_output) + \
              fmt_list(column_list, column_length_list, csv_output)


def print_what_depends_report(support_name_list, epics_version_list):
    """
    List all support modules and ioc's that depend on one or more support modules.
    :param support_name_list: list of support names that modules depend on
    :type support_name_list: list
    :param epics_version_list: list of EPICS versions to include in the output
    :type epics_version_list: list
    :return:
    """
    ioc_dict = {}
    support_dict = {}
    len_max = 0

    # Loop over all available EPICS versions
    for epics_version in epics_version_list:

        # Support modules
        for support_name in get_support_module_list(epics_version, MATURITY_PROD):
            # if skip_name(support_name, support_name_list) or skip_exclude(support_name, exclude_list):
            #     continue
            for support_version in get_support_module_versions(support_name, epics_version):
                sup = SupportModule(support_name, support_version, epics_version, MATURITY_PROD)
                dep_names = [x.name for x in sup.get_support_module_dependencies()]
                # print dep_names
                for name in dep_names:
                    if name in support_name_list:
                        # support_set.add(support_name)
                        if support_name not in support_dict:
                            support_dict[support_name] = set()
                        support_dict[support_name].add(name)
                        len_max = max(len_max, len(support_name))
        # print support_dict

        # IOC's
        ioc_name_list = get_ioc_list(epics_version, MATURITY_PROD)
        for ioc_target_name in ioc_name_list:
            for site in SITE_LIST:
                for ioc_version in get_ioc_versions(ioc_target_name, epics_version, site):
                    ioc_name = get_ioc_name(ioc_target_name, site)
                    # print ioc_name, ioc_version
                    ioc = IOC(ioc_name)
                    ioc.set_attributes(MATURITY_PROD, epics_version, site, ioc_target_name, ioc_version)
                    dep_names = [x.name for x in ioc.get_ioc_dependencies()]
                    # print dep_names
                    for name in dep_names:
                        if name in support_name_list:
                            # support_set.add(support_name)
                            if ioc_target_name not in support_dict:
                                ioc_dict[ioc_target_name] = set()
                            ioc_dict[ioc_target_name].add(name)
                            len_max = max(len_max, len(ioc_target_name))
        # print ioc_dict

        # Format output
        format_string = ' ' * 3 + '{0:' + str(len_max) + '}    {1}'
        print epics_version
        for item in sorted(support_dict):
            print format_string.format(str(item), str(list(support_dict[item])))
        for item in sorted(ioc_dict):
            print format_string.format(str(item), str(list(ioc_dict[item])))
        if len(epics_version_list) > 1:
            print ''


def command_line_arguments(argv):
    """
    Process command line arguments
    :param argv: command line arguments from sys.argv[1:]
    :type argv: list
    :return: argparse Namespace
    :rtype: Namespace
    """

    # Define text that will be printed at the end of the '-h' option
    epilog_text = """If no arguments are supplied, the list of all ioc's in the """ + \
                  """ redirector directory will be printed.""" + \
                  """ The default area is '""" + AREA_SUPPORT + """'.""" + \
                  """ The latest version of EPICS will be used if no version is specified."""

    parser = ArgumentParser(epilog=epilog_text)

    parser.add_argument(action='store',
                        nargs='*',
                        dest='name',
                        default=[],
                        help='ioc or support module name')

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
                        help='exclude matching items from the output')

    parser.add_argument('-e', '--epics',
                        action='store',
                        nargs='*',
                        dest='epics',
                        default=[],
                        help='Restrict output to EPICS version(s) (\'' + EPICS_ALL + '\' for all versions)')

    parser.add_argument('--qe', '--query-epics',
                        action='store_true',
                        dest='list_epics',
                        default=False,
                        help='list all versions of EPICS available in prod')
    parser.add_argument('--qs', '--query-support',
                        action='store_true',
                        dest='list_support',
                        default=False,
                        help='list all support packages available in prod')
    parser.add_argument('--qi', '--query-ioc',
                        action='store_true',
                        dest='list_ioc',
                        default=False,
                        help='list all ioc\'s available in prod')

    parser.add_argument('-d', '--what-depends',
                        action='store_true',
                        dest='depends',
                        default=False,
                        help='list support modules and ioc\'s in prod that depend on one or more modules')

    parser.add_argument('-r', '--report',
                        action='store_true',
                        dest='report',
                        default=False,
                        help='print dependency report of all support modules and ioc\'s in prod')

    parser.add_argument('--csv',
                        action='store_true',
                        dest='csv',
                        default=False,
                        help='print dependency report in csv format')

    parser.add_argument('-t', '--test',
                        action='store',
                        nargs=1,
                        dest='test',
                        default=[],
                        help=SUPPRESS)

    return parser.parse_args(argv)


if __name__ == '__main__':

    # Testing
    # args = command_line_arguments(['-h'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '--qe'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '--qs'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '--qi', '-e', 'all'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '-r'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '-i', '-r'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '-r', 'lib', 'motor'])
    # args = command_line_arguments(['-t', 'gem_sw_cp_3', '-d', 'slalib', 'timelib', 'astlib'])

    args = command_line_arguments(sys.argv[1:])

    # Override the data directory (testing)
    if args.test:
        Config.set_root_directory(args.test[0])

    # Abort if the redirector, production and work directories do not exist.
    # It doesn't make sense to continue if this information is not available.
    if not (isdir(Config.redirector_dir()) and isdir(Config.prod_dir()) and isdir(Config.work_dir())):
        print 'Redirector, prod and/or work directories do not exist'
        exit(1)

    # Determine what version(s) of EPICS will be used based on what options were selected.
    # Most reports require at least one version of EPICS to work properly.
    # It will be the latest version available if the user doesn't specify one.
    if any([args.list_epics, args.list_support, args.list_ioc, args.report, args.depends]):
        if args.epics:
            if EPICS_ALL in args.epics:
                epics_list = get_epics_versions(MATURITY_PROD)  # use all
            else:
                epics_list = args.epics  # use specified
        else:
            epics_list = [get_latest_epics_version(MATURITY_PROD)]  # use latest
    else:
        epics_list = args.epics
    # print epics_list

    # Sort the EPICS list in reverse order (we want to the the newest version of EPICS first)
    epics_list = sorted(epics_list, reverse=True)

    # Decide what to print based on the command line options.
    if args.list_epics:
        # list available EPICS versions
        print_epics_version_list()

    elif args.list_support:
        # list available support modules
        print_support_module_list(epics_list)

    elif args.list_ioc:
        # list available ioc's
        print_ioc_list(epics_list)

    elif args.depends:
        # who depends on what
        print_what_depends_report(args.name, epics_list)

    elif args.report:
        # matrix dependency reports
        if args.area == AREA_IOC:
            print_ioc_dependency_report(args.name, args.exclude, epics_list, args.csv)
        else:
            print_support_module_dependency_report(args.name, args.exclude, epics_list, args.csv)

    elif args.name:
        # report on entries in the redirector directory (i.e. in use)
        if args.area == AREA_IOC:
            print_active_ioc_dependencies(args.name, args.exclude, epics_list)
        else:
            print_active_support_module_dependencies(args.name, args.exclude, args.epics)

    else:
        # 'configure-ioc -L' output if no options are specified
        print_active_ioc_summary(args.exclude, epics_list, args.links)

    exit(0)
