import argparse
from multiprocessing import (Pool, Process, Manager, Queue, Value)
from pixiu.tester.ea_tester_graph import EATesterGraphServer
from pixiu.pxtester import PXTester
from pixiu.builder import EABuilder
from pixiu.optimizer import EAOptimizer
from tabulate import tabulate
from ctypes import c_wchar_p
import json
import uuid
import hashlib
import traceback
import os
from datetime import datetime

graph_server = None


class MainApp:
    def __init__(self, args):
        if args.action_name == 'test':
            self.test_names = []
            self.data_file = args.datafile
            self.set_tag(args.tag)

    @staticmethod
    def str2bool(v):
        if isinstance(v, bool):
           return v
        if v.lower() in ('yes', 'true', 't', 'y', '1'):
            return True
        elif v.lower() in ('no', 'false', 'f', 'n', '0'):
            return False
        else:
            raise argparse.ArgumentTypeError('Boolean value expected.')

    def load_data(self, ext=''):
        try:
            # with open(f"pxdata/{self.data_file}", "r") as f:
            with open(f"pxdata/{self.data_file}{ext}", "r") as f:
                s = f.read()
                return json.loads(s)
        except:
            traceback.print_exc()
        return None

    def save_data(self, data, ext=''):
        try:
            # with open(f"pxdata/{self.data_file}", "w") as f:
            with open(f"pxdata/{self.data_file}{ext}", "w") as f:
                f.write(json.dumps(data))
            return True
        except:
            traceback.print_exc()
        return False
    #
    # def load_data(self):
    #     try:
    #         with open(f"pxdata/{self.data_file}", "r") as f:
    #             s = f.read()
    #             return json.loads(s)
    #     except:
    #         traceback.print_exc()
    #     return None
    #
    # def save_data(self, data):
    #     try:
    #         with open(f"pxdata/{self.data_file}", "w") as f:
    #             f.write(json.dumps(data))
    #         return True
    #     except:
    #         traceback.print_exc()
    #     return False

    def load_tag_data(self, tag):
        if not tag:
            return None
        d = self.load_data()
        if d is None:
            d = {'version': '0.1.0', 'tags': {}}
        return d['tags'][tag]

    def save_tag_data(self, tag, data):
        if not tag:
            return
        d = self.load_data()
        if d is None:
            d = {'version': '0.1.0', 'tags': {}}
        d['tags'][tag] = data
        self.save_data(d)

    def load_tag_graph_data(self, tag):
        if not tag:
            return None
        d = self.load_data(ext=f".{tag}.gd")
        return d

    def save_tag_graph_data(self, tag, data):
        if not tag:
            return
        self.save_data(data, ext=f".{tag}.gd")

    def set_tag(self, tag):
        if tag is None:
            self.tag = hashlib.md5(str(uuid.uuid4()).encode("utf-8")).hexdigest()
        else:
            self.tag = tag

    def output_report(self, reports, compare_reports=[]):
        report_str = f"\n-- Result (Tag: {self.tag}) --\n"
        idx = 1
        data = []
        headers = self.test_names

        for key in reports:
            item = reports[key][self.test_names[0]]
            precision = item.get('precision', 2)
            item_type = item.get('type', 'value')
            # item_aggr = item.get('aggr', None)
            report_str += f"{idx:02d}). {item['desc']}: "
            if len(compare_reports) > 0:
                row = [idx, f"{item['desc']}({self.tag[:12]})"]
            else:
                row = [idx, f"{item['desc']}"]
            report_str = self.gen_report_row(headers, item_type, key, precision, report_str, reports, row)
            data.append(row)
            report_str += "\n"
            for cr in compare_reports:
                row = [idx, f"{item['desc']}({cr['tag'][:12]})"]
                report_str = self.gen_report_row(headers, item_type, key, precision, report_str, cr['reports'], row, reports)
                data.append(row)
                report_str += "\n"
            idx += 1
        #
        headers.append("Total/Avg")
        print(f"Output (Tag: {self.tag}):")
        print(tabulate(data, headers=headers, tablefmt="pretty", stralign="left"))

    def gen_report_row(self, headers, item_type, key, precision, report_str, reports, row, compare_reports=None):
        total_value = 0
        for tn in self.test_names:
            item = reports[key][tn]
            compare_item = None
            if compare_reports:
                compare_item = compare_reports[key][tn]
            v = None
            if item['value'] is not None:
                if item_type == 'value':
                    v = round(item['value'], precision)
                    total_value += v
                    #
                    if compare_item and compare_item['value']:
                        cv = round(compare_item['value'], precision)
                        diff = round(v - cv, precision)
                        if cv < v:
                            v = f"{v} ({diff}) ↑"
                        elif cv > v:
                            v = f"{v} ({diff}) ↓"
                elif item_type == '%':  # %
                    v = round(item['value'] * 100, precision)
                    total_value += v
                    vs = f"{v} %"
                    if compare_item:
                        cv = round(compare_item['value'] * 100, precision)
                        diff = round(v - cv, precision)
                        if cv < v:
                            vs = f"{vs} ({diff}) ↑"
                        elif cv > v:
                            vs = f"{vs} ({diff}) ↓"
                    v = vs
            if v is None:
                v = 0 if item['value'] is None else item['value']
                total_value = v
            report_str += f"{v}  | "
            row.append(v)
        # total
        if total_value is not None:
            if item_type == 'value':
                total_value = f"{round(total_value, precision)} / {round(total_value / len(headers), precision)}"
            if item_type == '%':
                total_value = f"{round(total_value, precision)} % / {round(total_value / len(headers), precision)} %"
        row.append(total_value)
        return report_str


    def run_tester(self, test_config_path, test_name, script_path, log_path, print_log_type, result_value, graph,
                   message_queue, graph_data, exec):
        graph_server = None
        try:
            if graph:
                graph_server = EATesterGraphServer(message_queue)
            pxt = PXTester(test_config_path=test_config_path, test_name=test_name, script_path=script_path,
                           log_path=log_path, print_log_type=print_log_type, test_result=result_value,
                           tester_graph_server=graph_server, test_graph_data=graph_data)
            if exec:
                # pxt.execute("", sync=True)
                pxt.execute_script("", sync=True)
            else:
                pxt.execute("", sync=True)
            return True
        except:
            traceback.print_exc()
        return False

    #
    # def run_tester(self, test_config_path, test_name, script_path, log_path, print_log_type, result_value, graph,
    #                message_queue, graph_data, exec):
    #     graph_server = None
    #     if graph:
    #         graph_server = EATesterGraphServer(message_queue)
    #     pxt = PXTester(test_config_path=test_config_path, test_name=test_name, script_path=script_path,
    #                    log_path=log_path, print_log_type=print_log_type, test_result=result_value,
    #                    tester_graph_server=graph_server, test_graph_data=graph_data)
    #     pxt.execute("", sync=True)
    #
    def get_script_path(self, args):
        if not args.scriptpath:
            return None
        if not os.path.isdir(args.scriptpath):
            return args.scriptpath
        if not args.tag:
            return None
        #
        dir_name = os.path.basename(args.scriptpath)
        for flag in ("_V", "_v", "@"):
            script_name = f"{dir_name}{flag}{args.tag}.py"
            script_path = os.path.join(args.scriptpath, script_name)
            if not os.path.isfile(script_path):
                script_path = None
            else:
                break

        return script_path



    def start_mp(self, args, manager, message_queue):
        # global g_graph_server
        # test_config_path = args.testconfig
        # test_name = args.testname, script_path = args.scriptpath,
        # log_path = args.logpath, print_log_type = args.printlogtype
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

    def get_compare_reports(self, args, compare_reports):
        if args.compare:
            for c in args.compare:
                compare_data = self.load_tag_data(c)
                if compare_data:
                    r = {}
                    self.__convert_report(r, compare_data['result'])
                    compare_reports.append(dict(tag=c, reports=r))

    def __convert_report(self, reports, ri):
        for key in ri[self.test_names[0]]['report']:
            reports[key] = {}
            for tn in self.test_names:
                reports[key][tn] = ri[tn]['report'][key]

    def start_sp(self, args, manager, message_queue):
        self.test_names = args.testname
        #
        results = {}
        # manager = Manager()
        pool_args = []
        script_path = self.get_script_path(args)
        if not script_path:
            print(f"ERROR: Invalid Script Path.")
            return 1

        for test_name in args.testname:
            tr = manager.Value(c_wchar_p, '')
            gd = manager.Value(c_wchar_p, '')
            pool_args.append((args.testconfig, test_name, script_path, args.logpath, args.printlogtype, tr,
                              args.graph, message_queue, gd, args.exec))
            # results[test_name] = tr
            results[test_name] = dict(result=tr, graph_data=gd)

        #
        for pa in pool_args:
            self.run_tester(*pa)
        #
        reports = {}
        ri = {}
        graph_data = {}
        for tn in results:
            try:
                res = json.loads(results[tn]['result'].value)
                ri[tn] = res
                graph_data[tn] = json.loads(results[tn]['graph_data'].value)
            except:
                traceback.print_exc()
        #
        tag_data = dict(result=ri, utc_time=datetime.utcnow().isoformat())
        self.save_tag_data(self.tag, tag_data)
        self.save_tag_graph_data(self.tag, graph_data)
        self.__convert_report(reports, ri)
        compare_reports = []
        self.get_compare_reports(args, compare_reports)
        self.output_report(reports, compare_reports)

    def compare_result(self, args):
        self.test_names = args.testname
        #
        #
        reports = {}
        tag_data = self.load_tag_data(self.tag)
        self.__convert_report(reports, tag_data['result'])
        #
        compare_reports = []
        self.get_compare_reports(args, compare_reports)
        self.output_report(reports, compare_reports)

    def send_graph_data(self, graph_server, graph_data):
        if graph_server is None or graph_data is None:
            return False
        for tn in graph_data:
            gd = graph_data[tn]['graph_data']
            print(f"gd={gd['name'], len(gd['ticks'])}")
            for tick in gd['ticks']:
                data = dict(cmd='update_data', name=gd['name'], symbol=gd['symbol'], group=gd['group'],
                            data=dict(price=tick))
                graph_server.send_message(json.dumps(data))
        return True

    def load_graph_data(self, args, graph_server):
        # self.test_names = args.testname
        # print(self.test_names)
        tag_gd = self.load_tag_graph_data(self.tag)
        # for tn in args.testname:
        #     gd =
        # print(f"tag_gd={type(tag_gd)}")
        self.send_graph_data(graph_server, tag_gd)

        #
        if args.compare:
            for c in args.compare:
                tag_gd = self.load_tag_graph_data(c)
                self.send_graph_data(graph_server, tag_gd)

    # def compare_result(self, args):
    #     self.test_names = args.testname
    #     #
    #     #
    #     reports = {}
    #     tag_data = self.load_tag_data(self.tag)
    #     self.__convert_report(reports, tag_data['result'])
    #     #
    #     compare_reports = []
    #     self.get_compare_reports(args, compare_reports)
    #     self.output_report(reports, compare_reports)
    #
    def build_ea(self, build_config_file, ea_output_path):
        ea_builder = EABuilder({})
        with open(build_config_file) as f:
            build_config_string = f.read()
            build_config = json.loads(build_config_string)
            ea_builder.build(build_config, ea_output_path)

    def optimize_ea(self, config_file, ea_output_path, mode='fast'):
        ea_optimizer = EAOptimizer(dict(config_file_path=config_file, output_path=ea_output_path,))
        ea_optimizer.optimize(options=dict(mode=mode))



def main(*args, **kwargs):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='', dest='action_name', required=True)
    parser_test = subparsers.add_parser('test', help='Test EA')
    parser_test.add_argument('-c', '--testconfig', type=str, required=True, help='Test config path')
    # parser.add_argument('-n', '--testname', type=str, required=True, help='Test name')
    parser_test.add_argument('-n', '--testname',  nargs='+', required=True, help='Test name')
    parser_test.add_argument('-s', '--scriptpath', type=str, required=False, help='Script path')
    parser_test.add_argument('-o', '--logpath', type=str, help='Log path')
    parser_test.add_argument('-p', '--printlogtype', nargs='+', default=['ea', 'report'], required=False,
                        help='Print log type,  account order ea report')
    parser_test.add_argument('-m', '--multiprocessing', type=MainApp.str2bool, default=True, help='Multiprocessing mode')
    parser_test.add_argument('-t', '--tag', type=str, help='Tag')
    parser_test.add_argument('-l', '--datafile', type=str, default='_pixiu_data.json', help='Data file name')
    parser_test.add_argument('-r', '--compare', nargs='+', help='Compare with the tags list')
    parser_test.add_argument('-g', '--graph', type=MainApp.str2bool, default=False, help='Display tester graph')
    parser_test.add_argument('-x', '--exec', type=str, required=False, help='Exec command')
    #
    parser_build = subparsers.add_parser('build', help='Build EA')
    parser_build.add_argument('-c', '--buildconfig', type=str, required=True, help='Build config path')
    parser_build.add_argument('-o', '--output', type=str, required=True, help='EA output path')
    parser_build.add_argument('-t', '--test', type=str, required=False, help='Test')
    #
    parser_build = subparsers.add_parser('optimize', help='Optimize EA')
    parser_build.add_argument('-c', '--optimizeconfig', type=str, required=True, help='Optimize config path')
    parser_build.add_argument('-o', '--output', type=str, required=True, help='EA output path')
    parser_build.add_argument('-t', '--test', type=str, required=False, help='Test')
    parser_build.add_argument('-m', '--mode', type=str, default='fast', required=False, help='Mode')
    # parser_build.add_argument('-b', '--build', type=str, required=False, help='Build EA')

    args = parser.parse_args()
    if args.action_name == 'build':
        MainApp(args).build_ea(args.buildconfig, args.output)
    elif args.action_name == 'optimize':
        MainApp(args).optimize_ea(args.optimizeconfig, args.output, args.mode)
    else:
        manager = Manager()

        graph_server = None
        message_queue = None

        if args.graph:
            message_queue = manager.Queue()
            graph_server = EATesterGraphServer(message_queue)
            graph_server.start()

        if args.scriptpath:
            if args.multiprocessing:
                MainApp(args).start_mp(args, manager, message_queue)
            else:
                MainApp(args).start_sp(args, manager, message_queue)
        elif len(args.compare) > 0 and args.tag:
            MainApp(args).compare_result(args)
            if graph_server is not None:
                MainApp(args).load_graph_data(args, graph_server)
                graph_server.join()
        else:
            print("Error")

        if graph_server:
            graph_server.stop()
    # pxt = PXTester(test_config_path=args.testconfig, test_name=args.testname, script_path=args.scriptpath,
    #                log_path=args.logpath, print_log_type=args.printlogtype)
    # pxt.execute("", sync=True)


if __name__ == '__main__':
    main()

