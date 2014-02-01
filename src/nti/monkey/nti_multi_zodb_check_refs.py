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

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


from nti.monkey import gevent_patch_on_import
from nti.monkey import relstorage_timestamp_repr_patch_on_import
from nti.monkey import relstorage_zlibstorage_patch_on_import
from nti.monkey import relstorage_explicitly_close_memcache_patch_on_import

gevent_patch_on_import.patch()
relstorage_timestamp_repr_patch_on_import.patch()
relstorage_zlibstorage_patch_on_import.patch()
relstorage_explicitly_close_memcache_patch_on_import.patch()

try:
	import MySQLdb
except ImportError:
	# This may or may not work.
	from nti.monkey import relstorage_umysqldb_patch_on_import
	relstorage_umysqldb_patch_on_import.patch()

# See extensive comments.
from nti.monkey.nti_multi_zodb_gc import fixrefs
import sys
from pkg_resources import load_entry_point

def main():
	fixrefs()
	sys.exit(
		load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-check-refs')()
	)

if __name__ == '__main__':
	main()
