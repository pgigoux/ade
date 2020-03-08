#!/usr/bin/python
"""
Auxiliary routines and classes used to handle version information.

Classes:
    Redirector: redirector links
    IOC: ioc version information
    SupportModule: support module version information
    Macro: make file macro substitutions
    Config: configuration; to support testing
"""
import os
import re
from os import listdir, readlink
from os import sep as directory_delimiter
from os.path import islink, isdir, join

# Software maturity values
MATURITY_PROD = 'prod'
MATURITY_WORK = 'work'
MATURITY_TEST = 'test'
MATURITY_LIST = [MATURITY_PROD, MATURITY_WORK, MATURITY_TEST]

# Site values
SITE_CP = 'cp'
SITE_MK = 'mk'
SITE_LIST = [SITE_CP, SITE_MK]

# System types
AREA_IOC = 'ioc'
AREA_SUPPORT = 'support'
AREA_LIST = [AREA_IOC, AREA_SUPPORT]

# EPICS version environment variable
ENV_EPICS_VERSION = 'GEM_EPICS_RELEASE'

# Value used to indicate all versions of EPICS in reports
EPICS_ALL = 'all'

# Value returned by str.find() where there's no match
NOT_FOUND = -1


def fmt(item_list, width, csv=False, csv_delimiter=','):
    """
    Format a list of items in columns of at least width characters (same with for all elements).
    This routine supports output in csv format as well as variable widths.
    :param item_list: list of items to format
    :type item_list: list
    :param width: column width, or None if no fixed width is required
    :type width: int
    :param csv: format as csv output
    :type csv: bool
    :param csv_delimiter: delimiter to use in csv output
    :type csv_delimiter: str
    :return: formatted line
    :rtype: str
    """
    format_string = ''
    if csv:
        for n in range(len(item_list)):
            format_string += '{:s}' + csv_delimiter
    else:
        for n in range(len(item_list)):
            if width is None:
                format_string += '{:s} '
            else:
                format_string += '{:' + str(width + 1) + 's} '
    return format_string.format(*item_list)


def fmt_list(item_list, width_list, csv=False, csv_delimiter=','):
    """
    Format a list of items in columns of at least width characters (separate width for each element).
    This routine supports output in csv format as well as variable widths.
    :param item_list: list of items to format
    :type item_list: list
    :param width_list: list of column widths (None if no fixed width is required)
    :type width_list: list
    :param csv: format as csv output
    :type csv: bool
    :param csv_delimiter: delimiter to use in csv output
    :type csv_delimiter: str
    :return: formatted line
    :rtype: str
    """
    # The item and width lists must be of the same size
    if len(item_list) != len(width_list):
        raise IndexError

    format_string = ''
    if csv:
        return fmt(item_list, 0, csv, csv_delimiter)
    else:
        for n in range(len(item_list)):
            # format_string += '{' + str(n) + ':' + str(width_list[n] + 1) + 's} '
            if width_list[n] is None:
                format_string += '{:s} '
            else:
                format_string += '{:' + str(width_list[n] + 1) + 's} '
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
    Auxiliary routine used to skip an ioc or support module from the output based on its EPICS version.
    It will return false if the epics version list is empty or contains EPICS_ALL.
    :param epics_version: ioc or support module epics version
    :type epics_version: str
    :param epics_version_list: list
    :type epics_version_list: list
    :return: boolean value indicating whether the epics version should be excluded or not
    :rtype: bool
    """
    if not epics_version_list or EPICS_ALL in epics_version_list:
        return False
    else:
        return epics_version not in epics_version_list


def get_ioc_name(ioc_target_name, site):
    """
    This is an auxiliary routine to return the ioc name from the ioc target name
    and the site in a consistent way all over the code.
    :param ioc_target_name: ioc target name (e.g. mcs)
    :type ioc_target_name: str
    :param site: site name ('cp' or 'mk')
    :type site: str
    :return: ioc name (e.g. mcs-cp-ioc)
    :rtype: str
    """
    return ioc_target_name + '-' + site + '-' + 'ioc'


def default_ioc_version(version, maturity):
    """
    Return the version number passed as an argument if the maturity is MATURITY_PROD, i.e.
    when a version is supposed to be defined. Otherwise return the maturity as the version.
    This routine is intended to always return a non-empty version string for printing purposes.
    :param version: version string
    :type version: str
    :param maturity: software maturity
    :type maturity: str
    :return: non empty version
    :rtype: str
    """
    return version if maturity == MATURITY_PROD else maturity


def get_epics_versions(maturity):
    """
    Return the list of EPICS versions available in the production directory.
    It is assumed that the EPICS directory start with an 'R'
    :param maturity: software maturity
    :type maturity: str
    :return: unsorted list of EPICS versions
    :rtype: list
    """
    directory = Config.maturity_directory(maturity)
    if isdir(directory):
        return [f for f in listdir(directory) if re.search('^R', f) and isdir(join(directory, f))]
    else:
        return []


def get_latest_epics_version(maturity):
    """
    Return the latest version of EPICS available.
    :param maturity: software maturity
    :type maturity: str
    :return:
    """
    epics_list = sorted(get_epics_versions(maturity), reverse=True)
    return epics_list[0] if epics_list else []


def get_default_epics_version(maturity):
    """
    Return the default version of EPICS in use.
    :param maturity: software maturity
    :type maturity: str
    :return:
    """
    try:
        version = os.environ[ENV_EPICS_VERSION]
    except KeyError:
        version = get_latest_epics_version(maturity)
    return version


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
                    version = MATURITY_WORK
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
                elif MATURITY_TEST in lst:
                    # no dependency information available for MATURITY_TEST
                    pass
        f.close()
        # print '--', output_list
        return sorted(output_list)
    except IOError:
        return []


def get_ioc_list(epics_version, maturity):
    """
    Return the list of ioc's available for a given EPICS version
    :param epics_version: EPICS version
    :type epics_version: str
    :param maturity: software maturity ('prod' or 'work')
    :type maturity: str
    :return: list of ioc (target) names available for the given EPICS version
    :rtype: list
    """
    # print 'ioc_list', epics_version, maturity
    directory = join(Config.maturity_directory(maturity), epics_version, 'ioc')
    # print directory
    if isdir(directory):
        return sorted(listdir(directory))
    else:
        return []
    pass


def get_ioc_versions(ioc_target_name, epics_version, site):
    """
    Get the versions available for a given IOC, EPICS version and site.
    If no versions are available it will return an empty list.
    :param ioc_target_name: ioc target name (e.g. 'mcs')
    :type ioc_target_name: str
    :param epics_version: EPICS version
    :type epics_version: str
    :param site: site name ('cp' or 'mk')
    :type site: str
    :return: list of versions available
    :rtype: list
    """
    directory = join(Config.maturity_directory(MATURITY_PROD), epics_version, 'ioc', ioc_target_name, site)
    # print directory
    if isdir(directory):
        return sorted(listdir(directory))
    else:
        return []


def get_support_module_list(epics_version, maturity):
    """
    Return the list of support modules available for a given EPICS version
    :param epics_version: EPICS version
    :type epics_version: str
    :param maturity: software maturity ('prod' or 'work')
    :type maturity: str
    :return: list of support modules available for the given EPICS version
    :rtype: list
    """
    # print 'get_support_module_list', epics_version, maturity
    directory = join(Config.maturity_directory(maturity), epics_version, 'support')
    # print directory
    if isdir(directory):
        return sorted(listdir(directory))
    else:
        return []


def get_support_module_versions(support_module_name, epics_version):
    """
    Get the versions available for a given support module and version of EPICS.
    If no versions are available it will return an empty list.
    :param support_module_name: support module name
    :type support_module_name: str
    :param epics_version: EPICS version
    :type epics_version: str
    :return: list of versions available
    :rtype: list
    """
    directory = join(Config.maturity_directory(MATURITY_PROD), epics_version, 'support', support_module_name)
    if isdir(directory):
        return sorted(listdir(directory))
    else:
        return []


class Config:
    """
    Class used to handle the location of the prod, work, test and redirector directories.
    It was introduced to group the routines to handle where the software is stored in one place,
    and also to allow switching to directories containing test data at run time.
    """

    # Default root directory.
    DEFAULT_DIR = join(directory_delimiter, 'gem_sw')  # production

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
        Return full path of the production directory
        :return: production directory
        :rtype: str
        """
        return join(cls.root_dir, MATURITY_PROD)

    @classmethod
    def work_dir(cls):
        """
        Return full path of the work directory
        :return: work directory
        :rtype: str
        """
        return join(cls.root_dir, MATURITY_WORK)

    @classmethod
    def test_dir(cls):
        """
        Return full path of the test directory
        :return: test directory
        :rtype: str
        """
        return join(cls.root_dir, MATURITY_TEST)

    @classmethod
    def redirector_dir(cls):
        """
        Return full path of the redirector directory
        :return: redirector directory
        :rtype: str
        """
        return join(cls.prod_dir(), 'redirector')

    @classmethod
    def maturity_directory(cls, maturity):
        """
        Return the full directory path for a given software maturity
        :param maturity: software maturity (MATURITY_PROD, MATURITY_WORK or MATURITY_TEST)
        :type maturity: str
        :return: production or work directory
        :rtype: str
        """
        if maturity == MATURITY_PROD:
            return cls.prod_dir()
        elif maturity == MATURITY_WORK:
            return cls.work_dir()
        else:
            return cls.test_dir()


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
        self.pattern = re.compile(r'\$\([a-zA-Z0-9_]+\)')

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
                    pattern = r'\$\(' + macro_name + r'\)'
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

    def __init__(self):
        """
        Initializes the Redirector object. It builds the list of all IOCs in the redirector directory.
        IOC objects are stored in a dictionary indexed by the ioc name.
        The IOC objects contain all the information that can be extracted from the IOC links.
        """
        self.ioc_dict = {}
        ioc_name_list = self._get_redirector_links()
        # print ioc_name_list
        for ioc_name in ioc_name_list:
            ioc = IOC(ioc_name)
            ioc.set_attributes_from_link(self._get_ioc_link(ioc_name))
            self.ioc_dict[ioc_name] = ioc

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
        return self.ioc_dict[ioc_name] if ioc_name in self.ioc_dict else None

    def get_ioc_names(self):
        """
        Return the list of IOC names in the redirector directory.
        :return: list of names
        :rtype: list
        """
        # print 'get_ioc_names', self.ioc_name_list
        return sorted(self.ioc_dict.keys())

    def get_ioc_list(self):
        """
        Return the list of IOC objects in the redirector directory.
        The list is built when the Redirector object is constructed.
        :return: list of IOC objects
        :rtype: list
        """
        return sorted(self.ioc_dict.values(), key=lambda x: x.name)

    @staticmethod
    def _get_redirector_links():
        """
        Return the list of links in the redirector directory
        :return: list of links
        :rtype: list
        """
        # print 'get_redirector_links', exclude_list
        redirector_directory = Config.redirector_dir()
        if isdir(redirector_directory):
            file_list = [f for f in listdir(redirector_directory) if islink(join(redirector_directory, f))]
            # if exclude_list:
            #     m = re.compile('|'.join(exclude_list))
            #     file_list = [f for f in file_list if m.search(f) is None]
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
    name:          IOC name in the redirector directory (e.g. mcs-cp-ioc)
    maturity       software maturity ('prod' or 'work')
    epics          EPICS version (e.g. R3.14.12.6)
    site:          IOC site ('cp' or 'mk')
    target_name:   IOC target name, i.e. name of the directory where the software is stored (e.g. 'mcs')
    version:       IOC version (e.g. 1-8-R314-2) or blank if maturity is MATURITY_WORK
    bsp            EPICS BSP (e.g. RTEMS-mvme2307)
    boot:          IOC boot image (e.g. gcal-cp-ioc.boot)
    """

    # def __init__(self, ioc_name):
    def __init__(self, ioc_name):
        self.name = ioc_name
        (self.maturity, self.epics, self.site, self.target_name, self.version,
         self.bsp, self.boot, self.link) = ('', '', '', '', '', '', '', '')
        # self.link = ioc_link
        # (self.maturity, self.epics, self.site, self.target_name, self.version,
        #  self.bsp, self.boot) = self._split_ioc_link(ioc_link)

    def set_attributes(self, maturity, epics, site, target_name, version, bsp='', boot=''):
        self.maturity = maturity
        self.epics = epics
        self.site = site
        self.target_name = target_name
        self.version = version
        self.bsp = bsp
        self.boot = boot

    def set_attributes_from_link(self, ioc_link):
        self.link = ioc_link
        (self.maturity, self.epics, self.site, self.target_name, self.version,
         self.bsp, self.boot) = self._split_ioc_link(ioc_link)

    def __str__(self):
        """
        :return: string representation of the IOC object
        :rtype: str
        """
        format_string = 'name={}, maturity={}, epics={}, site={}, target={}, version={}, bsp={}, boot={}'
        return format_string.format(self.name, self.maturity, self.epics, self.site, self.target_name,
                                    self.version if self.version else 'n/a', self.bsp, self.boot)

    @staticmethod
    def _split_ioc_link(link):
        """
        Split the link in its different components.
        It protects against links that do not follow the expected convention.
        The software maturity is forced to MATURITY_TEST if it's not any of
        the valid possibilities. This can happen in ill-formed links.

        The different elements in the link are packed in a tuple as follows:
        0: maturity ('prod' or 'work')
        1: EPICS version (e.g. R3.14.12.6)
        2: EPICS BSP (e.g. RTEMS-mvme2307)
        3: IOC site ('cp' or 'mk')
        4: IOC target name (e.g. 'mcs')
        5: IOC version (e.g. 1-8-R314-2) or blank if maturity=work
        6: IOC boot image (e.g. gcal-cp-ioc.boot)

        :param link: link in the redirector directory
        :type link: str
        :return: seven element tuple
        :rtype: tuple
        """
        lst = link.split(directory_delimiter)
        # print len(lst), lst, lst[2]
        maturity = lst[2] if len(lst) > 2 else MATURITY_TEST
        if maturity not in MATURITY_LIST:
            maturity = MATURITY_TEST
        if maturity != MATURITY_TEST:
            epics_version = lst[3] if len(lst) > 3 else ''
            ioc_target_name = lst[5] if len(lst) > 5 else ''
            ioc_site = lst[6] if len(lst) > 6 else ''
            ioc_version = lst[7] if len(lst) > 7 and maturity == MATURITY_PROD else ''
        else:
            epics_version = ''
            ioc_target_name = ''
            ioc_site = ''
            ioc_version = ''
        epics_bsp = lst[-2] if len(lst) > 1 else ''
        ioc_boot = lst[-1] if len(lst) > 0 else ''
        return maturity, epics_version, ioc_site, ioc_target_name, ioc_version, epics_bsp, ioc_boot

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
            return [SupportModule(t[0], t[1], t[2], t[3]) for t in sorted(support_list)]
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


if __name__ == '__main__':
    exit(0)
