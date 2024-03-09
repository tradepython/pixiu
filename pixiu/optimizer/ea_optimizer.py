
import ast
import time
import traceback
from multiprocessing import (Pool, Process, Manager, Queue, Value)
from multiprocessing.pool import AsyncResult
from pixiu.pxtester import PXTester
import astunparse
import os
import json5 as json
import itertools
import hashlib
from datetime import datetime
from ctypes import c_wchar_p
from enum import Enum

file_dir = os.path.dirname(__file__)

class TaskStatus(int, Enum):
    WAITING = 0
    RUNNING = 100
    FINISHED = 200
    ERROR = 300


class EAOptimizer:
    """EA Optimizer"""

    def __init__(self, params):
        super(object, self).__init__()
        self.symbols = []
        self.variables = {}
        self.name = None
        self.source = None
        self.stop_optimize = False
        self.opt_tasks_info_dict = {'tasks': {}, 'reports': {}}
        self.report_item_template = {
            "balance": {},
            "total_net_profit": {},
            "total_net_profit_rate": {},
            "sharpe_ratio": {},
            "sortino_ratio": {},
            "absolute_drawdown": {},
            "max_drawdown": {},
            "max_drawdown_rate": {},
            "min_volume": {},
            "max_volume": {},
            "total_trades": {},
            "profit_trades": {},
            "win_rate": {},
            "trade_max_profit": {},
            "trade_avg_profit": {},
            "trade_max_loss": {},
            "trade_avg_loss": {},
            "loss_trades": {},
            "gross_profit": {},
            "gross_loss": {},
            "short_positions": {},
            "short_positions_win": {},
            "long_positions": {},
            "long_positions_win": {},
            "max_consecutive_wins": {},
            "max_consecutive_wins_money": {},
            "max_consecutive_losses": {},
            "max_consecutive_losses_money": {},
            }

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

    def make_opt_config_file_path(self, file_name, opt_config_path):
        file_path = os.path.abspath(os.path.join(opt_config_path, f"{file_name}.json"))
        return file_path

    def save_optimization_config(self, file_path, config):
        # file_path = self.make_opt_config_file_path(file_name, opt_config_path)
        with open(file_path, 'w') as f:
            f.write(json.dumps(config, quote_keys=True))

    def load_optimization_config(self, file_path):
        try:
            # file_path = self.make_opt_config_file_path(file_name, opt_config_path)
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
        # code = compile(source, file_path, 'exec')
        # exec(code, gloabl_dict, local_dict)
        new_source = astunparse.unparse(ps)
        # code = compile(new_source, file_path, 'exec')
        # exec(code, gloabl_dict, local_dict)
        with open(file_path, 'w') as f:
            f.write(new_source)
        code_md5 = hashlib.md5(new_source.encode("utf-8")).hexdigest()
        config['code_md5'] = code_md5
        config['script_path'] = file_path

    def run_tester(self, test_config_path, test_name, script_path, log_path, print_log_type, result_value):
        try:
            pxt = PXTester(test_config_path=test_config_path, test_name=test_name, script_path=script_path,
                           log_path=log_path, print_log_type=print_log_type, test_result=result_value,
                           tester_graph_server=None, test_graph_data=None)
            pxt.execute("", sync=True)
            return True
        except:
            traceback.print_exc()
        return False

    def run_optimization_task(self, pool, manager, task_config, test_report):
        task_uid = task_config['task_uid']
        test_config = task_config['test_config']
        test_name = task_config['test_name']
        script_path = task_config['script_path']
        log_path = task_config.get('log_path', None)
        test_log_config = task_config.get('test_log_config', [])
        args = (test_config, test_name, script_path, log_path, test_log_config, test_report)
        # results[test_name] = dict(result=tr, graph_data=gd)
        #
        return pool.apply_async(self.run_tester, args)
        # self.run_tester(*args)

    # def start_mp(self, args, manager, message_queue):
    #     self.test_names = args.testname
    #     #
    #     results = {}
    #     # manager = Manager()
    #     pool_args = []
    #     pool = Pool()
    #     script_path = self.get_script_path(args)
    #     if not script_path:
    #         print(f"ERROR: Invalid Script Path.")
    #         return 1
    #
    #     # q = manager.Queue()
    #     for test_name in args.testname:
    #         tr = manager.Value(c_wchar_p, '')
    #         gd = manager.Value(c_wchar_p, '')
    #         graph_data = manager.Value(c_wchar_p, '')
    #         pool_args.append((args.testconfig, test_name, script_path, args.logpath, args.printlogtype, tr,
    #                           args.graph, message_queue, gd, args.exec))
    #         # results[test_name] = tr
    #         results[test_name] = dict(result=tr, graph_data=gd)
    #     #
    #     for pa in pool_args:
    #         pool.apply_async(self.run_tester, pa)
    #     #
    #     pool.close()
    #     pool.join()
    #     reports = {}
    #     ri = {}
    #     graph_data = {}
    #     for tn in results:
    #         try:
    #             res = json.loads(results[tn]['result'].value)
    #             ri[tn] = res
    #             #
    #             graph_data[tn] = json.loads(results[tn]['graph_data'].value)
    #         except:
    #             traceback.print_exc()
    #     #
    #     tag_data = dict(result=ri, utc_time=datetime.utcnow().isoformat())
    #     self.save_tag_data(self.tag, tag_data)
    #     self.save_tag_graph_data(self.tag, graph_data)
    #     #
    #     self.__convert_report(reports, ri)
    #     compare_reports = []
    #     self.get_compare_reports(args, compare_reports)
    #     self.output_report(reports, compare_reports)

    def make_task_path(self, opt_config_path, symbol, task_uid):
        dir = f"tasks/{symbol}/{task_uid}"
        opt_tasks_config_path = os.path.join(opt_config_path, dir)
        os.makedirs(opt_tasks_config_path, exist_ok=True)
        return opt_tasks_config_path

    def generate_task_config(self, opt_config_path, task_info, test_config, test_log_config):
        task_uid = task_info['task_uid']
        task_status = task_info['status']
        symbol = task_info['symbol']
        variables = task_info['variables']
        test_name = task_info['test_name']
        opt_tasks_config_path = self.make_task_path(opt_config_path, symbol, task_uid)
        # dir = f"tasks/{symbol}/{task_uid}"
        # opt_tasks_config_path = os.path.join(opt_config_path, dir)
        # os.makedirs(opt_tasks_config_path, exist_ok=True)
        file_name = task_uid
        task_config = None
        if task_status == TaskStatus.FINISHED:
            file_path = self.make_opt_config_file_path(file_name, opt_tasks_config_path)
            task_config = self.load_optimization_config(file_path)
            if task_config is None:
                task_status = TaskStatus.WAITING
        if task_status != TaskStatus.FINISHED:
            # test_name = f"test{symbol.upper()}"
            task_config = dict(task_uid=task_uid, variables=variables, test_config=test_config,
                               test_name=test_name,
                               test_log_config=test_log_config,
                               symbol=symbol)
            file_path = os.path.join(opt_tasks_config_path, f"{task_uid}.py")
            self.generate_optimization_code_file(file_path, task_config)
            file_path = self.make_opt_config_file_path(file_name, opt_tasks_config_path)
            self.save_optimization_config(file_path, task_config)

        return task_config

    def _get_next_task(self, opt_config, opt_config_path, opt_tasks_info, task_count=1):
        test_config = opt_config['test_config']
        test_log_config = opt_config['test_log_config']
        tasks_dict = opt_tasks_info['tasks']
        waiting_tasks = opt_tasks_info['waiting_tasks']
        running_tasks = opt_tasks_info['running_tasks']
        ret = []
        for queue in (running_tasks, waiting_tasks):
            for task_uid in queue:
                task_info = tasks_dict[task_uid]
                task_config = self.generate_task_config(opt_config_path, task_info, test_config, test_log_config)
                if task_config:
                    ret.append(task_config)
                if len(ret) >= task_count:
                    break
        return ret

    def init_task_report_config(self, symbol, report_config):
        report_config['symbol'] = symbol
        report_config['asc'] = {}
        report_config['desc'] = {}
        for key in self.report_item_template:
            report_config['asc'][key] = []
            report_config['desc'][key] = []

    def update_task_report(self, symbol, task_uid, report, report_config, count=10):
        if symbol != report_config['symbol']:
            return False
        for key in self.report_item_template:
            for sort in (('asc', False), ('desc', True)):
                data = report_config[sort[0]][key]
                uid_list = list(map(lambda x: x[1], data))
                if task_uid not in uid_list:
                    value = report[key]['value']
                    pair = (value, task_uid)
                    data.append(pair)
                    try:
                        data.sort(key=lambda tup: tup[0], reverse=sort[1])
                    except:
                        traceback.print_exc()
        return True



    def check_task_result(self, result_dict, opt_config_path):
        updated = False
        remove_list = []
        for task_ticket in result_dict:
            ri = result_dict[task_ticket]
            task_uid = ri['task_uid']
            result = ri['result']
            symbol = ri['symbol']
            if isinstance(result, AsyncResult):
                if result.ready():
                    test_report = ri['test_report']
                    report = json.loads(test_report.value)['report']
                    remove_list.append(task_ticket)
                    # create result file
                    file_name = f"{task_uid}-result"
                    #
                    opt_tasks_info = self.get_opt_tasks_info(symbol, 'tasks')
                    task_info = opt_tasks_info['tasks'][task_uid]
                    task_info['status'] = TaskStatus.FINISHED
                    opt_tasks_config_path = self.make_task_path(opt_config_path, symbol, task_uid)
                    file_path = self.make_opt_config_file_path(file_name, opt_tasks_config_path)
                    result_config = dict(report=report,
                                         time_utc=datetime.utcnow().isoformat(),
                                         ts_utc=datetime.utcnow().timestamp())
                    self.save_optimization_config(file_path, result_config)
                    #
                    opt_tasks_info['running_tasks'].pop(task_uid, None)
                    opt_tasks_info['finished_tasks'][task_uid] = dict(task_uid=task_uid)
                    self.set_opt_tasks_info_update_flag(symbol, info_type='tasks')
                    #
                    report_config = self.get_opt_tasks_info(symbol, 'reports')
                    self.update_task_report(symbol, task_uid, report, report_config, count=10)
                    self.set_opt_tasks_info_update_flag(symbol, info_type='reports')
                    updated = True
            if self.stop_optimize:
                break
        #
        for key in remove_list:
            result_dict.pop(key, None)
        return updated

    def count_task_processing(self, result_dict):
        busy_count = 0
        for task_uid in result_dict:
            result = result_dict[task_uid]['result']
            if isinstance(result, AsyncResult):
                if not result.ready():
                    busy_count += 1
            if self.stop_optimize:
                break
        return busy_count

    def get_opt_tasks_info(self, symbol, info_type, config_uid=None, opt_config_path=None):
        if config_uid and opt_config_path:
            tasks_file_name = f"{config_uid}-{symbol}-{info_type}"
            file_path = self.make_opt_config_file_path(tasks_file_name, opt_config_path)
            opt_tasks_info = self.load_optimization_config(file_path)
            if opt_tasks_info is None:
                opt_tasks_info = {}
            self.opt_tasks_info_dict[info_type][symbol] = dict(info=opt_tasks_info, path=file_path, updated=False)
        else:
            opt_tasks_info = self.opt_tasks_info_dict[info_type].get(symbol, dict(info={}, path=None, updated=False))['info']
        return opt_tasks_info

    def _write_opt_tasks_info(self,  data):
        data['info']['time_utc'] = datetime.utcnow().isoformat()
        data['info']['ts_utc'] = datetime.utcnow().timestamp()
        self.save_optimization_config(data['path'], data['info'])
        data['updated'] = False

    def write_opt_tasks_info(self, info_type, symbol=None):
        if symbol is None:
            for sym in self.opt_tasks_info_dict[info_type]:
                data = self.opt_tasks_info_dict[info_type][sym]
                if data['updated']:
                    self._write_opt_tasks_info(data)
        else:
            data = self.opt_tasks_info_dict[info_type].get(symbol, None)
            if data:
                self._write_opt_tasks_info(data)

    def set_opt_tasks_info_update_flag(self, symbol, info_type, updated=True):
        data = self.opt_tasks_info_dict[info_type].get(symbol, None)
        if data:
            data['updated'] = updated

    # def optimize(self, config_file, output_path, max_tasks=os.cpu_count()):
    def get_next_task_list(self, opt_config, opt_config_path, max_tasks):
        task_list = []
        config_uid = opt_config['config_uid']
        for symbol in opt_config['symbols']:
            # tasks_file_name = f"{config_uid}-{symbol}-tasks"
            # opt_tasks_info = self.load_optimization_config(tasks_file_name, opt_config_path)
            opt_tasks_info = self.get_opt_tasks_info(symbol, 'tasks', config_uid, opt_config_path)
            test_name = f"test{symbol.upper()}"
            if len(opt_tasks_info) == 0:
                waiting_tasks = {}
                tasks = {}
                for key in opt_config['variables']:
                    var = opt_config['variables'][key]
                    task_info = dict(task_uid=key, status=TaskStatus.WAITING, symbol=symbol,
                                     variables=var, test_name=test_name)
                    waiting_tasks[key] = dict(task_uid=key)
                    tasks[key] = task_info
                opt_tasks_info['tasks'] = tasks
                opt_tasks_info['waiting_tasks'] = waiting_tasks
                opt_tasks_info['finished_tasks'] = {}
                opt_tasks_info['running_tasks'] = {}
                opt_tasks_info['error_tasks'] = {}
                self.set_opt_tasks_info_update_flag(symbol, info_type='tasks')
            report_config = self.get_opt_tasks_info(symbol, 'reports', config_uid, opt_config_path)
            if len(report_config) == 0:
                self.init_task_report_config(symbol, report_config)
                self.set_opt_tasks_info_update_flag(symbol, info_type='reports')
            task_count = max_tasks - len(task_list)
            if task_count <= 0:
                break
            tasks = self._get_next_task(opt_config, opt_config_path, opt_tasks_info, task_count=task_count)
            task_list.extend(tasks)
        return task_list

    # def optimize(self, config_file, output_path, max_tasks=os.cpu_count()):
    def optimize(self, config_file, output_path, max_tasks=1):
        #
        opt_config = self.parse_config(config_file)
        config_uid = opt_config['config_uid']
        dir = f"optimization/{config_uid}"
        opt_config_path = os.path.join(output_path, dir)
        os.makedirs(opt_config_path, exist_ok=True)
        file_name = config_uid
        file_path = self.make_opt_config_file_path(file_name, opt_config_path)
        self.save_optimization_config(file_path, opt_config)
        opt_config = self.load_optimization_config(file_path)
        pool = Pool()
        manager = Manager()
        result_dict = {}

        while not self.stop_optimize:
            tasks = self.get_next_task_list(opt_config, opt_config_path, max_tasks=max_tasks)
            for task_config in tasks:
                task_uid = task_config['task_uid']
                symbol = task_config['symbol']
                task_ticket = hashlib.md5(f"{symbol}-{task_uid}".encode("utf-8")).hexdigest()
                if task_ticket not in result_dict:
                    opt_tasks_info = self.get_opt_tasks_info(symbol, 'tasks')
                    opt_tasks_info['running_tasks'][task_uid] = dict(task_uid=task_uid)
                    opt_tasks_info['waiting_tasks'].pop(task_uid, None)
                    test_report = manager.Value(c_wchar_p, '')
                    ret = self.run_optimization_task(pool, manager, task_config, test_report)
                    result_dict[task_ticket] = dict(task_uid=task_uid, result=ret, test_report=test_report,
                                                    symbol=symbol)
                    self.set_opt_tasks_info_update_flag(symbol, info_type='tasks')
            # self.write_opt_tasks_info()
            #
            busy_count = self.count_task_processing(result_dict)
            self.check_task_result(result_dict, opt_config_path)
            self.write_opt_tasks_info(info_type='tasks')
            self.write_opt_tasks_info(info_type='reports')
            if len(tasks) == 0 and busy_count <= 0:
                break
            if busy_count < max_tasks:
                continue
            time.sleep(0.1)

        pool.close()
        pool.join()

   # def optimize(self, config_file, output_path, max_tasks=1):
   #      #
   #      opt_config = self.parse_config(config_file)
   #      config_uid = opt_config['config_uid']
   #      dir = f"optimization/{config_uid}"
   #      opt_config_path = os.path.join(output_path, dir)
   #      os.makedirs(opt_config_path, exist_ok=True)
   #      file_name = config_uid
   #      self.save_optimization_config(file_name, opt_config, opt_config_path)
   #      opt_config = self.load_optimization_config(file_name, opt_config_path)
   #      pool = Pool()
   #      manager = Manager()
   #      result_dict = {}
   #
   #      for symbol in opt_config['symbols']:
   #          tasks_file_name = f"{config_uid}-{symbol}-tasks"
   #          opt_tasks_info = self.load_optimization_config(tasks_file_name, opt_config_path)
   #          test_name = f"test{symbol.upper()}"
   #          if opt_tasks_info is None:
   #              waiting_tasks = {}
   #              tasks = {}
   #              for key in opt_config['variables']:
   #                  var = opt_config['variables'][key]
   #                  task_info = dict(task_uid=key, status=TaskStatus.WAITING, symbol=symbol,
   #                                   variables=var, test_name=test_name)
   #                  waiting_tasks[key] = dict(task_uid=key)
   #                  tasks[key] = task_info
   #              opt_tasks_info = dict(tasks=tasks,  waiting_tasks=waiting_tasks,
   #                                    finished_tasks={}, running_tasks={}, error_tasks={})
   #          tasks = self.get_next_task(opt_config, opt_config_path, opt_tasks_info)
   #          if len(tasks):
   #              break
   #          for task_config in tasks:
   #              task_uid = task_config['task_uid']
   #              opt_tasks_info['running_tasks'][task_uid] = dict(task_uid=task_uid)
   #              opt_tasks_info['waiting_tasks'].pop(task_uid, None)
   #              test_report = manager.Value(c_wchar_p, '')
   #              ret = self.run_optimization_task(pool, manager, task_config, test_report)
   #              result_dict[task_uid] = dict(result=ret, test_report=test_report)
   #          self.save_optimization_config(tasks_file_name, opt_tasks_info, opt_config_path)
   #          #
   #          while not self.stop_optimize:
   #              busy_count = self.count_task_processing(result_dict)
   #              updated = self.check_task_result(result_dict, opt_config_path, opt_tasks_info)
   #              if updated:
   #                  self.save_optimization_config(tasks_file_name, opt_tasks_info, opt_config_path)
   #              if busy_count < max_tasks:
   #                  break
   #              time.sleep(100)
   #
   #      pool.close()
   #      pool.join()
   #
    #
    # def optimize(self, config_file, output_path, max_tasks=10):
    #     #
    #     opt_config = self.parse_config(config_file)
    #     config_uid = opt_config['config_uid']
    #     test_config = opt_config['test_config']
    #     test_log_config = opt_config['test_log_config']
    #     dir = f"optimization/{config_uid}"
    #     opt_config_path = os.path.join(output_path, dir)
    #     os.makedirs(opt_config_path, exist_ok=True)
    #     file_name = config_uid
    #     self.save_optimization_config(file_name, opt_config, opt_config_path)
    #     opt_config = self.load_optimization_config(file_name, opt_config_path)
    #     pool = Pool()
    #     manager = Manager()
    #     for symbol in opt_config['symbols']:
    #         file_name = f"{config_uid}-{symbol}-tasks"
    #         opt_tasks_info = self.load_optimization_config(file_name, opt_config_path)
    #         if opt_tasks_info is None:
    #             opt_tasks_info = dict(tasks={})
    #         for task_uid in opt_config['variables']:
    #             task_info = opt_tasks_info.get(task_uid, {})
    #             task_tested = task_info.get('tested', False)
    #             dir = f"tasks/{symbol}/{task_uid}"
    #             opt_tasks_config_path = os.path.join(opt_config_path, dir)
    #             os.makedirs(opt_tasks_config_path, exist_ok=True)
    #             file_name = task_uid
    #             if task_tested:
    #                 task_config = self.load_optimization_config(file_name, opt_tasks_config_path)
    #                 if task_config is None:
    #                     task_tested = False
    #             if not task_tested:
    #                 variables = opt_config['variables'][task_uid]
    #                 test_name = f"test{symbol.upper()}"
    #                 task_config = dict(task_uid=task_uid, variables=variables, test_config=test_config,
    #                                    test_name=test_name,
    #                                    test_log_config=test_log_config,
    #                                    symbol=symbol)
    #                 file_path = os.path.join(opt_tasks_config_path, f"{task_uid}.py")
    #                 self.generate_optimization_code_file(file_path, task_config)
    #                 self.save_optimization_config(file_name, task_config, opt_tasks_config_path)
    #                 self.run_optimization_task(pool, manager, task_uid, task_config)
    #
    #     pool.close()
    #     pool.join()
    #
