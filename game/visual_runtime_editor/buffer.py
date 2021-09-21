# -*- coding: utf-8 -*-
"""
    visual_runtime_editor.buffer
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A buffer, either read-only or read-write

"""

from os import linesep, write, close
from codecs import open as codecs_open
from shutil import move
from tempfile import mkstemp
from .history import History


class ReadOnlyBuffer(object):
    """ container and load interface for read only data """
    def __init__(self, fname):
        self.load(fname)

    def __getitem__(self, ndx):
        return self.data[ndx]

    def __len__(self):
        return len(self.data)

    def load(self, fname=None):
        """ load file into buffer """
        if fname is not None:
            self.fname = fname
        self.data = []
        with codecs_open(self.fname, encoding='utf-8') as lines:
            for line in lines:
                self.data.append(line.rstrip("\r\n"))


class ReadWriteBuffer(ReadOnlyBuffer):
    """ buffer that allows edit and save and maintains a history """
    def __init__(self, fname, past=None):
        super(ReadWriteBuffer, self).__init__(fname)
        self.history = History(past=past)
        self.start_change = 0

    @property
    def changed(self):
        """ whether file changed, since save: differs from undo """
        return len(self.history.past) != self.start_change

    def __setitem__(self, ndx, value):
        if value != self.data[ndx]:
            self.history.append(("__setitem__", ndx), [self.data[ndx]])
            self.data[ndx] = value

    def load(self, fname=None, past=None):
        super(ReadWriteBuffer, self).load(fname)
        self.history = History(past or [{"sbc": {"lnr": None, "cx": None, "cy": None}}])

    def save(self):
        """ save file """
        if self.changed:
            file_handle, abs_path = mkstemp()
            for line in self.data:
                write(file_handle, line + linesep)
            close(file_handle)
            move(abs_path, self.fname)
            self.start_change = len(self.history.past)

    def __delitem__(self, ndx):
        if isinstance(ndx, slice):
            k = ("insert", (ndx.start, ndx.stop))
        else:
            k = ("insert", ndx)
        ndx = slice(*ndx) if isinstance(ndx, tuple) else ndx
        self.history.append(k, [self.data[ndx]])
        del self.data[ndx]

    def insert(self, ndx, value):
        """ insert into buffer """
        self.history.append(("__delitem__", ndx), [])
        if isinstance(ndx, tuple):
            # FIXME: this counterintuitive tuple insert is used in undo/redo
            self.data[ndx[0]:ndx[0]] = value
        else:
            self.data.insert(ndx, value)
