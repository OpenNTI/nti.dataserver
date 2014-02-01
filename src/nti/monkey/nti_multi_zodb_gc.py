#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A hack to help us ensure that we are loading and monkey-patching
the desired parts of multi-zodb-gc before it gets started. This is needed
in general, not just with RelStorage.

.. note:: You should have the MySQL-python driver installed; the
	umysqldb patch may be unreliable at scale. See that
	patch for details.

Note that we cannot use pypy; :mod:`zc.zodbgc` uses ``Unpickler.unload()``,
which seems to be found only in cPython2 implementations. Even using the new
:mod:`zodbpickle` package as we do still has problems, noload being implemented
only in the C extension (which may or may not compile).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_timestamp_repr_patch_on_import
from nti.monkey import relstorage_zlibstorage_patch_on_import
from nti.monkey import relstorage_external_gc_patch_on_import
from nti.monkey import relstorage_explicitly_close_memcache_patch_on_import


relstorage_timestamp_repr_patch_on_import.patch()
relstorage_zlibstorage_patch_on_import.patch()
relstorage_external_gc_patch_on_import.patch()
relstorage_explicitly_close_memcache_patch_on_import.patch()

try:
	import MySQLdb
except ImportError:
	# This may or may not work.
	from nti.monkey import relstorage_umysqldb_patch_on_import
	relstorage_umysqldb_patch_on_import.patch()

logger = __import__('logging').getLogger(__name__)


# zc.zodbdgc 0.6.1 on Python 2.7 runs into an issue with
# the `noload` operation of the unpickler being broken. Specifically,
# when `persistent_load` is used together with `noload` to find references,
# multi-database references are never found. Each multi-database
# reference is reported as an empty list. It seems that `noload` does not
# look inside the "binary persistent ids" that make up multi-database refernces
# (possibly because they are objects, unlike the normal tuples?). An earlier
# version of this patch simply ignored the empty lists (which
# otherwise lead to an IndexError), but that breaks
# multi-db references. Instead, we must actually use the `load` operation,
# not the noload operation. This slows things down, and requires
# that there are no broken class references?


# See ZODB.serialize for a description of the possible ref types:
# ZODB persistent references are of the form::
# oid
# 	A simple object reference.
# (oid, class meta data)
# 	A persistent object reference
# [reference_type, args]
# 	An extended reference
# 	Extension references come in a number of subforms, based on the
# 	reference types.
# 	The following reference types are defined:
# 	'w'
# 		Persistent weak reference.	The arguments consist of an oid
# 		and optionally a database name.
# 	'n'
# 		Multi-database simple object reference.	 The arguments consist
# 		of a database name, and an object id.
# 	'm'
# 		Multi-database persistent object reference.	 The arguments consist
# 		of a database name, an object id, and class meta data.
# The following legacy format is also supported.
# [oid]
# 	A persistent weak reference

from zodbpickle.fastpickle import Unpickler
from cStringIO import StringIO

def getrefs(p, storage_name, ignore):
	"Return a sequence of (db_name, oid) pairs"
	refs = []
	u = Unpickler(StringIO(p))
	u.persistent_load = refs # Just append to this list
	b1 = u.noload() # Once for the class/type reference
	try:
		b2 = u.load() # again for the state
	except ImportError:
		# we couldn't access this object anyway, so any
		# references it held are no good
		logger.debug("Failed to load state for an object in %s", storage_name, exc_info=True)
	for ref in refs:
		if isinstance(ref, tuple):
			# (oid, class meta data)
			yield storage_name, ref[0]
		elif isinstance(ref, bytes):
			# oid
			yield storage_name, ref
		elif not ref:
			print("Empty reference?", ref, refs, b1, b2)
			raise ValueError("Unexpected empty reference")
		elif ref:
			assert isinstance(ref, list)
			# [reference type, args] or [oid]
			if len(ref) == 1:
				print("Legacy persistent weak ref")
				yield storage_name, ref
				continue

			# Args is always a tuple, but depending on
			# the value of the reference type, the order
			# may be different. Types n and m are in the right
			# order, type w is different
			kind, ref = ref

			if kind in (b'n', b'm'):
				if ref[0] not in ignore:
					yield ref[:2]
			elif kind == b'w':
				if len(ref) == 1: # oid in this db
					yield storage_name, ref[0]
				elif len(ref) == 2: # oid in other db
					yield ref[1], ref[0]
				else:
					raise ValueError('Unknown weak ref type', ref)
			else:
				raise ValueError('Unknown persistent ref', kind, ref)


def configure():
	"""
	Some pickles in the wild (notably ACLs) need ZCA to be set up
	in order to successfully load. The result of failing to do this
	is a TypeError.
	"""

	from zope.component.hooks import setHooks
	setHooks()
	from nti.dataserver.utils import _configure
	_configure(set_up_packages=('nti.dataserver',))

def fixrefs():
	import zc.zodbdgc
	zc.zodbdgc.getrefs = getrefs
	configure()

import sys

from pkg_resources import load_entry_point

def main():
	fixrefs()

	# Not a threaded process, no need to check for switches
	sys.setcheckinterval( 100000 )

	sys.exit(
		load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-gc')()
	)

if __name__ == '__main__':
	main()
