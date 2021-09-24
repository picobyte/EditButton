init -1700 python in _editor:
    from store import config, style
    import os
    import re
    from time import time
    import pygame
    from pygments import highlight
    from visual_runtime_editor import *
    #import visual_runtime_editor

    # further specified when formatter is loaded (RenpyBuffer)
    style._editor_error = renpy.style.Style(style.default)


    class RenPyBuffer(ReadWriteBuffer):
        """ layer formating to display the buffer as text in a ren'py screen """
        def __init__(self, language='en', style='monokai'):
            self.style = style
            super(RenPyBuffer, self).__init__(fname=Editor.fname)
            self.set_format(language, style=style)
            self.lexer = RenPyLexer(stripnl=False)

        def set_format(self, language=None, style=None, **kwargs):
            self.language = language or self.language
            self.style = style or self.style
            self.formatter = RenPyFormatter(language=self.language, style=self.style, **kwargs)
            self.set_error_style()

        def parse(self, force=False):
            """ If changes were not yet parsed, check for errors; create colored_buffer for view on screen """
            if self.history.changed or force:
                document = os.linesep.join(self.data)
                renpy.parser.parse_errors = []
                renpy.parser.parse(self.fname, document)
                escaped = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', document))

                # NOTE: must split on newline here, not os.linesep, or it won't work in windows
                self.colored_buffer = highlight(escaped, self.lexer, self.formatter).split('\n')

        def get_color(self, arg):
            return self.formatter.get_style_defs(arg)

        def set_error_style(self):
            """ used for suggestion hyperlinks """
            style._editor_error.font = get_font()
            style._editor_error.size = TextView.font['size']
            style._editor_error.color = self.get_color("error")
            style._editor_error.background = self.get_color("error background")
            style._editor_error.hover_underline = True


    class TextView(object):

        # mono fonts should be implementable, require tweaking the two ratios.
        # adjust 1st ratio until selection shadows lines vertically, if shadow is too early, decrease ratio
        # adjust 2nd ratio until selection shadows a line entirely, if shadow is too short, decrease ratio

        fonts = {"Inconsolata-Regular": ("codeface/fonts/inconsolata", 1.0, 1.0),
                 "ProggyClean": ("codeface/fonts/proggy-clean", 1.166, 1.233)}
        font = {"name": "Inconsolata-Regular", "size": 28}

        """keeps track of horizontal position in text. Wrapping is not taken into account for position."""
        def __init__(self, console, data, font=None, nolines=None, lnr=0, wheel_scroll_lines=3):
            self.data = data
            self.lnr = lnr
            self.console = console
            self.show_errors = ""
            self.wheel_scroll_lines = wheel_scroll_lines
            self.keymap = set(['mousedown_4', 'mousedown_5'])
            self._add_km(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['repeat_', 'shift_', 'repeat_shift_', ''])
            self._add_km(['HOME', 'END'], ['ctrl_'])
            self.set_font(font or (TextView.font["name"], TextView.font["size"]))

        @staticmethod
        def get_max_char_per_line(name=None, size=None):
            name = name or TextView.font['name']
            size = size or TextView.font['size']
            return TextView.fonts[name][1] * 3840.545 / size

        @staticmethod
        def get_max_lines_per_screen(name=None, size=None):
            name = name or TextView.font['name']
            size = size or TextView.font['size']
            return TextView.fonts[name][2] * (2.3 + 912.0 / size)

        def set_font(self, font=None):
            if font:
                TextView.font['name'] = font[0]
                TextView.font['size'] = font[1]
                TextView._max_lines = int(TextView.get_max_lines_per_screen())
            self.data.set_error_style()
            self.cbuflines = TextView._max_lines
            self.parse()

        def _add_km(self, km, mod):
            self.keymap.update([m+'K_'+k for k in km for m in mod])

        @property
        def line(self):
            return self.wrapped_buffer[Editor.cy]

        def nr_of_lines(self):
            return len(self.wrapped_buffer)

        @property
        def coords(self):
            return {"lnr": self.lnr, "cx": Editor.cx, "cy": Editor.cy, "CX": Editor.CX, "CY": Editor.CY}

        def rewrap(self):
            """ a copy of the buffer in view that is wrapped as shown in view """
            self.wrapped_buffer = []
            self.wrap2buf = {}
            atline = 0
            tot = 0
            for line in self.data[self.lnr:min(self.lnr + TextView._max_lines, len(self.data))]:
                wrap = renpy.text.extras.textwrap(line, TextView.get_max_char_per_line()) or ['']

                offs = 0
                for l in wrap:
                    offs += line.index(l, offs) - offs
                    self.wrap2buf[tot]=(offs, atline)
                    tot += 1
                    if tot > TextView._max_lines:
                        return
                    offs += len(l)
                    self.wrapped_buffer.append(l)
                atline += 1
                self.cbuflines = atline
                if offs != len(line):
                    renpy.error(os.linesep.join(["rewrap() discrepancy", line, str(offs), str(len(line)), str(wrap)]))

        def parse(self, force=False):
            self.data.parse(force)
            self.rewrap()
            if self.show_errors is not None:
                err = renpy.parser.parse_errors
                self.show_errors = ""
                if err:
                    self.show_errors = re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', os.linesep.join(err)))

        def update_cursor(self, force=False):
            mouse = "; mouse: {0}, {1}".format(Editor.mousex, Editor.mousey) if hasattr(Editor, "mousey") else ""
            config.window_title = Editor.fname + ": line %d+%d, char %d%s" % (self.lnr, Editor.cy, Editor.cx, mouse)
            self.data.history.update_cursor(self.console, force)

        def UP(self, sub=1, new_history_entry=True):
            if new_history_entry:
                self.update_cursor()

            sub = min(Editor.cy + self.lnr, sub)
            cursor_movement = min(Editor.cy, sub)
            Editor.cy -= cursor_movement
            self.lnr -= sub - cursor_movement
            if cursor_movement == 0: # then view moved
                self.rewrap()
                # either suggestion screen positions needs to be updated or closed
                hide_all_screens_with_name("_editor_menu", layer="transient")

        def DOWN(self, add=1, new_history_entry=True):
            if new_history_entry:
                self.update_cursor()
            cursor_movement = min(self.nr_of_lines() - Editor.cy - 1, add)
            add -= cursor_movement
            if cursor_movement:
                Editor.cy += cursor_movement
            elif self.lnr + add < len(self.data): # view movement
                hide_all_screens_with_name("_editor_menu", layer="transient")
                self.lnr += add
                self.rewrap()
                while Editor.cy >= self.nr_of_lines():
                    Editor.cy -= 1
                    self.parse()
            else:
                 Editor.CY = Editor.cy

        def PAGEUP(self):
            self.UP(self.nr_of_lines())

        def PAGEDOWN(self):
            self.DOWN(self.nr_of_lines())

        def ctrl_HOME(self):
            self.update_cursor(self.console)
            Editor.cy = self.lnr = 0

        def ctrl_END(self):
            self.update_cursor()
            Editor.cy = self.nr_of_lines() - 1
            self.lnr = len(self.data) - Editor.cy - 1

        def mousedown_4(self): self.UP(self.wheel_scroll_lines)
        def mousedown_5(self): self.DOWN(self.wheel_scroll_lines)


    class EditView(TextView):

        def __init__(self, **kwargs):
            super(EditView, self).__init__(**kwargs)

            self._add_km(['BACKSPACE', 'DELETE', 'RETURN'], ['repeat_', ''])
            self._add_km(['HOME', 'END'], ['shift_', 'ctrl_', 'ctrl_shift_', ''])
            self._add_km(['LEFT', 'RIGHT'], ['shift_', 'ctrl_', 'ctrl_shift_', 'repeat_ctrl_shift_', '', 'repeat_shift_', 'repeat_ctrl_', 'repeat_'])
            self._add_km(['UP', 'DOWN'], ['shift_', 'repeat_shift_'])
            Editor.max = 0xffff
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
            cx, cy, CX, CY, selection = self.console.ordered_cursor_coordinates()
            if not selection:
                return ""
            sx, sy, ex, ey = self.cursor2buf_coords(cx, cy, CX, CY)
            copy = ""
            for y in xrange(sy, ey):
                copy += self.data[y][sx:len(self.data[y])] + os.linesep
                sx = 0
            return copy+self.data[ey][sx:ex]

        def LEFT(self, sub=1, new_history_entry=True):
            if new_history_entry:
                self.update_cursor()

            while Editor.cx < sub and self.wrap2buf[Editor.cy][0]:
                sub -= Editor.cx + 1
                self.UP()
                Editor.cx = len(self.line)
            Editor.max = max(Editor.cx - sub, 0)

        def RIGHT(self, add=1, new_history_entry=True):
            if new_history_entry:
                self.update_cursor()

            bx, by = self.wrap2buf[Editor.cy]
            while Editor.cx + add > len(self.line) and bx+Editor.cx <= len(self.data[self.lnr+by]):
                add -= len(self.line) - Editor.cx + 1
                self.DOWN()
                Editor.cx = 0
            Editor.cx = min(Editor.cx + add, len(self.line))
            Editor.max = Editor.cx

        def ctrl_LEFT(self):
            bx, by = self.wrap2buf[Editor.cy]
            m = re.compile(r'\w*\W*$').search(self.data[self.lnr+by][:bx+Editor.cx])
            if m:
                self.LEFT(len(m.group(0)))

        def ctrl_RIGHT(self):
            bx, by = self.wrap2buf[Editor.cy]
            m = re.compile(r'^\w*\W*').match(self.data[self.lnr+by][bx+Editor.cx:])
            if m:
                self.RIGHT(len(m.group(0)))

        def HOME(self):
            self.update_cursor()
            Editor.max = 0

        def END(self):
            self.update_cursor()
            Editor.max = 0xffff

        def RETURN(self): self.insert(['',''])

        def BACKSPACE(self):
            self.update_cursor(force=True)
            if Editor.cx == Editor.CX and Editor.cy == Editor.CY:
                if Editor.cx or self.wrap2buf[Editor.cy][0]:
                    self.LEFT(new_history_entry=False)
                elif self.lnr + Editor.cy != 0:
                    self.UP(new_history_entry=False)
                    Editor.max = len(self.line)
                else:
                    return
                Editor.cx = Editor.max
            self.DELETE(force=False)

        def cursor2buf_coords(self, cx, cy, CX, CY, _selection=None):
            sx, sy = self.wrap2buf[cy]
            ex, ey = self.wrap2buf[CY]
            return (sx+cx, sy+self.lnr, ex+CX, ey+self.lnr)

        def DELETE(self, force=True):
            self.update_cursor(force=force)
            cx, cy, CX, CY, selection = self.console.ordered_cursor_coordinates()
            sx, sy, ex, ey = self.cursor2buf_coords(cx, cy, CX, CY)

            if sx != len(self.data[sy]) or selection:
                ex += 0 if selection else 1 # then delete the one right of the cursor
                start = self.data[sy][:sx]
                del self.data[sy:ey]
                self.data[sy] = start + self.data[sy][ex:]
            elif sy < len(self.data) - 1:
                Editor.max = len(self.data[sy])
                self.data[sy] += self.data[sy+1]
                del self.data[sy+1]
            self.parse()
            Editor.cy = Editor.CY = cy
            if cx > len(self.line):
                # fix cursor placement if space was deleted causing a word at the end of the line to wrap to the next line
                cx -= len(self.line) + 1
                self.DOWN(new_history_entry=False)
            elif sx < self.wrap2buf[cy][0]:
                # fix cursor placement when word at start of line was shortened and now wraps
                dx = self.wrap2buf[cy][0] - sx
                self.UP(new_history_entry=False)
                cx = len(self.line) + 1 - dx
            Editor.max = Editor.cx = Editor.CX = cx

        def copy(self):
            selection = self.get_selected()
            if selection is not "":
                import pyperclip # to use external copy buffer
                pyperclip.copy(selection)

        def cut(self):
            if Editor.CX != Editor.cx or Editor.CY != Editor.cy:
                self.copy()
                self.handlekey("DELETE")

        def insert(self, entries=None):
            import pyperclip
            self.update_cursor(force=True)

            if entries == None: # paste in absences of entries
                entries = pyperclip.paste().split(os.linesep)

            cx, cy, CX, CY, selection = self.console.ordered_cursor_coordinates()

            if cx != CX or cy != CY:
                self.DELETE(force=False)

            cx, cy = Editor.cx, Editor.cy

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
            if len(entries) <= 1 and cx + len(entries[0]) - self.wrap2buf[Editor.cy][0] < len(self.line):
                Editor.cx = cx + len(entries[0])
            else:
                self.UP(new_history_entry=False)
                for e in entries:
                    self.DOWN(new_history_entry=False)
                    Editor.cx = cx + len(e)
                    while Editor.cx - self.wrap2buf[Editor.cy][0] > len(self.line):
                        self.DOWN(new_history_entry=False)
                        if not self.wrap2buf[Editor.cy][0]:
                            break
                    cx = 0
                Editor.CY = Editor.cy

            Editor.cx -= self.wrap2buf[Editor.cy][0]
            Editor.max = Editor.CX = Editor.cx
            renpy.redraw(self.console, 0)

        def handlekey(self, keystr):
            """ repeat keys are handled as normal keys; unless shift is provided selection is discarded and cursor is redrawn """
            getattr(self, re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)(?:shift_)?K_', r'\1', keystr))()
            Editor.cx = min(Editor.max, len(self.line))
            if "shift_" not in keystr:
                Editor.CX, Editor.CY = Editor.cx, Editor.cy
            renpy.redraw(self.console, 0)

        def colorize(self, txt, at_start, at_end):
            return ('{color=#000000}' if at_start else '') + txt + ('{/color}' if at_end else '')

        def display(self):
            ll = min(self.lnr + self.cbuflines, len(self.data))
            section = os.linesep.join(self.data.colored_buffer[self.lnr:ll])
            section = self.colorize(section, self.lnr != 0, ll != len(self.data))
            return re.sub(r'(\{/color\}[^{}]*)\{/color\}$', r'\1', section)

        def ctrl_z(self):
            self.data.history.undo(self)

        def ctrl_y(self):
            self.data.history.redo(self)

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
            had_selection = (abs(Editor.cx - Editor.CX) + 1) * (abs(Editor.cy - Editor.CY) + 1)
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
                    Editor.CY = Editor.CX = self.lnr = 0
                    self.PAGEUP()
                    self.HOME()
                    self.rewrap()
            if chars is None:
                renpy.notify("Not found")
            else:
                Editor.cx = Editor.CX
                Editor.cy = Editor.CY
                self.RIGHT(chars)
                Editor.CX, Editor.CY = Editor.cx, Editor.cy
                self.RIGHT(m.end()-m.start())
                renpy.redraw(self.console, 0)

        def suggestions_for_selected(self):
            return self.data.formatter.lang.candidates(self.get_selected())

        def set_spellcheck_modus(self, value):
            if not value:
                renpy.hide_screen("_editor_menu", layer="transient")
            self.data.formatter.do_check = value
            self.parse(force=True)
            renpy.redraw(self.console, 0)

    class Editor(renpy.Displayable):
        mousex = mousey = fname = view = context_menu = None
        context_options = []
        buffer = {}
        timer = time()
        is_mouse_pressed = False
        max = cx = cy = CX = CY = 0 # last two are meant for dragging
        suggestion_menu = None #TODO: make this a hashmap per word?
        original_title = None

        def __init__(self, *a, **b):
            super(Editor, self).__init__(a, b)
            Editor.context_options.append({ "name": "language", "submenu": ["de", "en", "es", "fr", "pt", "ru"] })
            Editor.context_options.append({"name": "style", "submenu": ["abap", "algol_nu", "arduino", "autumn", "borland", "colorful", "default", "emacs", "friendly", "fruity", "igor", "inkpot", "lovelace", "manni", "monokai", "murphy", "native", "pastie", "perldoc", "rainbow_dash", "rrt", "sas", "tango", "vim", "vs", "xcode"] })
            # also present but problematic:
            self.is_visible = False

        @staticmethod
        def ordered_cursor_coordinates():
            cx, cy = Editor.cx, Editor.cy
            CX, CY = Editor.CX, Editor.CY

            selection = True

            if cy > CY:
                Editor.cy, Editor.CY = CY, cy
                Editor.cx, Editor.CX = CX, cx

            elif cy == CY:
                if cx > CX:
                    Editor.cx, Editor.CX = CX, cx
                elif cx == CX:
                    selection = False
            return (Editor.cx, Editor.cy, Editor.CX, Editor.CY, selection)

        def render(self, width, height, st, at):
            """ draw the cursor or the selection """
            R = renpy.Render(width, height)
            C = R.canvas()
            dx = width / TextView.get_max_char_per_line()
            dy = height / TextView.get_max_lines_per_screen()
            selection = self.view.data.get_color("highlight")
            if Editor.cy == Editor.CY:
                if Editor.CX == Editor.cx:
                    C.line((255,255,255,255),(Editor.cx*dx,Editor.cy*dy),(Editor.cx*dx, (Editor.cy+1.0)*dy))
                else:
                    C.rect(selection,(Editor.cx*dx, Editor.cy*dy, (Editor.CX-Editor.cx)*dx, dy))
            elif Editor.cy < Editor.CY:
                x = Editor.cx
                for y in xrange(Editor.cy, Editor.CY):
                    C.rect(selection, (x*dx, y*dy, (len(self.view.wrapped_buffer[y])-x)*dx, dy))
                    x = 0
                C.rect(selection, (0, Editor.CY*dy, Editor.CX*dx, dy))
            else:
                x = Editor.CX
                for y in xrange(Editor.CY, Editor.cy):
                    C.rect(selection, (x*dx, y*dy, (len(self.view.wrapped_buffer[y])-x)*dx, dy))
                    x = 0
                C.rect(selection, (0, Editor.cy*dy, Editor.cx*dx, dy))
            return R

        def show_debug_messages(self, do_show):
            self.view.show_errors = "" if do_show else None
            self.view.parse()

        def _screen_to_cursor_coordinates(self, x, y):
            Editor.max = int(x * TextView.get_max_char_per_line() / config.screen_width)
            cy = int(y * TextView.get_max_lines_per_screen() / config.screen_height)

            if cy >= self.view.nr_of_lines():
                cy = self.view.nr_of_lines() - 1
            return (min(Editor.max, len(self.view.wrapped_buffer[cy])), cy)

        def sbc(self, lnr=None, cx=None, cy=None, CX=None, CY=None):
            """set buffer coordinates"""
            devlog.info("sbc (%s, %s, %s, %s, %s)" % (lnr, cx, cy, CX, CY))
            self.view.lnr = self.view.lnr if lnr is None else lnr
            Editor.cx = Editor.cx if cx is None else cx
            Editor.cy = Editor.cy if cy is None else cy
            Editor.CX = Editor.cx if CX is None else CX
            Editor.CY = Editor.cy if CY is None else CY
            self.view.rewrap()

        def select_word(self):
            bx, by = self.view.wrap2buf[Editor.cy]
            m = re.compile(r'\w*$').search(self.view.data[self.view.lnr+by][:bx+Editor.cx])
            if m:
                Editor.cx -= len(m.group(0))
            m = re.compile(r'^\w*').match(self.view.data[self.view.lnr+by][bx+Editor.cx:])
            if m:
                Editor.max = Editor.CX = min(Editor.cx+len(m.group(0)), len(self.view.line))

        def event(self, ev, x, y, st):
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                Editor.cx, Editor.cy = self._screen_to_cursor_coordinates(x, y)
                self.view.update_cursor()
                if time() - Editor.timer < 0.5:
                    self.select_word()
                else:
                    Editor.timer = time()
                    Editor.CX, Editor.CY = Editor.cx, Editor.cy
                renpy.redraw(self, 0)
                Editor.is_mouse_pressed = True
                hide_all_screens_with_name("_editor_menu", layer="transient")
            elif ev.type == pygame.MOUSEMOTION: # Updates the position of the mouse every time the player moves it
                Editor.mousex = x
                Editor.mousey = y
                if Editor.is_mouse_pressed:
                    Editor.CX, Editor.CY = self._screen_to_cursor_coordinates(x, y)
                renpy.redraw(self, 0)
            elif Editor.is_mouse_pressed and ev.type == pygame.MOUSEBUTTONUP:
                renpy.redraw(self, 0)
                if ev.type == pygame.MOUSEBUTTONUP:
                    Editor.CX, Editor.CY, Editor.cx, Editor.cy = Editor.cx, Editor.cy, Editor.CX, Editor.CY
                    Editor.is_mouse_pressed = False

        def start(self, ctxt, offset=2):
            (fname, lnr) = ctxt
            if fname: # no fname indicates failure
                lnr = lnr - 1
                Editor.fname = os.path.join(renpy.config.basedir, fname)

                if fname not in Editor.buffer:
                    Editor.buffer[fname] = EditView(console=self, data=RenPyBuffer(), lnr=lnr)
                else:
                    self.view.lnr = lnr
                    self.view.handlekey("END") # NB. call via handlekey triggers cursor redraw.
                self.view = Editor.buffer[fname]
                self.is_visible = True
                self.view.rewrap()
                if Editor.original_title is None:
                    Editor.original_title = config.window_title
                renpy.redraw(self, 0)

        def exit(self, discard=False, apply=False):
            """ unless discarded, changes are kept in store. Applied changes are not visible until reload (shift+R). """
            self.is_visible = False
            Editor.max = Editor.cx = Editor.cy = Editor.CX = Editor.CY = 0 # last two are meant for dragging
            if Editor.original_title is not None:
                config.window_title = Editor.original_title
            if discard:
                #reload from disk
                self.view.data.load()
                self.view.parse()
            elif apply:
                self.view.data.save()

        def add_suggestion_menu(self):
            self.select_word()
            choices = self.view.suggestions_for_selected()
            renpy.redraw(self, 0)
            Editor.is_mouse_pressed = False

            cw = config.screen_width / TextView.get_max_char_per_line()
            ch = config.screen_height / self.view.get_max_lines_per_screen()

            x = int(Editor.cx * cw)
            if Editor.cy + 1 + len(choices) <= TextView._max_lines or Editor.cy - len(choices) < 0:
                y = int((1 + Editor.cy) * ch)
            else:
                y = int((Editor.cy - len(choices)) * ch)

            coords = self.ordered_cursor_coordinates()
            def replacer(pick):
                if pick:
                    self.sbc(cx=coords[0], cy=coords[1], CX=coords[2], CY=coords[3])
                    self.view.insert([pick])
                return pick

            Editor.suggestion_menu=SelectionMenu(x=x, y=y, cw=cw, ch=ch, font=TextView.font['name'], font_size=TextView.font['size'], choices=choices, layer="transient", handler=replacer, options={'timeout':(1.5, 0.2)})
            renpy.restart_interaction()

        def add_context_menu(self):
            def devlogger(pick):
                if pick[0] == "language":
                    self.view.data.set_format(language=pick[1])
                elif pick[0] == "style":
                    self.view.data.set_format(style=pick[1])
                elif pick[0] == "font":
                    self.view.set_font(pick[1:])
                self.view.parse(force=True)
                renpy.redraw(self, 0)

                devlog.info(pick)
                return ""

            # TODO/FIXME: context menu doesn't have to follow screen/view font parameters
            cw = config.screen_width / TextView.get_max_char_per_line()
            ch = config.screen_height / TextView.get_max_lines_per_screen()

            Editor.context_menu=SelectionMenu(x=Editor.mousex, y=Editor.mousey,
                                              cw=cw, ch=ch, font=TextView.font['name'],
                                              font_size=TextView.font['size'], choices=self.context_options,
                                              layer="master", handler=devlogger)


    class SelectionMenu(renpy.Displayable):
        required_init_args = {'x', 'y', 'cw', 'ch', 'font', 'font_size', 'choices', 'handler', 'layer'}
        def __init__(self, id="", base_menu=None, options=None, **kwargs):

            for arg in self.required_init_args:
                setattr(self, arg, kwargs[arg])
                del kwargs[arg]
            super(SelectionMenu, self).__init__(**kwargs)

            self.__dict__.update({"id": id, "base_menu": base_menu, "options": options if options else {}})

            wordlen_max = max(map(lambda x: len(str(x["name"] if isinstance(x, (dict, renpy.python.RevertableDict)) else x)) + 1, self.choices))
            self.area = (self.x, self.y, int(wordlen_max * self.cw), int(len(self.choices) * self.ch))
            self.nested_menu = []
            self.focus()
            if renpy.get_screen("_editor_menu", layer=self.layer):
                renpy.end_interaction("")
            if base_menu:
                # XXX: for some reason not shown for overlay layer.
                renpy.show_screen("_editor_menu", self, _layer=self.layer)
            else:
                renpy.invoke_in_new_context(renpy.call_screen, "_editor_menu", self, _layer=self.layer)

        def focus(self, keep=False):
            if 'timeout' in self.options and keep is False:
                self.timeout = self.options['timeout'][0]
                self.polling = self.options['timeout'][1]
                self.last_focus = time()
            else:
                self.timeout = 0.0
            if self.base_menu:
                self.base_menu.focus(keep)

        def event(self, ev, x, y, st):
            if ev.type == pygame.MOUSEBUTTONDOWN:
                renpy.end_interaction("")

        def end(self, pick=None):
            devlog.warn(str(pick))
            if pick or self.timeout != 0.0:
                if self.base_menu:
                    renpy.hide_screen("_editor_menu", layer=self.layer)
                    if isinstance(pick, (list, renpy.python.RevertableList)):
                        pick.insert(0, self.id)
                        self.base_menu.end(pick)
                    else:
                        self.base_menu.end([self.id, pick])
                else:
                    renpy.end_interaction("" if pick is None else self.handler(pick))


        def act(self, pick=None, hovered=None):
            """selection, (un)hover event or timeout"""
            if pick != None:
                index, pick = pick
                if not isinstance(pick, (dict, renpy.python.RevertableDict)):
                    self.end(pick)
                elif 'submenu' in pick:
                    kwargs = dict((k, getattr(self, k)) for k in self.required_init_args)

                    # TODO/FIXME 1. could implement stacking as cards for menus
                    # TODO/FIXME 2. choose other side if there's no space right of the menu

                    kwargs['layer'] = config.layers[config.layers.index(self.layer)+1]
                    # if this errors, you're using too many side menus. use a
                    # different solution instead.

                    if renpy.get_screen("_editor_menu", layer=kwargs['layer']):
                        renpy.hide_screen("_editor_menu", layer=kwargs['layer'])

                    kwargs['choices'] = pick["submenu"]
                    kwargs['id'] = pick['name']
                    kwargs['y'] = int(kwargs['y'] + index * self.ch)
                    kwargs['x'] = int(kwargs['x'] + self.area[2])
                    self.nested_menu.append(SelectionMenu(base_menu=self, **kwargs))
            elif hovered is True:
                self.focus(keep=True)
            elif hovered is False:
                self.focus()
            elif self.timeout != 0.0 and time() - self.last_focus > self.timeout:
                 self.end()

        def render(self, width, height, st, at):
            R = renpy.Render(width, height)
            renpy.redraw(self, 1)
            return R

        def visit(self):
            return self.nested_menu

init 1701 python in _editor:

    def hyperlink_styler_wrap(target):
        if len(target) <= 8 or target[0:8] != "_editor:":
            return hyperlink_styler(target)

        return style._editor_error

    def hyperlink_callback_wrap(target):
        if len(target) <= 8 or target[0:8] != "_editor:":
            return hyperlink_callback(target)

        if not renpy.get_screen("_editor_menu", layer="transient"):
            editor.add_suggestion_menu()

    def hide_all_screens_with_name(name, layer=None):
        for layer in config.layers if layer is None else [layer]:
            while renpy.get_screen(name, layer=layer):
                renpy.hide_screen(name, layer=layer)

    if config.developer or config.editor:
        editor = Editor()

        style.default.hyperlink_functions = (hyperlink_styler_wrap, hyperlink_callback_wrap, None)

    def get_font(name=TextView.font['name']):
        return TextView.fonts[name][0] + "/" + name + ".ttf"

init 1702:
    style _editor_textbutton:
        font _editor.get_font("Inconsolata-Regular")
        size 28
        color "#fff"
        hover_color "ff2"


screen _editor_menu(selection):
    if selection.timeout != 0.0:
        timer selection.polling action Function(selection.act) repeat True
    frame:
        padding (0, 0)
        background "#111a"
        area selection.area
        add selection
        vbox:
            for (index, pick) in enumerate(selection.choices):
                textbutton (pick["name"] if isinstance(pick, (dict, renpy.python.RevertableDict)) else str(pick)):
                    padding (0, 0)
                    minimum (0, 0)
                    text_font _editor.get_font(selection.font)
                    text_size selection.font_size
                    text_color "#fff"
                    text_hover_color "ff2"
                    hovered Function(selection.act, hovered=True)
                    unhovered Function(selection.act, hovered=False)
                    action Function(selection.act, pick=(index, pick))
        key "K_ESCAPE" action Hide("_editor_menu")


screen _editor_main:
    layer "master"
    default editor = _editor.editor
    default view = editor.view
    frame:
        padding (0, 0)
        pos (0, 0)
        background view.data.get_color("background")
        add editor
        text view.display() font _editor.get_font() size view.font['size']
        if view.show_errors:
            window:
                align (0.5, 1.0)
                background Frame("gui/namebox.png", gui.namebox_borders, tile=gui.namebox_tile, xalign=gui.name_xalign)
                text view.show_errors style "_editor_error"

        for keystr in sorted(view.keymap, key=len):
            key keystr action Function(view.handlekey, keystr)

        key "shift_K_RETURN" action [Function(editor.exit, apply = True), Return()]
        key "shift_K_KP_ENTER" action [Function(editor.exit, apply = True), Return()]

        key "K_ESCAPE" action [Function(editor.exit), Return()]

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

        key "ctrl_K_a" action [Function(view.handlekey, "ctrl_K_END"), Function(view.handlekey, "ctrl_shift_K_HOME")]
        key "ctrl_K_c" action Function(view.copy)
        key "ctrl_K_v" action Function(view.insert)
        key "ctrl_K_x" action Function(view.cut)
        for keystr in 'zy':
            key 'ctrl_K_'+keystr action Function(view.handlekey, 'ctrl_K_'+keystr)
            key 'repeat_ctrl_K_'+keystr action Function(view.handlekey, 'repeat_ctrl_K_'+keystr)

        # probably this should be a renpy.cal_screen or Call
        key "ctrl_K_f" action Show("_editor_find")

        if renpy.get_screen("_editor_menu"):
            key 'mousedown_1' action Function(_editor.hide_all_screens_with_name, "_editor_menu")
        elif renpy.get_screen("_editor_find"):
            key 'mousedown_1' action Hide("_editor_find")
        else:
            key 'mouseup_3' action Function(editor.add_context_menu)
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
            if view.data.formatter.do_check:
                textbutton _("No check") action Function(view.set_spellcheck_modus, False)
            else:
                textbutton _("Suggest") action Function(view.set_spellcheck_modus, True)

# FIXME: should a call_screen and a reusable renpy.displayable that supports tabs among others.
screen _editor_find(layer="overlay"):
    #TODO Regex replace
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
                    action Hide("_editor_find", _layer=layer)
                    keysym('K_ESCAPE')



