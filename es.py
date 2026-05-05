#!/usr/bin/env python
"""es - Everything Search CLI wrapper using Everything SDK"""
import sys, os, ctypes, argparse

DLL_PATH = r'D:\GenericAgent\temp\everything-sdk\dll\Everything64.dll'

def get_dll():
    return ctypes.WinDLL(DLL_PATH)

def search(query, max_results=20, match_case=False, match_whole=False, path_only=False):
    dll = get_dll()
    # Set up function prototypes
    dll.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
    dll.Everything_SetSearchW.restype = None
    dll.Everything_SetMax.argtypes = [ctypes.c_uint]
    dll.Everything_SetMax.restype = None
    dll.Everything_SetMatchCase.argtypes = [ctypes.c_bool]
    dll.Everything_SetMatchCase.restype = None
    dll.Everything_SetMatchWholeWord.argtypes = [ctypes.c_bool]
    dll.Everything_SetMatchWholeWord.restype = None
    dll.Everything_QueryW.argtypes = [ctypes.c_bool]
    dll.Everything_QueryW.restype = ctypes.c_bool
    dll.Everything_GetNumResults.restype = ctypes.c_uint
    dll.Everything_GetResultFullPathNameW.argtypes = [ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
    dll.Everything_GetResultFullPathNameW.restype = ctypes.c_uint
    dll.Everything_GetResultFileNameW.argtypes = [ctypes.c_uint]
    dll.Everything_GetResultFileNameW.restype = ctypes.c_wchar_p
    dll.Everything_GetResultPathW.argtypes = [ctypes.c_uint]
    dll.Everything_GetResultPathW.restype = ctypes.c_wchar_p
    dll.Everything_Reset.restype = None

    dll.Everything_Reset()
    dll.Everything_SetSearchW(query)
    dll.Everything_SetMax(max_results)
    dll.Everything_SetMatchCase(match_case)
    dll.Everything_SetMatchWholeWord(match_whole)
    
    if not dll.Everything_QueryW(True):
        print("Query failed. Is Everything running?", file=sys.stderr)
        return
    
    num = dll.Everything_GetNumResults()
    buf = ctypes.create_unicode_buffer(32767)
    
    for i in range(num):
        dll.Everything_GetResultFullPathNameW(i, buf, 32767)
        if path_only:
            path = buf.value
            idx = path.rfind('\\')
            print(path[:idx] if idx > 0 else path)
        else:
            print(buf.value)
    
    dll.Everything_Reset()

def main():
    parser = argparse.ArgumentParser(description='Everything Search CLI')
    parser.add_argument('query', help='Search query (supports wildcards, regex, etc.)')
    parser.add_argument('-n', '--max-results', type=int, default=20, help='Max results (default: 20)')
    parser.add_argument('-c', '--match-case', action='store_true', help='Case sensitive search')
    parser.add_argument('-w', '--match-whole', action='store_true', help='Match whole word')
    parser.add_argument('-p', '--path-only', action='store_true', help='Output directory paths only')
    args = parser.parse_args()
    search(args.query, args.max_results, args.match_case, args.match_whole, args.path_only)

if __name__ == '__main__':
    main()
