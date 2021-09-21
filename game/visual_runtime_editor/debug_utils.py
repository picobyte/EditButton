"PyLint, silence"


class LogIterable(object):
    """ Iterable that logs changes """
    def __init__(self, logger, iter_type, contained=None):
        self.logger = logger
        self.last = None
        self.contained = iter_type(contained)
        for func in dir(iter_type):
            if func not in dir(LogIterable):
                setattr(self, func, getattr(self.contained, func))

    def __getitem__(self, key):
        self.last = str(key)
        return self.contained[key]

    def __setitem__(self, key, vslue):
        self.logger.info("["+str(key)+"] = "+str(key))
        self.contained.__setitem__(key, self.get_logger(key))

    def __delitem__(self, key):
        self.logger.info(".__delitem__("+str(key)+")")
        self.contained.__delitem__(key)

    def append(self, value):
        """ logging append """
        self.logger.info(".append("+str(value)+")")
        self.contained.append(self.get_logger(value))

    def __repr__(self):
        return repr(self.contained)

    def __len__(self):
        return len(self.contained)

    def clear(self):
        "PyLint, silence"
        return self.contained.clear()

    def copy(self):
        "PyLint, silence"
        return self.contained.copy()

    def has_key(self, key):
        "PyLint, silence"
        return key in self.contained

    def update(self, *args, **kwargs):
        "PyLint, silence"
        return self.contained.update(*args, **kwargs)

    def keys(self):
        "PyLint, silence"
        return self.contained.keys()

    def values(self):
        "PyLint, silence"
        return self.contained.values()

    def items(self):
        "PyLint, silence"
        return self.contained.items()

    def pop(self, *args):
        "PyLint, silence"
        return self.contained.pop(*args)

    def __cmp__(self, dict_):
        "PyLint, silence"
        return self.contained.__cmp__(dict_)

    def __contains__(self, item):
        return item in self.contained

    def __iter__(self):
        return iter(self.contained)

    def info(self, message):
        "PyLint, silence"
        self.logger.info("["+self.last+"]"+message)

    def get_logger(self, value):
        "PyLint, silence"
        if isinstance(value, dict):
            return LogDict(logger=self, dct=value)
        if isinstance(value, list):
            return LogList(logger=self, lst=value)
        return value


class LogDict(LogIterable):
    """ dict that logs changes """
    def __init__(self, logger=None, dct=None):
        super(LogDict, self).__init__(logger, dict, dct)


class LogList(LogIterable):
    """ list that logs changes """
    def __init__(self, logger=None, lst=None):
        super(LogList, self).__init__(logger, list, lst)
