init python:
    import os
    import re
    import shutil

    from tempfile import mkstemp
    import math

    has_renpyformatter = True
    try:
        from pygments import highlight
        from renpy_lexer import RenPyLexer
        from renpyformatter import RenPyFormatter
        from pygments.styles import get_style_by_name
    except ImportError:
        has_renpyformatter = False

    style.editor = Style(style.default)
    # must be monospace or need/add shadow
    style.editor.font = "Inconsolata-Regular.ttf"
    style.editor.color = "#FFFFFF" # caret

    def linkhandler(target):
        # the dfault handler:
        m = re.match('^([a-zA-Z_][\w.]*)\s*\(.*\)$', target)
        if m and callable(m.group(1)):
            eval(m.group(0))
        elif ":" in target:
            try:
                import webbrowser
                webbrowser.open(target)
            except:
                pass
        else:
            renpy.call_in_new_context(target)

    def hyperlink_styler(target):
        return style.hyperlink_text

    def get_filetree(dir=renpy.config.gamedir, extension=('.py','.rpy')):
        list = []
        i = len(renpy.config.gamedir) + 1
        for path, dirs, files in os.walk(dir):
            for file in files:
                if file.endswith(extension):
                    list.append(os.path.join(path[i:], file))
        return list

    class TextData(object):
        y = 0
        firstline = 0
        def __init__(self):
            self.buffer = []
        @property
        def lastline(self): return len(self.buffer)

        def deserialize(self, fname):
            with open(os.path.join(renpy.config.basedir, fname)) as fh:
                for line in fh:
                    self.buffer.append(line.rstrip('\r\n'))

    class rpio(object):
        def __init__(self): self.keymap = set()
        def rpescape(self, string): return re.sub(r'(?<!\{)(\[(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', string))
        def _list_keymap(self, km, n, mod): return [mod+'K_'+k for k in km] + ['repeat_'+mod+'K_'+k for k in km] + n
        def repeat_keymap(self, km = [], n = [], mod=''): self.keymap.update(self._list_keymap(km, n, mod))
        def remove_repeat_keymap(self, km = [], n = [], mod=''): self.keymap.difference_update(self._list_keymap(km, n, mod))
        def all_subclasses(self, cls): return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in self.all_subclasses(s)]

    class TextView(rpio):
        wheel_scroll_lines = 3
        cursor = [0, 0, 0, 0] # last two are for dragging
        def __init__(self, fname=None, nolines=None, lnr=None, lexer=None, format_style=None, wheel_scroll_lines=None):
            super(TextView, self).__init__()
            self.data = TextData()
            self.lnr = lnr if lnr else 0
            self.lexer = lexer if lexer else RenPyLexer()
            self.formater = RenPyFormatter(style=format_style if format_style else 'monokai')
            self.deserialize(fname)
            self.input_changed = False
            # XXX default nolines should be relative to window + font size
            self.nolines = nolines if nolines else int(config.screen_height / (34 + style.default.line_leading + style.default.line_spacing)) - 1
            self.repeat_keymap(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['mousedown_4', 'mousedown_5'])
            self.repeat_keymap(["HOME", "END"], mod="ctrl_")

        @property
        def buffer(self): return self.data.buffer
        #@property
        #def prompt(self): return '' # could be used to show line numbers.
        @property
        def line(self): return self.buffer[self.lnr+self.cursor[1]]

        def deserialize(self, fname):
            #pygments strips leading whitespace. this prevent that.
            self.colored_buffer = []
            self.fname = fname
            self.data.deserialize(fname)
            for line in self.buffer:
                if line != "":
                    break
                self.colored_buffer.append("")

            self.colored_buffer.extend(highlight(os.linesep.join(self.buffer), self.lexer, self.formater).split(os.linesep))

        def gotoline(self, lineno):
            if self.input_changed:
                #self.buffer[self.lnr + self.data.y] = self.rpescape(self._input)
                renpy.get_widget("edit", "lines").set_text(os.linesep.join(self.buffer))
            return min(max(lineno, self.data.firstline), self.data.lastline-self.cursor[1]-1)

        def UP(self):
            self.cursor[1] = max(self.cursor[1] - 1, 0)
            self.lnr = self.gotoline(self.lnr - (self.cursor[1] == 0))

        def DOWN(self):
            self.cursor[1] = min(self.cursor[1] + 1, self.nolines)
            self.lnr = self.gotoline(self.lnr + (self.cursor[1] == self.nolines))

        def PAGEUP(self): self.lnr = self.gotoline(self.lnr - self.nolines)
        def PAGEDOWN(self): self.lnr = self.gotoline(self.lnr + self.nolines)

        def ctrl_HOME(self): self.lnr = self.gotoline(self.data.firstline)
        def ctrl_END(self): self.lnr = self.gotoline(self.data.lastline)

        def mousedown_4(self): self.lnr = self.gotoline(self.lnr - self.wheel_scroll_lines)
        def mousedown_5(self): self.lnr = self.gotoline(self.lnr + self.wheel_scroll_lines)

        def handlekey(self, keystr):
            getattr(self, re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)K_', r'\1', keystr))()

    class EditView(TextView):

        def __init__(self, **kwargs):
            super(EditView, self).__init__(**kwargs)

            #self.styleprefix = "editor"
            self._input = ''
            self.repeat_keymap(["BACKSPACE", "RETURN", "LEFT", "RIGHT"], ["K_HOME", "K_END"])
            self.fontsize = 34
            self.END()

        def LEFT(self):
            self.caret_max = min(self.caret_max - 1, len(self.line))
            self.cursor[0] = self.caret_max

        def RIGHT(self):
            self.caret_max = min(self.caret_max + 1, len(self.line))
            self.cursor[0] = self.caret_max

        def HOME(self):
            self.caret_max = 0
            self.cursor[0] = 0

        def END(self):
            self.caret_max = 0xffff
            self.cursor[0] = min(self.caret_max, len(self.line))

        def handlekey(self, keystr):
            keystr = re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)K_', r'\1', keystr)
            getattr(self, keystr)()
            if keystr not in self.__dict__:
                self.cursor[0] = min(self.caret_max, len(self.line))

        @property
        def caret(self): return ' ' * self.cursor[0]

        def serialize(self):
            if self.changes:
                try:
                    fh, abs_path = mkstemp()
                    for line in self.buffer:
                        os.write(fh, line + os.linesep)

                    os.close(fh)
                    shutil.move(abs_path, self.fname)
                    self.changes = 0 # changes applied
                except Exception:
                    pass

        def context_lines(self):
            # copied from old code, was it missing? - see _update()
            s = max(self.lnr - self.nolines, 1)
            e = min(s + self.nolines + 1, len(self.buffer))

            #pygments strips leading whitespace. prevent this.
            lines = ""
            while s != e and self.buffer[s].rstrip('\r\n') == "":
                lines += self.buffer[s]
                s += 1
            if has_renpyformatter:
                lines += highlight("".join(self.buffer[s:e]), self.lexer, RenPyFormatter(style='monokai'))
            else:
                for i in range(s, e):
                    alpha = -min(0.8, 0.1 * math.log(abs(i-self.lnr) + 1))
                    lines += ("{alpha=%.2f}" % alpha) + self.buffer[i] + "{/alpha}"
            return lines

        def _update(self, update): # FIXME
            inp = renpy.get_widget("edit", "input")
            self.cursor[0] = inp.caret_pos
            self._input = update
            if not self.input_changed and self.buffer[self.lnr + self.data.y] != update:
                self.input_changed = True

            self.buffer[self.lnr + self.data.y] = update
            lns = renpy.get_widget("edit", "lines")
            lns.set_text(self.context_lines())

        def RETURN(self): # FIXME

            y = self.cursor[1]
            inp = renpy.get_widget("edit", "input")
            self.buffer[self.lnr + self.data.y] = self.rpescape(self._input[inp.caret_pos:])

            self._input = self._input[:inp.caret_pos]
            self.buffer.insert(y, '')
            self.input_changed = True
            self.gotoline(y + 1)
            inp.caret_pos = 0

        def BACKSPACE(self):

            y = self.lnr+self.cursor[1]
            inp = renpy.get_widget("edit", "input")

            if inp.caret_pos == 0:
                if self.lnr != 0: #FIXME
                    self.input_changed = True
                    self.buffer[y - 1] += self.buffer[y]
                    del self.buffer[y]
                    self.UP()
                    inp.caret_pos = 5

                    #FIXME concatenate line with previous and make cursor right
            else: # FIXME jumps to end of line
                self.buffer[y] = self.line[:-1]

        def display(self):
            txt = '{color=#000000}' if self.lnr != 0 else ''
            lastline = min(self.lnr + self.nolines, self.data.lastline)
            txt += os.linesep.join(self.colored_buffer[self.lnr:lastline])
            if lastline == self.data.lastline != 0:
                txt += '{/color}'
            return txt

        def get_ypos(self):
            return min(self.cursor[1], self.nolines) * self.fontsize;

        def external_editor(self, transient=1):
            renpy.exports.launch_editor([self.fname], self.lnr, transient=transient)

    class Editor(rpio):
        def __init__(self, fname=None):
            super(Editor, self).__init__()
            self.fl = {}
            self._createview(fname)

        def _createview(self, fname, offset=2):
            if fname is None:
                (fname, lnr) = renpy.get_filename_line()
            lnr = lnr - 1 if fname else 0 # no fname indicates failure

            if fname not in self.fl:
                self.fl[fname] = EditView(fname=fname, lnr=lnr)
            self.view = self.fl[fname]

    class Clicker(object):
        links = {}
        def __init_(self):
            self.orig_hln_cb = config.hyperlink_callback
            #config.hyperlink_callback = self.clicked

        def clickify(self, links):
            for f in links:
                self.links[f] = True
            return os.linesep.join(["{a="+f+"}"+f+"{/a}" for f in links])
        def clicked(self, link):
            devlog.info(link)

screen openfile():
    frame:
        default filetree = get_filetree()
        default nolines = 30
        default firstline = 0
        default lastline = max(0, len(filetree) - nolines)
        default lnr = 0
        xpadding 10
        ypadding 10
        xpos 100
        background "#272822"
        $ clicker = Clicker()

        text clicker.clickify(filetree[lnr:(min(lnr, lastline)+nolines)]) style "editor"

        key "K_UP" action SetScreenVariable("lnr", max(lnr - 1, firstline))
        key "K_DOWN" action SetScreenVariable("lnr", min(lnr + 1, lastline))
        key "repeat_K_UP" action SetScreenVariable("lnr", max(lnr - 1, firstline))
        key "repeat_K_DOWN" action SetScreenVariable("lnr", min(lnr + 1, lastline))

        key "K_HOME" action SetScreenVariable("lnr", firstline)
        key "K_END" action SetScreenVariable("lnr", lastline)

        key "K_PAGEUP" action SetScreenVariable("lnr", max(lnr-nolines, firstline))
        key "K_PAGEDOWN" action SetScreenVariable("lnr", min(lnr+nolines, lastline))

        key "repeat_K_PAGEUP" action SetScreenVariable("lnr", max(lnr-nolines, firstline))
        key "repeat_K_PAGEDOWN" action SetScreenVariable("lnr", min(lnr+nolines, lastline))

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if editor.view.input_changed:
                textbutton _("Apply") action Function(editor.view.serialize)
            #textbutton _("Screenshot") action Function(renpy.screenshot, '/tmp/ed.png')
            textbutton _("Cancel") action Return()

style editor_frame:
        xpadding 10
        ypadding 10
        xpos 100
        background "#272822"

screen edit():
    style_prefix "editor"
    hbox:
        frame:

            add Input(default=editor.view.caret, changed=editor.view._update, ypos=editor.view.get_ypos(), style=style.editor) id "input"

            text editor.view.display() style "editor" id "lines"

            for keystr in editor.view.keymap:
                key keystr action Function(editor.view.handlekey, keystr)

        vbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if editor.view.input_changed:
                textbutton _("Apply") action Function(editor.view.serialize)
            textbutton _("Open file") action ShowMenu('openfile')
            textbutton _("External editor") action Function(editor.view.external_editor)
            #textbutton _("Screenshot") action Function(renpy.screenshot, '/tmp/ed.png')
            textbutton _("Cancel") action Return()
