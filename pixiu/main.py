import argparse
from pixiu.pxtester import PXTester

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def main(*args, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--testconfig', type=str, required=True, help='Test config path')
    parser.add_argument('-n', '--testname', type=str, required=True, help='Test name')
    parser.add_argument('-s', '--scriptpath', type=str, required=True, help='Script path')
    parser.add_argument('-o', '--logpath', type=str, help='Log path')
    parser.add_argument('-p', '--printlogtype', nargs='+', default=['ea', 'report'], required=False,
                        help='Print log type,  account order ea report')
    args = parser.parse_args()
    pxt = PXTester(test_config_path=args.testconfig, test_name=args.testname, script_path=args.scriptpath,
                   log_path=args.logpath, print_log_type=args.printlogtype)
    pxt.execute("", sync=True)


if __name__ == '__main__':
    main()

