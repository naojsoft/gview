About
-----

gview is a simple and flexible astronomical FITS viewer modeled after
the older ZVIEW viewer used for some optical instruments at Subaru Telescope
in Hawaii.  The viewer uses the ginga scientific imaging python toolkit
created and maintained by software engineers at Subaru Telescope, National
Astronomical Observatory of Japan.

gview is licensed under a 3-clause BSD license (see LICENSE.txt).

Installation
------------

gview depends on ginga, which is a pure python package.  ginga, in turn,
depends on several scientific python libraries.

Installation is the standard:

$ python setup.py install [options]

Starting
--------

Start up the viewer with 

$ gview 

Optionally, you can create a log to troubleshoot, if necessary:

$ gview --loglevel=20 --stderr --log=/tmp/gview.log

Other options can be seen with the help:

$ gview --help

Usage
-----

Type commands into the command box; the output is shown in the running
history box below that.

The basic idea behind the viewer is that you have buffers and viewers,
and they are named.

Help
----

help [cmd]
  - get a general help message or specific help for a command

