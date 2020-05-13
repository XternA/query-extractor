import os
import re
import sys
from pathlib import Path
import pprint

OPTIONS = {
    '-f': '--file',
    '-p': '--path',
    '-o': '--output',
    '-t': '--type',
    '-q': '--query',
}

QUERIES = (
    'GET \/.*\?((.*=.*)(&?))+',
    # 'POST /measurement/measurements',
)

def main():
    print('====================== [ LOGFILE QUERY ANALYSER ] ======================')
    args = CmdArgs.get_cmd_args()
        
    log_processor = LogProcessor()
    pp = pprint.PrettyPrinter(indent=4)
    
    def process_logs(files):
        catagories = log_processor.query_log_files(QUERIES, files)
        pp.pprint(catagories)
    
    def process_paths(paths):
        path = PathPrcocess()
        catagories = path.analyse_paths(paths, log_processor.query_log_files, QUERIES)
        pp.pprint(catagories)
        
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

        query_types = {}
        with open(filepath, 'r') as f:            
            for line in f:
                for query in queries:
                    for match in re.finditer(f'{query}', line, re.S):
                        query = match.group().split(' ')
                        
                        http_verb = query[0]
                        query_params = query[1].split('=')
                        query_string = query_params[0]
                        
                        uri_has_id = False
                        temp = query_params[0].split('?')[0].split('/')
                        for x in temp:
                            if x.isdigit():
                                uri_has_id = True
                                break
                        
                        if uri_has_id:
                            query_string = query_params[0].rsplit('/', 1)
                            
                            if query_string[1][0].isdigit():
                                if '?' in query_string[1]:
                                    query_string = query_string[0] + '/X?' + query_string[1].split('?')[1]
                                else:
                                    query_string = query_string[0] + '/X/' + query_string[1].split('/')[1]
                            elif query_string[0][-1:].isdigit():
                                query_string = query_string[0].rsplit('/', 1)[0] + '/X/' + query_string[1]
                        else:
                            for param in query_params[2:]:
                                if '&' in param:
                                    query_string += '&' + param.split('&')[1]
                            
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
