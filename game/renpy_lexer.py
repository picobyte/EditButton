# -*- coding: utf-8 -*-

import re

from pygments.lexer import RegexLexer, include, bygroups, using, \
    default, words, combined
from pygments.util import shebang_matches
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation
from pygments.lexers.python import PythonLexer

class RenPyLexer(RegexLexer):

    name = 'RenPy'
    aliases = ['renpy']
    filenames = ['*.rpy']
    mimetypes = ['text/x-python', 'application/x-python']

    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting
            (r'%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
             '[hlL]?[diouxXeEfFgGcrs%]', String.Interpol),
            # backslashes, quotes and formatting signs must be parsed one at a time
            (r'[^\\\'"%\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r'%', ttype),
            # newlines are an error (use "nl" state)
        ]

    tokens = {
        'root': [
            (r'\n', Text),
            (r'^(\s*)([rRuU]{,2}"""(?:.|\n)*?""")', bygroups(Text, String.Doc)),
            (r"^(\s*)([rRuU]{,2}'''(?:.|\n)*?''')", bygroups(Text, String.Doc)),
            (r'[^\S\n]+', Text),
            (r'\A#!.+$', Comment.Hashbang),
            (r'#.*$', Comment.Single),
            (r'[]{}:(),;[]', Punctuation),
            (r'\\\n', Text),
            (r'\\', Text),
            (r'(in|is|and|or|not)\b', Operator.Word),
            (r'!=|==|<<|>>|[-~+/*%=<>&^|.]', Operator),
            include('keywords'),
            (r'(def)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'funcname'),

            (r'(label)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'label'),
            (r'(define)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'define'),
            (r'\s+(\$)', bygroups(Keyword, Text), 'python-content'),
            (r'(screen)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'screen'),
            (r'(style)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'style'),

            (r'(class)((?:\s|\\\s)+)', bygroups(Keyword, Text), 'classname'),
            (r'(from)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'fromimport'),
            (r'(import)((?:\s|\\\s)+)', bygroups(Keyword.Namespace, Text),
             'import'),
            include('builtins'),
            include('backtick'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"""', String.Double, 'tdqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'''", String.Single, 'tsqs'),
            ('(?:[rR]|[uU][rR]|[rR][uU])"', String.Double, 'dqs'),
            ("(?:[rR]|[uU][rR]|[rR][uU])'", String.Single, 'sqs'),
            ('[uU]?"""', String.Double, combined('stringescape', 'tdqs')),
            ("[uU]?'''", String.Single, combined('stringescape', 'tsqs')),
            ('[uU]?"', String.Double, combined('stringescape', 'dqs')),
            ("[uU]?'", String.Single, combined('stringescape', 'sqs')),
            include('name'),
            include('numbers'),
        ],

        'label': [
            ('[a-zA-Z_]\w*', Name.Label, '#pop')
        ],
        'define': [
            ('[a-zA-Z_]\w*', Name.Variable, '#pop')
        ],
        'screen': [
            ('[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'style': [
            ('[a-zA-Z_]\w*', Name.Property, '#pop')
        ],
        'python-content': [
            (r'(\s*)(\$)',
             bygroups(Punctuation, Text, Punctuation, Text, Name.Tag, Text,
                      Punctuation), '#pop'),
            (r'(?<!\\)(?:\\\\)*$', using(PythonLexer)),
        ],

        'keywords': [
            (words((
                'assert', 'break', 'continue', 'del', 'elif', 'else', 'except',
                'exec', 'finally', 'for', 'global', 'if', 'lambda', 'pass',
                'print', 'raise', 'return', 'try', 'while', 'yield',
                'yield from', 'as', 'with'), suffix=r'\b'),
             Keyword),
        ],
        'builtins': [
            (words((
                '__import__', 'abs', 'all', 'any', 'apply', 'basestring', 'bin',
                'bool', 'buffer', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
                'cmp', 'coerce', 'compile', 'complex', 'delattr', 'dict', 'dir', 'divmod',
                'enumerate', 'eval', 'execfile', 'exit', 'file', 'filter', 'float',
                'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'hex', 'id',
                'input', 'int', 'intern', 'isinstance', 'issubclass', 'iter', 'len',
                'list', 'locals', 'long', 'map', 'max', 'min', 'next', 'object',
                'oct', 'open', 'ord', 'pow', 'property', 'range', 'raw_input', 'reduce',
                'reload', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
                'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type',
                'unichr', 'unicode', 'vars', 'xrange', 'zip'),
                prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'(?<!\.)(self|None|Ellipsis|NotImplemented|False|True'
             r')\b', Name.Builtin.Pseudo),
            (words((
                'ArithmeticError', 'AssertionError', 'AttributeError',
                'BaseException', 'DeprecationWarning', 'EOFError', 'EnvironmentError',
                'Exception', 'FloatingPointError', 'FutureWarning', 'GeneratorExit',
                'IOError', 'ImportError', 'ImportWarning', 'IndentationError',
                'IndexError', 'KeyError', 'KeyboardInterrupt', 'LookupError',
                'MemoryError', 'NameError', 'NotImplemented', 'NotImplementedError',
                'OSError', 'OverflowError', 'OverflowWarning', 'PendingDeprecationWarning',
                'ReferenceError', 'RuntimeError', 'RuntimeWarning', 'StandardError',
                'StopIteration', 'SyntaxError', 'SyntaxWarning', 'SystemError',
                'SystemExit', 'TabError', 'TypeError', 'UnboundLocalError',
                'UnicodeDecodeError', 'UnicodeEncodeError', 'UnicodeError',
                'UnicodeTranslateError', 'UnicodeWarning', 'UserWarning',
                'ValueError', 'VMSError', 'Warning', 'WindowsError',
                'ZeroDivisionError'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Exception),
        ],
        'numbers': [
            (r'(\d+\.\d*|\d*\.\d+)([eE][+-]?[0-9]+)?j?', Number.Float),
            (r'\d+[eE][+-]?[0-9]+j?', Number.Float),
            (r'0[0-7]+j?', Number.Oct),
            (r'0[bB][01]+', Number.Bin),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (r'\d+L', Number.Integer.Long),
            (r'\d+j?', Number.Integer)
        ],
        'backtick': [
            ('`.*?`', String.Backtick),
        ],
        'name': [
            (r'@[\w.]+', Name.Decorator),
            ('[a-zA-Z_]\w*', Name),
        ],
        'funcname': [
            ('[a-zA-Z_]\w*', Name.Function, '#pop')
        ],
        'classname': [
            ('[a-zA-Z_]\w*', Name.Class, '#pop')
        ],
        'import': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'as\b', Keyword.Namespace),
            (r',', Operator),
            (r'[a-zA-Z_][\w.]*', Name.Namespace),
            default('#pop')  # all else: go back
        ],
        'fromimport': [
            (r'(?:[ \t]|\\\n)+', Text),
            (r'import\b', Keyword.Namespace, '#pop'),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r'None\b', Name.Builtin.Pseudo, '#pop'),
            # sadly, in "raise x from y" y will be highlighted as namespace too
            (r'[a-zA-Z_.][\w.]*', Name.Namespace),
            # anything else here also means "raise x from y" and is therefore
            # not an error
            default('#pop'),
        ],
        'stringescape': [
            (r'\\([\\abfnrtv"\']|\n|N\{.*?\}|u[a-fA-F0-9]{4}|'
             r'U[a-fA-F0-9]{8}|x[a-fA-F0-9]{2}|[0-7]{1,3})', String.Escape)
        ],
        'strings-single': innerstring_rules(String.Single),
        'strings-double': innerstring_rules(String.Double),
        'dqs': [
            (r'"', String.Double, '#pop'),
            (r'\\\\|\\"|\\\n', String.Escape),  # included here for raw strings
            include('strings-double')
        ],
        'sqs': [
            (r"'", String.Single, '#pop'),
            (r"\\\\|\\'|\\\n", String.Escape),  # included here for raw strings
            include('strings-single')
        ],
        'tdqs': [
            (r'"""', String.Double, '#pop'),
            include('strings-double'),
            (r'\n', String.Double)
        ],
        'tsqs': [
            (r"'''", String.Single, '#pop'),
            include('strings-single'),
            (r'\n', String.Single)
        ],
    }

    def analyse_text(text):
        return shebang_matches(text, r'pythonw?(2(\.\d)?)?') or \
            'import ' in text[:1000]


