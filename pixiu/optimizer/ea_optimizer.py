
import ast
import traceback
from multiprocessing import (Pool, Process, Manager, Queue, Value)
from pixiu.pxtester import PXTester
import astunparse
import os
import json5 as json
import itertools
import hashlib
from datetime import datetime
from ctypes import c_wchar_p

file_dir = os.path.dirname(__file__)

class EAOptimizer:
    """EA Optimizer"""

    def __init__(self, params):
        super(object, self).__init__()
        self.symbols = []
        self.variables = {}
        self.name = None
        self.source = None

    def config_path_to_abs_path(self, config_file_path, file_path):
        ret = file_path
        if not os.path.isabs(file_path):
            dir = os.path.dirname(config_file_path)
            ret = os.path.abspath(os.path.join(dir, file_path))
        return ret

    def parse_config(self, config_file):
        with open(config_file) as f:
            config_string = f.read()
            config = json.loads(config_string)
        optimization_config = config[0]['optimization_config']
        self.name = optimization_config['name']
        self.source = self.config_path_to_abs_path(config_file, optimization_config['source'])
        source_md5 = hashlib.md5(open(self.source, 'rb').read()).hexdigest()
        #
        symbols = optimization_config['optimization']['symbols']
        variables_dict = {}
        var_list_dict = {}
        flag_list = []
        for var in optimization_config['optimization']['variables']:
            var_name = optimization_config['optimization']['variables'][var].get('name', None)
            var_name = var if var_name is None else var_name
            var_val = optimization_config['optimization']['variables'][var]
            self.variables[var_name] = var_val
            flag_list.append(f"{var_name}-{var_val['start']}-{var_val['stop']}-{var_val['step']}")
            for v in range(var_val['start'], var_val['stop'], var_val['step']):
                n = f"{var_name}_{v}"
                variables_dict[n] = (var_name, v)
                vl = var_list_dict.get(var_name, [])
                vl.append(n)
                var_list_dict[var_name] = vl
        #
        var_list = []
        for key in var_list_dict:
            var_list.append(var_list_dict[key])

        prd_list = list(itertools.product(*var_list))
        opt_var_config = {}
        for prd in prd_list:
            val = {}
            key = ""
            for p in prd:
                v = variables_dict[p]
                val[v[0]] = v[1]
                key = f"{key}-{p}" if key else f"{p}"
                key = hashlib.md5(key.encode("utf-8")).hexdigest()
            opt_var_config[key] = val
        #
        flag_list.sort()
        flag = source_md5 + '-' + '-'.join(flag_list)
        flag_uid = hashlib.md5(flag.encode("utf-8")).hexdigest()
        test_config = self.config_path_to_abs_path(config_file, optimization_config['test_config'])
        opt_config = dict(type="optimization_config", config_uid=flag_uid,
                          symbols=symbols,
                          variables=opt_var_config,
                          test_config=test_config,
                          test_log_config=optimization_config['test_log_config'],
                          time_utc=datetime.utcnow().isoformat(),
                          ts_utc=datetime.utcnow().timestamp())
        return opt_config

    def save_optimization_config(self, file_name, config, opt_config_path):
        file_path = os.path.abspath(os.path.join(opt_config_path, f"{file_name}.json"))
        with open(file_path, 'w') as f:
            f.write(json.dumps(config, quote_keys=True))

    def load_optimization_config(self, file_name, opt_config_path):
        try:
            file_path = os.path.abspath(os.path.join(opt_config_path, f"{file_name}.json"))
            with open(file_path, 'r') as f:
                config = json.loads(f.read())
            return config
        except:
            traceback.print_exc()
        return None

    def generate_optimization_code_file(self, file_path, config):
        source = open(self.source).read()
        gloabl_dict = dict()
        local_dict = dict()
        # values_config = dict(ADX=123, ADX_PERIOD=456, NEAR_PERIOD=789, FAR_PERIOD=101112)
        values_config = config['variables']
        ps = ast.parse(source)
        for element in ps.body:
            if isinstance(element, ast.Assign):
                if isinstance(element.targets[0], ast.Name):
                    if isinstance(element.targets[0].ctx, ast.Store):
                        element_id = element.targets[0].id
                        if element_id in values_config:
                            new_val = values_config[element_id]
                            if new_val:
                                element.value.value = new_val #ast.Constant(value=new_val)
        code = compile(source, file_path, 'exec')
        exec(code, gloabl_dict, local_dict)
        new_source = astunparse.unparse(ps)
        code = compile(new_source, file_path, 'exec')
        exec(code, gloabl_dict, local_dict)
        with open(file_path, 'w') as f:
            f.write(new_source)
        code_md5 = hashlib.md5(new_source.encode("utf-8")).hexdigest()
        config['code_md5'] = code_md5
        config['script_path'] = file_path

    def run_tester(self, test_config_path, test_name, script_path, log_path, print_log_type, result_value, exec):
        graph_server = None
        try:
            pxt = PXTester(test_config_path=test_config_path, test_name=test_name, script_path=script_path,
                           log_path=log_path, print_log_type=print_log_type, test_result=result_value,
                           tester_graph_server=graph_server, test_graph_data=None)
            if exec:
                # pxt.execute("", sync=True)
                pxt.execute_script("", sync=True)
            else:
                pxt.execute("", sync=True)
            return True
        except:
            traceback.print_exc()
        return False

    def run_optimization_task(self, pool, manager, task_uid, task_config):
        test_config = task_config['test_config']
        test_name = task_config['test_name']
        script_path = task_config['script_path']
        log_path = task_config.get('log_path', None)
        test_log_config = task_config.get('test_log_config', [])
        tr = manager.Value(c_wchar_p, '')
        args = (test_config, test_name, script_path, log_path, test_log_config, tr, False)
        # results[test_name] = dict(result=tr, graph_data=gd)
        #
        # pool.apply_async(self.run_tester, args)
        self.run_tester(*args)

    def start_mp(self, args, manager, message_queue):
        self.test_names = args.testname
        #
        results = {}
        # manager = Manager()
        pool_args = []
        pool = Pool()
        script_path = self.get_script_path(args)
        if not script_path:
            print(f"ERROR: Invalid Script Path.")
            return 1

        # q = manager.Queue()
        for test_name in args.testname:
            tr = manager.Value(c_wchar_p, '')
            gd = manager.Value(c_wchar_p, '')
            graph_data = manager.Value(c_wchar_p, '')
            pool_args.append((args.testconfig, test_name, script_path, args.logpath, args.printlogtype, tr,
                              args.graph, message_queue, gd, args.exec))
            # results[test_name] = tr
            results[test_name] = dict(result=tr, graph_data=gd)
        #
        for pa in pool_args:
            pool.apply_async(self.run_tester, pa)
        #
        pool.close()
        pool.join()
        reports = {}
        ri = {}
        graph_data = {}
        for tn in results:
            try:
                res = json.loads(results[tn]['result'].value)
                ri[tn] = res
                #
                graph_data[tn] = json.loads(results[tn]['graph_data'].value)
            except:
                traceback.print_exc()
        #
        tag_data = dict(result=ri, utc_time=datetime.utcnow().isoformat())
        self.save_tag_data(self.tag, tag_data)
        self.save_tag_graph_data(self.tag, graph_data)
        #
        self.__convert_report(reports, ri)
        compare_reports = []
        self.get_compare_reports(args, compare_reports)
        self.output_report(reports, compare_reports)

    def optimize(self, config_file, output_path):
        #
        opt_config = self.parse_config(config_file)
        config_uid = opt_config['config_uid']
        test_config = opt_config['test_config']
        test_log_config = opt_config['test_log_config']
        dir = f"optimization/{config_uid}"
        opt_config_path = os.path.join(output_path, dir)
        os.makedirs(opt_config_path, exist_ok=True)
        file_name = config_uid
        self.save_optimization_config(file_name, opt_config, opt_config_path)
        opt_config = self.load_optimization_config(file_name, opt_config_path)
        pool = Pool()
        manager = Manager()
        for symbol in opt_config['symbols']:
            file_name = f"{config_uid}-{symbol}-tasks"
            opt_tasks_info = self.load_optimization_config(file_name, opt_config_path)
            if opt_tasks_info is None:
                opt_tasks_info = dict(tasks={})
            for task_uid in opt_config['variables']:
                task_info = opt_tasks_info.get(task_uid, {})
                task_tested = task_info.get('tested', False)
                dir = f"tasks/{symbol}/{task_uid}"
                opt_tasks_config_path = os.path.join(opt_config_path, dir)
                os.makedirs(opt_tasks_config_path, exist_ok=True)
                file_name = task_uid
                if task_tested:
                    task_config = self.load_optimization_config(file_name, opt_tasks_config_path)
                    if task_config is None:
                        task_tested = False
                if not task_tested:
                    variables = opt_config['variables'][task_uid]
                    test_name = f"test{symbol.upper()}"
                    task_config = dict(task_uid=task_uid, variables=variables, test_config=test_config,
                                       test_name=test_name,
                                       test_log_config=test_log_config,
                                       symbol=symbol)
                    file_path = os.path.join(opt_tasks_config_path, f"{task_uid}.py")
                    self.generate_optimization_code_file(file_path, task_config)
                    self.save_optimization_config(file_name, task_config, opt_tasks_config_path)
                    self.run_optimization_task(pool, manager, task_uid, task_config)

        pool.close()
        pool.join()

