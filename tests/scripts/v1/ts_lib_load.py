###[lib]=["test_lib==1.0"]

assertEqual(lib_test0(), True)
assertEqual(lib_test1(), True)
assertEqual(lib_test2(), True)
set_test_result("OK")
#
StopTester()