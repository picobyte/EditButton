# EditButton
Add a quick fix/edit button for Ren'Py developers

Requirements: git, python (2), pip and the installation of python libraries as described below.

The first three should be available for Windows or Mac, just google e.g. 'git for windows'.

```bash
git clone https://github.com/picobyte/EditButton.git

git clone --depth 2 --filter=blob:none --sparse https://github.com/chrissimpkins/codeface.git ./game/codeface

cd game/codeface
git sparse-checkout set 'fonts/proggy-clean' 'fonts/inconsolata/'
cd -

# in windows msdos I believe you can use `python -m pip' instead of pip
pip install --target ./game/python-packages pyperclip

pip install --constraint <(echo "pygments == 2.5.2") --target ./game/python-packages pygments --upgrade

pip install --target ./game/python-packages pyspellchecker==0.5.6
```

move/replace the \_\_init\_\_\.py file:
```bash
mv pygments_filters_init_py_replacement game/python-packages/pygments/filters/__init__.py
```
In windows similar; e.g. just copy the first file, remove the existing file in the subdirectory, and paste the new file there and rename it accordingly.

The spellchecker seems to mislocate the python-packages. In Linux a symlink can resolve this:
```bash
ln -s game/python-packages/
```
Not sure if also a problem in windows but a solution could be to to duplicate the pyspellchecker directory (with pip like below or simply copy)
```
python -m pip install --target python-packages pyspellchecker==0.5.6
```

Latest working version of pygments is 2.5.2, thereafter python 2 support was removed.

Replacing the __init__.py file is to remove non utf-8 characters, which causes a bytecode error during Ren'Py compilation. This should produce the same as `sed -i 's/[\d128-\d255]/./g' game/python-packages/pygments/filters/__init__.py`

To add the edit button to an existing project, add to your in screens.rpy `screen quick_menu()` (just below the yalign):
```renpy
        if config.developer and _editor.editor:
            textbutton _("Edit") action [_editor.editor.start(renpy.get_filename_line()), ShowMenu('_editor_main')]
```

also needed to run are the files:
```
game/codeface/fonts/inconsolata/Inconsolata-Regular.ttf
game/renpyformatter.py
game/renpy_lexer.py
game/edit_button.rpy
```

This is a runtime Ren'Py editor. Licensed LGPL or MIT under certain conditions. Do not use this in commercial closed source only visual novels without eventual public releases unless a permission was granted.

