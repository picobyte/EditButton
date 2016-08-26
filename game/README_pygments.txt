

To get color support, you need to install the pygments module in your game directory. And modfy some non utf-8 characters as described below.

On linux pygments can be installed from the commandline:


cd /path/to/your/renpy/project/game

pip install --target ./python-packages pygments


However, since some files contain non utf-8 characters, this causes the following error in Ren'Py.

...
    from pygments.lexers.python import PythonLexer
SyntaxError: (unicode error) 'utf8' codec can't decode byte 0xb7 in position 0: invalid start byte (__init__.py, line 232)


The file uses particular characters to indicate the presence of whitespace, described in http://pygments.org/docs/filters/ class VisibleWhitespaceFilter. We don't need them. To replcae these by dots in the linux commandline:

sed -i 's/[\d128-\d255]/./g' python-packages/pygments/filters/__init__.py



