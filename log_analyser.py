import glob
import os
import re
import sys
from pathlib import Path

OPTIONS = {
    '-h': '--help',
    '-f': '--file',
    '-p': '--path',
    '-s': '--sort'
}

QUERIES = [
    r'GET (/.*)\s+'
]

SPECIAL_PATTERNS = [
    r'/(t\d+)(\?|/)',
    r'/(\d+)(\?|/)',
    r'/application/applications.*/(.*)(\?|/)',
    r'/user/(.*)/.*(\?|/)',
    r'/(t\d+|\d+)$'
]

BLACKLIST = [
    r'GET /service/.*'
]

def bootstrap():
    def help_doc():
        print("\nTool for extracting HTTP request query usage from log files.\n")
        print(' ARGUMENT:           USAGE:')
        print("     -f --file       -f <file> - single or multiple files.")
        print("     -p --path       -p <path> - single or multiple paths.")
        print("     -s --sort       -s n - sort the output catorgies by the highest number of queries first.")
    
    args = CmdArgs.get_cmd_args()    
    if OPTIONS['-h'] in args or len(args) == 0: help_doc(); exit(0)
    return args


def main():
    args = bootstrap()
    print('====================== [ LOGFILE QUERY ANALYSER ] ======================\n')
    log_processor = QueryProcessor()
    
    def process_logs(files):
        catagories = log_processor.query_log_files(QUERIES, files)
        print_catagories(catagories, SORT_OPTION)
    
    def process_paths(paths):
        catagories = PathProcessor().process_paths(paths, log_processor.query_log_files, QUERIES)
        print_catagories(catagories, SORT_OPTION)
    
    SORT_OPTION = args[OPTIONS['-s']][0] if OPTIONS['-s'] in args else None
    if OPTIONS['-p'] in args:
        process_paths(args[OPTIONS['-p']])
    elif OPTIONS['-f'] in args:
        process_logs(args[OPTIONS['-f']])


def update_dictionary(src: dict, dest: dict):
    if src is None and dest is None: return
    
    for key in src.keys():
        if key in dest:
            dest[key] += src[key]
        else:
            dest[key] = src[key]


def print_catagories(catagories: dict, sort_type=None):
    if len(catagories) == 0:
        print('\nNo queries found for the given file/path supplied.')
        return
    
    print('\n[ Catagories ]')
    
    total_count = 0
    if sort_type == 'n':
        catagories = sorted(catagories.items(), key=lambda x: x[1], reverse=True)
        for catagory in catagories:
            count = catagories[1]
            total_count += count
            print(f'{catagory[0]} : {count}')
    else:
        for key in sorted(catagories.keys()):
            count = catagories[key]
            total_count += count
            print(f'{key} : {count}')
    
    print(f'\nTotal Query Types: {len(catagories)}')
    print(f'Total Query Count: {total_count}')


class CmdArgs:
    
    @staticmethod
    def get_cmd_args():
        cmd_args = {}
        valid_cmd = None
        has_argv = False
        
        for arg in sys.argv:
            cmd_arg, valid_arg = CmdArgs._check_arg_type(arg)
            
            if cmd_arg is not None and valid_arg:
                valid_cmd = cmd_arg
                if cmd_args.get(cmd_arg) is None:
                    cmd_args.update({cmd_arg : []})
                    has_argv = True
            else:
                if cmd_arg is None and valid_arg:
                    has_argv = False
                else:
                    if valid_cmd is not None and has_argv:
                        cmd_args[valid_cmd].append(arg)
        
        return cmd_args
    
    
    @staticmethod
    def _check_arg_type(input: str):
        def get_argv_key(input):
            return OPTIONS.get(input)
            
        if input.startswith('-') and (len(input) == 2):
            return get_argv_key(input), True
        if input.startswith('--'):
            return get_argv_key(input[1:3]), True
        return input, False


class QueryProcessor:
    
    def query_log_file(self, queries, file, path=None):
        filepath = os.path.join(os.getcwd() if path is None else path, file)
        print(f'Analysing: {file}  -->  {filepath}')
        
        def aggregate_query_params(params: list):
            param_string = ''
            for param in params:
                if '&' in param:
                    param_string += '&' + param.split('&')[1]
            return param_string

        query_types = {}
        with open(filepath, 'r') as f:
            for line in f:
                for x in BLACKLIST:
                    for match in re.finditer(x, line, re.S):
                        if match: line = None; break
                
                if line:
                    for query in queries:
                        for match in re.finditer(query, line, re.S):
                            query = match.group().split(' ')
                            http_verb, raw_query = query[0], query[1]
                            
                            if '?' not in raw_query and '=' not in raw_query:
                                query_params = raw_query
                                target_qstring = query_params
                            else:
                                query_params = raw_query.split('=')
                                target_qstring = query_params[0]
                            
                            special_pattern = None        
                            for pattern in SPECIAL_PATTERNS:
                                match = re.search(pattern, target_qstring)
                                if match:
                                    special_pattern = match.groups()[0]
                                    break
                            
                            if special_pattern:
                                if type(query_params) is str:
                                    qstring = query_params.split(special_pattern)
                                    param_string = '' if qstring[1] == '' else qstring[1]
                                else:
                                    qstring = query_params[0].split(special_pattern)
                                    param_string = qstring[1] + aggregate_query_params(query_params[1:])
                                    
                                qstring = f'{qstring[0]}X{param_string}'
                            else:
                                qstring = query_params[0] + aggregate_query_params(query_params[1:])
                                
                            qstring = f'{http_verb} {qstring}'
                            if qstring in query_types:
                                query_types[qstring] += 1
                            else:
                                query_types[qstring] = 1
        
        return query_types


    def query_log_files(self, queries, files, path=None):      
        t1, t2 = [], []
        for file in files:
            for f in glob.glob(file):
                x = os.path.normpath(Path(f).absolute())
                if not os.path.isdir(x):
                    pathfile = x.rsplit(os.sep, 1)
                    t1.append(pathfile[1])
                    t2.append(pathfile[0])
        
        if len(t1) > 0: files = t1; path = t2
        
        catagories = {}
        for index, file in enumerate(files):
            data = self.query_log_file(queries, file, path[index])
            update_dictionary(data, catagories)
        return catagories


class PathProcessor:
    
    def process_path(self, path, function, queries, *args, **kwargs):
        all_files, paths = [], []
        for root, dirs, files in os.walk(path, topdown=True):
            for f in files:
                all_files.append(f)
                paths.append(root)
        
        return function(queries, all_files, paths)
        

    def process_paths(self, paths, function, queries, *args, **kwargs):
        catagories = {}
        for path in paths:
            for path in glob.glob(path):
                path = os.path.normpath(Path(path).absolute())
                data = self.process_path(path, function, queries, *args, **kwargs)
                update_dictionary(data, catagories)
        return catagories


if __name__ == "__main__": main()
