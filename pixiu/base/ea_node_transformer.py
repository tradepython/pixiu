
from RestrictedPython.transformer import (RestrictingNodeTransformer, copy_locations,)
import ast



# https://rokujyouhitoma.hatenablog.com/entry/2018/06/05/063701
class EARestrictingNodeTransformer(RestrictingNodeTransformer):

    def inject_print_collector(self, node, position=0):
        #see: https://github.com/zopefoundation/RestrictedPython/blob/c1bc989e1fa060273594e39a86d3c4fb3ffe3a4b/src/RestrictedPython/transformer.py#L79
        print_used = self.print_info.print_used
        printed_used = self.print_info.printed_used

        if print_used or printed_used:
            # Add '_print = _print_(_getattr_)' add the top of a
            # function/module.
            _print = ast.Assign(
                targets=[ast.Name('_print', ast.Store())],
                value=ast.Call(
                    func=ast.Name("_print_", ast.Load()),
                    args=[ast.Name("_getattr_", ast.Load())],
                    keywords=[]))

            if isinstance(node, ast.Module):
                _print.lineno = position
                _print.col_offset = position
                ast.fix_missing_locations(_print)
            else:
                copy_locations(_print, node)

            node.body.insert(position, _print)

            # if not printed_used:
            #     self.warn(node, "Prints, but never reads 'printed' variable.")
            #
            # elif not print_used:
            #     self.warn(node, "Doesn't print, but reads 'printed' variable.")

    # def visit_Import(self, node):
    #     self.error(node, 'Import statements are not allowed.')
    # visit_ImportFrom = visit_Import

# source_code = "import this"
#
# try:
#     byte_code = compile_restricted(
#         source=source_code,
#         filename='<inline>',
#         mode='exec',
#         policy=EARestrictingNodeTransformer)
#     exec(byte_code)
# except SyntaxError as e:
#     raise e