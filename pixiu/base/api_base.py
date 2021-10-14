
import math
import json
from datetime import (datetime, timedelta)
import random
import numpy as np
import pandas as pd
import time
from RestrictedPython.Guards import (guarded_unpack_sequence, )
from RestrictedPython.Eval import (default_guarded_getiter, )
import inspect
from pixiu.api.utils import (load_json, dump_json)

from ..api.v1 import (TimeFrame, OrderCommand, Order, APIStub as API_V1)

import logging
log = logging.getLogger(__name__)


class API_V1_Base(API_V1):
    """"""
    def __init__(self, data_source, default_symbol):
        self.data_source = data_source
        self.default_symbol = default_symbol

    def dict_to_order(self, order_dict):
        return Order(order_dict)

    # def datetime_(self, *args, **kwargs):
    #     return datetime(*args, **kwargs)

    #
    def default_guarded_getitem(self, ob, index):
        # No restrictions.
        return ob[index]

    def default_guarded_getattr(self, object, name, default=None):
        # No restrictions.
        return getattr(object, name, default)

    def default_unpack_sequence(self, *args, **kwargs):
        # No restrictions.
        #see: https://github.com/zopefoundation/RestrictedPython/blob/master/tests/transformer/test_assign.py
        return guarded_unpack_sequence(*args, **kwargs)
        # return getattr(object, name, default)

    def default_getiter(self, *args, **kwargs):
        # No restrictions.
        # return args.__iter__()
        return default_guarded_getiter(*args, **kwargs)

    def lock_object(self):
        return LockObject
    #
    def set_fun(self, env_dict):
        #BuildIn
        #see: https://github.com/zopefoundation/RestrictedPython/blob/9d3d403a97d7f030b6ed0f82900b2efac151dec3/tests/transformer/test_classdef.py
        env_dict["__metaclass__"] = type #support class
        env_dict["__name__"] = "ea_script" #support class
        env_dict["_write_"] = lambda x: x
        #support print
        env_dict["_print_"] = self._print_
        env_dict["_getitem_"] = self.default_guarded_getitem
        env_dict["_getiter_"] = self.default_getiter
        env_dict["_unpack_sequence_"] = self.default_unpack_sequence
        #System Functions
        env_dict["json"] = json
        env_dict["load_json"] = load_json
        env_dict["dump_json"] = dump_json
        env_dict["round"] = round
        env_dict["dict"] = dict
        env_dict["list"] = list
        env_dict['math'] = math
        env_dict['nan'] = np.nan
        env_dict['isnan'] = np.isnan
        env_dict['isnull'] = pd.isnull
        env_dict["datetime"] = datetime
        env_dict["timedelta"] = timedelta
        env_dict["random"] = random
        env_dict["time"] = time
        env_dict["pandas"] = pd
        env_dict["numpy"] = np
        #
        env_dict["LockObject"] = self.lock_object

        #
        members = inspect.getmembers(API_V1)
        for m in members:
            fun_n = m[0]
            if not fun_n.startswith('_'):
                env_dict[fun_n] = getattr(self, fun_n)
            elif fun_n == "__global_defines__":
                global_defines = getattr(self, fun_n)
                for k in global_defines:
                    env_dict[k] = global_defines[k]

