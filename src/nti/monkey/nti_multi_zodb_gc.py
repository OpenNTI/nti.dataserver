#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of multi-zodb-gc before it gets started. Needed
with relstorage.

.. note:: You must have the MySQL-python driver installed, as we
	cannot monkey patch to use umysqldb due to errors. See
	that patch for details.

.. note:: Until such time as either the developers or we implement
	a ``deleteObject`` method for RelStorage, this process is only
	good for analyzing RelStorage into a separate analysis database.
	It cannot perform actual GC.

.. note:: History-free RelStorages do not require regular packing,
	but they do require regular garbage collection. This can be
	done only when ``pack-gc`` is set to ``true``, and, because
	this script cannot be used to perform GC, only in a single database
	at a time with ``zodbpack`` (NEVER in a multi-database).
	(zodbpack could be used to pack history-preserving storages that are
	part of a multi-database; they *must* have ``pack-gc`` set to false.)

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
from nti.monkey import relstorage_external_gc_patch_on_import

relstorage_timestamp_repr_patch_on_import.patch()
relstorage_zlibstorage_patch_on_import.patch()
relstorage_external_gc_patch_on_import.patch()

# zc.zodbdgc 0.6.1 has an issue dealing with new refs
# that are empty. This copy of its function
# fixes that and avoids an IndexError on line 287
import cPickle
import cStringIO
def getrefs(p, rname, ignore):
	refs = []
	u = cPickle.Unpickler(cStringIO.StringIO(p))
	u.persistent_load = refs
	u.noload()
	u.noload()
	for ref in refs:
		if isinstance(ref, tuple):
			yield rname, ref[0]
		elif isinstance(ref, str):
			yield rname, ref
		elif ref:
			assert isinstance(ref, list)
			ref = ref[1]
			if ref[0] not in ignore:
				yield ref[:2]
import zc.zodbdgc
zc.zodbdgc.getrefs = getrefs

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
