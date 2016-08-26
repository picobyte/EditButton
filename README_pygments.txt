

To get color support, you need to install the pygments module in your game directory.

pip install --target ./game/python-packages pygments

And modify change game/python-packages/pygments/filters/__init__.py

mv pygments_filters_init_py_replacement game/python-packages/pygments/filters/__init__.py



# Alternatively, this should work as well:
# sed -i 's/[\d128-\d255]/./g' game/python-packages/pygments/filters/__init__.py


