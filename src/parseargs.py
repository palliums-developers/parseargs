#!/usr/bin/python3
import operator, types
import sys, getopt
import json
sys.path.append("..")
import traceback
import datetime
#from .models import BtcRpc
from enum import Enum

#module name
name="parseargs"

class parseargs:
    __args = {}
    __unique = []

    class argtype(Enum):
        LIST = 0x01
        STR  = 0x02
        JSON = 0x03

    def __init__(self, globals = None):
        self.globals = globals
        pass

    def __del__(self):
        pass

    def clear(self):
        self.__args = {}
        self.__unique = []

    def appendunique(self, opts_unique):
        if opts_unique is None:
            return
        self.__unique.append(list(opts_unique))

    def check_unique(self, opts):
        opt_list = [self.get_name(opt) for opt in opts]
        for uni in self.__unique:
            count = 0
            for opt in opt_list:
                if opt in uni:
                    count += 1
                if count > 1:
                    print(f"found Mutually exclusive parameters ({uni})")
                    sys.exit(2)


    def isvalid(self, name):
        arg = name[2:]
        return arg in self.__args.keys()

    def hasarg(self, name):
        for key in self.__args:
            arg = self.__args[key]["key"]
            if arg.find('-') >= 0 and name[2:] == arg.replace('-', ''):
                return True
        return False

    def get_name(self, opt):
        return opt.replace("-", "")

    def has_callback(self, opt):
        return self.__args[self.get_name(opt)]["callback"] is not None

    def callback(self, opt, *args):
        name = self.get_name(opt)
        self.exit_check_opt_arg_min(opt, args, self.__args[name]["min_args"])
        if self.__args[name]["hasarg"]:
            self.__args[name]["callback"](*args)
        else:
            self.__args[name]["callback"]()

    def append(self, name, desc, hasarg = False, arglist = None, optional_arglist = None, priority = 100, argtype = argtype.LIST, callback = None):

        arg_name = name
        if self.is_func_or_method(name):
            arg_name = name.__name__
            if not callback:
                callback = name

        if arg_name in self.__args:
            raise Exception(f"arg({arg_name}) is exists.")

        min_args = len(arglist) if arglist else 0

        arglist_all = ""
        if arglist:
            arglist_all = f"{arglist}"

        if optional_arglist:
            arglist_all += f" {optional_arglist}"

        if callback and arglist is None and optional_arglist is None:
            arg_defaults = callback.__defaults__
            arglist_all = list(callback.__code__.co_varnames[:callback.__code__.co_argcount])
            min_args = len(arglist_all) - len(arg_defaults) if arg_defaults else len(arglist_all)
            hasarg = len(arglist_all) > 0
            if arg_defaults:
                for i in range(len(arg_defaults)):
                    iarg = 0 - i - 1
                    arglist_all[iarg] = f"{arglist_all[iarg]}={json.dumps(arg_defaults[iarg]) if arg_defaults[iarg] is not None else None}"
            arglist_all = ', '.join(arglist_all)

        
        arglist_all = arglist_all.replace("[", "")
        arglist_all = arglist_all.replace("]", "")

        if hasarg:
            key = f"{arg_name}-"
            value = f"desc: {desc} format: --{arg_name} \"{arglist_all}\""
        else:
            key = arg_name
            value = f"desc: {desc} format: --{arg_name}"

        self.__args[arg_name] = {"key": key, \
                "value": value, \
                "required": arglist, \
                "required_count": len(arglist) if arglist else 0, \
                "optional": optional_arglist, \
                "optional_count": len(optional_arglist) if optional_arglist else 0, \
                "priority": priority, \
                "argtype": argtype, \
                "callback": callback, \
                "hasarg": hasarg, \
                "min_args": min_args}

    def remove(self, name):
        self.__args.pop(name)
        self.__unique.remove(name)

    def show_args(self):
        for key in list(self.__args.keys()):
            print("{}{} \n\t\t\t\t{}".format("--", key, self.__args[key]["value"].replace('\n', '')))
        sys.exit(2)

    def exit_error_opt(self, opt):
        print(self.__args[self.get_name(opt)]["value"])
        sys.exit(2)

    def __show_arg_info(self, info):
        print(info)


    def list_arg_name(self):
        return [ "--" + arg.replace('-', "") for arg in self.args.keys()]

    def show_help(self, args):
        if args is not None and len(args) > 0 and args[0] == "--help":
            self.show_args()

        if args is None or len(args) == 0:
            self.show_args()

        if args is None or len(args) != 2 or args[0] != "help" :
            find = False
            for name in args:
                if find == True:
                    find = False
                    continue
                if self.isvalid(name) == False:
                    self.show_args()
                if self.hasarg(name) == True:
                    find = True
            return

        name = args[1]

        self.__show_arg_info("--{} \n\t{}".format(name, self.__args[name]["value"].replace("format:", "\n\tformat:")))

        sys.exit(2)

    def __sort_opts(self, opts):
        sorted_opts = []
        for opt in opts:
            if isinstance(opt, tuple):
                opt_name = opt[0]
            args = self.__args[self.get_name(opt_name)]
            for i, sopt in enumerate(sorted_opts):
                if isinstance(sopt, tuple):
                    sopt_name = sopt[0]
                sargs = self.__args[self.get_name(sopt_name)]
                if args["priority"] < sargs["priority"]:
                    sorted_opts.insert(i, opt)
                    break
            else:
                sorted_opts.append(opt)
        return sorted_opts

    def check_opts(self, opts):
        names = [opt for opt, arg in opts]
        self.check_unique(names)

    def getopt(self, argv):
        opts, err_msg = getopt.getopt(argv, None, [arg["key"].replace('-', "=") for _, arg in self.__args.items()])
        opts = self.__sort_opts(opts)
        self.check_opts(opts)
        return (opts, err_msg)

    def is_matched(self, opt, names):
        if isinstance(names, str):
            names = [names]

        nl = [ "--" + name for name in names]
        return opt in nl

    def split_arg(self, opt, arg):
        if arg is None:
            return (0, None)

        #arg is not json format
        arg_list = None
        name = self.get_name(opt)
        if self.__args[name]["argtype"] == self.argtype.STR:
            arg_list = [arg]
        elif self.__args[name]["argtype"] == self.argtype.STR:
            arg_list = json.loads(argstr)
        else:
            if "," not in arg:
                argstr = "[\"{}\"]".format(arg)
            else:
                argstr = "[{}]".format(arg)
            arg_list = json.loads(argstr)
        return  (len(arg_list), arg_list)

    def exit_check_opt_arg(self, opt, arg, arg_count):
        count, arg_list = self.split_arg(opt, arg)
        counts = []
        if isinstance(arg_count, int):
            counts.append(arg_count)
        if count not in counts:
            self.exit_error_opt(opt)

    def exit_check_opt_arg_min(self, opt, arg, arg_count):
        if not isinstance(arg, str):
            count = len(arg)
        else:
            count, arg_list = self.split_arg(opt, arg)

        if count < arg_count:
            self.exit_error_opt(opt)

    def is_func_or_method(self, func):
        return isinstance(func, types.MethodType) or isinstance(func, types.FunctionType)

    def append_func(self, func):
        if not self.is_func_or_method(func): raise Exception(f"{func} is not FunctionType or MethodType")
        func_name = func.__name__
        if func_name not in self.globals: self.globals.update({func_name:func})

    def get_func_name(self, value):
        names = self.get_funcs()
        if value.isnumeric():
            value= names[int(value)]
        return value

    def get_funcs(self):
        func_names = {} 
        index = 0
        no_includes = ["call_func"]

        self.append_func(self.show_funcs)
        self.append_func(self.show_func_args)
        for key, value in self.globals.items():
            if self.is_func_or_method(value) and key not in no_includes:
                func_names.update({index: key})
                index += 1
        return func_names
    
    def show_funcs(self):
        print(f"funcs list: {self.get_funcs()}")
    
    def call_func(self, name, *args, **kwargs):
    
        name = self.get_func_name(name)
        callback = self.globals[name]
        arglist_all = self.get_func_args(name)
        if (len(args) == 0 and len(kwargs) == 0):
            return callback()
        elif len(args) > 0 and len(kwargs) > 0:
            return callback(*args, **kwargs)
        elif len(args) > 0 and len(kwargs) == 0:
            return callback(*args)
        elif len(args) == 0 and len(kwargs) > 0:
            return callback(**kwargs)
    
    def get_func_args(self, name):
        name = self.get_func_name(name)

        callback = self.globals[name]
        arg_defaults = callback.__defaults__
        arglist_all = list(callback.__code__.co_varnames[:callback.__code__.co_argcount])
        min_args = len(arglist_all) - len(arg_defaults) if arg_defaults else len(arglist_all)
        hasarg = len(arglist_all) > 0
        if arg_defaults:
            for i in range(len(arg_defaults)):
                iarg = 0 - i - 1
                arglist_all[iarg] = f"{arglist_all[iarg]}={json.dumps(arg_defaults[iarg]) if arg_defaults[iarg] else None}"
        arglist_all = ', '.join(arglist_all)
        return arglist_all
    
    def show_func_args(self, name):
        arglist_all = self.get_func_args(name)
        name = self.get_func_name(name)
        print(f"{name}({arglist_all})")
    
    def show_args_list(self):
        funcs_list = [f"{name} : {index}" for index, name in self.get_funcs().items()]
        help_info = str(f" --help show help \n --fix FUNC_NAME ARGS. call functins(name : index) input name or index:.{'.'.join(funcs_list)} \n --main ARGS call test_narmal \n --func_args FUNC_NAME show founcs args") 
        help_info = help_info.replace(".", "\n\t")
        print(help_info)
    
    def test(self, argv):
        if len(argv) == 1:
            self.show_args_list()
        elif argv[1] == "--func_args" and len(argv) == 3:
            show_func_args(argv[2])
        elif argv[1] == "--fix" and len(argv) >= 3:
            ret = self.call_func(argv[2], *argv[3:])
            if ret :   print(ret);
        elif argv[1] == "--main":
            self.test_narmal(len(argv) - 2, argv[2:])
        else: 
            self.show_args_list()
