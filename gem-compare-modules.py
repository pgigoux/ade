#!/usr/bin/env python3

import os
import re
import sys
from docopt import docopt
from functools import partial
from collections import namedtuple, defaultdict
filename=os.path.basename(__file__)

__doc__ = f"""
Module Compare

Usage:
  {filename} [-v] [-e EPICS] [-s SITE] IOC:VERSION IOC:VERSION...
  {filename} -h | --help

Options:
  -h --help           Show this screen
  -v --verbose        Be verbose. This can be helpful if the script can't seem to find an IOC
  -e --epics=EPICS    Defaults to $GEM_EPICS_RELEASE. If the variable is not declared, then this argument becomes mandatory.
  -s --site=SITE      Defaults to $GEM_SITE. If the variable is not declared, then this argument becomes mandatory..
  IOC-VERSION         Name of an IOC and version to use as the source. Version can either be a numeric one (taken out of $PROD/ioc/IOC), 'current', 'work', or a path to the $TOP directory of the IOC. If no version is provided, 'current' is assumed.
                      If 'current' is given, the $TOP will be discovered making use of the links at the redirector, and then IOC must match the system name in there.
"""

Environment = namedtuple('Environment', 'root release site')
Support = namedtuple('Support', 'var path version')
IocData = namedtuple('IocData', 'unique_id target full_name site top')

ROOT = '/gem_sw'
RESET_COLOR  = '\x1b[0m'
BRIGHT_GREEN = '\x1b[38;5;46m'
BRIGHT_RED   = '\x1b[38;5;196m'

log = None
def log_ver(text, verbose):
    if verbose:
        print(text)

def expand_variable(var_dict, value):
    for name, sub in var_dict.items():
        value = value.replace(f'$({name})', sub)
    return value

def extract_version(path):
    base, potential = os.path.split(path)
    return potential if re.match(r'^\d+-\d+', potential) else None

EXCLUDE_MODULES = set(['EPICS_RELEASE', 'EPICS_BASE'])

def extract_support(env, ioc_name, top):
    var_dict = {}
    release_info = []
    try:
        for line in open(os.path.join(top, 'configure', 'RELEASE')):
            line = line.split('#')[0].strip()
            if line:
                try:
                    var_name, value = [text.strip() for text in line.split('=')]
                    expanded = expand_variable(var_dict, value)
                    if var_name not in EXCLUDE_MODULES and os.path.exists(os.path.join(expanded, 'lib')):
                        release_info.append(Support(var_name, expanded, extract_version(expanded)))
                    var_dict[var_name] = expanded
                except ValueError:
                    pass
    except IOError as e:
        raise IOError(f"Extracting modules for {ioc_name}: No such file {e.filename}")

    return release_info

def mod_version(mod):
    return mod.version if mod.version is not None else mod.path

def get_ioc_from_target(target, site):
    return target if target.endswith('-ioc') else f"{target}-{site}-ioc"

class IocDecoder:
    def __init__(self, env):
        self.seen = defaultdict(int)
        self.env = env

    def decode(self, ioc_ver):
        ioc_name_raw, _, version = ioc_ver.partition(':')
        ioc_target, _, ioc_site_maybe = ioc_name_raw.partition('/')
        ioc_site = ioc_site_maybe or self.env.site
        ioc_name = get_ioc_from_target(ioc_target, ioc_site)

        if not version:
            version = 'current'

        path = None
        if version.lower() == 'current':
            link = os.path.join(self.env.root, 'prod', 'redirector', ioc_name)
            if not os.path.exists(link):
                raise IOError(f"Error finding '{ioc_ver}': No such link under the redirector")
            path = os.path.realpath(link)
            while link != '/':
                path, last = os.path.split(path)
                if last == 'bin':
                    break
            else:
                raise IOError(f"Error finding '{ioc_ver}': Non-standard deployment")
        elif version.lower() == 'work':
            path = os.path.join(self.env.root, 'work', self.env.release, 'ioc', ioc_target, ioc_site)
        elif os.path.exists(version):
            path = os.path.abspath(version)
        else: # Assume this is a numeric version
            path = os.path.join(self.env.root, 'prod', self.env.release, 'ioc', ioc_target, ioc_site, version)
        if not os.path.exists(path):
            raise IOError(f"Error finding '{ioc_ver}': Path does not exist '{path}'")

        seen = self.seen[ioc_target]
        unique = ioc_target if not seen else f'{ioc_target}({seen + 1})'
        self.seen[ioc_target] += 1

        return IocData(unique_id=unique,
                       target=ioc_target,
                       full_name=ioc_name,
                       site=ioc_site,
                       top=path)

if __name__ == '__main__':
    args = docopt(__doc__, version="Module Compare 1.0", options_first=True)

    release = args['--epics'] or os.environ.get('GEM_EPICS_RELEASE')
    if release is None:
        print("The EPICS release is undefined. Please, try again providing --epics")
        sys.exit(1)

    # Test for site
    site = args['--site'] or os.environ.get('GEM_SITE')
    if site is None:
        print("The site is undefined. Please, try again providing --site")
        sys.exit(1)
    site = site.lower()
    log = partial(log_ver, verbose=args['--verbose'])

    env = Environment(ROOT, release, site)

    ioc_decoder = IocDecoder(env)

    try:
        ioc_details = list(map(ioc_decoder.decode, args['IOC:VERSION']))
    except (IOError, NotImplementedError) as e:
        print(e)
        sys.exit(-1)

    ioc_info = {}
    widest   = {}
    all_modules = set()
    try:
        for ioc in ioc_details:
            dct = {}
            mod_list = extract_support(env, ioc.target, ioc.top)
            widest[ioc.unique_id] = len(ioc.unique_id)
            for mod in mod_list:
                version = mod_version(mod)
                widest[ioc.unique_id] = max(len(version), widest[ioc.unique_id])
                dct[mod.var] = version
                all_modules.add(mod.var)
            ioc_info[ioc.unique_id] = dct
    except IOError as e:
        print(e)
        sys.exit(-1)

    ioc_names = [ioc.unique_id for ioc in ioc_details]
    widest_name = max(len(uid) for uid in ioc_names)
    for ioc in ioc_details:
        log(f"{ioc.unique_id:{widest_name}}: {ioc.top}")

    widest_module = max(len(mname) for mname in all_modules)
    print(f"{'':{widest_module}} {'  '.join(ioc.center(widest[ioc]) for ioc in ioc_names)}")
    for mod in sorted(all_modules):
        elements = [f"{ioc_info[ioc].get(mod, '---'):{widest[ioc]}}" for ioc in ioc_names]
        color = BRIGHT_RED if len(set(e.strip() for e in elements)) != 1 else ''
        print(f"{color}{mod:{widest_module}} {'  '.join(elements)}{RESET_COLOR}")
