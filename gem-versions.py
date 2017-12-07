#!/usr/bin/python
import sys
import re
from argparse import ArgumentParser, SUPPRESS
from os import listdir, readlink
from os import sep as directory_delimiter
from os import curdir as current_directory
from os.path import islink, isdir, join

# Software maturity values
MATURITY_PROD = 'prod'
MATURITY_WORK = 'work'

# Site values
SITE_CP = 'cp'
SITE_MK = 'mk'
SITE_LIST = [SITE_CP, SITE_MK]

# System types
AREA_IOC = 'ioc'
AREA_SUPPORT = 'support'
AREA_LIST = [AREA_IOC, AREA_SUPPORT]


def default_version(version):
    """
    Convert version number to 'work' if the version is an empty string.
    Otherwise leave it unchanged.
    :param version: version string
    :return: non empty version
    :rtype: str
    """
    return version if version else MATURITY_WORK


def get_epics_versions(maturity):
    """
    Return the list of EPICS versions available in the production directory.
    It is assumed that the EPICS directory start with an 'R'
    :param maturity
    :type maturity: str
    :return: list of EPICS versions
    :rtype: list
    """
    directory = Config.maturity_directory(maturity)
    if isdir(directory):
        return [f for f in listdir(directory) if re.search('^R', f) and isdir(join(directory, f))]
    else:
        return []


def get_dependencies(file_name, prod_support, work_support):
    """
    Get system dependencies. This is done by parsing the 'configure/RELEASE' files looking
    fo any dependencies to support modules. The support modules parameters should
    provide the lists of all prod/work support modules available for the EPICS version of interest.
    :param file_name: full RELEASE file name
    :type file_name: str
    :param prod_support: list of prod support modules available
    :type prod_support: list
    :param work_support: list of work support modules available
    :type work_support: list
    :return: list of tuples with support modules and versions
    :rtype: list
    """
    m = Macro()
    output_list = []
    # print 'get_dependencies', file_name
    try:
        f = open(file_name, 'r')
        for line in f:
            line = line.strip()
            # print line
            if re.search('^#', line):
                continue
            l_val, r_val = m.process_line(line)
            # print '+', l_val, r_val
            lst = r_val.split(directory_delimiter)
            if len(lst) > 1:
                if MATURITY_WORK in lst:
                    epics = lst[-3]
                    name = lst[-1]
                    version = 'work'
                    # print '=', name, version
                    if name in work_support:
                        output_list.append((name, version, epics, MATURITY_WORK))
                        # print '=', module_name, version
                elif MATURITY_PROD in lst:
                    epics = lst[-4]
                    name = lst[-2]
                    version = lst[-1]
                    if name in prod_support:
                        output_list.append((name, version, epics, MATURITY_PROD))
        f.close()
        # print '--', output_list
        return sorted(output_list)
    except IOError:
        return []


def get_support_module_list(epics_version, maturity):
    """
    Return the list of support modules available for a given EPICS version
    :param epics_version: EPICS version
    :type epics_version: str
    :param maturity: software maturity ('prod' or 'work')
    :type maturity: str
    :return: list of support modules available for the give EPICS version
    :rtype: list
    """
    # print 'get_support_module_list', epics_version, maturity
    directory = Config.maturity_directory(maturity)
    # print directory
    if isdir(directory):
        return listdir(join(directory, epics_version, 'support'))
    else:
        raise IOError('Directory ' + directory + ' does not exist')


class Config:
    """
    Class used to handle the location of the prod, work and redirector directories.
    It was introduced to change the location of these directories at run time to facilitate
    running this program against directories containing test data.
    """

    # Predefined root directories.
    DEFAULT_DIR = join(directory_delimiter, 'gem_sw')  # production
    ROOT_DIR_CP = join(current_directory, 'gem_sw_cp')  # test cp
    ROOT_DIR_MK = join(current_directory, 'gem_sw_mk')  # test mk

    # Root directory (used by other routines in this class)
    root_dir = DEFAULT_DIR

    def __init__(self):
        pass

    @classmethod
    def set_root_directory(cls, root_directory):
        """
        Set the root directory to a location other than the default.
        :param root_directory: software root directory
        :type root_directory: str
        :return: None
        """
        cls.root_dir = root_directory

    @classmethod
    def prod_dir(cls):
        """
        :return: production directory
        :rtype: str
        """
        return join(cls.root_dir, MATURITY_PROD)

    @classmethod
    def work_dir(cls):
        """
        :return: work directory
        :rtype: str
        """
        return join(cls.root_dir, MATURITY_WORK)

    @classmethod
    def redirector_dir(cls):
        """
        :return: redirector directory
        :rtype: str
        """
        return join(cls.prod_dir(), 'redirector')

    @classmethod
    def maturity_directory(cls, maturity):
        """
        Return the directory for a given software maturity
        :param maturity: software maturity (MATURITY_PROD or MATURITY_WORK)
        :type maturity: str
        :return: production or work directory
        :rtype: str
        """
        return cls.prod_dir() if maturity == MATURITY_PROD else cls.work_dir()


class Macro:
    """
    Class used to encapsulate the routines in charge of expanding
    a make file macro of the form $(macro).
    """

    def __init__(self):
        """
        The macro dictionary is used to keep track of the macros defined so far.
        The macro regular expression is precompiled to increase speed.
        """
        self.macro_dictionary = {}
        self.pattern = re.compile('\$\([a-zA-Z0-9_]+\)')

    @staticmethod
    def _cleaned_macro(macro):
        """
        Extract macro name from a macro reference.
        It strips the dollar sign and the parentheses from the definition.
        :param macro: macro definition (e.g. $(EPICS_RELEASE))
        :type macro: str
        :return: macro name (e.g. EPICS_RELEASE)
        :rtype: str
        """
        return re.sub('[$(){}]', '', macro).strip()

    def _replace_macros(self, line):
        """
        Replace macros in a line.
        :param line: line where macros should be replaced
        :type line: str
        :return: line with macros replaced
        :rtype: str
        """
        # print "_replace_macros", line
        # Look for matches only if there are macros in the dictionary
        if self.macro_dictionary:
            match_list = self.pattern.finditer(line)
            for match in match_list:
                macro_name = self._cleaned_macro(match.group())
                # print '++ match', macro_name, self.macro_dictionary
                if macro_name in self.macro_dictionary:
                    pattern = '\$\(' + macro_name + '\)'
                    line = re.sub(pattern, self.macro_dictionary[macro_name], line)
        return line

    def process_line(self, line):
        """
        :param line:
        :type line: str
        :return: line with replaced macros
        :rtype: str
        """
        # print 'process', line
        if re.search('.*=.*', line):
            l_val, r_val = line.split('=')
            l_val = l_val.strip()
            r_val = r_val.strip()
            # print '--', l_val, r_val
            r_val = self._replace_macros(r_val)
            self.macro_dictionary[l_val] = r_val
            # line = self._replace_macros(line)
        else:
            l_val, r_val = line, ''
        # print '-- [' + line + ']'
        return l_val, r_val


class Redirector:
    def __init__(self, exclude_list=[]):
        """
        Initializes the Redirector object. It builds the list of all IOCs in the redirector directory.
        IOC objects are stored in a dictionary indexed by the ioc name.
        The IOC objects contain all the information that can be extracted from the IOC links.
        The IOCs whose name match any of the strings in the exclude list are not included in the IOC lists.
        :param exclude_list: list of IOC's to exclude from the redirector directory
        :type exclude_list: list
        """
        self.ioc_dict = {}
        ioc_name_list = self._get_redirector_links(exclude_list)
        # print ioc_name_list
        for ioc_name in ioc_name_list:
            ioc = IOC(ioc_name, self._get_ioc_link(ioc_name))
            # print ioc
            self.ioc_dict[ioc_name] = ioc
            # print self.ioc_dict

    def __str__(self):
        return str(self.ioc_dict.keys())

    def get_ioc(self, ioc_name):
        """
        The the IOC object for a given name.
        :param ioc_name: IOC name
        :type ioc_name: str
        :return: IOC object
        :rtype IOC
        """
        return self.ioc_dict[ioc_name]

    def get_ioc_names(self):
        """
        Return the list of IOC names in the redirector directory.
        :return: list of names
        :rtype: list
        """
        # print 'get_ioc_names', self.ioc_name_list
        # return self.ioc_name_list
        return self.ioc_dict.keys()

    def get_ioc_list(self):
        """
        Return the list of IOC objects in the redirector directory.
        The list is built when the Redirector object is constructed.
        :return: list of IOC objects
        :rtype: list
        """
        return self.ioc_dict.values()

    @staticmethod
    def _get_redirector_links(exclude_list):
        """
        Return the list of links in the redirector directory
        :param exclude_list: list of IOCs to exclude from the list
        :type exclude_list: list
        :return: list of links
        :rtype: list
        """
        # print 'get_redirector_links', exclude_list
        redirector_directory = Config.redirector_dir()
        if isdir(redirector_directory):
            file_list = [f for f in listdir(redirector_directory) if islink(join(redirector_directory, f))]
            if exclude_list:
                m = re.compile('|'.join(exclude_list))
                file_list = [f for f in file_list if m.search(f) is None]
            # print '==', file_list
            return sorted(file_list)
        else:
            raise IOError('Directory ' + redirector_directory + ' does not exist')

    @staticmethod
    def _get_ioc_link(ioc_name):
        """
        Return the file pointed by the link corresponding to an IOC.
        The file referenced by the link is normally the boot binary.
        :param ioc_name: IOC name (e.g. mcs-ioc-cp)
        :type ioc_name: str
        :return: file referenced by the link
        :rtype: str
        """
        full_file_name = join(Config.redirector_dir(), ioc_name)
        if islink(full_file_name):
            return readlink(full_file_name)
        else:
            raise IOError(full_file_name + ' is not a link')


class IOC:
    """
    Class used to store the attributes of a single IOC:
    name:          IOC name in the redirector directory
    maturity       software maturity ('prod' or 'work')
    epics          EPICS version (e.g. R3.14.12.6)
    bsp            EPICS BSP (e.g. RTEMS-mvme2307)
    site:          IOC site ('cp' or 'mk')
    target_name:   IOC target name, i.e. name of the directory where the software is stored (e.g. 'mcs')
    version:       IOC version (e.g. 1-8-R314-2) or blank if maturity==work
    boot:          IOC boot image (e.g. gcal-cp-ioc.boot)
    """

    def __init__(self, ioc_name, ioc_link):
        self.name = ioc_name
        self.link = ioc_link
        (self.maturity, self.epics, self.bsp, self.site, self.target_name, self.version,
         self.boot) = self._split_ioc_link(ioc_link)

    def __str__(self):
        """
        :return: string representation of the IOC object
        :rtype: str
        """
        format_string = 'name={0}, maturity={1}, epics={2}, bsp={3}, site={4}, target={5}, version={6}, boot={7}'
        return format_string.format(self.name, self.maturity, self.epics, self.bsp, self.site, self.target_name,
                                    self.version if self.version else 'n/a', self.boot)

    @staticmethod
    def _split_ioc_link(link):
        """
        Split the link in its different components.
        The different elements in the link ar packed in a tuple as follows:
        0: maturity ('prod' or 'work')
        1: EPICS version (e.g. R3.14.12.6)
        2: EPICS BSP (e.g. RTEMS-mvme2307)
        3: IOC site ('cp' or 'mk')
        4: IOC target name (e.g. 'mcs')
        5: IOC version (e.g. 1-8-R314-2) or blank if maturity=work
        6: IOC boot image (e.g. gcal-cp-ioc.boot)
        :param link: file pointed to by the link in the redirector directory
        :type link: str
        :return: seven element tuple
        :rtype: tuple
        """
        lst = link.split(directory_delimiter)
        maturity = lst[2]
        epics_version = lst[3]
        ioc_target_name = lst[5]
        ioc_site = lst[6]
        ioc_version = lst[7] if maturity == MATURITY_PROD else ''
        epics_bsp = lst[-2]
        ioc_boot = lst[-1]
        return maturity, epics_version, epics_bsp, ioc_site, ioc_target_name, ioc_version, ioc_boot

    def _get_ioc_release_file(self):
        """
        Return the name of the ioc RELEASE file, for instance:
        /gem_sw/prod/R3.14.12.6/ioc/mcs/cp/1-2-BR314/configure/RELEASE
        :return: release file name
        :rtype: str
        """
        directory = Config.maturity_directory(self.maturity)
        if self.maturity == MATURITY_PROD:
            release_file = join(directory, self.epics, AREA_IOC, self.target_name, self.site,
                                self.version, 'configure', 'RELEASE')
        else:
            release_file = join(directory, self.epics, AREA_IOC, self.target_name, self.site,
                                'configure', 'RELEASE')
        return release_file

    def get_ioc_versions(self):
        """
        Get number ioc existing versions if maturity==prod, or an empty list if maturity==work
        :return: list of support package dependencies
        :rtype: list
        """
        # print 'get_ioc_versions', ioc_target_name, epics_version, ioc_site, maturity
        if self.maturity == MATURITY_PROD:
            directory = join(Config.prod_dir(), self.epics, 'ioc', self.target_name, self.site)
            # print directory
            if isdir(directory):
                return listdir(directory)
            else:
                return []  # no versions available
        else:
            return []  # no versions in work

    def get_ioc_dependencies(self):
        """
        Get the list of dependencies of the IOC to other support module.
        The list will be empty if there are no dependencies.
        :return: list of SupportModule objects
        :rtype: list
        """
        # print 'get_ioc_dependencies', ioc_target_name
        release_file = self._get_ioc_release_file()
        # print '-', release_file
        support_list = get_dependencies(release_file,
                                        get_support_module_list(self.epics, MATURITY_PROD),
                                        get_support_module_list(self.epics, MATURITY_WORK))
        # print '+', self.name, support_list
        if support_list:
            return [SupportModule(t[0], t[1], t[2], t[3]) for t in support_list]
        else:
            return []  # no dependencies


class SupportModule:
    """
    Class used to store the attributes of a single support module.
    The support module id is a unique identifier for the support module. The current is just a tuple
    containing of all the other attributes, but it could be (for instance) an md5 hash.
    name:      support module name (e.g. iocStats)
    version:   support module version (e.g. 1-8-R314-2) or blank if maturity==work
    maturity   software maturity ('prod' or 'work')
    epics      EPICS version (e.g. R3.14.12.6)
    id:        support module id
    """

    def __init__(self, support_name, support_version, support_epics, support_maturity):
        self.name = support_name
        self.version = support_version
        self.epics = support_epics
        self.maturity = support_maturity
        self.id = (self.name, self.version, self.epics, self.maturity)

    def __str__(self):
        """
        :return: string representation of the SupportModule object
        :rtype: str
        """
        format_string = 'name={0}, version={1}, epics={2}, maturity={3}'
        return format_string.format(self.name, self.version, self.epics, self.maturity)

    def _get_support_release_file(self):
        """
        Return the name of the ioc RELEASE file, for instance:
        /gem_sw/prod/R3.14.12.6/support/iocStats/3-1-14-3-BR314/configure/RELEASE
        :return: release file name
        :rtype: str
        """
        directory = Config.maturity_directory(self.maturity)
        if self.maturity == MATURITY_PROD:
            release_file = join(directory, self.epics, AREA_SUPPORT, self.name,
                                self.version, 'configure', 'RELEASE')
        else:
            release_file = join(directory, self.epics, AREA_SUPPORT, self.name,
                                'configure', 'RELEASE')
        return release_file

    def get_support_module_dependencies(self):
        """
        Get the dependencies of support module dependencies to other support modules.
        The list will be empty if there are no dependencies.
        :return: list of SupportModule objects
        :rtype: list
        """
        release_file = self._get_support_release_file()
        support_list = get_dependencies(release_file,
                                        get_support_module_list(self.epics, MATURITY_PROD),
                                        get_support_module_list(self.epics, MATURITY_WORK))
        # print support_list
        if support_list:
            return [SupportModule(t[0], t[1], t[2], t[3]) for t in support_list]
        else:
            return []  # no dependencies


# Output routines

def print_ioc_summary(print_links, argv):
    """
    Print version information for all IOC's in the redirector directory
    :param print_links: Print raw links (same output as configure-ioc -L)
    :type print_links: bool
    :param exclude_list: list of IOCs to exclude
    :param argv: command line arguments
    :type argv: argparse.Namespace
    :return None
    """
    rd = Redirector(argv.exclude)
    len_max = len(max(rd.get_ioc_names(), key=len))  # for formatting
    # print '-', rd.get_ioc_names()
    format_string_links = '{0:' + str(len_max) + '}  {1}'
    format_string_details = '{0:' + str(len_max) + '}  {1:5} {2:14} {3:15} {4:13} {5}'
    for ioc in sorted(rd.get_ioc_list(), key=lambda x: x.name):
        # print ioc
        if print_links:
            print format_string_links.format(ioc.name, ioc.link)
        else:
            print format_string_details.format(ioc.name, ioc.maturity, ioc.epics, ioc.bsp, ioc.version, ioc.boot)


def print_ioc_dependencies(ioc_name, argv):
    """
    Print IOC and dependency information. It will print the IOC version, EPICS version
    and EPICS BSP for the IOC, and the list of support modules and versions.
    :param ioc_name: IOC name (e.g. mcs-cp-ioc)
    :type ioc_name: str
    :param argv: command line arguments
    :type argv: argparse.Namespace
    :return None
    """
    # print 'print_ioc_dependencies', ioc_name
    rd = Redirector(argv.exclude)
    if ioc_name in sorted(rd.get_ioc_names()):
        ioc = rd.get_ioc(ioc_name)
        print '{0} {1} {2} {3} {4}'.format(ioc.name, default_version(ioc.version), ioc.boot, ioc.epics, ioc.bsp)
        for support_module in ioc.get_ioc_dependencies():
            print '   {0:16} {1}'.format(support_module.name, support_module.version)
    else:
        print ioc_name + ' not found'


def print_support_module_dependencies(support_module_name, argv):
    """
    Print the support module dependencies to other support modules, as well as the IOC's
    that depend on the support module.
    :param support_module_name: support module name
    :type support_module_name: str
    :param argv: command line arguments
    :type argv: argparse.Namespace
    :return None
    """
    # print 'print_support_module_dependencies', support_module_name

    # The ioc dictionary is used to create a cross reference between support modules and IOC objects.
    # It is indexed by the support module id. There won't be repeated dependencies.
    ioc_dict = {}

    # The support module dictionary is used to map support module id's with SupportModule objects.
    # Repeated dependencies will be discarded.
    sup_dict = {}

    # Populate the two dictionaries. We loop over all the ioc's in the redirector directory
    # and then iterate over the dependencies for each ioc.
    rd = Redirector(argv.exclude)
    for ioc in rd.get_ioc_list():
        # print '-', ioc
        for sup in ioc.get_ioc_dependencies():
            sup_dict[sup.id] = sup  # repeated entries are discarded at this point
            assert (isinstance(sup, SupportModule))
            # print '  ', sup
            if sup.name == support_module_name:
                if sup.id in ioc_dict:
                    ioc_dict[sup.id].append(ioc)
                else:
                    ioc_dict[sup.id] = [ioc]

    # Print the support module dependencies first, followed by the ioc's that use the support module
    for sup_id in sorted(ioc_dict):
        sup = sup_dict[sup_id]
        # print '--', sup
        assert (isinstance(sup, SupportModule))
        print sup.name, sup.version, sup.epics
        for dep in sorted(sup.get_support_module_dependencies(), key=lambda x: x.name):
            print '   {0:16} {1:16} {2}'.format(dep.name, default_version(dep.version), dep.epics)
        for ioc in sorted(ioc_dict[sup_id], key=lambda x: x.name):
            assert (isinstance(ioc, IOC))
            print '   {0:16} {1:16} {2}'.format(ioc.name, default_version(ioc.version), ioc.epics)
        print


def tests(argv):
    """
    :param argv: command line arguments
    :type argv: argparse.Namespace
    :return:
    """

    # Test - print routines
    print_ioc_summary(False, args)
    print_support_module_dependencies(args.module_name, args)
    print_support_module_dependencies('iocStats', args)

    # Test - general routines
    print 'default_version', default_version('1.0')
    print 'default_version', default_version('')
    print 'get_epics_versions', get_epics_versions(MATURITY_PROD)
    print 'get_epics_versions', get_epics_versions(MATURITY_WORK)
    print 'get_support_module_list', get_support_module_list('R3.14.12.6', MATURITY_PROD)
    print 'get_support_module_list', get_support_module_list('R3.14.12.4', MATURITY_WORK)
    print 'get_dependencies', \
        get_dependencies('./gem_sw/prod/R3.14.12.6/ioc/mcs/cp/1-2-BR314/configure/RELEASE',
                         get_support_module_list('R3.14.12.6', MATURITY_PROD),
                         get_support_module_list('R3.14.12.6', MATURITY_WORK))
    print 'get_dependencies', \
        get_dependencies('./gem_sw/prod/R3.14.12.6/support/iocStats/3-1-14-3-BR314/configure/RELEASE',
                         get_support_module_list('R3.14.12.6', MATURITY_PROD),
                         get_support_module_list('R3.14.12.6', MATURITY_WORK))

    # Test - Config
    for directory in (Config.ROOT_DIR_CP, Config.ROOT_DIR_MK):
        Config.set_root_directory(directory)
        print 'redirector dir', Config.redirector_dir()
        print 'prod dir', Config.prod_dir()
        print 'work dir', Config.work_dir()
        print 'mat_dir prod', Config.maturity_directory(MATURITY_PROD)
        print 'mat_dir work', Config.maturity_directory(MATURITY_WORK)

    # Test - redirector
    print Redirector()
    print Redirector([])
    print Redirector(['lab'])

    rd = Redirector()
    print 'get_ioc_names', rd.get_ioc_names()
    print 'get_ioc_list', rd.get_ioc_list()
    print 'get_ioc', rd.get_ioc('mcs-cp-ioc')

    # Test - IOC


if __name__ == '__main__':

    # Process command line arguments
    epilog_text = """The default area is '""" + AREA_SUPPORT + """'""" + \
                  """. The list of all IOC's in the redirector directory will be printed if no module is scpecified."""
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
    parser.add_argument(action='store',
                        nargs='?',
                        dest='module_name',
                        help='',
                        default=[])
    parser.add_argument('-r', '--root',
                        action='store',
                        nargs=1,
                        dest='root',
                        default='',
                        help=SUPPRESS)

    args = parser.parse_args(sys.argv[1:])
    # args = parser.parse_args(['-h'])
    # args = parser.parse_args(['-r', Config.ROOT_DIR_CP])
    # args = parser.parse_args(['iocStats', '-r', Config.ROOT_DIR_CP])
    # args = parser.parse_args(['-i', 'mcs-cp-ioc'])
    # args = parser.parse_args(['-i', 'labvme6-sbf-ioc'])
    # args = parser.parse_args(['-l'])
    # args = parser.parse_args(['-i', 'mcs-cp-ioc', '-x', 'lab'])
    # args = parser.parse_args([ '-x', 'sim', 'test'])
    # print args

    # tests(args)
    # exit(0)

    if args.root:
        Config.set_root_directory(args.root[0])

    # Abort if the redirector, production and work directories do not exist
    if not (isdir(Config.redirector_dir()) and isdir(Config.prod_dir()) and isdir(Config.work_dir())):
        print 'No redirector, prod or work directory found'
        exit(0)

    if args.module_name:
        if args.area == AREA_IOC:
            print_ioc_dependencies(args.module_name, args)
        else:
            print_support_module_dependencies(args.module_name, args)
            pass
    else:
        print_ioc_summary(args.links, args)

    exit(0)
