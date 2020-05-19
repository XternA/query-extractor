import os
import re
import sys
from pathlib import Path

OPTIONS = {
    '-f': '--file',
    '-p': '--path',
    '-s': '--sort'
}

QUERIES = [
    'GET (/.*)\s+'
]

SPECIAL_PATTERNS = [
    '/(t\d+)(\?|/)',  # Tenant IDs
    '/(\d+)(\?|/)',   # Integer only IDs
    '/application/applications.*/(.*)(\?|/)',
    '/user/(.*)\/.*(\?|/)',
    '/(t\d+|\d+)$'
]

BLACKLIST = [
    'GET /service/.*'
]

def main():
    print('====================== [ LOGFILE QUERY ANALYSER ] ======================')
    args = CmdArgs.get_cmd_args()
        
    log_processor = LogProcessor()
    
    def process_logs(files):
        catagories = log_processor.query_log_files(QUERIES, files)
        print_catagories(catagories, SORT_OPTION)
    
    def process_paths(paths):
        path = PathPrcocess()
        catagories = path.analyse_paths(paths, log_processor.query_log_files, QUERIES)
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
    print('\n[ Catagories ]')

    if sort_type == 'n':
        catagories = sorted(catagories.items(), key=lambda x: x[1], reverse=True)
        for catagory in catagories:
            print(f'{catagory[0]} : {catagory[1]}')
    else:
        for key in sorted(catagories.keys()):
            print(f'{key} : {catagories[key]}')
    
    print(f'\nTotal Query Types: {len(catagories)}')


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


class LogProcessor:
    
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
                                target_query_string = query_params
                            else:
                                query_params = raw_query.split('=')
                                target_query_string = query_params[0]
                            
                            special_pattern = None        
                            for pattern in SPECIAL_PATTERNS:
                                match = re.search(pattern, target_query_string)
                                if match:
                                    special_pattern = match.groups()[0]
                                    break
                            
                            if special_pattern:
                                if type(query_params) is not list:
                                    query_string = query_params.split(special_pattern)
                                    param_string = '' if query_string[1] == '' else query_string[1]
                                else:
                                    query_string = query_params[0].split(special_pattern)
                                    param_string = query_string[1] + aggregate_query_params(query_params[1:])
                                    
                                query_string = f'{query_string[0]}X{param_string}'
                            else:
                                query_string = query_params[0] + aggregate_query_params(query_params[1:])
                                
                            query_string = f'{http_verb} {query_string}'
                            
                            if query_string in query_types:
                                query_types[query_string] += 1
                            else:
                                query_types[query_string] = 1
        
        return query_types


    def query_log_files(self, queries, files, path=None):
        catagories = {}
        for file in files:
            data = self.query_log_file(queries, file, path)
            update_dictionary(data, catagories)
        return catagories


class PathPrcocess:
    
    def analyse_path(self, path, function, queries, *args, **kwargs):
        path = Path(path).absolute()
        return function(queries, os.listdir(path), path)
        

    def analyse_paths(self, paths, function, queries, *args, **kwargs):
        catagories = {}
        for path in paths:
            data = self.analyse_path(path, function, queries, *args, **kwargs)
            update_dictionary(data, catagories)
        return catagories


if __name__ == "__main__": main()
