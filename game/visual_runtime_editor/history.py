""" history management for editor """
from operator import itemgetter


class History(object):
    # pylint: disable=
    """ keep track of history for editor """
    def __init__(self, past=None):
        self.past = past or [{"sbc": {"lnr": None, "cx": None, "cy": None}}]
        self.rewrite = True  # disable this while undoing / redoing
        self.at = -1
        self.changed = True

    def update_cursor(self, editor, force):
        """ add new history entry, unless part of a combined edit action """
        if len(self.past[len(self.past) - 1]) != 1:
            if self.rewrite:
                del self.past[(self.at+1):]

            self.past.append({})
        last = self.past[len(self.past) - 1]
        if force or len(last) == 0 or last["sbc"]["cx"] is None:
            self.past[len(self.past) - 1]["sbc"] = editor.view.coords

    def append(self, func_ndx_key, args):
        """ appends to history. also past populates this, to allow redo """
        front = len(self.past) - 2

        if self.rewrite and (self.at == -1 or self.at < front or (self.at == front)):
            self.at += 1
            del self.past[(self.at+1):]
            if len(self.past[self.at]) > 1:
                self.past[self.at] = {"sbc": self.past[self.at-1]["sbc"]}
        elif self.at == len(self.past):
            self.past.append({"sbc": self.past[self.at-1]["sbc"]})

        if func_ndx_key not in self.past[self.at]:
            self.past[self.at][func_ndx_key] = args
        self.changed = True

    def undo_redo_helper(self, view):
        action = self.past[self.at]
        self.past[self.at] = {"sbc": view.coords}
        self.rewrite = False
        for (func, kwargs) in sorted(action.items(), key=itemgetter(0)):
            if func == "sbc":
                view.console.sbc(**kwargs)
            else:
                getattr(view.data, func[0])(func[1], *kwargs)
        self.rewrite = True
        view.parse()

    def undo(self, view):
        if self.at >= 0:
            if self.at == len(self.past):
                self.at -= 1
            if self.at != 0 and len(self.past[self.at]) == 1:
                self.at -= 1
            elif self.at == len(self.past) - 1:
                self.past.append({"sbc": view.coords})
            self.undo_redo_helper(view)
            self.at -= 1

    def redo(self, view):
        if self.at < len(self.past) - 1:
            self.at += 1
            self.undo_redo_helper(view)
            if self.at == len(self.past) - 1 and len(self.past[self.at]) == 1:
                self.at += 1
