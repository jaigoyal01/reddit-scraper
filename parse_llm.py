import ast, pathlib
code = pathlib.Path('llm_service.py').read_text(encoding='utf-8')
ast.parse(code)
print('llm_service syntax OK')
