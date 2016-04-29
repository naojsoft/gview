#
# main.py -- configuration for running gview
#
# Eric Jeschke (eric@naoj.org)
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys

from ginga.misc import log

from gview import GView
import ginga.toolkit as ginga_toolkit


def main(options, args):

    logger = log.get_logger("gview", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    from ginga.gw import Widgets

    app = Widgets.Application(logger=logger)

    gv = GView.GView(logger, app)
    #app.add_callback('shutdown', gv.quit)

    i = 0
    for arg in args:
        name = 'gview_%d' % i
        viewer = gv.zv.make_viewer(name)
        viewer.load_file(args[i])
        i += 1

    try:
        # TODO: unify these
        if hasattr(app, 'start'):
            app.start()

        else:
            while True:
                app.process_events()

    except KeyboardInterrupt:
        print("Terminating gview...")


def run_viewer(sys_argv):
    # Parse command line options
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                      default='qt',
                      help="Choose GUI toolkit (gtk|qt)")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")
    log.addlogopts(optprs)

    (options, args) = optprs.parse_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
