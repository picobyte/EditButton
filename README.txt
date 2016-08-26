

To get color support, you need to install the pygments module in your game directory.

pip install --target ./game/python-packages pygments

And modify change game/python-packages/pygments/filters/__init__.py

mv pygments_filters_init_py_replacement game/python-packages/pygments/filters/__init__.py



# The alternative for the file replacement, is the removal of non utf-8 characters therein, which cause a bytecode error during Ren'Py compilation:
# sed -i 's/[\d128-\d255]/./g' game/python-packages/pygments/filters/__init__.py


