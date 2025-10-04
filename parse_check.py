import ast, pathlib
code = pathlib.Path('main.py').read_text(encoding='utf-8')
ast.parse(code)
print('AST OK')
