#! /usr/bin/env python
# -*- coding: utf-8 -*-

# ==================================================
# CYCLONE.PY
#
# Cyclone -- an easy backup and synchronization tool
# Copyright 2011
# Released under DWTFYWT Public License
# See LICENSE file for more details
# ===================================================

'''\
cyclone is an easy to use backup and two-way synchronization tool.
It aims to be lightweight and cross-platform.
'''

import sys, stat
from time import time, strftime, localtime
from os import sep as OSseparator
from os import stat as get_stat
from os import name as os_name
from os import walk, remove, makedirs
from optparse import OptionParser
from shutil import rmtree, copy2
from os.path import join, basename, getmtime
from os.path import exists, isdir, getsize, splitext


class Cyclone(object):
    'Cyclone base synchronization class'

    def __init__(self, source_dir, target_dir, \
                     mode = 'push', options_dic = None):
        self._source = source_dir
        self._target = target_dir
        self._mode = mode
        self._options = options_dic
        self._ex_patterns = options_dic['ex_patterns']

    def synchronize(self):
        'Main synchronization method'
        date = strftime('%d/%m/%y at %H:%M', localtime())
        self._print_out('=' * 50)
        self._print_out('Process beginning on %s' % date)
        start = time()

        if self._mode == 'push':
            self._sync(self._source, self._target)
        elif self._mode == 'mirror':
            self._sync(self._source, self._target)
            self._sync(self._target, self._source)

        out = 0 # temporary
        if out != 0:
            self._print_err('Process exited with error code !')
        else:        
            self._print_out('-' * 50)
            self._print_out('Synchronization complete ! (%d secondes)' % (time() - start))
            self._print_out('=' * 50)

    def _sync(self, source_dir, target_dir):
        'Synchronization control'
        if not isdir(source_dir):
            self._print_err('Source directory does not exist !')
            return 1
        
        if not basename(source_dir) == basename(target_dir):
            self._print_err('Source and target directories must not have the same basename !')
            return 1
        
        if not isdir(target_dir):
            self._print_out('First synchronization... copying all the tree\nand exiting. This can take a while, please wait.')
            
            try:
                makedirs(target_dir)
            except OSError:
                self._print_err('Unable to create target directory !')
                return 1
            
            self._update(source_dir, target_dir)
            
        else:   
            if self._options['cleanup']:
                self._clean(source_dir, target_dir)
            
            self._update(source_dir, target_dir)

    def _exclude_file(self, s_file, ex_path_data, ex_ext_data):
        'Applying exclusion filters'
        excluded = False
        if (self._ex_patterns['ex_path'] is not None):
            for ep in ex_path_data:
                if ep in s_file:
                    self._print_out('[ EXCLUDING FILE ] :\t %s' % s_file)
                    excluded = True
                    break
                
        if (self._ex_patterns['ex_ext'] is not None):
            for ext in ex_ext_data:
                if ext == splitext(s_file)[1]:
                    self._print_out('[ EXCLUDING FILE ] :\t %s' % s_file)
                    excluded = True
                    break     
                        
        if (self._ex_patterns['ex_size'] is not None) and \
                ((getsize(s_file) * 10**-6) >= self._ex_patterns['ex_size']) and (not excluded):
            self._print_out('[ EXCLUDING FILE ] :\t %s' % s_file)
            excluded = True

        return excluded

    def _update(self, source_dir, target_dir):
        'One-way synchronization method'
        file_error = False
        ls_source = self._get_files(source_dir)
 
        if self._ex_patterns['ex_path'] is not None:
            ex_path_data = self._ex_patterns['ex_path'].split(',')
            
        if self._ex_patterns['ex_ext'] is not None:
            ex_ext_data = self._ex_patterns['ex_ext'].split(',')

        for s_dir in ls_source[1]:        
            t_dir = s_dir.replace(source_dir, target_dir)

            if not exists(t_dir):
                excluded = False
                if self._ex_patterns['ex_path'] is not None:
                    for ep in ex_path_data:
                        if ep in s_dir:
                            self._print_out('[ EXCLUDING DIR ] :\t %s' % s_dir)
                            excluded = True
                            break
                    
                if not excluded:
                    try:
                        self._print_out('[ MAKING DIR ] :\t %s' % t_dir)
                        makedirs(t_dir)
                        
                    except IOError:
                        file_error = True
            
        for s_file in ls_source[0]:
            t_file = s_file.replace(source_dir, target_dir)

            if (not exists(t_file)) or (round(getmtime(t_file), 3) < round(getmtime(s_file), 3)):    
                excluded = self._exclude_file(s_file, ex_path_data, ex_ext_data)

                if not excluded:
                    if (os_name != 'posix') or (os_name == 'posix' and self._is_regular(s_file)):
                        self._print_out('[ UPDATING FILE ] :\t %s' % t_file)
                        try:
                            copy2(s_file, t_file)
                        except IOError:
                            file_error = True                
        if file_error:
            self._print_out("NOTE : some files were no longer available in source directory\n and thus were not be processed.")    

    def _clean(self, source_dir, target_dir):
        'clean extraneous files on target side'
        tree_change = False
        ls_target = self._get_files(target_dir)

        for t_dir in ls_target[1]:
            s_dir_ref = t_dir.replace(target_dir, source_dir)
 
        if not isdir(s_dir_ref):
            self._print_out('[ REMOVING DIR ] :\t %s' % t_dir)
            rmtree(t_dir, True)
            tree_change = True

        if tree_change == True:
            ls_target = self._get_files(target_dir)
        
        for s_file in ls_target[0]:
            s_file_ref = s_file.replace(target_dir, source_dir)
            if not exists(s_file_ref):
                self._print_out('[ REMOVING FILE ] :\t %s' % s_file)
                remove(s_file)

    def _get_files(self, pth):
        'make recursive file list from'
        files = []
        dirs = []
        for dirn, subn, filen in walk(pth):
            for f in filen:
                files.append(join(dirn, f)) 
                dirs.append(dirn)
        return (files, dirs)

    def _is_regular(self, pth, get_errors = False):
        'Test if a file is regular or not'
        try:
            return stat.S_ISREG(get_stat(pth)[0])
        except:
            if get_errors:
                return ('ERROR', pth)
            else:
                pass
                 
    def _print_out(self, txt):
        'verbose output message method'
        if self._options['verbose'] == True:
            sys.stdout.write(txt + '\n')
            
    def _print_err(self, txt):
        'std error printing method'
        sys.stderr.write("*** ERROR : " + txt + " ***\n")


if __name__ == '__main__':

    parser = OptionParser()
                        
    parser.add_option("-c", "--cleanup", dest='cleanup', action='store_true',
                        default=False,
                        help="Clean target directory (remove obsolet files)")
                        
    parser.add_option("-v", "--verbose", dest="verbose", action='store_true',
                        default=False,
                        help="Get verbose output")

    parser.add_option("-x", "--exclude-path", dest="ex_path",
                        default=None,
                        help="Exclude specific file path")

    parser.add_option("-S", "--exclude-size", dest="ex_size",
                        default=None,
                        help="Exclude files with size exceeding X Mo")

    parser.add_option("-X", "--exclude-ext", dest="ex_ext",
                        default=None,
                        help="Exclude files by extension")

    options, args = parser.parse_args()

    if options.ex_size is not None: options.ex_size = float(options.ex_size)
    ex_patterns = {'ex_path': options.ex_path,
                   'ex_size': options.ex_size,
                   'ex_ext': options.ex_ext }

    options_dic = {'verbose': options.verbose,
                   'cleanup': options.cleanup,
                   'ex_patterns': ex_patterns}

    try:
        source_dir = args[1]
        direction = args[0]
        target_dir = args[2]

        if direction not in ('push', 'mirror'):
            raise ValueError

    except:
        print('Usage : cyclone.py push|mirror source_directory target_directory [-OPTIONS]\nSee cyclone.py -h  \
               for more details.')
        sys.exit(1)
    
    if source_dir[-1] == OSseparator:
        source_dir = source_dir[:-1]

    target_dir = join(target_dir, basename(source_dir))    
    cyclone_sync = Cyclone(source_dir, target_dir, direction, options_dic)

    cyclone_sync.synchronize()
