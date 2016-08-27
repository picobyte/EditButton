init python:
    import os
    import re
    import shutil

    from tempfile import mkstemp
    import math
    has_renpyformatter = True
    edit_line_color = "#fff"

    try:
        from pygments import highlight
        from renpy_lexer import RenPyLexer
        from renpyformatter import RenPyFormatter
        from pygments.styles import get_style_by_name
    except ImportError:
        has_renpyformatter = False


    class Patch(object):
        maxlines = 24
        lnr = 0
        fname = ""
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
            return min(self.maxlines, self.lnr - 1) * (style.default.size + 6)

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
        def recode_rpy_files(self):
            self.files_changed = False
            for filename, lines in self.fl.iteritems():
                if lines[0]:
                    fh, abs_path = mkstemp()

                    for linenr in range(1, len(lines)):
                        os.write(fh, lines[linenr]+os.linesep)

                    os.close(fh)
                    shutil.move(abs_path, os.path.join(renpy.config.basedir, filename))
                    lines[0] = False # changes applied

        def update_dialogue(self, what):

            if self.updated_context():
                # adapt `what' if already changed this session.
                matched = re.match(r'^[^"\'#]*("(?:[^"]*|\\.)"|\'(?:[^\']+?|\\.)\').*$', self.line)

            return matched.group(1)[1:-1] if matched else what

        def change_context(self, add):

            # if at end of input and we move, rather than inserting a line, edit one elsewhere.
            prompt = renpy.get_widget("edit", "prompt")
            if prompt and "(End of dialogue)" in prompt.text:
                del self.fl[self.fname][self.lnr]
                prompt.set_text("")

            self.lnr = max(1, min(self.lnr + add, len(self.fl[self.fname]) - 1))

        def external_editor(self, transient=1):
            renpy.exports.launch_editor([self.fname], self.lnr, transient=transient)

        def update_lines(self, update):
            lns = renpy.get_widget("edit", "lines")
            #if ed and lns:
            self.fl[self.fname][self.lnr] = update + os.linesep
            lns.set_text(self.context_lines())

        # FIXME: edit button behaviour is a bit odd. also darker than rest?
        def end_of_dialogue(self):
            if self.updated_context():
                m = re.match("^(\s+)", self.line)
                if m:
                    self.fl[self.fname].insert(self.lnr, m.group(1))
                    renpy.call_screen("edit")

image my_img:

screen edit():
    window:
        style "nvl_window"

        xpos gui.text_xpos

        # TODO: only draw cursor and remove this:
        add Input(default=patch.line, style="default", changed=patch.update_lines, ypos=patch.get_cursor_pos(), color="#000")

        if len(patch.fl[patch.fname]) > 1:
            text patch.context_lines() id "lines" style "default" ypos 0

        key "K_RETURN" action Return("K_RETURN")

        key "K_UP" action Function(patch.change_context, add=-1)
        key "K_DOWN" action Function(patch.change_context, add=1)

        key "ctrl_K_HOME" action Function(patch.change_context, add=-(1 << 24))
        key "ctrl_K_END" action Function(patch.change_context, add=1 << 24)

        key "K_PAGEUP" action Function(patch.change_context, add=-patch.maxlines)
        key "K_PAGEDOWN" action Function(patch.change_context, add=patch.maxlines)

        key "repeat_K_UP" action Function(patch.change_context, add=-1)
        key "repeat_K_DOWN" action Function(patch.change_context, add=+1)

        key "repeat_K_PAGEUP" action Function(patch.change_context, add=-patch.maxlines)
        key "repeat_K_PAGEDOWN" action Function(patch.change_context, add=patch.maxlines)

        hbox:
            style_prefix "quick"

            xalign 0.5
            yalign 1.0
            if patch.files_changed:
                textbutton _("Apply") action Function(patch.recode_rpy_files)
                textbutton _("Undo Changes") action Function(patch.undo)
            textbutton _("External editor") action Function(patch.external_editor)
            textbutton _("Screenshot") action Function(renpy.screenshot, '/tmp/ed.png')
            textbutton _("Cancel") action Return()
