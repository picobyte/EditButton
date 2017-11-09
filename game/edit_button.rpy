init -1500 python:

    style.editor = Style(style.default)

    # must be monospace or need/add shadow
    style.editor.font = "Inconsolata-Regular.ttf"

init -1500 python in _editor:
    from store import config, style
    import store
    import os
    import re

    import math

    from pygments import highlight
    from renpy_lexer import RenPyLexer
    from renpyformatter import RenPyFormatter
    from pygments.styles import get_style_by_name

    class ReadOnlyData(object):
        """ container and load interface for the read only data """
        def __init__(self, fname): self.load(fname)
        def __getitem__(self, ndx): return self.data[ndx]
        def __len__(self): return len(self.data)

        def load(self, fname=None):
            if fname is not None:
                self.fname = fname
            self.data = []
            with open(self.fname) as fh:
                for line in fh:
                    self.data.append(line.rstrip('\r\n'))

    class ReadWriteData(ReadOnlyData):
        """ to allow edit and saving """
        def __init__(self, fname):
            super(ReadWriteData, self).__init__(fname)
            self.changes = []
            self.start_change = 0

        def __setitem__(self, ndx, value):
            if value != self.data[ndx]:
                self.changes.append(["__setitem__", ndx, self.data[ndx]])
                self.data[ndx] = value

        def save(self):
            import shutil
            from tempfile import mkstemp
            if self.changes:
                fh, abs_path = mkstemp()
                for line in self.data:
                    os.write(fh, line + os.linesep)
                os.close(fh)
                shutil.move(abs_path, self.fname)
                self.start_change = len(self.changes)

        def __delitem__(self, ndx):
            self.changes.append(["insert", ndx, self.data[ndx]])
            del(self.data[ndx])

        def insert(self, ndx, value):
            self.changes.append(["__delitem__", ndx]) # FIXME
            self.data.insert(ndx, value)


    class rpio(object):
        def __init__(self): self.keymap = set()
        def rpescape(self, string): return re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', string))
        def _list_keymap(self, km, n, mod): return [mod+'K_'+k for k in km] + ['repeat_'+mod+'K_'+k for k in km] + n
        def repeat_keymap(self, km = [], n = [], mod=''): self.keymap.update(self._list_keymap(km, n, mod))

    class TextView(rpio):
        wheel_scroll_lines = 3
        def __init__(self, console, data, nolines=None, lnr=None, lexer=None, format_style=None, wheel_scroll_lines=None):
            super(TextView, self).__init__()
            self.data = data
            self.lnr = lnr if lnr else 0
            self.lineLenMax = 109
            self.lexer = lexer if lexer else RenPyLexer(stripnl=False)
            self.formater = RenPyFormatter(style=format_style if format_style else 'monokai')
            self.show_errors = ""
            self.parse()
            # XXX default nolines should be relative to window + font size
            self._nolines = nolines if nolines else int(config.screen_height / (34 + style.default.line_leading + style.default.line_spacing)) - 1
            self.repeat_keymap(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['mousedown_4', 'mousedown_5'])
            self.repeat_keymap(["HOME", "END"], mod="ctrl_")
            self.console = console

        @property
        def line(self): return self.data[self.lnr+self.console.cy]

        @property
        def nolines(self):
            # for each in displaydata,
            nolines = 0
            for i in xrange(self.lnr, min(self.lnr + self._nolines, len(self.data))):
                line_wraps = int(len(self.data[i])/self.lineLenMax) + 1
                if nolines + line_wraps > self._nolines:
                    break
                nolines += line_wraps
            return nolines

        def parse(self):
            self.colored_data = highlight(self.rpescape(os.linesep.join(self.data)), self.lexer, self.formater).split(os.linesep)
            renpy.parser.parse_errors = []
            renpy.parser.parse(self.data.fname, os.linesep.join(self.data))
            if self.show_errors is not None:
                self.show_errors = "\n{color=#f00}{size=-10}" + os.linesep.join(renpy.parser.parse_errors) +"{/size}{/color}" if renpy.parser.parse_errors else ""

        def gotoline(self, lineno):
            return min(max(lineno, 0), len(self.data)-self.console.cy-1)

        def UP(self, sub=1):
            sub = min(self.console.cy + self.lnr, sub)
            part = min(self.console.cy, sub)
            self.console.cy -= part
            self.lnr -= sub - part

        def DOWN(self, add=1):
            add = min(add, len(self.data) - self.console.cy - self.lnr - 1)
            part = min(self.nolines - self.console.cy - 1, add)
            self.console.cy += part
            self.lnr += add - part

        def PAGEUP(self): self.UP(self.nolines)
        def PAGEDOWN(self): self.DOWN(self.nolines)

        def ctrl_HOME(self): self.lnr = self.gotoline(0)
        def ctrl_END(self): self.lnr = self.gotoline(len(self.data))

        def mousedown_4(self): self.UP(3)
        def mousedown_5(self): self.DOWN(3)

    class EditView(TextView):

        def __init__(self, **kwargs):
            super(EditView, self).__init__(**kwargs)

            #self.styleprefix = "editor"
            self.repeat_keymap(["BACKSPACE", "DELETE", "RETURN", "LEFT", "RIGHT"], ["K_HOME", "K_END"])
            self.fontsize = 34
            self.handlekey("END")
            self.nrSymbol = ")!@#$%^&*("
            self.oSymName = [ "BACKQUOTE", "MINUS", "EQUALS", "LEFTBRACKET", "RIGHTBRACKET",
                                "BACKSLASH", "SEMICOLON", "QUOTE", "COMMA", "PERIOD", "SLASH"]
            self.oSymLow = r"`-=[]\;',./"
            self.oSymUpp = r'~_+{}|:"<>?'
            self.changed = False

        def LEFT(self, sub=1): self.console.max = max(self.console.cx - sub, 0)
        def RIGHT(self, add=1): self.console.max = min(self.console.cx + add, len(self.line))

        def HOME(self): self.console.max = 0
        def END(self): self.console.max = 0xffff # FIXME: what to do with very long lines?

        def RETURN(self):
            y = self.lnr+self.console.cy
            self.data.insert(y+1, self.data[y][self.console.cx:])
            self.data[y] = self.data[y][:self.console.cx]
            self.parse()
            self.changed = True
            self.console.max = 0
            self.DOWN()

        def BACKSPACE(self):

            y = self.lnr+self.console.cy

            self.changed = True
            if self.console.cx == 0:
                if self.lnr + self.console.cy != 0: #FIXME
                    self.console.max = len(self.data[y - 1])
                    self.data[y - 1] += self.data[y]
                    del self.data[y]
                    self.UP()
            else:
                self.LEFT()
                self.console.cx = min(self.console.max, len(self.line))
                self.DELETE()
            self.parse()

        def DELETE(self):
            x = self.console.cx
            y = self.lnr+self.console.cy
            buf = self.data[y]
            self.changed = True
            if x != len(self.line):
                self.data[y] = buf[:x] + buf[x+1:]
            elif y != self.nolines:
                self.console.max = len(buf)
                self.data[y] += self.data[y+1]
                del self.data[y+1]
            self.parse()

        def insert(self, s):
            x = self.console.cx
            buf = self.data[self.lnr+self.console.cy]
            self.data[self.lnr+self.console.cy] = buf[:x] + s + buf[x:]
            self.console.max += len(s)
            self.console.cx = min(self.console.max, len(self.line))
            renpy.redraw(self.console, 0)
            self.changed = True
            self.parse()

        def handlekey(self, keystr):
            getattr(self, re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)K_', r'\1', keystr))()
            self.console.cx = min(self.console.max, len(self.line))
            renpy.redraw(self.console, 0)

        def save(self):
            if self.changed:
                fh, abs_path = mkstemp()
                for line in self.data:
                    os.write(fh, line + os.linesep)
                os.close(fh)
                shutil.move(abs_path, self.fname)
                self.changed = False

        def colorize(self, txt, at_start=False, at_end=False):
            return ('{color=#000000}' if at_start else '') + txt + ('{/color}' if at_end else '')

        def display(self):
            ll = min(self.lnr + self.nolines, len(self.data))
            return self.colorize(os.linesep.join(self.colored_data[self.lnr:ll]), self.lnr != 0, ll != len(self.data)) + (self.show_errors if self.show_errors else "")

        def external_editor(self, ctxt, transient=1):
            renpy.exports.launch_editor([ctxt[0]], ctxt[1], transient=transient)

    class Editor(renpy.Displayable):
        def __init__(self, *a, **b):
            super(Editor, self).__init__(a, b)
            self.max = 0xffff
            self.fl = {}
            self.fname = None
            self.view = None
            self.exit() # sets tis_visible and cursor coords to default

        def render(self, width, height, st, at):
            R = renpy.Render(width, height)
            C = R.canvas()
            dx = width / 110
            dy = height / 31
            C.line((255,255,255,255),(self.cx*dx,self.cy*dy),(self.cx*dx,(self.cy+0.95)*dy))
            return R

        def debug(self, do_show=False):
            self.view.show_errors = "" if do_show else None
            self.view.parse()

        def event(self, ev, x, y, st):
            import pygame
            if ev.type == pygame.MOUSEBUTTONDOWN:
                self.max = int(x * 113.3 / config.screen_width)
                self.cy = int(y * 31.5 / config.screen_height)

                if self.view.lnr + self.cy >= len(self.view.data):
                    self.cy -= self.view.lnr + self.cy - len(self.view.data) + 1

                self.cx = min(self.max, len(self.view.data[self.view.lnr+self.cy]))
                renpy.redraw(self, 0)

        def start(self, ctxt, offset=2):
            (fname, lnr) = ctxt
            lnr = lnr - 1 if fname else 0 # no fname indicates failure
            self.fname = os.path.join(renpy.config.basedir, fname)

            if fname not in self.fl:
                self.fl[fname] = EditView(console=self, data=ReadWriteData(self.fname), lnr=lnr)
            else:
                self.view.lnr = lnr
                self.view.handlekey("END") # NB. call via handlekey triggers cursor redraw.
            self.view = self.fl[fname]
            self.is_visible = True

        def exit(self, discard=False, apply=False):
            """
            Applied changes are not visible until reload (shift+R).
            """
            self.is_visible = False
            self.cx = self.cy = self.cx2 = self.cy2 = 0 # last two are meant for dragging
            if discard:
                #reload from disk
                self.view.data.load()
                self.view.parse()
            elif apply:
                self.view.save()

    editor = Editor()

init 1701 python in _editor:

    if config.developer or config.editor:
        editor = Editor()

style editor_frame:
        xpadding 10
        ypadding 10
        xpos 0
        background "#272822"

screen editor:
    style_prefix "editor"
    default editor = _editor.editor
    default view = editor.view
    frame:

        add editor
        text editor.view.display() style "editor"

        for keystr in view.keymap:
            key keystr action Function(view.handlekey, keystr)

        key "shift_K_RETURN" action [Function(editor.exit, apply = True), Return()]
        key "shift_K_KP_ENTER" action [Function(editor.exit, apply = True), Return()]

        key "K_ESCAPE" action [Function(editor.exit), Return()]

        key "K_TAB" action Function(view.insert, "    ")
        key "K_SPACE" action Function(view.insert, " ")
        key "repeat_K_SPACE" action Function(view.insert, " ")

        for i in xrange(0, len(view.oSymName)):
            key "K_"+view.oSymName[i] action Function(view.insert, view.oSymLow[i])
            key "shift_K_"+view.oSymName[i] action Function(view.insert, view.oSymUpp[i])
            key "repeat_K_"+view.oSymName[i] action Function(view.insert, view.oSymLow[i])
            key "repeat_shift_K_"+view.oSymName[i] action Function(view.insert, view.oSymUpp[i])

        for nr in xrange(0, 10):
            key "K_"+str(nr) action Function(view.insert, str(nr))
            key "K_KP"+str(nr) action Function(view.insert, str(nr))
            key "repeat_K_"+str(nr) action Function(view.insert, str(nr))
            key "repeat_K_KP"+str(nr) action Function(view.insert, str(nr))
            key "shift_K_"+str(nr) action Function(view.insert, view.nrSymbol[nr])
            key "repeat_shift_K_"+str(nr) action Function(view.insert, view.nrSymbol[nr])

        for c in xrange(ord('a'), ord('z')+1):
            key "K_"+chr(c) action Function(view.insert, chr(c))
            key "shift_K_"+chr(c) action Function(view.insert, chr(c).upper())
            key "repeat_K_"+chr(c) action Function(view.insert, chr(c))
            key "repeat_shift_K_"+chr(c) action Function(view.insert, chr(c).upper())

        key "K_KP_PERIOD" action Function(view.insert, ".")
        key "K_KP_DIVIDE" action Function(view.insert, "/")
        key "K_KP_MULTIPLY" action Function(view.insert, "*")
        key "K_KP_MINUS" action Function(view.insert, "-")
        key "K_KP_PLUS" action Function(view.insert, "+")
        key "K_KP_EQUALS" action Function(view.insert, "=")

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if view.changed:
                if not renpy.parser.parse_errors:
                    textbutton _("Apply") action [Function(editor.exit, apply = True), Return()]
                elif view.show_errors is None:
                    textbutton _("Debug") action Function(editor.debug, True)
                else:
                    textbutton _("Silence") action Function(editor.debug)
                textbutton _("Cancel") action [Function(editor.exit, discard = True), Return()]
            textbutton _("Visual") action [Function(editor.exit), Return()]
