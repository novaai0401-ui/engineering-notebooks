"""Run executable notebook cells in order without installing Jupyter."""
import argparse
import ast
import asyncio
import inspect
import json
from pathlib import Path

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--book', help='Notebook stem, for example 06-algorithms-and-design-patterns')
args = parser.parse_args()
books = sorted(root.glob('[0-9][0-9]-*.ipynb'))
if args.book:
    books = [book for book in books if book.stem == args.book]
    if not books:
        parser.error('Unknown notebook stem')
for book in books:
    scope = {'__name__': '__notebook__'}
    print('\nRUNNING', book.name)
    for cell in json.loads(book.read_text(encoding='utf-8'))['cells']:
        if cell['cell_type'] != 'code':
            continue
        source = ''.join(cell['source'])
        result = eval(compile(source, book.name, 'exec', flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT), scope)
        if inspect.isawaitable(result):
            asyncio.run(result)
    print('PASSED', book.name)

