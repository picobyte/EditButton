init -100 python:
    import os
    import sys
    import logging

    # absolute path to the game directory, which is formatted according
    # to the conventions of the local OS
    gamedir = os.path.normpath(config.gamedir)

    # required to make the above work with with RenPy:
    config.reject_backslash = False

    # setting the window on center
    # useful if game is launched in the window mode
    os.environ['SDL_VIDEO_CENTERED'] = '1'

    sys.setdefaultencoding('utf-8')

    # Game may bug out on saving, in such case, comment should be removed
    # config.use_cpickle = False


    # enable logging via the 'logging' module
    format='%(levelname)-8s%(message)s'
    logging.basicConfig(level=logging.DEBUG, format=format)
    devlog = logging.getLogger(" ".join([config.name, config.version]))
    devlogfile = logging.FileHandler(os.path.join(gamedir, "devlog.txt"))
    devlogfile.setLevel(logging.DEBUG)
    devlog.addHandler(devlogfile)
    devlog.critical("\n--- launch ---")
    fm = logging.Formatter(format)
    devlogfile.setFormatter(fm)
    del fm
    devlog.info("Game directory: %s" % gamedir)

    devlog = logging.getLogger(" ".join([config.name, config.version]))
    _editor.devlog = devlog

