This is a runtime Ren'Py editor. Licensed LGPL or MIT under certain conditions. Do not use this in commercial closed source only visual novels without eventual public releases.

Requirements:
install python libraries

```bash
pip install --target ./game/python-packages pyperclip

pip install --constraint <(echo "pygments == 2.5.2") --target ./game/python-packages pygments --upgrade
mv pygments_filters_init_py_replacement game/python-packages/pygments/filters/__init__.py

pip install --target ./game/python-packages pyspellchecker==0.5.6
ln -s game/python-packages/
```
Not sure if also a problem in windows but the spellchecker seems to mislocate teh python-packages. that's what the symlink tries to resolve. In windows a workign slution could be to to duplicate the pyspellchecker directory
```
pip install --target python-packages pyspellchecker==0.5.6
```
or rather however you manage to do that in windows.

Latest working version of pygments is 2.5.2, thereafter python 2 support was removed.

Replacing the file is to remove non utf-8 characters, which causes a bytecode error during Ren'Py compilation. this should produce the same as `sed -i 's/[\d128-\d255]/./g' game/python-packages/pygments/filters/__init__.py`


