import argparse
from threading import Thread
from multiprocessing import Pool, Process, Manager
from pixiu.pxtester import PXTester
from tabulate import tabulate
from ctypes import c_wchar_p
import json


def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

test_names = []
def output_report(reports):
    report_str = "\n-- Result --\n"
    idx = 1
    data = []
    headers = test_names
    for key in reports:
        item = reports[key][test_names[0]]
        report_str += f"{idx:02d}). {item['desc']}: "
        row = [idx, item['desc']]
        for tn in test_names:
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


def run_tester(test_config_path, test_name, script_path, log_path, print_log_type, result_value):
    pxt = PXTester(test_config_path=test_config_path, test_name=test_name, script_path=script_path,
                   log_path=log_path, print_log_type=print_log_type, test_result=result_value)
    pxt.execute("", sync=True)

def start(args):
    # test_config_path = args.testconfig
    # test_name = args.testname, script_path = args.scriptpath,
    # log_path = args.logpath, print_log_type = args.printlogtype
    threads = []
    global test_reports
    test_reports = {}
    global test_names
    test_names = args.testname
    #
    results = {}
    manager = Manager()
    for test_name in args.testname:
        tr = manager.Value(c_wchar_p, '')
        # t = Thread(target=run_tester, args=(args.testconfig, test_name, args.scriptpath, args.logpath, args.printlogtype))
        t = Process(target=run_tester, args=(args.testconfig, test_name, args.scriptpath, args.logpath, args.printlogtype, tr))
        results[test_name] = tr
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    reports = {}
    ri = {}
    for tn in results:
        res = json.loads(results[tn].value)
        ri[tn] = res
    for key in ri[test_names[0]]['report']:
        reports[key] = {}
        for tn in test_names:
            reports[key][tn] = ri[tn]['report'][key]
    output_report(reports)

def main(*args, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--testconfig', type=str, required=True, help='Test config path')
    # parser.add_argument('-n', '--testname', type=str, required=True, help='Test name')
    parser.add_argument('-n', '--testname',  nargs='+', required=True, help='Test name')
    parser.add_argument('-s', '--scriptpath', type=str, required=True, help='Script path')
    parser.add_argument('-o', '--logpath', type=str, help='Log path')
    parser.add_argument('-p', '--printlogtype', nargs='+', default=['ea', 'report'], required=False,
                        help='Print log type,  account order ea report')
    args = parser.parse_args()
    start(args)
    # pxt = PXTester(test_config_path=args.testconfig, test_name=args.testname, script_path=args.scriptpath,
    #                log_path=args.logpath, print_log_type=args.printlogtype)
    # pxt.execute("", sync=True)


if __name__ == '__main__':
    main()

