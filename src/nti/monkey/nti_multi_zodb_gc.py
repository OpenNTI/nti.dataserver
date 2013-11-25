#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of multi-zodb-gc before it gets started. Needed
with relstorage.

.. note:: You must have the MySQL-python driver installed, as we
	cannot monkey patch to use umysqldb due to errors. See
	that patch for details.

Note that we cannot use pypy; :mod:`zc.zodbgc` uses ``Unpickler.unload()``,
which seems to be found only in cPython2 implementations. We would have to
replace its dependency on that with the new :mod:`zodbpickle` package (and
even then its not clear this would work; it seems that noload is only
available in the C code, not the python version).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_timestamp_repr_patch_on_import
from nti.monkey import relstorage_zlibstorage_patch_on_import

relstorage_timestamp_repr_patch_on_import.patch()
relstorage_zlibstorage_patch_on_import.patch()

import sys
# Not a threaded process, no need to check for switches
sys.setcheckinterval( 100000 )

from pkg_resources import load_entry_point

def main():
	sys.exit(
		load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-gc')()
	)

if __name__ == '__main__':
	main()
