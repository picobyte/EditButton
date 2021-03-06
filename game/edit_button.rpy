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
    import textwrap
    import time

    import math

    from pygments import highlight
    from renpy_lexer import RenPyLexer
    from renpyformatter import RenPyFormatter

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
            else:
                self._undo[self.at] = what
                self.at += 1
            self.mode = 0
        def undo(self):
            if self.at > 0 and self.at <= len(self._undo):
                self.mode = 1
                return self._undo[self.at-1]
        def redo(self):
            if self.at < len(self._undo):
                self.mode = 2
                return self._undo[self.at]

    class ReadOnlyData(object):
        """ container and load interface for read only data """
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
        """ also allows edit and save """
        def __init__(self, fname):
            super(ReadWriteData, self).__init__(fname)
            self.history = History()
            self.start_change = 0

        @property
        def changed(self):
            return len(self.history._undo) > self.start_change

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
            if self.changed:
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

    class RenPyData(ReadWriteData):
        def __init__(self, fname, format_style=None):
            super(RenPyData, self).__init__(fname)
            self.lexer = RenPyLexer(stripnl=False)
            self.formater = RenPyFormatter(style=format_style if format_style else 'monokai')
            self._last_parsed_changes = None

        def parse(self):
            """ If changes were not yet parsed, check for errors; create colored_buffer for view on screen """
            if self.history.at != self._last_parsed_changes:
                document = os.linesep.join(self.data)
                renpy.parser.parse_errors = []
                renpy.parser.parse(self.fname, document)
                escaped = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', document))

                # NOTE: must split on newline here, not os.linesep, or it won't work in windows
                self.colored_buffer = highlight(escaped, self.lexer, self.formater).split('\n')
                self._last_parsed_changes = self.history.at

    class TextView(object):
        """keeps track of horizontal position in text. Wrapping is not taken into account"""
        wheel_scroll_lines = 3
        def __init__(self, console, data, nolines=None, lnr=None, wheel_scroll_lines=None):
            self.data = data
            self.lnr = lnr if lnr else 0
            self.lineLenMax = 111
            self.show_errors = ""
            self.keymap = set(['mousedown_4', 'mousedown_5'])
            # XXX default nolines should be relative to window + font size
            self._maxlines = nolines if nolines else int(config.screen_height / (34 + style.default.line_leading + style.default.line_spacing)) - 1
            self.parse()
            self._add_km(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['repeat_', ''])
            self._add_km(['HOME', 'END'], ['ctrl_'])
            self.console = console

        def _add_km(self, km, mod): self.keymap.update([m+'K_'+k for k in km for m in mod])

        @property
        def line(self): return self.wrapped_buffer[self.console.cy]
        @property
        def nolines(self):
            return len(self.wrapped_buffer)

        def rewrap(self):
            """ a copy of the buffer in view that is wrapped as shown in view """
            self.wrapped_buffer = []
            self.wrap2buf = {}
            atline = 0
            tot = 0
            for line in self.data[self.lnr:min(self.lnr + self._maxlines, len(self.data))]:
                wrap = renpy.text.extras.textwrap(line, self.lineLenMax) or ['']
                offs = 0
                for l in wrap:
                    offs += line.index(l, offs) - offs
                    self.wrap2buf[tot]=(offs, atline)
                    tot += 1
                    if tot > self._maxlines:
                        return
                    offs += len(l)
                atline += 1
                self.wrapped_buffer.extend(wrap)

        def parse(self):
            self.data.parse()
            self.rewrap()
            if self.show_errors is not None:
                err = renpy.parser.parse_errors
                self.show_errors = ""
                if err:
                    escaped = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', os.linesep.join(err)))
                    self.show_errors = os.linesep+"{color=#f00}{size=-10}" + escaped +"{/size}{/color}"

        def UP(self, sub=1):
            sub = min(self.console.cy + self.lnr, sub)
            cursor_movement = min(self.console.cy, sub)
            self.console.cy -= cursor_movement
            self.lnr -= sub - cursor_movement
            if cursor_movement == 0: # then view was moved
                self.rewrap()

        def DOWN(self, add=1):
            cursor_movement = min(self.nolines - self.console.cy - 1, add)
            add -= cursor_movement
            if cursor_movement:
                self.console.cy += cursor_movement
            elif self.console.cy > add: # view movement
                self.lnr += add
                self.rewrap()
                while self.console.cy >= self.nolines:
                    self.console.cy -= 1
                    self.parse()
            else:
                 self.console.CY = self.console.cy

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
            self._add_km(['UP', 'DOWN'], ['shift_', 'repeat_shift_'])
            self.fontsize = 34
            self.handlekey("END")
            # FIXME: this is QWERTY keyboard specific.
            self.nrSymbol = ")!@#$%^&*("
            self.oSymName = [ "BACKQUOTE", "MINUS", "EQUALS", "LEFTBRACKET", "RIGHTBRACKET",
                               "BACKSLASH", "SEMICOLON", "QUOTE", "COMMA", "PERIOD", "SLASH"]
            self.oSymLow = r"`-=[]\;',./"
            self.oSymUpp = r'~_+{}|:"<>?'
            self.copied = ""

        def LEFT(self, sub=1):
            while self.console.cx < sub and self.wrap2buf[self.console.cy][0]:
                sub -= self.console.cx + 1
                self.UP()
                self.console.cx = len(self.line)
            self.console.max = max(self.console.cx - sub, 0)
        def RIGHT(self, add=1):
            bx, by = self.wrap2buf[self.console.cy]
            while self.console.cx + add > len(self.line) and bx+self.console.cx < len(self.data[self.lnr+by]):
                add -= len(self.line) - self.console.cx + 1
                self.DOWN()
                self.console.cx = 0
            self.console.max = min(self.console.cx + add, len(self.line))

        def ctrl_LEFT(self):
            bx, by = self.wrap2buf[self.console.cy]
            m = re.compile(r'\w*\W*$').search(self.data[self.lnr+by][:bx+self.console.cx])
            if m:
                self.LEFT(len(m.group(0)))

        def ctrl_RIGHT(self):
            bx, by = self.wrap2buf[self.console.cy]
            m = re.compile(r'^\w*\W*').match(self.data[self.lnr+by][bx+self.console.cx:])
            if m:
                self.RIGHT(len(m.group(0)))

        def HOME(self): self.console.max = 0
        def END(self): self.console.max = 0xffff

        def RETURN(self): self.insert(['',''])

        def BACKSPACE(self):
            cons = self.console
            if cons.cx == cons.CX and cons.cy == cons.CY:
                if cons.cx or self.wrap2buf[cons.cy][0]:
                    self.LEFT()
                elif self.lnr + cons.cy != 0:
                    self.UP()
                    cons.max = len(self.line)
                else:
                    return
                cons.cx = cons.max
            self.DELETE()

        def _ordered_cursor_coordinates(self):
            cx, cy = self.console.cx, self.console.cy
            CX, CY = self.console.CX, self.console.CY

            none_selected = 0

            if cy > CY:
                cy, CY = CY, cy
                cx, CX = CX, cx

            elif cy == CY:
                if cx > CX:
                    cx, CX = CX, cx
                elif cx == CX:
                    none_selected = 1
            return (cx, cy, CX, CY, none_selected)

        def _cursor2buf_coords(self, cx, cy, CX, CY):
            sx, sy = self.wrap2buf[cy]
            ex, ey = self.wrap2buf[CY]
            return (sx+cx, sy+self.lnr, ex+CX, ey+self.lnr)

        def DELETE(self):
            cx, cy, CX, CY, none_selected = self._ordered_cursor_coordinates()
            sx, sy, ex, ey = self._cursor2buf_coords(cx, cy, CX, CY)

            if sx != len(self.data[sy]) or not none_selected:
                ex += none_selected # then delete the one right of the cursor
                start = self.data[sy][:sx]
                while sy != ey:
                    del self.data[sy]
                    ey -= 1
                self.data[sy] = start + self.data[sy][ex:]
            elif sy < len(self.data) - 1:
                self.console.max = len(self.data[sy])
                self.data[sy] += self.data[sy+1]
                del self.data[sy+1]
            self.parse()
            self.console.cy = self.console.CY = cy
            if cx > len(self.line):
                # fix cursor placement if space was deleted causing a word at the end of the line to wrap to the next line
                cx -= len(self.line) + 1
                self.DOWN()
            elif sx < self.wrap2buf[cy][0]:
                # fix cursor placement when word at start of line was shortened and now wraps
                dx = self.wrap2buf[cy][0] - sx
                self.UP()
                cx = len(self.line) + 1 - dx
            self.console.max = self.console.cx = self.console.CX = cx

        def copy(self):
            import pyperclip # to use external copy buffer
            cx, cy, CX, CY, none_selected = self._ordered_cursor_coordinates()
            sx, sy, ex, ey = self._cursor2buf_coords(cx, cy, CX, CY)
            if not none_selected:
                copy = ""
                for y in xrange(sy, ey):
                    copy += self.data[y][sx:len(self.data[y])] + os.linesep
                    sx = 0
                pyperclip.copy(copy+self.data[ey][sx:ex])

        def cut(self):
            if self.console.CX != self.console.cx or self.console.CY != self.console.cy:
                self.copy()
                self.handlekey("DELETE")

        def insert(self, entries=None):
            import pyperclip

            if entries == None: # paste in absences of entries
                entries = pyperclip.paste().split(os.linesep)

            cx, cy, CX, CY, none_selected = self._ordered_cursor_coordinates()

            if cx != CX or cy != CY:
                self.DELETE()

            cx, cy = self.console.cx, self.console.cy

            offs, atline = self.wrap2buf[cy]
            cx += offs
            by = atline + self.lnr

            end = self.data[by][cx:]
            self.data[by] = self.data[by][:cx] + entries[0]
            for l in entries[1:]:
                by += 1
                self.data.insert(by, l)
            self.data[by] += end
            self.parse()

            # move cursor
            if len(entries) <= 1 and cx + len(entries[0]) - self.wrap2buf[self.console.cy][0] < len(self.line): 
                self.console.cx = cx + len(entries[0])
            else:
                self.UP()
                for e in entries:
                    self.DOWN()
                    self.console.cx = cx + len(e)
                    while self.console.cx - self.wrap2buf[self.console.cy][0] > len(self.line):
                        self.DOWN()
                        if not self.wrap2buf[self.console.cy][0]:
                            break
                    cx = 0
                self.console.CY = self.console.cy

            self.console.cx -= self.wrap2buf[self.console.cy][0]
            self.console.max = self.console.CX = self.console.cx
            renpy.redraw(self.console, 0)

        def handlekey(self, keystr):
            """ repeat keys are handled as normal keys; unless shift is provided selection is discarded and cursor is redrawn """
            getattr(self, re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)(?:shift_)?K_', r'\1', keystr))()
            self.console.cx = min(self.console.max, len(self.line))
            if "shift_" not in keystr:
                self.console.CX, self.console.CY = self.console.cx, self.console.cy
            renpy.redraw(self.console, 0)

        def colorize(self, txt, at_start=False, at_end=False):
            return ('{color=#000000}' if at_start else '') + txt + ('{/color}' if at_end else '')

        def display(self):
            ll = min(self.lnr + self.nolines, len(self.data))
            return self.colorize(os.linesep.join(self.data.colored_buffer[self.lnr:ll]), self.lnr != 0, ll != len(self.data)) + (self.show_errors if self.show_errors else "")

        def _act_out(self, func, ndx, *args):
            """ handle undo/redo. Also makes sure the action remains in view """
            getattr(self.data, func)(ndx, *args)
            self.parse()
            self.console.cy = self.console.CY = ndx - self.lnr
            if self.console.cy < 0:
                self.UP(-self.console.cy)
            elif self.console.cy >= self.nolines:
                self.DOWN(self.console.cy-self.nolines-1)
            self.console.cx = self.console.CX = 0
            self.rewrap()

        def ctrl_z(self):
            act = self.data.history.undo()
            if act:
                self._act_out(*act)

        def ctrl_y(self):
            act = self.data.history.redo()
            if act:
                self._act_out(*act)

    class Editor(renpy.Displayable):
        def __init__(self, *a, **b):
            super(Editor, self).__init__(a, b)
            self.fl = {}
            self.fname = None
            self.view = None
            self.timer = time.time()
            self.is_mouse_pressed = False
            self.exit() # sets is_visible and cursor coords to default

        def render(self, width, height, st, at):
            """ draw the cursor or the selection """
            R = renpy.Render(width, height)
            C = R.canvas()
            dx = width / 110
            dy = height / 31
            selection = (16,16,16,255)
            if self.cy == self.CY:
                if self.CX == self.cx:
                    C.line((255,255,255,255),(self.cx*dx,self.cy*dy),(self.cx*dx, (self.cy+0.95)*dy))
                else:
                    C.rect(selection,(self.cx*dx, self.cy*dy, (self.CX-self.cx)*dx, 0.95*dy))
            elif self.cy < self.CY:
                x = self.cx
                for y in xrange(self.cy, self.CY):
                    C.rect(selection, (x*dx, y*dy, (len(self.view.wrapped_buffer[y])-x)*dx, 0.95*dy))
                    x = 0
                C.rect(selection, (0, self.CY*dy, self.CX*dx, 0.95*dy))
            else:
                x = self.CX
                for y in xrange(self.CY, self.cy):
                    C.rect(selection, (x*dx, y*dy, (len(self.view.wrapped_buffer[y])-x)*dx, 0.95*dy))
                    x = 0
                C.rect(selection, (0, self.cy*dy, self.cx*dx, 0.95*dy))
            return R

        def show_debug_messages(self, do_show):
            self.view.show_errors = "" if do_show else None
            self.view.parse()

        def _screen_to_cursor_coordinates(self, x, y):
            self.max = int(x * 113.3 / config.screen_width)
            cy = int(y * 31.5 / config.screen_height)

            # selection below displayes screen caused this. FIXME: maybe scroll down if this happens?
            if cy >= self.view.nolines:
                cy = self.view.nolines - 1
            return (min(self.max, len(self.view.wrapped_buffer[cy])), cy)

        def event(self, ev, x, y, st):
            import pygame
            if ev.type == pygame.MOUSEBUTTONDOWN:
                self.cx, self.cy = self._screen_to_cursor_coordinates(x, y)
                if time.time() - self.timer < 0.5:
                    bx, by = self.view.wrap2buf[self.cy]
                    m = re.compile(r'\w*$').search(self.view.data[self.view.lnr+by][:bx+self.cx])
                    if m:
                        self.cx -= len(m.group(0))
                    m = re.compile(r'^\w*').match(self.view.data[self.view.lnr+by][bx+self.cx:])
                    if m:
                        self.max = self.CX = min(self.cx+len(m.group(0)), len(self.view.line))
                else:
                    self.timer = time.time()
                    self.CX, self.CY = self.cx, self.cy
                renpy.redraw(self, 0)
                self.is_mouse_pressed = True
            if self.is_mouse_pressed and (ev.type == pygame.MOUSEMOTION or ev.type == pygame.MOUSEBUTTONUP):
                if ev.type == pygame.MOUSEMOTION:
                    self.CX, self.CY = self._screen_to_cursor_coordinates(x, y)
                renpy.redraw(self, 0)
                if ev.type == pygame.MOUSEBUTTONUP:
                    self.CX, self.CY, self.cx, self.cy = self.cx, self.cy, self.CX, self.CY
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
            """ unless discarded, changes are kept in store. Applied changes are not visible until reload (shift+R). """
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
        text view.display() style "editor"

        for keystr in sorted(view.keymap, key=len):
            key keystr action Function(view.handlekey, keystr)

        key "shift_K_RETURN" action [Function(editor.exit, apply = True), Return()]
        key "shift_K_KP_ENTER" action [Function(editor.exit, apply = True), Return()]

        for keystr in 'zy':
            key 'ctrl_K_'+keystr action Function(view.handlekey, 'ctrl_K_'+keystr)
            key 'repeat_ctrl_K_'+keystr action Function(view.handlekey, 'repeat_ctrl_K_'+keystr)

        key "K_ESCAPE" action [Function(editor.exit), Return()]

        key "ctrl_K_c" action Function(view.copy)
        key "ctrl_K_x" action Function(view.cut)
        key "ctrl_K_v" action Function(view.insert)

        key "K_TAB" action Function(view.insert, ["    "])
        key "K_SPACE" action Function(view.insert, [" "])
        key "repeat_K_SPACE" action Function(view.insert, [" "])

        for i in xrange(0, len(view.oSymName)):
            key "K_"+view.oSymName[i] action Function(view.insert, [view.oSymLow[i]])
            key "shift_K_"+view.oSymName[i] action Function(view.insert, [view.oSymUpp[i]])
            key "repeat_K_"+view.oSymName[i] action Function(view.insert, [view.oSymLow[i]])
            key "repeat_shift_K_"+view.oSymName[i] action Function(view.insert, [view.oSymUpp[i]])

        for nr in xrange(0, 10):
            key "K_"+str(nr) action Function(view.insert, [str(nr)])
            key "K_KP"+str(nr) action Function(view.insert, [str(nr)])
            key "repeat_K_"+str(nr) action Function(view.insert, [str(nr)])
            key "repeat_K_KP"+str(nr) action Function(view.insert, [str(nr)])
            key "shift_K_"+str(nr) action Function(view.insert, [view.nrSymbol[nr]])
            key "repeat_shift_K_"+str(nr) action Function(view.insert, [view.nrSymbol[nr]])

        for c in xrange(ord('a'), ord('z')+1):
            key "K_"+chr(c) action Function(view.insert, [chr(c)])
            key "shift_K_"+chr(c) action Function(view.insert, [chr(c).upper()])
            key "repeat_K_"+chr(c) action Function(view.insert, [chr(c)])
            key "repeat_shift_K_"+chr(c) action Function(view.insert, [chr(c).upper()])

        key "K_KP_PERIOD" action Function(view.insert, ["."])
        key "K_KP_DIVIDE" action Function(view.insert, ["/"])
        key "K_KP_MULTIPLY" action Function(view.insert, ["*"])
        key "K_KP_MINUS" action Function(view.insert, ["-"])
        key "K_KP_PLUS" action Function(view.insert, ["+"])
        key "K_KP_EQUALS" action Function(view.insert, ["="])

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if view.data.changed:
                if not renpy.parser.parse_errors:
                    textbutton _("Apply") action [Function(editor.exit, apply = True), Return()]
                elif view.show_errors is None:
                    textbutton _("Debug") action Function(editor.show_debug_messages, True)
                else:
                    textbutton _("Silence") action Function(editor.show_debug_messages, False)
                textbutton _("Cancel") action [Function(editor.exit, discard = True), Return()]
            textbutton _("Visual") action [Function(editor.exit), Return()]
