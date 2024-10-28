
import ast
import io
import random
import time
import traceback
import pkg_resources
from multiprocessing import (Pool, Process, Manager, Queue, Value)
from multiprocessing.pool import AsyncResult
from pixiu.pxtester import PXTester
import astunparse
import os
# import json5 as json
import pyjson5 as json
import itertools
import hashlib
from datetime import datetime
from ctypes import c_wchar_p
from enum import Enum
from tabulate import tabulate

file_dir = os.path.dirname(__file__)

MAX_STATS_TASK_COUNT = 100
class TaskStatus(int, Enum):
    WAITING = 0
    RUNNING = 100
    FINISHED = 200
    ERROR = 300

class ReplaceValue(ast.NodeTransformer):
    def __init__(self, values_config, result=None):
        super().__init__()
        self.values_config = values_config
        self.result = result

    def visit_Assign(self, node):
        replace_conditions = (isinstance(node.targets[0], ast.Name) and isinstance(node.targets[0].ctx, ast.Store))
        if replace_conditions:
            element_id = node.targets[0].id
            if element_id in self.values_config:
                new_val = self.values_config[element_id]
                if new_val:
                    replaced = True
                    # if isinstance(node.value, ast.Constant):
                    #     # element.value.value = new_val
                    #     node.value = ast.Constant(value=new_val)
                    # else:
                    #     replaced = False
                    if self.result is not None and replaced:
                        self.result[element_id] = dict(result=0, )
                    return ast.Assign(targets=[node.targets[0]], value=ast.Constant(value=new_val, kind=''))
        return node
                    # return node
        # ps = ast.parse(source)
        # for element in ps.body:
        #     if isinstance(element, ast.Assign):
        #         if isinstance(element.targets[0], ast.Name):
        #             if isinstance(element.targets[0].ctx, ast.Store):
        #                 element_id = element.targets[0].id
        #                 if element_id in values_config:
        #                     new_val = values_config[element_id]
        #                     if new_val:
        #                         replaced = True
        #                         if isinstance(element.value, ast.Constant):
        #                             # element.value.value = new_val
        #                             element.value = ast.Constant(value=new_val)
        #                         else:
        #                             replaced = False
        #                         if result is not None and replaced:
        #                             result[element_id] = dict(result=0, )
        # return ps

class EAOptimizer:
    """EA Optimizer"""

    def __init__(self, params):
        super(object, self).__init__()
        self.config_file_path = params.get('config_file_path', None)
        self.output_path = params.get('output_path', None)
        self.optimization_config = None
        self.symbols = []
        self.variables = {}
        self.name = None
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

    def get_source_code(self):
        source = self.config_path_to_abs_path(self.optimization_config['source'])
        code = open(source).read()
        return code

    def get_test_config(self):
        test_config = self.config_path_to_abs_path(self.optimization_config['test_config'])
        return test_config

    def get_symbols(self):
        symbols = self.optimization_config['optimization']['symbols']
        return symbols

    def get_variables(self):
        variables = self.optimization_config['optimization']['variables']
        return variables

    def config_path_to_abs_path(self, file_path):
        ret = file_path
        if not os.path.isabs(file_path):
            d = os.path.dirname(self.config_file_path)
            ret = os.path.abspath(os.path.join(d, file_path))
        return ret

    def load_config_file(self):
        with open(self.config_file_path) as f:
            config_string = f.read()
            config = json.loads(config_string)
            self.optimization_config = config[0]['optimization_config']

    def calculate_optimization_task_count(self):
        generator = self.optimization_config['optimization']['generator']
        if generator == 'random':
            max_tasks = int(self.optimization_config['optimization']['max_tasks'])
            return max_tasks
        elif generator == 'grid':
            variables = self.get_variables()
            task_count = 1
            for var in variables:
                var_name = variables[var].get('name', None)
                var_name = var if var_name is None else var_name
                var_val = variables[var]
                task_count *= (var_val['stop'] - var_val['start']) / var_val['step']
            return task_count
        return 0

    def generate_variable_md5(self, variable_dict):
        md5 = hashlib.md5(json.dumps(variable_dict, sort_keys=True).encode('utf-8')).hexdigest()
        return md5

    def parse_config(self):
        if not self.optimization_config:
            return None
        self.name = self.optimization_config['name']
        # self.source = self.config_path_to_abs_path(self.optimization_config['source'])
        code = self.get_source_code()
        # source_md5 = hashlib.md5(open(self.source, 'rb').read()).hexdigest()
        source_md5 = hashlib.md5(code.encode('utf-8')).hexdigest()
        #
        symbols = self.get_symbols()
        variables = self.get_variables()
        variables_dict = {}
        var_list_dict = {}
        flag_list = []
        for var in variables:
            var_name = variables[var].get('name', None)
            var_name = var if var_name is None else var_name
            var_val = variables[var]
            self.variables[var_name] = var_val
            flag_list.append(f"{var_name}-{var_val['start']}-{var_val['stop']}-{var_val['step']}")
            for v in range(int(var_val['start']), int(var_val['stop']), int(var_val['step'])):
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
            for p in prd:
                v = variables_dict[p]
                val[v[0]] = v[1]
            key = self.generate_variable_md5(val)
            opt_var_config[key] = val
        #
        flag_list.sort()
        flag = source_md5 + '-' + '-'.join(flag_list)
        flag_uid = hashlib.md5(flag.encode("utf-8")).hexdigest()
        test_config = self.get_test_config()
        #
        task_vars = None
        generator = self.optimization_config['optimization']['generator']
        if generator == 'random':
            max_tasks = int(self.optimization_config['optimization']['max_tasks'])
            key_list = list(opt_var_config.keys())
            keys = random.sample(key_list, min(max_tasks, len(key_list)))
            task_vars = {k: opt_var_config[k] for k in keys}
        elif generator == 'grid':
            task_vars = opt_var_config

        opt_config = dict(type="optimization_config", config_uid=flag_uid,
                          symbols=symbols,
                          variables=task_vars,
                          test_config=test_config,
                          test_log_config=self.optimization_config.get('test_log_config', ["order", "report"]),
                          time_utc=datetime.utcnow().isoformat(),
                          ts_utc=datetime.utcnow().timestamp())
        return opt_config


    def valid_config(self):
        return True

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

    def generate_optimization_parsed_code(self, source, values_config, result=None):
        ps = ast.parse(source)
        ps = ReplaceValue(values_config, result).visit(ps)
        return ps

    # def generate_optimization_parsed_code(self, source, values_config, result=None):
    #     ps = ast.parse(source)
    #     for element in ps.body:
    #         if isinstance(element, ast.Assign):
    #             if isinstance(element.targets[0], ast.Name):
    #                 if isinstance(element.targets[0].ctx, ast.Store):
    #                     element_id = element.targets[0].id
    #                     if element_id in values_config:
    #                         new_val = values_config[element_id]
    #                         if new_val:
    #                             replaced = True
    #                             if isinstance(element.value, ast.Constant):
    #                                 # element.value.value = new_val
    #                                 element.value = ast.Constant(value=new_val)
    #                             else:
    #                                 replaced = False
    #                             if result is not None and replaced:
    #                                 result[element_id] = dict(result=0, )
    #     return ps
    #
    def generate_optimization_code(self, source, values_config, result=None):
        ps = self.generate_optimization_parsed_code(source, values_config, result)
        new_code = astunparse.unparse(ps)
        #
        header_comments = ''
        buf = io.StringIO(source)
        lines = buf.readlines()
        for l in lines:
            if l.startswith('#'):
                header_comments = f"{header_comments}{l}"
            else:
                break
        if header_comments:
            new_code = f"{header_comments}{new_code}"
        return new_code

    def generate_optimization_code_file(self, file_path, config):
        code = self.get_source_code()
        values_config = config['variables']
        new_code = self.generate_optimization_code(code, values_config)
        with open(file_path, 'w') as f:
            f.write(new_code)
        code_md5 = hashlib.md5(new_code.encode("utf-8")).hexdigest()
        config['code_md5'] = code_md5
        config['script_path'] = file_path

    # def generate_optimization_code_file(self, file_path, config):
    #     code = self.get_source_code()
    #     values_config = config['variables']
    #     ps = self.generate_optimization_code(code, values_config)
    #     new_code = astunparse.unparse(ps)
    #     with open(file_path, 'w') as f:
    #         f.write(new_code)
    #     code_md5 = hashlib.md5(new_code.encode("utf-8")).hexdigest()
    #     config['code_md5'] = code_md5
    #     config['script_path'] = file_path

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


    def make_task_path(self, opt_config_path, symbol, task_uid):
        d = f"tasks/{symbol}/{task_uid}"
        opt_tasks_config_path = os.path.join(opt_config_path, d)
        os.makedirs(opt_tasks_config_path, exist_ok=True)
        return opt_tasks_config_path

    def generate_task_config(self, opt_config_path, task_info, test_config, test_log_config):
        task_uid = task_info['task_uid']
        task_status = task_info['status']
        symbol = task_info['symbol']
        variables = task_info['variables']
        test_name = task_info['test_name']
        opt_tasks_config_path = self.make_task_path(opt_config_path, symbol, task_uid)
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

    def update_task_report(self, symbol, task_uid, report, report_config, count=MAX_STATS_TASK_COUNT):
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
                        del data[count:]
                    except:
                        traceback.print_exc()
        return True

    def stats_task_result(self, opt_config_path, symbol, report_config, task_uid, count=MAX_STATS_TASK_COUNT):
        file_name = f"{task_uid}-result"
        #
        opt_tasks_config_path = self.make_task_path(opt_config_path, symbol, task_uid)
        file_path = self.make_opt_config_file_path(file_name, opt_tasks_config_path)
        result_config = self.load_optimization_config(file_path)
        if result_config is None:
            return False
        report = result_config['report']
        return self.update_task_report(symbol, task_uid, report, report_config, count=count)

    def stats_tasks_result(self, symbol, opt_config, opt_config_path, report_config):
        config_uid = opt_config['config_uid']
        opt_tasks_info = self.get_opt_tasks_info(symbol, 'tasks', config_uid, opt_config_path)
        finished_tasks = opt_tasks_info['finished_tasks']

        for task_uid in finished_tasks:
            self.stats_task_result(opt_config_path, symbol, report_config, task_uid)

    def _stats(self, opt_config, opt_config_path, symbols=None):
        config_uid = opt_config['config_uid']
        if symbols is None:
            symbols = opt_config['symbols']
        #
        for symbol in symbols:
            report_config = self.get_opt_tasks_info(symbol, 'reports', config_uid, opt_config_path)
            self.init_task_report_config(symbol, report_config)
            self.set_opt_tasks_info_update_flag(symbol, info_type='reports')
            self.stats_tasks_result(symbol, opt_config, opt_config_path, report_config)
            self.write_opt_tasks_info(info_type='reports')

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
                    opt_tasks_config_path = self.make_task_path(opt_config_path, symbol, task_uid)
                    file_path = self.make_opt_config_file_path(file_name, opt_tasks_config_path)
                    result_config = dict(report=report,
                                         time_utc=datetime.utcnow().isoformat(),
                                         ts_utc=datetime.utcnow().timestamp())
                    self.save_optimization_config(file_path, result_config)
                    #
                    self.update_task_status(symbol, task_uid, TaskStatus.FINISHED)
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

    def update_task_status(self, symbol, task_uid, status):
        opt_tasks_info = self.get_opt_tasks_info(symbol, 'tasks')
        task_info = opt_tasks_info['tasks'][task_uid]
        task_info['status'] = status
        if status == TaskStatus.FINISHED:
            opt_tasks_info['waiting_tasks'].pop(task_uid, None)
            opt_tasks_info['running_tasks'].pop(task_uid, None)
            opt_tasks_info['finished_tasks'][task_uid] = dict(task_uid=task_uid)
        elif status == TaskStatus.RUNNING:
            opt_tasks_info['running_tasks'][task_uid] = dict(task_uid=task_uid)
            opt_tasks_info['waiting_tasks'].pop(task_uid, None)
            opt_tasks_info['finished_tasks'].pop(task_uid, None)
        elif status == TaskStatus.WAITING:
            opt_tasks_info['waiting_tasks'][task_uid] = dict(task_uid=task_uid)
            opt_tasks_info['running_tasks'].pop(task_uid, None)
            opt_tasks_info['finished_tasks'].pop(task_uid, None)
        else:
            return

        self.set_opt_tasks_info_update_flag(symbol, info_type='tasks')

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

    def make_config_path(self, opt_config, output_path):
        config_uid = opt_config['config_uid']
        d = f"optimization/{config_uid}"
        opt_config_path = os.path.join(output_path, d)
        return opt_config_path

    def stats(self):
        opt_config = self.parse_config_file()
        opt_config_path = self.make_config_path(opt_config, self.output_path)
        self._stats(opt_config, opt_config_path)

    def output_report(self, symbol, tag, opt_config, report_config, report_items):
        report_str = f"\n-- Result (Tag: {tag}) --\n"
        data = []
        headers = ['item', 'rank', 'uid', 'value', 'config', 'desc']
        variables_dict = {}
        scores_dict = {}
        for ri in report_items:
            name = ri['name']
            sort = ri['sort']
            count = ri['count']
            weight = ri.get('weight', 0)
            rank_list = report_config[sort][name]
            index = 0
            total_rank = len(rank_list)
            for r in rank_list:
                value = r[0]
                uid = r[1]
                precision = ri.get('precision', 2)
                item_type = ri.get('type', 'value')
                desc = ri.get('desc', '')
                #
                if weight > 0:
                    uid_score = scores_dict.get(uid, 0)
                    score = (total_rank - index) / total_rank * 100.0 * weight
                    uid_score += score
                    scores_dict[uid] = uid_score
                row = [f"{name}({sort})", f"{index+1}", f"{uid}"]
                report_str = self.gen_report_row(value, item_type, precision, report_str, row, rank_list[0][0])
                #
                config_str = variables_dict.get(uid, None)
                if config_str is None:
                    var = opt_config['variables'][uid]
                    config_str = str(var)
                    variables_dict[uid] = config_str
                row.append(f"{config_str}")
                row.append(f"{desc}")
                data.append(row)
                report_str += "\n"
                index += 1
                if index >= count:
                    break
        #
        if len(scores_dict) > 0:
            sorted_scores = dict(sorted(scores_dict.items(), key=lambda item: item[1], reverse=True))
            index = 0
            for uid in sorted_scores:
                score = scores_dict[uid]
                row = [f"score rank", f"{index+1}", f"{uid}", score, variables_dict.get(uid, ''), '']
                data.append(row)
                index += 1

        print(f"Output (Tag: {tag}):")
        print(tabulate(data, headers=headers, tablefmt="pretty", stralign="left"))

    def gen_report_row(self, value, item_type, precision, report_str, row, compare_value=None):
        total_value = 0
        # item = reports[key][tn]
        v = None
        if value is not None:
            if item_type == 'value':
                v = round(value, precision)
                #
                if compare_value:
                    cv = round(compare_value, precision)
                    diff = round(v - cv, precision)
                    if cv < v:
                        v = f"{v} ({diff}) ↑"
                    elif cv > v:
                        v = f"{v} ({diff}) ↓"
            elif item_type == '%':  # %
                v = round(value * 100, precision)
                total_value += v
                vs = f"{v} %"
                if compare_value:
                    cv = round(compare_value * 100, precision)
                    diff = round(v - cv, precision)
                    if cv < v:
                        vs = f"{vs} ({diff}) ↑"
                    elif cv > v:
                        vs = f"{vs} ({diff}) ↓"
                v = vs
        if v is None:
            v = 0 if value is None else value
        report_str += f"{v}  | "
        row.append(v)
        return report_str

    def show_stats(self, symbols=None):
        opt_config = self.parse_config_file()
        opt_config_path = self.make_config_path(opt_config, self.output_path)
        config_uid = opt_config['config_uid']
        if symbols is None:
            symbols = opt_config['symbols']
        count = 10
        report_items = [
                         dict(name='balance', sort='desc',  count=count),
                         dict(name='total_net_profit', sort='desc', count=count),
                         dict(name='total_net_profit_rate', sort='desc', type='percent', weight=0.3, count=count),
                         dict(name='sharpe_ratio', sort='desc', weight=0.4, count=count),
                         dict(name='sortino_ratio', sort='desc', count=count),
                         dict(name='absolute_drawdown', sort='asc', count=count),
                         dict(name='max_drawdown', sort='asc', count=count),
                         dict(name='max_drawdown_rate', sort='asc', weight=0.2, type='percent', count=count),
                         dict(name='total_trades', sort='asc', weight=0.05, count=count),
                         dict(name='win_rate', sort='desc', weight=0.05, type='percent',  count=count),
                        ]
        for symbol in symbols:
            report_config = self.get_opt_tasks_info(symbol, 'reports', config_uid, opt_config_path)
            tag = f"{symbol}({config_uid})"
            self.output_report(symbol, tag, opt_config, report_config, report_items=report_items)

    def optimize(self, options):
        max_tasks = options.get('max_tasks', os.cpu_count())
        mode = options.get('mode', 'fast')
        #
        if self.config_file_path:
            self.load_config_file()
        opt_config = self.parse_config()
        if opt_config is None:
            print(f"Error: parse config")
            return
        #
        opt_start_time = datetime.now()
        pixiu_version = pkg_resources.get_distribution('pixiu').version
        print(f"\n\n == PiXiu({pixiu_version}) Optimization Start: {opt_start_time} \n\n")
        opt_config_path = self.make_config_path(opt_config, self.output_path)
        os.makedirs(opt_config_path, exist_ok=True)
        file_name = opt_config['config_uid']
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
                skip_task = False
                if mode == 'fast':
                    report_config = self.get_opt_tasks_info(symbol, 'reports')
                    skip_task = self.stats_task_result(opt_config_path, symbol, report_config, task_uid)
                if skip_task:
                    self.update_task_status(symbol, task_uid, TaskStatus.FINISHED)
                    continue
                task_ticket = hashlib.md5(f"{symbol}-{task_uid}".encode("utf-8")).hexdigest()
                if task_ticket not in result_dict:
                    # opt_tasks_info = self.get_opt_tasks_info(symbol, 'tasks')
                    # opt_tasks_info['running_tasks'][task_uid] = dict(task_uid=task_uid)
                    # opt_tasks_info['waiting_tasks'].pop(task_uid, None)
                    self.update_task_status(symbol, task_uid, TaskStatus.RUNNING)
                    test_report = manager.Value(c_wchar_p, '')
                    ret = self.run_optimization_task(pool, manager, task_config, test_report)
                    result_dict[task_ticket] = dict(task_uid=task_uid, result=ret, test_report=test_report,
                                                    symbol=symbol)
                    # self.set_opt_tasks_info_update_flag(symbol, info_type='tasks')
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
        opt_end_time = datetime.now()
        print(f"\n\n == PiXiu Backtesting End: {opt_end_time}, Total Time: {(opt_end_time - opt_start_time).total_seconds()} sec, {self.config_file_path} == \n\n")

        self.show_stats()

