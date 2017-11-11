init -1500 python:

    style.editor = Style(style.default)

    # must be monospace or need/add shadow
    style.editor.font = "Inconsolata-Regular.ttf"

init -1500 python in _editor:
    from store import config, style
    import store
    import os
    import re
    import codecs

    import math

    from pygments import highlight
    from renpy_lexer import RenPyLexer
    from renpyformatter import RenPyFormatter
    from pygments.styles import get_style_by_name

    class History(object):
        def __init__(self): self.reset()
        def reset(self):
            self._undo = []
            self.mode = 0
            self.at = 0
        def append(self, what):
            if self.mode == 0:
                if self.at < len(self._undo):
                    self._undo = self._undo[:self.at]
                self._undo.append(what)
                self.at += 1
            elif self.mode == 1:
                self.at -= 1
                self._undo[self.at] = what
                self.mode = 0
            else:
                self._undo[self.at] = what
                self.at += 1
                self.mode = 0
        def undo(self):
            if self.at > 0 and self.at <= len(self._undo):
                self.mode = 1
                return self._undo[self.at-1]
        def redo(self):
            self.mode = 2
            return self._undo[self.at]

    class ReadOnlyData(object):
        """ container and load interface for the read only data """
        def __init__(self, fname): self.load(fname)
        def __getitem__(self, ndx): return self.data[ndx]
        def __len__(self): return len(self.data)

        def load(self, fname=None):
            if fname is not None:
                self.fname = fname
            self.data = []
            fh = codecs.open(self.fname, encoding='utf-8')
            for line in fh:
                self.data.append(line.rstrip(u"\r\n"))

    class ReadWriteData(ReadOnlyData):
        """ allows edit and save """
        def __init__(self, fname):
            super(ReadWriteData, self).__init__(fname)
            self.history = History()
            self.start_change = 0

        def __setitem__(self, ndx, value):
            if value != self.data[ndx]:
                self.history.append(["__setitem__", ndx, self.data[ndx]])
                self.data[ndx] = value

        def load(self, fname=None):
            super(ReadWriteData, self).load(fname)
            self.history = History()

        def save(self):
            import shutil
            from tempfile import mkstemp
            if len(self.history._undo) > self.start_change: # any changes?
                fh, abs_path = mkstemp()
                for line in self.data:
                    os.write(fh, line + os.linesep)
                os.close(fh)
                shutil.move(abs_path, self.fname)
                self.start_change = len(self.history._undo)

        def __delitem__(self, ndx):
            self.history.append(["insert", ndx, self.data[ndx]])
            del(self.data[ndx])

        def insert(self, ndx, value):
            self.history.append(["__delitem__", ndx])
            self.data.insert(ndx, value)

        def undo(self):
            if self.history.at >= 0:
                act = self.history.undo()
                if act is not None:
                    getattr(self, act[0])(*act[1:])

        def redo(self):
            if self.history.at < len(self.history._undo):
                act = self.history.redo()
                if act is not None:
                    getattr(self, act[0])(*act[1:])

    class RenPyData(ReadWriteData):
        def __init__(self, fname, format_style=None):
            super(RenPyData, self).__init__(fname)
            self.lexer = RenPyLexer(stripnl=False)
            self.formater = RenPyFormatter(style=format_style if format_style else 'monokai')
            self._last_parsed_changes = None

        def parse(self):
            if self.history.at != self._last_parsed_changes:
                document = os.linesep.join(self.data)
                renpy.parser.parse_errors = []
                renpy.parser.parse(self.fname, document)
                escaped = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', document))
                self.colored_buffer = highlight(escaped, self.lexer, self.formater).split(os.linesep)
                self._last_parsed_changes = self.history.at
            return (self.colored_buffer, renpy.parser.parse_errors)

    class TextView(object):
        """keeps track of horizontal position in text. Wrapping is not taken into account"""
        wheel_scroll_lines = 3
        def __init__(self, console, data, nolines=None, lnr=None, wheel_scroll_lines=None):
            self.data = data
            self.lnr = lnr if lnr else 0
            self.lineLenMax = 109
            self.show_errors = ""
            self.keymap = set(['mousedown_4', 'mousedown_5'])
            self.parse()
            # XXX default nolines should be relative to window + font size
            self._nolines = nolines if nolines else int(config.screen_height / (34 + style.default.line_leading + style.default.line_spacing)) - 1
            self._add_km(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['repeat_', ''])
            self._add_km(['HOME', 'END'], ['ctrl_'])
            self.console = console

        def _add_km(self, km, mod): self.keymap.update([m+'K_'+k for k in km for m in mod])

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
            (self.colored_data, err) = self.data.parse()
            if self.show_errors is not None:
                self.show_errors = "\n{color=#f00}{size=-10}" + os.linesep.join(err) +"{/size}{/color}" if err else ""

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

        def ctrl_HOME(self): self.console.cy = self.lnr = 0
        def ctrl_END(self):
            self.console.cy = self.nolines - 1
            self.lnr = len(self.data) - self.console.cy - 1

        def mousedown_4(self): self.UP(self.wheel_scroll_lines)
        def mousedown_5(self): self.DOWN(self.wheel_scroll_lines)

    class EditView(TextView):

        def __init__(self, **kwargs):
            super(EditView, self).__init__(**kwargs)

            #self.styleprefix = "editor"
            self._add_km(['BACKSPACE', 'DELETE', 'RETURN'], ['repeat_', ''])
            self._add_km(['HOME', 'END'], ['shift_', ''])
            self._add_km(['LEFT', 'RIGHT'], ['shift_', 'ctrl_', 'ctrl_shift_', 'repeat_ctrl_shift_','', 'repeat_shift_', 'repeat_ctrl_', 'repeat_'])
            self.fontsize = 34
            self.handlekey("END")
            self.nrSymbol = ")!@#$%^&*("
            self.oSymName = [ "BACKQUOTE", "MINUS", "EQUALS", "LEFTBRACKET", "RIGHTBRACKET",
                               "BACKSLASH", "SEMICOLON", "QUOTE", "COMMA", "PERIOD", "SLASH"]
            self.oSymLow = r"`-=[]\;',./"
            self.oSymUpp = r'~_+{}|:"<>?'
            self.changed = False
            self.copied = ""

        def LEFT(self, sub=1): self.console.max = max(self.console.cx - sub, 0)
        def RIGHT(self, add=1): self.console.max = min(self.console.cx + add, len(self.line))

        def ctrl_LEFT(self):
            y = self.lnr+self.console.cy
            m = re.compile(r'\w*\W*$').search(self.data[y][:self.console.cx])
            if m:
                self.LEFT(len(m.group(0)))

        def ctrl_RIGHT(self):
            y = self.lnr+self.console.cy
            m = re.compile(r'^\w*\W*').match(self.data[y][self.console.cx:])
            if m:
                self.RIGHT(len(m.group(0)))

        def HOME(self): self.console.max = 0
        def END(self): self.console.max = 0xffff

        def RETURN(self):
            y = self.lnr+self.console.cy
            self.data.insert(y+1, self.data[y][self.console.cx:])
            self.data[y] = self.data[y][:self.console.cx]
            self.parse()
            self.changed = True
            self.console.max = 0
            self.DOWN()

        def BACKSPACE(self):
            cons = self.console

            y = self.lnr+cons.cy

            self.changed = True
            if cons.cx or cons.cx != cons.CX:
                self.LEFT()
                cons.cx = min(cons.max, len(self.line))
                self.DELETE()
                if cons.cx != cons.CX:
                    cons.max += cons.CX
            else:
                if self.lnr + cons.cy != 0: #FIXME
                    cons.max = len(self.data[y - 1])
                    self.data[y - 1] += self.data[y]
                    del self.data[y]
                    self.UP()
            self.parse()

        def DELETE(self):
            cons = self.console
            s, e = (cons.cx, cons.CX) if cons.cx < cons.CX else (cons.CX, cons.cx)
            y = self.lnr+cons.cy
            buf = self.data[y]
            self.changed = True
            if s != len(self.line):
                if e == s:
                    e += 1
                self.data[y] = buf[:s] + buf[e:]
                cons.max = cons.CX = s
            elif y < self.nolines - 1:
                cons.max = len(buf)
                self.data[y] += self.data[y+1]
                del self.data[y+1]
            self.parse()

        def copy(self):
            import pyperclip
            cons = self.console
            s, e = (cons.cx, cons.CX) if cons.cx < cons.CX else (cons.CX, cons.cx)
            pyperclip.copy(self.data[self.lnr+self.console.cy][s:e])

        def cut(self):
            self.copy()
            if self.console.CX != self.console.cx:
                self.handlekey("DELETE")

        def insert(self, s=None):
            import pyperclip
            if s == None:
                s = pyperclip.paste()
            if self.console.CX != self.console.cx:
                self.handlekey("DELETE")
            buf = self.data[self.lnr+self.console.cy]
            self.data[self.lnr+self.console.cy] = buf[:self.console.cx] + s + buf[self.console.cx:]
            self.console.max += len(s)
            self.console.CX = self.console.cx = min(self.console.max, len(self.line))
            renpy.redraw(self.console, 0)
            self.changed = True
            self.parse()

        def handlekey(self, keystr):
            getattr(self, re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)(?:shift_)?K_', r'\1', keystr))()
            self.console.cx = min(self.console.max, len(self.line))
            if "shift_" not in keystr:
                self.console.CX, self.console.CY = self.console.cx, self.console.cy
            renpy.redraw(self.console, 0)

        def colorize(self, txt, at_start=False, at_end=False):
            return ('{color=#000000}' if at_start else '') + txt + ('{/color}' if at_end else '')

        def display(self):
            ll = min(self.lnr + self.nolines, len(self.data))
            return self.colorize(os.linesep.join(self.colored_data[self.lnr:ll]), self.lnr != 0, ll != len(self.data)) + (self.show_errors if self.show_errors else "")

        def external_editor(self, ctxt, transient=1):
            renpy.exports.launch_editor([ctxt[0]], ctxt[1], transient=transient)

        def ctrl_z(self):
            self.data.undo()
            self.parse()

        def ctrl_y(self):
            self.data.redo()
            self.parse()

    class Editor(renpy.Displayable):
        def __init__(self, *a, **b):
            super(Editor, self).__init__(a, b)
            self.fl = {}
            self.fname = None
            self.view = None
            self.is_mouse_pressed = False
            self.exit() # sets is_visible and cursor coords to default

        def render(self, width, height, st, at):
            R = renpy.Render(width, height)
            C = R.canvas()
            dx = width / 110
            dy = height / 31
            color = (255,255,255,255)
            if self.CX == self.cx:
                C.line(color,(self.cx*dx,self.cy*dy),(self.cx*dx, (self.cy+0.95)*dy))
            elif self.cy == self.CY:
                C.rect(color,(self.cx*dx, self.cy*dy, (self.CX-self.cx)*dx, 0.95*dy))
            elif self.cy != self.CY:
                renpy.error("Multi line selection not yet implemented")
            return R

        def debug(self, do_show=False):
            self.view.show_errors = "" if do_show else None
            self.view.parse()

        def _getcycx(self, x, y):
            self.max = int(x * 113.3 / config.screen_width)
            cy = int(y * 31.5 / config.screen_height)

            if self.view.lnr + cy >= len(self.view.data):
                cy -= self.view.lnr + cy - len(self.view.data) + 1

            return (min(self.max, len(self.view.data[self.view.lnr+cy])), cy)

        def event(self, ev, x, y, st):
            import pygame
            if ev.type == pygame.MOUSEBUTTONDOWN:
                self.cx, self.cy = self._getcycx(x, y)
                self.CX, self.CY = self.cx, self.cy
                renpy.redraw(self, 0)
                self.is_mouse_pressed = True
            if self.is_mouse_pressed and ev.type == pygame.MOUSEMOTION or ev.type == pygame.MOUSEBUTTONUP:
                self.CX, self.CY = self._getcycx(x, y)
                self.CY = self.cy # TODO: allow multiple lines (and remove)
                renpy.redraw(self, 0)
                if ev.type == pygame.MOUSEBUTTONUP:
                    self.is_mouse_pressed = False

        def start(self, ctxt, offset=2):
            (fname, lnr) = ctxt
            if fname: # no fname indicates failure
                lnr = lnr - 1
                self.fname = os.path.join(renpy.config.basedir, fname)

                if fname not in self.fl:
                    self.fl[fname] = EditView(console=self, data=RenPyData(self.fname), lnr=lnr)
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
            self.max = self.cx = self.cy = self.CX = self.CY = 0 # last two are meant for dragging
            if discard:
                #reload from disk
                self.view.data.load()
                self.view.parse()
            elif apply:
                self.view.data.save()

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

        for keystr in sorted(view.keymap, key=len):
            key keystr action Function(view.handlekey, keystr)

        key "shift_K_RETURN" action [Function(editor.exit, apply = True), Return()]
        key "shift_K_KP_ENTER" action [Function(editor.exit, apply = True), Return()]

        for keystr in 'zy':
            key 'ctrl_K_'+keystr action Function(view.handlekey, 'ctrl_K_'+keystr)
            key 'repeat_ctrl_K_'+keystr action Function(view.handlekey, 'repeat_ctrl_K_'+keystr)

        key "K_ESCAPE" action [Function(editor.exit), Return()]

        key "ctrl_K_c" action Function(editor.view.copy)
        key "ctrl_K_x" action Function(editor.view.cut)
        key "ctrl_K_v" action Function(editor.view.insert)

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
