import argparse
from multiprocessing import Pool, Process, Manager
from pixiu.pxtester import PXTester
from tabulate import tabulate
from ctypes import c_wchar_p
import json


class MainApp:
    def __init__(self):
        self.test_names = []

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

    def output_report(self, reports):
        report_str = "\n-- Result --\n"
        idx = 1
        data = []
        headers = self.test_names
        for key in reports:
            item = reports[key][self.test_names[0]]
            report_str += f"{idx:02d}). {item['desc']}: "
            row = [idx, item['desc']]
            for tn in self.test_names:
                item = reports[key][tn]
                precision = item.get('precision', 2)
                item_type = item.get('type', 'value')
                if item_type == 'value':
                    v = round(item['value'], precision)
                elif item_type == '%':  # %
                    v = f"{round(item['value']*100, precision)} %"
                else:  # str
                    v = item['value']
                report_str += f"{v}  | "
                row.append(v)
            data.append(row)

            report_str += "\n"
            idx += 1
        print(tabulate(data, headers=headers, tablefmt="pretty"))

    def run_tester(self, test_config_path, test_name, script_path, log_path, print_log_type, result_value):
        pxt = PXTester(test_config_path=test_config_path, test_name=test_name, script_path=script_path,
                       log_path=log_path, print_log_type=print_log_type, test_result=result_value)
        pxt.execute("", sync=True)

    def start_mp(self, args):
        # test_config_path = args.testconfig
        # test_name = args.testname, script_path = args.scriptpath,
        # log_path = args.logpath, print_log_type = args.printlogtype
        self.test_names = args.testname
        #
        results = {}
        manager = Manager()
        pool_args = []
        pool = Pool()
        for test_name in args.testname:
            tr = manager.Value(c_wchar_p, '')
            pool_args.append((args.testconfig, test_name, args.scriptpath, args.logpath, args.printlogtype, tr))
            results[test_name] = tr
        #
        for pa in pool_args:
            pool.apply_async(self.run_tester, pa)
        #
        pool.close()
        pool.join()
        reports = {}
        ri = {}
        for tn in results:
            res = json.loads(results[tn].value)
            ri[tn] = res
        for key in ri[self.test_names[0]]['report']:
            reports[key] = {}
            for tn in self.test_names:
                reports[key][tn] = ri[tn]['report'][key]
        self.output_report(reports)

    def start_sp(self, args):
        self.test_names = args.testname
        #
        results = {}
        manager = Manager()
        pool_args = []
        pool = Pool()
        for test_name in args.testname:
            tr = manager.Value(c_wchar_p, '')
            pool_args.append((args.testconfig, test_name, args.scriptpath, args.logpath, args.printlogtype, tr))
            results[test_name] = tr
        #
        for pa in pool_args:
            self.run_tester(*pa)
        #
        reports = {}
        ri = {}
        for tn in results:
            res = json.loads(results[tn].value)
            ri[tn] = res
        for key in ri[self.test_names[0]]['report']:
            reports[key] = {}
            for tn in self.test_names:
                reports[key][tn] = ri[tn]['report'][key]
        self.output_report(reports)


def main(*args, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--testconfig', type=str, required=True, help='Test config path')
    # parser.add_argument('-n', '--testname', type=str, required=True, help='Test name')
    parser.add_argument('-n', '--testname',  nargs='+', required=True, help='Test name')
    parser.add_argument('-s', '--scriptpath', type=str, required=True, help='Script path')
    parser.add_argument('-o', '--logpath', type=str, help='Log path')
    parser.add_argument('-p', '--printlogtype', nargs='+', default=['ea', 'report'], required=False,
                        help='Print log type,  account order ea report')
    parser.add_argument('-m', '--multiprocessing', type=MainApp.str2bool, default=True, help='Multiprocessing mode')
    args = parser.parse_args()
    if args.multiprocessing:
        MainApp().start_mp(args)
    else:
        MainApp().start_sp(args)
    # pxt = PXTester(test_config_path=args.testconfig, test_name=args.testname, script_path=args.scriptpath,
    #                log_path=args.logpath, print_log_type=args.printlogtype)
    # pxt.execute("", sync=True)


if __name__ == '__main__':
    main()

