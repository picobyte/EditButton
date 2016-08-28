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
    style.editor.color = "#F92672" # caret
    linkstate = "default"

    def linkhandler(target):
        if linkstate == "default":
            renpy.call_in_new_context(target)
        else:
            devlog.info(target)

    def hyperlink_styler(target):
        return style.hyperlink_text

    class Editor(object):
        # XXX should be relative to window + font size
        maxlines = 28
        menuheight = 30

        french_spacing = 1 # needed for caret
        lnr = fname = None
        fl = {}
        def __init__(self):
            self.lexer = RenPyLexer()
            self.undo()

        def undo(self):
            self.files_changed = False
            self.updated_context()

        @property
        def line(self):
            return self.fl[self.fname][self.lnr].rstrip('\r\n')

        def context_lines(self):
            s = max(self.lnr - self.maxlines, 1)
            e = min(s + self.maxlines + 1, len(self.fl[self.fname]))

            #pygments strips leading whitespace. prevent this.
            lines = ""
            while s != e and self.fl[self.fname][s].rstrip('\r\n') == "":
                lines += self.fl[self.fname][s]
                s += 1
            if has_renpyformatter:
                lines += highlight("".join(self.fl[self.fname][s:e]), self.lexer, RenPyFormatter(style='monokai'))
            else:
                for i in range(s, e):
                    alpha = -min(0.8, 0.1 * math.log(abs(i-self.lnr) + 1))
                    lines += ("{alpha=%.2f}" % alpha) + self.fl[self.fname][i] + "{/alpha}"
            return lines

        def get_cursor_pos(self):
            return min(self.maxlines, self.lnr - 1) * (style.default.size + self.french_spacing) + self.menuheight

        def updated_context(self):

            ctxt = renpy.get_filename_line()
            if not ctxt[0]: # indicates failure
                return False

            (self.fname, self.lnr) = ctxt

            if not self.fname in self.fl:

                self.fl[self.fname] = [False]
                with open(os.path.join(renpy.config.basedir, self.fname)) as fh:

                    for line in fh:
                        self.fl[self.fname].append(line)
            return True

        ## apply changes to phrases to the .rpy file(s)
        def patch_rpy_files(self):
            self.files_changed = False
            for filename, lines in self.fl.iteritems():
                if lines[0]:
                    fh, abs_path = mkstemp()

                    for linenr in range(1, len(lines)):
                        os.write(fh, lines[linenr]+os.linesep)

                    os.close(fh)
                    shutil.move(abs_path, os.path.join(renpy.config.basedir, filename))
                    lines[0] = False # changes applied

        def change_context(self, add):

            # if at end of input and we move, rather than inserting a line, edit one elsewhere.
            prompt = renpy.get_widget("edit", "prompt")
            if prompt and "(End of dialogue)" in prompt.text:
                del self.fl[self.fname][self.lnr]
                prompt.set_text("")

            self.lnr = max(1, min(self.lnr + add, len(self.fl[self.fname]) - 1))

        def update_lines(self, update):
            lns = renpy.get_widget("edit", "lines")
            self.fl[self.fname][self.lnr] = update + os.linesep
            lns.set_text(self.context_lines())


        # XXX: not working for extended lines..??
        def update_dialogue(self, what):

            if self.updated_context():
                # adapt `what' if already changed this session.
                matched = re.match(r'^[^"\'#]*("(?:[^"]*|\\.)"|\'(?:[^\']+?|\\.)\').*$', self.line)
                if matched:
                    what = matched.group(1)[1:-1]
                    say = renpy.get_screen("say")
                    for i in say.children:
                        try:
                            i.set_text(what)
                        except Exception:
                            pass
                    #say.update()
                    #say_what = renpy.get_widget("window", "what")
                    #if say_what:
                    #say_what.set_text(what)

            return what


        def external_editor(self, transient=1):
            renpy.exports.launch_editor([self.fname], self.lnr, transient=transient)

        # FIXME: edit button behaviour is a bit odd. also darker than rest?
        def end_of_dialogue(self):
            if self.updated_context():
                m = re.match("^(\s+)", self.line)
                if m:
                    self.fl[self.fname].insert(self.lnr, m.group(1))
                    renpy.call_screen("edit")


    def get_filetree(dir=renpy.config.gamedir, extension=('.py','.rpy')):
        list = []
        i = len(renpy.config.gamedir) + 1
        for path, dirs, files in os.walk(dir):
            for file in files:
                if file.endswith(extension):
                    list.append(os.path.join(path[i:], file))
        return list
    class Clicker(object):
        links = {}
        def __init_(self):
            global linkstate
            linkstate = "openfile"
            self.orig_hln_cb = config.hyperlink_callback
            #config.hyperlink_callback = self.clicked

        def clickify(self, links):
            for f in links:
                self.links[f] = True
            return os.linesep.join(["{a="+f+"}"+f+"{/a}" for f in links])
        def clicked(self, link):
            devlog.info(link)
            linkstate = "default"

screen openfile():
    frame:
        default filetree = get_filetree()
        default maxlines = 30
        default firstline = 0
        default lastline = max(0, len(filetree) - maxlines)
        default lnr = 0
        xpadding 10
        ypadding 10
        xpos 100
        background "#272822"
        $ clicker = Clicker()

        text clicker.clickify(filetree[lnr:(min(lnr, lastline)+maxlines)]) style "editor"

        key "K_UP" action SetScreenVariable("lnr", max(lnr - 1, firstline))
        key "K_DOWN" action SetScreenVariable("lnr", min(lnr + 1, lastline))
        key "repeat_K_UP" action SetScreenVariable("lnr", max(lnr - 1, firstline))
        key "repeat_K_DOWN" action SetScreenVariable("lnr", min(lnr + 1, lastline))

        key "K_HOME" action SetScreenVariable("lnr", firstline)
        key "K_END" action SetScreenVariable("lnr", lastline)

        key "K_PAGEUP" action SetScreenVariable("lnr", max(lnr-maxlines, firstline))
        key "K_PAGEDOWN" action SetScreenVariable("lnr", min(lnr+maxlines, lastline))

        key "repeat_K_PAGEUP" action SetScreenVariable("lnr", max(lnr-maxlines, firstline))
        key "repeat_K_PAGEDOWN" action SetScreenVariable("lnr", min(lnr+maxlines, lastline))

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if editor.files_changed:
                textbutton _("Apply") action Function(editor.patch_rpy_files)
                textbutton _("Undo Changes") action Function(editor.undo)
            textbutton _("Screenshot") action Function(renpy.screenshot, '/tmp/ed.png')
            textbutton _("Cancel") action Return()

screen edit():
    frame:
        default lnr = None
        default fname = None
        xpadding 10
        ypadding 10
        xpos 200
        background "#272822"

        # TODO: only draw cursor and remove this:
        #default=' ' * len(editor.line)
        add Input(default=editor.line, changed=editor.update_lines, ypos=editor.get_cursor_pos(), style=style.editor)

        if len(editor.fl[editor.fname]) > 1:
            text editor.context_lines() id "lines" style "editor" ypos editor.menuheight

        key "K_RETURN" action Return("K_RETURN")

        key "K_UP" action Function(editor.change_context, add=-1)
        key "K_DOWN" action Function(editor.change_context, add=1)

        key "ctrl_K_HOME" action Function(editor.change_context, add=-(1 << 24))
        key "ctrl_K_END" action Function(editor.change_context, add=1 << 24)

        key "K_PAGEUP" action Function(editor.change_context, add=-editor.maxlines)
        key "K_PAGEDOWN" action Function(editor.change_context, add=editor.maxlines)

        key "repeat_K_UP" action Function(editor.change_context, add=-1)
        key "repeat_K_DOWN" action Function(editor.change_context, add=+1)

        key "repeat_K_PAGEUP" action Function(editor.change_context, add=-editor.maxlines)
        key "repeat_K_PAGEDOWN" action Function(editor.change_context, add=editor.maxlines)

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if editor.files_changed:
                textbutton _("Apply") action Function(editor.patch_rpy_files)
                textbutton _("Undo Changes") action Function(editor.undo)
            textbutton _("Open file") action ShowMenu('openfile')
            textbutton _("External editor") action Function(editor.external_editor)
            textbutton _("Screenshot") action Function(renpy.screenshot, '/tmp/ed.png')
            textbutton _("Cancel") action Return()
