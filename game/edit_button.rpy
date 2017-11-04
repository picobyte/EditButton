init -1500 python:

    style.editor = Style(style.default)

    # must be monospace or need/add shadow
    style.editor.font = "Inconsolata-Regular.ttf"

init -1500 python in _editor:
    from store import config, style
    import store
    import os
    import re
    import shutil

    from tempfile import mkstemp
    import math

    from pygments import highlight
    from renpy_lexer import RenPyLexer
    from renpyformatter import RenPyFormatter
    from pygments.styles import get_style_by_name

    class TextData(object):
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
        def rpescape(self, string): return re.sub(r'(?<!\{)(\{(\{\{)*)(?!\{)', r'{\1', re.sub(r'(?<!\[)(\[(\[\[)*)(?!\[)', r'[\1', string))
        def _list_keymap(self, km, n, mod): return [mod+'K_'+k for k in km] + ['repeat_'+mod+'K_'+k for k in km] + n
        def repeat_keymap(self, km = [], n = [], mod=''): self.keymap.update(self._list_keymap(km, n, mod))

    class TextView(rpio):
        wheel_scroll_lines = 3
        def __init__(self, console, fname=None, nolines=None, lnr=None, lexer=None, format_style=None, wheel_scroll_lines=None):
            super(TextView, self).__init__()
            self.data = TextData()
            self.lnr = lnr if lnr else 0
            self.lexer = lexer if lexer else RenPyLexer(stripnl=False)
            self.formater = RenPyFormatter(style=format_style if format_style else 'monokai')
            self.fname = os.path.join(renpy.config.basedir, fname)
            self.data.deserialize(self.fname)
            self.parse()
            # XXX default nolines should be relative to window + font size
            self.nolines = nolines if nolines else int(config.screen_height / (34 + style.default.line_leading + style.default.line_spacing)) - 1
            self.repeat_keymap(['UP', 'DOWN', 'PAGEUP', 'PAGEDOWN'], ['mousedown_4', 'mousedown_5'])
            self.repeat_keymap(["HOME", "END"], mod="ctrl_")
            self.console = console

        @property
        def buffer(self): return self.data.buffer
        @property
        def line(self): return self.buffer[self.lnr+self.cursor[1]]
        @property
        def cursor(self): return self.console.at

        def parse(self):
            self.colored_buffer = highlight(self.rpescape(os.linesep.join(self.buffer)), self.lexer, self.formater).split(os.linesep)
            renpy.parser.parse_errors = []
            renpy.parser.parse(self.fname, os.linesep.join(self.buffer))

        def gotoline(self, lineno):
            return min(max(lineno, self.data.firstline), self.data.lastline-self.cursor[1]-1)

        def UP(self):
            self.lnr = self.gotoline(self.lnr - (self.cursor[1] == self.data.firstline))
            self.cursor[1] = max(self.cursor[1] - 1, 0)

        def DOWN(self):
            self.cursor[1] = min(self.cursor[1] + 1, self.nolines)
            self.lnr = self.gotoline(self.lnr + (self.cursor[1] == self.nolines))

        def PAGEUP(self): self.lnr = self.gotoline(self.lnr - self.nolines)
        def PAGEDOWN(self): self.lnr = self.gotoline(self.lnr + self.nolines)

        def ctrl_HOME(self): self.lnr = self.gotoline(self.data.firstline)
        def ctrl_END(self): self.lnr = self.gotoline(self.data.lastline)

        def mousedown_4(self): self.lnr = self.gotoline(self.lnr - self.wheel_scroll_lines)
        def mousedown_5(self): self.lnr = self.gotoline(self.lnr + self.wheel_scroll_lines)

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

        def LEFT(self): self.console.max = max(self.cursor[0] - 1, 0)
        def RIGHT(self): self.console.max = min(self.cursor[0] + 1, len(self.line))

        def HOME(self): self.console.max = 0
        def END(self): self.console.max = 0xffff # FIXME: what to do with very long lines?

        def RETURN(self): # FIXME
            self.DOWN()
            #self.cursor[0] = 0
            y = self.lnr+self.cursor[1]
            self.buffer.insert(y, '')
            self.colored_buffer.insert(y, self.colorize('', self.lnr != 0))
            self.changed = True

        def BACKSPACE(self):

            y = self.lnr+self.cursor[1]

            self.changed = True
            if self.cursor[0] == 0:
                if self.lnr + self.cursor[1] != 0: #FIXME
                    self.console.max = len(self.buffer[y - 1])
                    self.buffer[y - 1] += self.buffer[y]
                    del self.buffer[y]
                    self.UP()
            else:
                self.LEFT()
                self.cursor[0] = min(self.console.max, len(self.line))
                self.DELETE()
            self.parse()

        def DELETE(self):
            x = self.cursor[0]
            y = self.lnr+self.cursor[1]
            buf = self.buffer[y]
            self.changed = True
            if x != len(self.line):
                self.buffer[y] = buf[:x] + buf[x+1:]
            elif y != self.nolines:
                self.console.max = len(buf)
                self.buffer[y] += self.buffer[y+1]
                del self.buffer[y+1]
            self.parse()

        def typekey(self, c):
            x = self.cursor[0]
            buf = self.buffer[self.lnr+self.cursor[1]]
            self.buffer[self.lnr+self.cursor[1]] = buf[:x] + c + buf[x:]
            self.console.max += 1
            self.cursor[0] = min(self.console.max, len(self.line))
            renpy.redraw(self.console, 0)
            self.changed = True
            self.parse()

        def handlekey(self, keystr):
            getattr(self, re.sub(r'^(?:repeat_)?(ctrl_|meta_|alt_|)K_', r'\1', keystr))()
            self.cursor[0] = min(self.console.max, len(self.line))
            renpy.redraw(self.console, 0)

        def serialize(self):
            if self.changed:
                fh, abs_path = mkstemp()
                for line in self.buffer:
                    os.write(fh, line + os.linesep)
                os.close(fh)
                shutil.move(abs_path, self.fname)
                self.changed = False

        def colorize(self, txt, at_start=False, at_end=False):
            return ('{color=#000000}' if at_start else '') + txt + ('{/color}' if at_end else '')

        def display(self):
            ll = min(self.lnr + self.nolines, self.data.lastline)
            return self.colorize(os.linesep.join(self.colored_buffer[self.lnr:ll]), self.lnr != 0, ll != self.data.lastline)

        def external_editor(self, ctxt, transient=1):
            renpy.exports.launch_editor([ctxt[0]], ctxt[1], transient=transient)

    class Editor(renpy.Displayable):
        def __init__(self, *a, **b):
            super(Editor, self).__init__(a, b)
            self.at = [0, 0, 0, 0] # last two are meant for dragging
            self.max = 0xffff
            self.fl = {}
            self.fname = None
            self.is_visible = False
            self.view = None

        def render(self, width, height, st, at):
            R = renpy.Render(width, height)
            C = R.canvas()
            dx = width / 110
            dy = height / 31
            C.line((255,255,255,255),(self.at[0]*dx,self.at[1]*dy),(self.at[0]*dx,(self.at[1]+0.95)*dy))
            return R

        def event(self, ev, x, y, st):
            import pygame
            if ev.type == pygame.MOUSEBUTTONDOWN:
                self.max = int(x * 114 / config.screen_width)
                self.at[1] = int(y * 31 / config.screen_height)

                if self.view.lnr + self.at[1] >= self.view.data.lastline:
                    self.at[1] -= self.view.lnr + self.at[1] - self.view.data.lastline + 1

                self.at[0] = min(self.max, len(self.view.buffer[self.view.lnr+self.at[1]]))
                renpy.redraw(self, 0)

        def start(self, ctxt, offset=2):
            (fname, lnr) = ctxt
            lnr = lnr - 1 if fname else 0 # no fname indicates failure
            self.fname = fname

            if fname not in self.fl:
                self.fl[fname] = EditView(console=self, fname=fname, lnr=lnr)
            else:
                self.view.lnr = lnr
                self.view.handlekey("END")
            self.view = self.fl[fname]
            self.is_visible = True

        def apply(self, release=False):
            """
            Applied changes are not visible until restart (FIXME). with release set, a restart is triggered.
            """
            self.view.serialize()
            self.is_visible = False
            if release:
                raise renpy.game.UtterRestartException()

        def discard(self):
            del(self.fl[self.fname])
            self.view = None

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

        key "shift_K_RETURN" action [Function(editor.apply), Return()]
        key "shift_K_KP_ENTER" action [Function(editor.apply), Return()]

        key "K_TAB" action Function(view.typekey, "    ")
        key "K_SPACE" action Function(view.typekey, " ")
        key "repeat_K_SPACE" action Function(view.typekey, " ")

        for i in xrange(0, len(view.oSymName)):
            key "K_"+view.oSymName[i] action Function(view.typekey, view.oSymLow[i])
            key "shift_K_"+view.oSymName[i] action Function(view.typekey, view.oSymUpp[i])
            key "repeat_K_"+view.oSymName[i] action Function(view.typekey, view.oSymLow[i])
            key "repeat_shift_K_"+view.oSymName[i] action Function(view.typekey, view.oSymUpp[i])

        for nr in xrange(0, 10):
            key "K_"+str(nr) action Function(view.typekey, str(nr))
            key "K_KP"+str(nr) action Function(view.typekey, str(nr))
            key "repeat_K_"+str(nr) action Function(view.typekey, str(nr))
            key "repeat_K_KP"+str(nr) action Function(view.typekey, str(nr))
            key "shift_K_"+str(nr) action Function(view.typekey, view.nrSymbol[nr])
            key "repeat_shift_K_"+str(nr) action Function(view.typekey, view.nrSymbol[nr])

        for c in xrange(ord('a'), ord('z')+1):
            key "K_"+chr(c) action Function(view.typekey, chr(c))
            key "shift_K_"+chr(c) action Function(view.typekey, chr(c).upper())
            key "repeat_K_"+chr(c) action Function(view.typekey, chr(c))
            key "repeat_shift_K_"+chr(c) action Function(view.typekey, chr(c).upper())

        key "K_KP_PERIOD" action Function(view.typekey, ".")
        key "K_KP_DIVIDE" action Function(view.typekey, "/")
        key "K_KP_MULTIPLY" action Function(view.typekey, "*")
        key "K_KP_MINUS" action Function(view.typekey, "-")
        key "K_KP_PLUS" action Function(view.typekey, "+")
        key "K_KP_EQUALS" action Function(view.typekey, "=")

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0

            if _editor.editor.view.changed:
                if not renpy.parser.parse_errors:
                    textbutton _("Apply") action [Function(_editor.editor.apply), Return()]
                    textbutton _("Release") action Function(_editor.editor.apply, True)
                else:
                    textbutton _("Debug") action Function(renpy.parser.report_parse_errors)
                textbutton _("Suspend") action Return()
                textbutton _("Cancel") action [Function(editor.discard), Return()]
