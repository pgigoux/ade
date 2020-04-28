#!/usr/bin/python
import sys
from argparse import ArgumentParser, SUPPRESS, Namespace
from os.path import isdir

from versions import IOC, SupportModule, Config
from versions import SITE_LIST, AREA_LIST, AREA_SUPPORT, AREA_IOC, EPICS_ALL
from versions import MATURITY_PROD
from versions import get_ioc_name
from versions import get_epics_versions, get_default_epics_version
from versions import get_ioc_list, get_ioc_versions
from versions import get_support_module_list, get_support_module_versions
from versions import skip_name, skip_exclude
from versions import fmt, fmt_list, sort_by_name_and_version

# String that will be appended to the support module or ioc name if it doesn't have any dependencies
NO_DEP_MARK = '(-)'

# Title that will be used in the column containg support or ioc version
VERSION_TITLE = 'Latest_Version'

# String used to mark empty dependency columns in text and csv outputs
EMPTY_DEPENDENCY_TEXT = '-'
EMPTY_DEPENDENCY_CSV = ' '


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
    This routine is a little messy because of all the column formatting needed for the text output.
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

    # String used to mark empty (no dependency) columns in the report
    empty_dependency = EMPTY_DEPENDENCY_CSV if csv_output else EMPTY_DEPENDENCY_TEXT

    # Iterate over all the elements in the dictionary. Each element is indexed by the name and the
    # version number, and the contents of each element is the list of supports modules it depends on.
    for key in dep_dict:

        # Determine the maximum length for each dependency (name and version).
        # The key is a tuple consisting of the name and version indexing the dictionary.
        # This will printed in the first and second column of the report.
        len_name_max = max(len_name_max, len(key[0]))
        len_version_max = max(len_version_max, len(key[1]))

        # Split the dependency names and versions in two separate list.
        # The module name is stored in one list and the versions in the other.
        # This is the place where the information for each dependency is extracted.
        dep_names[key] = [x.name for x in dep_dict[key]]
        dep_versions[key] = [x.version for x in dep_dict[key]]

        # Store the names into a set. This eliminates duplicate and empty names.
        referenced_names.update(dep_names[key])

        # Create a list of the maximum column length for each dependency.
        # This list will be used when formatting the output.
        for name, version in zip(dep_names[key], dep_versions[key]):
            # print name, version
            if name in column_lengths:
                column_lengths[name] = max(column_lengths[name], max(len(name), len(version)))
            else:
                column_lengths[name] = max(len(name), len(version))
                # print '-', name, column_lengths[name]

        # Keep track of the maximum name and version length for the dependencies.
        # Ignore those cases that don't have dependencies.
        try:
            len_dep_name_max = max(len_dep_name_max, len(max(dep_names[key], key=len)))
            len_dep_version_max = max(len_dep_version_max, len(max(dep_versions[key], key=len)))
        except ValueError:
            pass

    # The maximum length of the version column depends also on the column title
    len_version_max = max(len_version_max, len(VERSION_TITLE))

    # And the length of the first column will also depend on the EPICS version length.
    # Add the length of the string used to mark no dependencies.
    first_column_length = max(len_name_max, len(epics_version)) + len(NO_DEP_MARK)

    # Sort the set of support module names that are actually used.
    # Support modules that are not used are not included in this set.
    # Thus, the report will only include columns for relevant dependencies.
    referenced_names = sorted(referenced_names)

    # Create a list with the length of all the dependencies.
    # This list will be used while formatting the output.
    column_length_list = [column_lengths[x] for x in referenced_names]

    # Print title. The EPICS version will show up in the leftmost columns. This column will be
    # wide enough for the name and version of the support module or ioc.
    print fmt([epics_version], first_column_length, csv_output) + \
          fmt([VERSION_TITLE], len_version_max, csv_output) + \
          fmt_list(referenced_names, column_length_list, csv_output)

    # Print support modules or iocs. There will be one line per item. The first two columns
    # will have the name and version, followed by the versions of the dependency versions.
    # Only support modules and ioc's with dependencies will be listed in the output.
    # for name, version in sorted(dep_dict.keys()):
    for name, version in sort_by_name_and_version(dep_dict.keys()):

        # The dictionary key is the tuple (name, version)
        key = (name, version)

        # Mark those modules with no dependencies so they are easy to identify in the output
        if len(dep_names[key]) == 0:
            name += NO_DEP_MARK

        # Loop over the referenced dependencies (the report columns).
        # Trap those that are not a dependency.
        column_list = []
        for dep in referenced_names:
            try:
                idx = dep_names[key].index(dep)
                column_list.append(dep_versions[key][idx])
            except ValueError:  # no dependency
                column_list.append(empty_dependency)

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
    epilog_text = """Print version information of ioc\'s and support packages in the prod directory.""" + \
                  """If no arguments are supplied, the dependency matrix for support modules is generated. """ + \
                  """ The version of EPICS defined by GEM_EPICS_RELEASE is used by default."""

    parser = ArgumentParser(epilog=epilog_text)

    parser.add_argument(action='store',
                        nargs='*',
                        dest='name',
                        default=[],
                        help='list of ioc or support module names')

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

    # Test code
    # test_dir = '/Users/pgigoux/PycharmProjects/ade/gem_sw_cp_5'
    # args = command_line_arguments(['-h'])
    # args = command_line_arguments(['-t', test_dir])
    # args = command_line_arguments(['-t', test_dir, '--qe'])
    # args = command_line_arguments(['-t', test_dir, '--qs'])
    # args = command_line_arguments(['-t', test_dir, '--qi'])
    # args = command_line_arguments(['-t', test_dir, '--qi', '-e', 'all'])
    # args = command_line_arguments(['-t', test_dir, '-i'])
    # args = command_line_arguments(['-t', test_dir])
    # args = command_line_arguments(['-t', test_dir, '--csv'])
    # args = command_line_arguments(['-t', test_dir, 'astlib', 'motor'])
    # args = command_line_arguments(['-t', test_dir, '-i', 'crcs', 'motor'])
    # args = command_line_arguments(['-t', test_dir, '-d', 'timelib', 'astlib', 'motor'])
    # args = command_line_arguments(['-t', test_dir, '-d', 'timelib', 'astlib'])

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
    # It will be the default version available if the user doesn't specify one.
    if args.epics:
        if EPICS_ALL in args.epics:
            epics_list = get_epics_versions(MATURITY_PROD)  # use all
        else:
            epics_list = args.epics  # use specified
    else:
        epics_list = [get_default_epics_version(MATURITY_PROD)]

    # print epics_list

    # Sort the EPICS list in reverse order (we want to the the newest version of EPICS first)
    epics_list = sorted(epics_list, reverse=True)

    # Decide what to print based on the command line options.
    if args.list_epics:
        # list available EPICS versions
        print_epics_version_list()

    elif args.list_support:
        # list available support modules for all epics versions
        print_support_module_list(sorted(get_epics_versions(MATURITY_PROD), reverse=True))

    elif args.list_ioc:
        # list available ioc's
        print_ioc_list(sorted(get_epics_versions(MATURITY_PROD), reverse=True))

    elif args.depends:
        # what depends on what
        print_what_depends_report(args.name, epics_list)

    else:
        # report matrix
        if args.area == AREA_IOC:
            print_ioc_dependency_report(args.name, args.exclude, epics_list, args.csv)
        else:
            print_support_module_dependency_report(args.name, args.exclude, epics_list, args.csv)

    exit(0)
