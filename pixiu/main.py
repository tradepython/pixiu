import argparse
from pixiu.pxtester import PXTester

def main(*args, **kwargs):
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--testconfig', type=str, required=True, help='Test config path')
    parser.add_argument('-n', '--testname', type=str, required=True, help='Test name')
    parser.add_argument('-s', '--scriptpath', type=str, required=True, help='Script path')
    parser.add_argument('-o', '--logpath', type=str, help='Log path')
    args = parser.parse_args()
    pxt = PXTester(test_config_path=args.testconfig, test_name=args.testname, script_path=args.scriptpath,
                   log_path=args.logpath)
    pxt.execute("", sync=True)


if __name__ == '__main__':
    main()

