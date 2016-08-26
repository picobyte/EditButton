init python:
    import os
    import re
    import shutil

    from tempfile import mkstemp
    has_renpyformatter = True
    edit_line_color = "#777"

    try:
        from pygments import highlight
        from pygments.lexers.python import PythonLexer
        from renpyformatter import RenPyFormatter
    except ImportError:
        has_renpyformatter = False
        edit_line_color = "#fff"


    class Patch(object):
        before = 12
        after = 12
        def __init__(self):
            self.undo()

        def undo(self):
            self._fl = {}
            self.files_changed = False
            self.updated_context()

        @property
        def line(self):
            return self._fl[self.fname][self.lnr]

        def linedisplay(self, i=None):
            if not i:
                i = self.lnr
            line = self._fl[self.fname][i]
            if i != self.lnr:
                if has_renpyformatter:
                    line = highlight(line, PythonLexer(), RenPyFormatter()).rstrip('\r\n')
                else:
                    line = ("{alpha=-%.2f}" % min(0.8, 0.07 * abs(i-self.lnr))) + line + "{/alpha}"

            return (line, "edit"+str(i))

        def lines_before(self):
            return [self.linedisplay(i) for i in range(max(self.lnr - self.before, 1), self.lnr)]

        def lines_after(self):
            mx = min(self.lnr + self.after + self.before - min(self.before, self.lnr - 1), len(self._fl[self.fname]))
            return [self.linedisplay(i) for i in range(self.lnr + 1, mx)]

        ## the current file & linenr is returned as list
        def updated_context(self):

            ctxt = renpy.get_filename_line()
            if not ctxt[0]: # indicates failure
                return False

            (self.fname, self.lnr) = ctxt

            if not self.fname in self._fl:

                self._fl[self.fname] = [False]
                with open(os.path.join(renpy.config.basedir, self.fname)) as fh:

                    for line in fh:
                        self._fl[self.fname].append(line.rstrip('\r\n'))
            return True

        ## apply a modification to a displayed phrase, in cache until applied.
        def recode(self):

            ed = renpy.get_widget("edit", "Edit")
            if ed.default != ed.content:

                self.files_changed = self._fl[self.fname][0] = True # 0th marks changed
                self._fl[self.fname][self.lnr] = ed.content

        ## apply changes to phrases to the .rpy file(s)
        def recode_rpy_files(self):
            self.files_changed = False
            for filename, lines in self._fl.iteritems():
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

            self.recode()
            # if at end of input and we move, rather than inserting a line, edit one elsewhere.
            prompt = renpy.get_widget("edit", "prompt")
            if prompt and "(End of dialogue)" in prompt.text:
                del self._fl[self.fname][self.lnr]
                prompt.set_text("")

            self.lnr = max(1, min(self.lnr + add, len(self._fl[self.fname]) - 1))

            ed = renpy.get_widget("edit", "Edit")
            ed.default = self.line
            ed.update_text(self.line, True)

        def external_editor(self, transient=1):
            renpy.exports.launch_editor([self.fname], self.lnr, transient=transient)

        # FIXME: edit button behaviour is a bit odd. also darker than rest?
        def end_of_dialogue(self):
            if self.updated_context():
                m = re.match("^(\s+)", self.line)
                if m:
                    self._fl[self.fname].insert(self.lnr, m.group(1))
                    renpy.call_screen("edit", prompt="(End of dialogue)")


screen edit(prompt=None):
    style_prefix "input"

    window:
        style "nvl_window"

        vbox:
            ypos 0
            xpos gui.text_xpos
            xanchor gui.text_xalign
            #ypos gui.text_ypos

            if prompt:
                text prompt id "prompt" style "input_prompt"

            for line in patch.lines_before():
                text line[0] id line[1] style "default"

            input id "Edit" default patch.linedisplay()[0] style "default" color edit_line_color

            for line in patch.lines_after():
                text line[0] id line[1] style "default"

            key "K_RETURN" action [Function(patch.recode), Return("K_RETURN")]

            key "K_UP" action Function(patch.change_context, add=-1)
            key "K_DOWN" action Function(patch.change_context, add=1)

            key "K_HOME" action Function(patch.change_context, add=-(1 << 24))
            key "K_END" action Function(patch.change_context, add=1 << 24)

            key "K_PAGEUP" action Function(patch.change_context, add=-patch.before-patch.after)
            key "K_PAGEDOWN" action Function(patch.change_context, add=patch.before+patch.after)

            key "repeat_K_UP" action Function(patch.change_context, add=-1)
            key "repeat_K_DOWN" action Function(patch.change_context, add=+1)

            key "repeat_K_PAGEUP" action Function(patch.change_context, add=-patch.before-patch.after)
            key "repeat_K_PAGEDOWN" action Function(patch.change_context, add=patch.before+patch.after)

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
