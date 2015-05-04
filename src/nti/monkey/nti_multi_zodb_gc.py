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

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from . import relstorage_patch_all_except_gevent_on_import

relstorage_patch_all_except_gevent_on_import.patch()

from . import python_persistent_bugs_patch_on_import
python_persistent_bugs_patch_on_import.patch()

logger = __import__('logging').getLogger(__name__)

# zc.zodbdgc 0.6.1 on Python 2.7+ runs into an issue with
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
# that we have a broken object factory and some other tweaks to be sure
# that we can actually load all the data.
# See
# https://mail.zope.org/pipermail/zodb-dev/2014-January/015168.html
# https://mail.zope.org/pipermail/zodb-dev/2014-January/015165.html
# http://bugs.python.org/issue1101399
# http://hg.python.org/releasing/2.7.6/rev/d0f005e6fadd
# https://github.com/zopefoundation/zodbpickle/issues/9

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

# XXX: This is fixed in https://github.com/zopefoundation/zc.zodbdgc/pull/1.
# We should just switch to that branch everywhere.

try:
	from zodbpickle.fastpickle import Unpickler
except ImportError: # PyPy?
	from cPickle import Unpickler

from cStringIO import StringIO

_has_noload = True
try:
	Unpickler(StringIO(b'')).noload
except AttributeError:
	_has_noload = False

_all_missed_classes = set()

from zope.app.broken.broken import Broken
import ZODB.broken

def _make_find_global():
	Broken_ = Broken # make it local for speed
	_find_global = ZODB.broken.find_global

	def type_(name, bases, tdict):
		logger.warn("Broken class reference to %s", tdict['__module__'] + '.' + name)
		_all_missed_classes.add(tdict['__module__'] + '.' + name)
		cls = type(name, bases, tdict)
		return cls

	def _the_find_global(modulename, globalname):
		return _find_global(modulename, globalname, Broken_, type_)

	return _the_find_global

find_global = _make_find_global()

def getrefs(p, storage_name, ignore):
	"Return a sequence of (db_name, oid) pairs"
	refs = []
	u = Unpickler(StringIO(p))
	u.persistent_load = refs # Just append to this list
	u.find_global = find_global
	if _has_noload:
		b1 = u.noload() # Once for the class/type reference
	else:
		# if we don't have noload, we also probably don't support the
		# optimized case of appending to the list, so we
		# need to give it a callable
		u.persistent_load = refs.append
		# PyPy calls find_global 'find_class'; is that not a standard
		# attribute?
		u.find_class = find_global
		b1 = u.load()
	try:
		b2 = u.load() # again for the state
	except AttributeError as e:
		if e.message != "'DATETIME' object has no attribute 'numtype'":
			# Ancient whoosh error
			raise

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

import zope.interface.declarations
def Provides(*interfaces):
	"""
	Due to a bug in nti.mimetype, some very old objects
	may have invalid values for __provides__. We fix this
	by ignoring them, since the only contain class objects
	"""
	return zope.interface.declarations.ProvidesClass(interfaces[0])

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


	# Similarly, some pickles to site components exist in the database
	# but we don't want to actually try to load all the sites, so replace
	# the component lookup with simply returning a new registry
	# (they pickle as a call to the global function BC with args (parent, name))
	# which is what the constructor takes
	import z3c.baseregistry.baseregistry
	z3c.baseregistry.baseregistry.BC = z3c.baseregistry.baseregistry.BaseComponents

	# Some pickles may also refer to a library
	from zope import component
	from nti.contentlibrary.library import EmptyLibrary
	from nti.contentlibrary.interfaces import IContentPackageLibrary
	component.provideUtility(EmptyLibrary(), IContentPackageLibrary)

def fixrefs():
	import zc.zodbdgc
	zc.zodbdgc.getrefs = getrefs
	configure()
	# Only *after* we're configured
	zope.interface.declarations.Provides = Provides

def report():
	if _all_missed_classes:
		logger.warn("The following classes are missing: %s", _all_missed_classes)


import sys

from pkg_resources import load_entry_point

def main():
	fixrefs()

	# Not a threaded process, no need to check for switches
	sys.setcheckinterval( 100000 )
	try:
		ec = load_entry_point('zc.zodbdgc', 'console_scripts', 'multi-zodb-gc')()
	finally:
		report()
	sys.exit(ec)


if __name__ == '__main__':
	main()
