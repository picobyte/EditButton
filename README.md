# EditButton
Add a quick fix/edit button for Ren'Py developerment. without config.developer set the editor isn't be accessible.

The editor provides a means to proofread your visual novel while running it and without leaving. One button in the quickmenu provides access to this editor that shows the Ren'py code at the location you were, in visual modus. The editor provides basic features, has a few quirks still, but I believe nothing serious.

The editor isn't perfect, and currently has a limited set of features:
* basic editing
 - cursor, clipboard, selection (Shift+)(Ctrl+)key movement,
 - selection can only cover the screen you're working in; WIP
* Undo / redo, (Ctrl-z/Ctrl-y), only the cursor position thereafter is a bit odd, WIP.
* editor display style configuration (color scheme)
* Ren'py error checking - can be hidden.
* file saving
 - only available if the code is without errors. A safety net, because error make the editor is unavailable.
 - save returns to visual modus and after a reload (Ctrl+R) changes should be shown.
 - there should probably also be a save without leaving the editor
* returning to visual modus discarding changes
* returning to visual modus keeping changes *temporarily* in memory
 - changes are lost after reload or loading.
* Spell checking:
 - languages English, also available for French, German, Portuguese, Spanish. Russian should work with an update, see below.
 - suggestions for changes can be chosen from a drop-down (or pull-up) menu
* find text, very basic, still.
* file and line number are shown in the menu title, cursor and mouse position as well, updated upon cursor movement. 
* there is a right-click mouse menu.
 - languages and styles can be chosen here.
 - currently selecting font is listed but broken. (I can get one side-menu, but the second, for font size is not shown, WIP). 

Repository: https://github.com/picobyte/EditButton
You can also report issues and feature requests there.


To add the edit button to an existing project, add to your in screens.rpy `screen quick_menu()` (just below the yalign):
```renpy
        if config.developer and _editor.editor:
            textbutton _("Edit") action [_editor.editor.start(renpy.get_filename_line()), ShowMenu('_editor_main')]
```

Further requirements are: git, python2, pip and the installation of a few python libraries as described below.

```bash
git clone https://github.com/picobyte/EditButton.git

git clone --depth 2 --filter=blob:none --sparse https://github.com/chrissimpkins/codeface.git ./game/codeface

cd game/codeface
git sparse-checkout set 'fonts/proggy-clean' 'fonts/inconsolata/'
cd -
```

Actually Russian was not included by default. To get Russian and updates for all languages:
```bash
git clone --depth 2 --filter=blob:none --sparse https://github.com/barrust/pyspellchecker.git ./pyspellchecker

cd pyspellchecker
git sparse-checkout set spellchecker/resources/{de,en,es,fr,pt,ru}.json.gz
cd -
cp pyspellchecker/spellchecker/resources/* python-packages/spellchecker/resources/
```


```bash
# in windows msdos I believe you can use `python -m pip' instead of pip
pip install --target ./game/python-packages pyperclip

# Latest working version of pygments is 2.5.2, thereafter python 2 support was removed.
pip install --constraint <(echo "pygments == 2.5.2") --target ./game/python-packages pygments --upgrade

pip install --target ./game/python-packages pyspellchecker==0.5.6
```

move/replace the \_\_init\_\_\.py file:
```bash

# the __init__.py file has non utf-8 characters, which causes a bytecode error during Ren'Py compilation:
# The replacement file was produced with `sed -i 's/[\d128-\d255]/./g' game/python-packages/pygments/filters/__init__.py`

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

To add the edit button to an existing project, add to your in screens.rpy `screen quick_menu()` (just below the yalign):
```renpy
        if config.developer and _editor.editor:
            textbutton _("Edit") action [_editor.editor.start(renpy.get_filename_line()), ShowMenu('_editor_main')]
```

This is a runtime Ren'Py editor. Licensed LGPL or MIT can be allowed under certain conditions. Do not use this in commercial closed source only visual novels without eventual public releases unless a permission was granted.

