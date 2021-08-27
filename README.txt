This is a runtime Ren'Py editor. Do not use this in commercial only visual novels without eventual public release.

To get color support, you need to install the pygments module in your game directory.

latest working version is 2.5.2, in a2d5f6b318d70d8d6a230cba46c8fc585efdaf1e python 2 support was removed.

pip install --constraint <(echo "pygments == 2.5.2") --target ./game/python-packages pygments --upgrade
pip install --target ./game/python-packages pyperclip

And modify change game/python-packages/pygments/filters/__init__.py

mv pygments_filters_init_py_replacement game/python-packages/pygments/filters/__init__.py



# The alternative for the file replacement, is the removal of non utf-8 characters therein, which cause a bytecode error during Ren'Py compilation:
# sed -i 's/[\d128-\d255]/./g' game/python-packages/pygments/filters/__init__.py

