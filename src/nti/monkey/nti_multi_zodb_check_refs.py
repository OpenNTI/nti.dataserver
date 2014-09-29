#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of multi-zodb-check-refs before it gets started. Needed
with relstorage.

.. note:: You must have the MySQL-python driver installed, as we
	cannot monkey patch to use umysqldb due to errors. See
	that patch for details.

Note that we cannot use pypy; :mod:`zc.zodbgc` uses ``Unpickler.unload()``,
which seems to be found only in cPython2 implementations. We would have to
replace its dependency on that with the new :mod:`zodbpickle` package (and
even then its not clear this would work; it seems that noload is only
available in the C code, not the python version).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

from . import python_persistent_bugs_patch_on_import
python_persistent_bugs_patch_on_import.patch()

# See extensive comments.
from nti.monkey.nti_multi_zodb_gc import report
from nti.monkey.nti_multi_zodb_gc import fixrefs

import sys
from pkg_resources import load_entry_point

def main():
	fixrefs()
	try:
		ec = load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-check-refs')()
	finally:
		report()
	sys.exit(ec)

if __name__ == '__main__':
	main()
