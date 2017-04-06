#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Spawn a xterm window that displays realtime debug values.

With this script accessible from your to-be-debugged program: create an
instance of XTBug class. This creates a pipe to write to, and launches
a subprocess that runs this same program as a script inside a separate xterm
window. The subprocess reads from the previously created pipe and displays
any values sent to it by calling the previously created instance from within
the debugged program.

LICENSE & COPYRIGHT
-----
   Copyright (c) 2017 @MrMattBusby
       All rights reserved
        Licensed LGPL-v3.0
See LICENSE for a copy of the license

USAGE
-----
    import time
    try:
        from xtbug import XTBug
        DEBUG1 = XTBug()            # Creates pipe, spawns XTerm window
        DEBUG2 = XTBug()            # 2nd window example
        DEBUG3 = XTBug()            # 3rd window example
    except ImportError:
        DEBUG1 = lambda x: None
        DEBUG2 = lambda x: None
        DEBUG3 = lambda x: True
    def fn():
        a = 1
        b = 1
        while DEBUG3:               # Debug everything vars(), returns True
            a += 1
            b += a*2
            DEBUG1()                    # Debug everything
            DEBUG2(locals(), 'a', 'b')  # Debug a list of variables
            time.sleep(0.01)            # Needs to sleep some...
    fn()

TODO
-----
- Use threads, as option

"""
from __future__ import print_function

import os as _os
import sys as _sys
import time as _time
import subprocess as _subprocess
import pprint as _pprint
import curses as _curses
import inspect as _inspect
try:
    import cPickle as _pickle
except ImportError:
    import pickle as _pickle

_PIPE = '/tmp/xtbug{0}.pipe'
_KEEP_XTERM_OPEN = True  # Set true to see any tracebacks or program-end info


class XTBug(object):
    """Instanciated from the debugging program's side."""

    _count = 0

    def __init__(self, fg='white',
                 bg='blue',
                 w=120,
                 h=60,
                 hold=_KEEP_XTERM_OPEN):

        self._mycount = XTBug._count
        XTBug._count += 1
        self._pipe = _PIPE.format(self._mycount)

        try:
            _os.mkfifo(self._pipe)
        except OSError:
            _os.remove(self._pipe)
            _os.mkfifo(self._pipe)

        _time.sleep(0.05)

        # Open new xterm running debugger in a separate process
        options = [
            'xterm',
            '+sb',
            '{0}hold'.format(('+', '-')[hold]),
            '+aw',
            '-geometry', 'x'.join([str(w), str(h)]),
            '-bg', bg,
            '-fg', fg,
            '-T', self._pipe,
            '+ah',
            '+bc',
            '-cr', 'black',
            '-uc',
            '-e', 'python', './xtbug.py', '_xterm_win', str(self._mycount)]
        self._subp = _subprocess.Popen(options, shell=False)

        _time.sleep(0.5)

        # Non-blocking named pipe
        self.sout = _os.open(self._pipe, _os.O_RDWR | _os.O_NONBLOCK)

    def __bool__(self):
        return self.__nonzero__()

    def __nonzero__(self):
        self.__call__(_inspect.getargvalues(
            _inspect.currentframe().f_back)[-1])
        return True

    def __call__(self, variables=None, *args):
        # Send a pickle via named pipe
        if variables is None:
            variables = _inspect.getargvalues(
                _inspect.currentframe().f_back)[-1]
        if args:
            dic = {}
            for each in args:
                try:
                    dic[each] = variables.pop(each)
                except KeyError:
                    continue
            variables = dic
        try:
            _os.write(self.sout, _pickle.dumps(
                sorted([(str(k), _pprint.pformat(v)) for (k, v) in
                        list(variables.items())])))
        except OSError:
            pass  # Resource temp unavail

    def __del__(self):
        _os.close(self.sout)


def _xterm_win():
    """Debug window launched inside xterm."""
    pipe = _PIPE.format(_sys.argv[2])
    sin = open(pipe, 'r')  # Blocking

    def main(scr):
        """Run inside a curses wrapper."""
        _curses.use_default_colors()
        _curses.noecho()
        _curses.cbreak()
        _curses.curs_set(0)
        _curses.delay_output(0)
        outprev = ''
        while True:
            out = ''
            fmt = "{0:30}{1}\n"
            for each in _pickle.load(sin):
                name, val = each
                name = '{0} {1} '.format(
                    name[:29], '.' * (28 - len(name[:29])))
                out += fmt.format(name, val)
            if out and out != outprev:
                scr.clear()
                try:
                    scr.addstr(0, 0, out)
                except _curses.error:
                    scr.addstr(0, 0, "Error: Output line too long?")
                outprev = out
                scr.refresh()
    try:
        _curses.wrapper(main)
    except EOFError:
        pass  # Debugged program was exited
    except KeyboardInterrupt:
        pass
    finally:
        sin.close()
        _os.remove(pipe)
    if _KEEP_XTERM_OPEN:
        print("Exited! Please close this window...")


def _demo():
    """Run demo if no other arguments are provided."""
    debug1 = XTBug()
    debug2 = XTBug()
    debug3 = XTBug()
    aaa = 1
    bbb = 1
    while debug3:
        aaa += 1
        bbb += aaa * 2
        debug1()
        debug2(locals(), 'aaa', 'bbb')
        _time.sleep(0.01)

if __name__ == "__main__":
    if len(_sys.argv) > 1 and _sys.argv[1] in ('-h', '--help'):
        print(__doc__)
    elif len(_sys.argv) > 1:
        _xterm_win()
    else:
        _demo()
