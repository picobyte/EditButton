init -1700 python  in _editor:

    font = "codeface/fonts/inconsolata/Inconsolata-Regular.ttf"
    #font = "codeface/fonts/proggy-clean/ProggyClean.ttf"
    fontsize = 34.0
    # trying to relate this to ratios from game/codeface/fonts/*/vertical_metrics.txt:
    if "/Inconsolata-Regular.ttf" in font:
        # 1.049, both (bottom of vertical_metrics file):
        Typo_Asc_Desc_Linegap_per_UPM = 1.135
        winAsc_winDesc_per_UPM = 1.0485
    elif "/ProggyClean.ttf" in font:
        # first should be 1.0, other 0.8125:
        Typo_Asc_Desc_Linegap_per_UPM = 1.0
        winAsc_winDesc_per_UPM = 0.820


    maxCharPerLine = 127.875 / Typo_Asc_Desc_Linegap_per_UPM
    maxLinesPerScreen = 30.5 / winAsc_winDesc_per_UPM

init:
    style _editor:
        # must be monospace or need/add shadow
        font _editor.font
        size _editor.fontsize #gui.text_size

    style _editor_frame:
        padding (0, 0)
        pos (0, 0)
        background "#272822"

    style _editor_window:
        align (0.5, 1.0)
        background Frame("gui/namebox.png", gui.namebox_borders, tile=gui.namebox_tile, xalign=gui.name_xalign)

    style _editor_error is _editor:
        size int(_editor.fontsize * 0.80)
        color "#d00"
        hover_color "#f11"
        hover_underline True

    style _editor_search is _editor:
        align (0.5, 0.5)
        background Frame("gui/namebox.png", gui.namebox_borders, tile=gui.namebox_tile, xalign=gui.name_xalign)
        padding gui.namebox_borders.padding

    style _editor_suggestion_frame:
        padding (0, 0)
        background "#111a"

    style _editor_textbutton is _editor:
        color "#fff"
        hover_color "ff2"

screen _editor_find:
    default editor = _editor.editor
    default view = editor.view
    frame:
        align (0.5, 0.5)
        background AlphaMask(Image("gui/frame.png", gui.confirm_frame_borders), mask="#000a")
        vbox:
            align (0.4, 0.5)
            text "Enter search string:\n":
                size 20
                color "#fff"

            add Input(hover_color="#3399ff",size=28, color="#afa", default=view.search_string, changed=view.search_init, length=256)
            hbox:
                textbutton "OK":
                    text_style "_editor_textbutton"
                    action Function(view.search)
                    keysym('K_RETURN', 'K_KP_ENTER')
                textbutton "Cancel":
                    text_style "_editor_textbutton"
                    action Hide("_editor_find")
                    keysym('K_ESCAPE')

screen _editor_suggestions(coords, suggestion_area, alts):
    style_prefix "_editor_suggestion"
    frame:
        area suggestion_area
        vbox:
            for alt in alts:
                textbutton alt:
                    padding (0, 0)
                    minimum (0, 0)
                    text_style "_editor_textbutton"
                    action Function(_editor.editor.view.replace, alt, coords)

        key "K_ESCAPE" action Hide("_editor_suggestions")

init -1500 python in _editor:
    from store import config, style
    import store
    import os
    import re
    import codecs
    import textwrap
    import time

    from pygments import highlight
    from renpy_lexer import RenPyLexer
    from renpyformatter import RenPyFormatter
    from spellchecker import SpellChecker
    lang = SpellChecker(language='en') # should also support ru, es, fr, pt and de
    spellcheck_modus = "Suggest"

    class History(object):
        def __init__(self):
            self._undo = []
            self.mode = 0
            self.at = 0

        def append(self, what):
            if self.mode == 0:
                if self.at < len(self._undo):
                    self._undo = self._undo[:self.at]
                self._undo.append([what])
                self.at += 1
            else:
                self._undo[self.at].append(what)

        def undo(self, act_out):
            if self.at > 0 and self.at <= len(self._undo):
                self.mode = 1
                self.at -= 1
                actions = reversed(self._undo[self.at])
                self._undo[self.at] = []
                for act in actions:
                    act_out(*act)
                self.mode = 0

        def redo(self, act_out):
            if self.at < len(self._undo):
                self.mode = 1
                actions = reversed(self._undo[self.at])
                self._undo[self.at] = []
                for act in actions:
                    act_out(*act)
                self.at += 1
                self.mode = 0

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
            global spellcheck_modus
            if self.history.at != self._last_parsed_changes:
                unknown_words = Set()
                if spellcheck_modus != "No check":
                    for l in self.data:
                        for w in lang.split_words(l):
                            if w not in lang:
                               unknown_words.add(w)
                document = os.linesep.join(self.data)
                renpy.parser.parse_errors = []
                renpy.parser.parse(self.fname, document)
                escaped = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', document))

                # NOTE: must split on newline here, not os.linesep, or it won't work in windows
                self.colored_buffer = highlight(escaped, self.lexer, self.formater).split('\n')
                for w in unknown_words:
                    for i in xrange(0, len(self.colored_buffer)):
                        self.colored_buffer[i] = re.sub(r'\b'+w+r'\b', r'{a=_spell:'+w+r'}'+w+r'{/a}', self.colored_buffer[i])
                self._last_parsed_changes = self.history.at

    class TextView(object):
        """keeps track of horizontal position in text. Wrapping is not taken into account for position."""
        wheel_scroll_lines = 3
        def __init__(self, console, data, nolines=None, lnr=0, wheel_scroll_lines=None):
            global fontsize
            global maxCharPerLine, maxLinesPerScreen
            global Typo_Asc_Desc_Linegap_per_UPM, winAsc_winDesc_per_UPM
            self.data = data
            self.lnr = lnr
            self.show_errors = ""
            self.keymap = set(['mousedown_4', 'mousedown_5'])
            self._maxlines = int(maxLinesPerScreen)
            self.parse()
            self._add_km(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['repeat_', ''])
            self._add_km(['HOME', 'END'], ['ctrl_'])
            self.console = console
            self.cbuflines = self._maxlines

        def _add_km(self, km, mod): self.keymap.update([m+'K_'+k for k in km for m in mod])

        @property
        def line(self): return self.wrapped_buffer[self.console.cy]
        @property
        def nolines(self):
            return len(self.wrapped_buffer)

        def rewrap(self):
            """ a copy of the buffer in view that is wrapped as shown in view """
            global maxCharPerLine
            self.wrapped_buffer = []
            self.wrap2buf = {}
            atline = 0
            tot = 0
            for line in self.data[self.lnr:min(self.lnr + self._maxlines, len(self.data))]:
                wrap = renpy.text.extras.textwrap(line, maxCharPerLine) or ['']

                offs = 0
                for l in wrap:
                    offs += line.index(l, offs) - offs
                    self.wrap2buf[tot]=(offs, atline)
                    tot += 1
                    if tot > self._maxlines:
                        return
                    offs += len(l)
                    self.wrapped_buffer.append(l)
                atline += 1
                self.cbuflines = atline
                if offs != len(line):
                    renpy.error(os.linesep.join(["rewrap() discrepancy", line, str(offs), str(len(line)), str(wrap)]))

        def parse(self):
            self.data.parse()
            self.rewrap()
            if self.show_errors is not None:
                err = renpy.parser.parse_errors
                self.show_errors = ""
                if err:
                    self.show_errors = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', os.linesep.join(err)))

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
            elif self.lnr + add < len(self.data): # view movement
                self.lnr += add
                self.rewrap()
                while self.console.cy >= self.nolines:
                    self.console.cy -= 1
                    self.parse()
            else:
                 self.console.CY = self.console.cy

        def PAGEUP(self):
            self.UP(self.nolines)

        def PAGEDOWN(self):
            self.DOWN(self.nolines)

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

            self._add_km(['BACKSPACE', 'DELETE', 'RETURN'], ['repeat_', ''])
            self._add_km(['HOME', 'END'], ['shift_', ''])
            self._add_km(['LEFT', 'RIGHT'], ['shift_', 'ctrl_', 'ctrl_shift_', 'repeat_ctrl_shift_','', 'repeat_shift_', 'repeat_ctrl_', 'repeat_'])
            self._add_km(['UP', 'DOWN'], ['shift_', 'repeat_shift_'])
            self.handlekey("END")
            # FIXME: this is QWERTY keyboard specific.
            self.nrSymbol = ")!@#$%^&*("
            self.oSymName = [ "BACKQUOTE", "MINUS", "EQUALS", "LEFTBRACKET", "RIGHTBRACKET",
                               "BACKSLASH", "SEMICOLON", "QUOTE", "COMMA", "PERIOD", "SLASH"]
            self.oSymLow = r"`-=[]\;',./"
            self.oSymUpp = r'~_+{}|:"<>?'
            self.copied = ""
            self.show_search = False
            self.search_string = ""
            self.find_upstream = None
            self.find_downstream = None

        def get_selected(self):
            cx, cy, CX, CY, none_selected = self.console.ordered_cursor_coordinates()
            if none_selected:
                return ""
            sx, sy, ex, ey = self.cursor2buf_coords(cx, cy, CX, CY)
            copy = ""
            for y in xrange(sy, ey):
                copy += self.data[y][sx:len(self.data[y])] + os.linesep
                sx = 0
            return copy+self.data[ey][sx:ex]

        def LEFT(self, sub=1):
            while self.console.cx < sub and self.wrap2buf[self.console.cy][0]:
                sub -= self.console.cx + 1
                self.UP()
                self.console.cx = len(self.line)
            self.console.max = max(self.console.cx - sub, 0)
        def RIGHT(self, add=1):
            bx, by = self.wrap2buf[self.console.cy]
            while self.console.cx + add > len(self.line) and bx+self.console.cx <= len(self.data[self.lnr+by]):
                add -= len(self.line) - self.console.cx + 1
                self.DOWN()
                self.console.cx = 0
            self.console.cx = min(self.console.cx + add, len(self.line))
            self.console.max = self.console.cx

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

        def cursor2buf_coords(self, cx, cy, CX, CY, _none_selected=None):
            sx, sy = self.wrap2buf[cy]
            ex, ey = self.wrap2buf[CY]
            return (sx+cx, sy+self.lnr, ex+CX, ey+self.lnr)

        def DELETE(self):
            cx, cy, CX, CY, none_selected = self.console.ordered_cursor_coordinates()
            sx, sy, ex, ey = self.cursor2buf_coords(cx, cy, CX, CY)

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
            selection = self.get_selected()
            if selection is not "":
                import pyperclip # to use external copy buffer
                pyperclip.copy(selection)

        def cut(self):
            if self.console.CX != self.console.cx or self.console.CY != self.console.cy:
                self.copy()
                self.handlekey("DELETE")

        def insert(self, entries=None):
            import pyperclip

            if entries == None: # paste in absences of entries
                entries = pyperclip.paste().split(os.linesep)

            cx, cy, CX, CY, none_selected = self.console.ordered_cursor_coordinates()

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

            # distinction required to prevent cursor jump when pasting/inserting on first line.
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

        def colorize(self, txt, at_start, at_end):
            return ('{color=#000000}' if at_start else '') + txt + ('{/color}' if at_end else '')

        def display(self):
            ll = min(self.lnr + self.cbuflines, len(self.data))
            return self.colorize(os.linesep.join(self.data.colored_buffer[self.lnr:ll]), self.lnr != 0, ll != len(self.data))

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
            self.data.history.undo(self._act_out)

        def ctrl_y(self):
            self.data.history.redo(self._act_out)

        def search_init(self, search):
            self.search_string = search
            renpy.show_screen("_editor_find")

        def search(self):
            if self.search_string is not "":
                sx, sy, ex, ey = self.cursor2buf_coords(*self.console.ordered_cursor_coordinates())
                self.find_downstream = re.finditer(self.search_string, "\n".join(self.data[:sy-1]) + "\n" + self.data[sy][:(sx + len(self.search_string) - 1)])
                self.find_upstream = re.finditer(self.search_string, self.data[sy][sx:] + "\n" + "\n".join(self.data[sy+1:]))
                self.search_next()

        def search_next(self):
            chars = None
            had_selection = (abs(self.console.cx - self.console.CX) + 1) * (abs(self.console.cy - self.console.CY) + 1)
            try:
                while True:
                    m = next(self.find_upstream)
                    if m.start() != 0: # do not return exact same match
                        break
                chars = m.start()
            except StopIteration:
                try:
                    while True:
                        m = next(self.find_downstream)
                        if m.start() != 0:
                            break
                    chars = m.start()
                except StopIteration:
                    renpy.notify("Not found")
                    pass
                if chars is not None:
                    self.console.CY = self.console.CX = self.lnr = 0
                    self.PAGEUP()
                    self.HOME()
                    self.rewrap()
            if chars is None:
                renpy.notify("Not found")
            else:
                self.console.cx = self.console.CX
                self.console.cy = self.console.CY
                self.RIGHT(chars)
                self.console.CX, self.console.CY = self.console.cx, self.console.cy
                self.RIGHT(m.end()-m.start())
                renpy.redraw(self.console, 0)

        def replace(self, alt, coords):
            if renpy.get_screen("_editor_suggestions"):
                renpy.hide_screen("_editor_suggestions")
            self.console.cx = coords[0]
            self.console.cy = coords[1]
            self.console.CX = coords[2]
            self.console.CY = coords[3]
            self.insert([alt])

        def get_suggestions(self):
            global maxCharPerLine, maxLinesPerScreen
            global Typo_Asc_Desc_Linegap_per_UPM, winAsc_winDesc_per_UPM

            char_width = config.screen_width / maxCharPerLine
            char_height = config.screen_height / maxLinesPerScreen

            x = int(self.console.cx * char_width)
            y = int((1.0 + self.console.cy) * char_height)

            suggestions = lang.candidates(self.get_selected())
            wordlen_max = max(map(lambda x: len(x), suggestions))
            width = int(wordlen_max * char_width)
            height = int(len(suggestions) * char_height)

            return (self.console.ordered_cursor_coordinates(), (x, y, width, height), suggestions)

    class Editor(renpy.Displayable):
        def __init__(self, *a, **b):
            super(Editor, self).__init__(a, b)
            self.fl = {}
            self.fname = None
            self.view = None
            self.timer = time.time()
            self.is_mouse_pressed = False
            self.exit() # sets is_visible and cursor coords to default

        def ordered_cursor_coordinates(self):
            cx, cy = self.cx, self.cy
            CX, CY = self.CX, self.CY

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

        def render(self, width, height, st, at):
            """ draw the cursor or the selection """
            global maxCharPerLine, maxLinesPerScreen
            global Typo_Asc_Desc_Linegap_per_UPM, winAsc_winDesc_per_UPM
            R = renpy.Render(width, height)
            C = R.canvas()
            dx = width / maxCharPerLine
            dy = height / maxLinesPerScreen
            selection = (16,16,16,255)
            if self.cy == self.CY:
                if self.CX == self.cx:
                    C.line((255,255,255,255),(self.cx*dx,self.cy*dy),(self.cx*dx, (self.cy+1.0)*dy))
                else:
                    C.rect(selection,(self.cx*dx, self.cy*dy, (self.CX-self.cx)*dx, dy))
            elif self.cy < self.CY:
                x = self.cx
                for y in xrange(self.cy, self.CY):
                    C.rect(selection, (x*dx, y*dy, (len(self.view.wrapped_buffer[y])-x)*dx, dy))
                    x = 0
                C.rect(selection, (0, self.CY*dy, self.CX*dx, dy))
            else:
                x = self.CX
                for y in xrange(self.CY, self.cy):
                    C.rect(selection, (x*dx, y*dy, (len(self.view.wrapped_buffer[y])-x)*dx, dy))
                    x = 0
                C.rect(selection, (0, self.cy*dy, self.cx*dx, dy))
            return R

        def show_debug_messages(self, do_show):
            self.view.show_errors = "" if do_show else None
            self.view.parse()

        def _screen_to_cursor_coordinates(self, x, y):
            global maxCharPerLine, maxLinesPerScreen
            global Typo_Asc_Desc_Linegap_per_UPM, winAsc_winDesc_per_UPM
            self.max = int(x * (maxCharPerLine + (1.0 / winAsc_winDesc_per_UPM)) / config.screen_width)
            cy = int(y * (maxLinesPerScreen + (1.0 / winAsc_winDesc_per_UPM)) / config.screen_height)

            # selection below displays screen caused this. FIXME: maybe scroll down if this happens?
            if cy >= self.view.nolines:
                cy = self.view.nolines - 1
            return (min(self.max, len(self.view.wrapped_buffer[cy])), cy)

        def select_word(self):
            bx, by = self.view.wrap2buf[self.cy]
            m = re.compile(r'\w*$').search(self.view.data[self.view.lnr+by][:bx+self.cx])
            if m:
                self.cx -= len(m.group(0))
            m = re.compile(r'^\w*').match(self.view.data[self.view.lnr+by][bx+self.cx:])
            if m:
                self.max = self.CX = min(self.cx+len(m.group(0)), len(self.view.line))

        def event(self, ev, x, y, st):
            import pygame
            global Typo_Asc_Desc_Linegap_per_UPM, winAsc_winDesc_per_UPM
            if ev.type == pygame.MOUSEBUTTONDOWN:
                self.cx, self.cy = self._screen_to_cursor_coordinates(x, y / winAsc_winDesc_per_UPM)
                if time.time() - self.timer < 0.5:
                    self.select_word()
                else:
                    self.timer = time.time()
                    self.CX, self.CY = self.cx, self.cy
                renpy.redraw(self, 0)
                self.is_mouse_pressed = True
            if self.is_mouse_pressed and (ev.type == pygame.MOUSEMOTION or ev.type == pygame.MOUSEBUTTONUP):
                if ev.type == pygame.MOUSEMOTION:
                    self.CX, self.CY = self._screen_to_cursor_coordinates(x, y / winAsc_winDesc_per_UPM)
                renpy.redraw(self, 0)
                if ev.type == pygame.MOUSEBUTTONUP:
                    self.CX, self.CY, self.cx, self.cy = self.cx, self.cy, self.CX, self.CY
                    self.is_mouse_pressed = False
            if renpy.get_screen("_editor_suggestions"):
                renpy.hide_screen("_editor_suggestions")

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
                self.view.rewrap()
                renpy.redraw(self, 0)

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


        def set_spellcheck_modus(self):
            global spellcheck_modus
            if spellcheck_modus == "No check":
                spellcheck_modus = "Suggest"
                renpy.hide_screen("_editor_suggestions")
            else:
                spellcheck_modus = "No check"
            self.view.data._last_parsed_changes = None
            self.view.parse()
            renpy.redraw(self, 0)

    editor = Editor()

init 1701 python in _editor:

    if config.developer or config.editor:
        editor = Editor()

    def hyperlink_styler_wrap(target):
        if len(target) <= 7 or target[0:7] != "_spell:":
            return hyperlink_styler(target)

        return style._editor_error

    def hyperlink_callback_wrap(target):
        if len(target) <= 7 or target[0:7] != "_spell:":
            return hyperlink_callback(target)

        if not renpy.get_screen("_editor_suggestions"):
            editor.select_word()
            editor.is_mouse_pressed = False
            renpy.show_screen("_editor_suggestions", *editor.view.get_suggestions())
            renpy.restart_interaction()

    style.default.hyperlink_functions = (hyperlink_styler_wrap, hyperlink_callback_wrap, None)


screen _editor_main:
    style_prefix "_editor"
    default editor = _editor.editor
    default view = editor.view
    frame:

        add editor
        text view.display() style "_editor"
        if view.show_errors:
            window:
                text view.show_errors style "_editor_error"

        for keystr in sorted(view.keymap, key=len):
            key keystr action Function(view.handlekey, keystr)

        key "shift_K_RETURN" action [Function(editor.exit, apply = True), Return()]
        key "shift_K_KP_ENTER" action [Function(editor.exit, apply = True), Return()]

        for keystr in 'zy':
            key 'ctrl_K_'+keystr action Function(view.handlekey, 'ctrl_K_'+keystr)
            key 'repeat_ctrl_K_'+keystr action Function(view.handlekey, 'repeat_ctrl_K_'+keystr)

        key "K_ESCAPE" action [Function(editor.exit), Return()]

        key "ctrl_K_c" action Function(view.copy)
        key "ctrl_K_f" action Show("_editor_find")
        key "ctrl_K_v" action Function(view.insert)
        key "ctrl_K_x" action Function(view.cut)

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

        if renpy.get_screen("_editor_suggestions"):
            key 'mousedown_1' action Hide("_editor_suggestions")

        if renpy.get_screen("_editor_find"):
            key 'mousedown_1' action Hide("_editor_suggestions")

        hbox:
            style_prefix "quick"
            align (0.5, 1.0)
            if view.data.changed:
                if not renpy.parser.parse_errors:
                    textbutton _("Apply") action [Function(editor.exit, apply = True), Return()]
                elif view.show_errors is None:
                    textbutton _("Debug") action Function(editor.show_debug_messages, True)
                else:
                    textbutton _("Hide") action Function(editor.show_debug_messages, False)
                textbutton _("Cancel") action [Function(editor.exit, discard = True), Return()]
            textbutton _("Visual") action [Function(editor.exit), Return()]
            if _editor.spellcheck_modus == "Suggest":
                textbutton _("No check") action Function(editor.set_spellcheck_modus)
            if _editor.spellcheck_modus == "No check":
                textbutton _("Suggest") action Function(editor.set_spellcheck_modus)

