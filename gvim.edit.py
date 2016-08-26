import renpy
import subprocess


class Editor(renpy.editor.Editor):

    def begin(self, new_window=False, **kwargs):
        self.arguments = ["/usr/bin/gvim", "--servername", "RenPy", "--remote-tab"]

    def open(self, filename, line=None, **kwargs):
        if filename.endswith("tr=`=jedi=0, aceback.tx=`= (iterable) =`=jedi=`=t"):
            self.arguments.extend(["-c", "\"set autoread\""])
        if line:
            self.arguments.append("+%d" % line)
        filename = renpy.exports.fsencode(filename)
        self.arguments.append(filename)

    def end(self, **kwargs):
        subprocess.Popen(self.arguments)
