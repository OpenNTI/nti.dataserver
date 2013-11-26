#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Originally from http://david.wglick.org/2009/visualizing-the-zodb-with-graphviz/
# heavily modified to support multi databases

from ZODB.utils import u64
import collections

def _node_name( oid, oiddbname ):
	return b'%s.%s' % (oiddbname, u64(oid))

def get_reference_dumper(refs, multi_refs, name_predicate):
	# This is a callback which will be called whenever a reference is found.
	filtered_oids = set()
	def dump_reference(oid, oiddbname, roid, rdbname, rclass):
		if name_predicate(rclass) and (oiddbname,oid) not in filtered_oids:
			refs.append( b'%s -> %s\n' % ( _node_name(oid, oiddbname), _node_name( roid, rdbname ) ) )
		else:
			filtered_oids.add( (rdbname, roid) )
		multi_refs[rdbname].add(roid)
		multi_refs[oiddbname].add(oid)
	return dump_reference

def export_databases(context, name_predicate=None):
	"""
	Walks a ZODB databases for everything reachable from ``context`` and dumps the object graph in graphviz .dot format.
	"""
	f = open('plone.dot', 'w')
	f.write(b'digraph plone {\n')
	refs = []
	def _refs():
		for ref in refs:
			f.write(ref)
		f.write(b'}\n')
		del refs[:]
	# database-name => oids referenced
	multi_refs = collections.defaultdict(set)
	done_oids = set()
	# First, the things from this database itself
	if name_predicate is None:
		name_predicate = id
	reference_callback = get_reference_dumper(refs, multi_refs, name_predicate)

	base_oid = context._p_oid
	conn = context._p_jar
	root_db_name = conn.db().database_name
	_export_database(f, conn, base_oid, reference_callback, name_predicate, done_oids)


	# Now, things referenced from other databases
	# Note that this gets just one level, some are potentially
	# missed (?)
	for db_name, oids in list(multi_refs.items()):
		if db_name == root_db_name:
			continue
		new_conn = conn.get_connection(db_name)
		for oid in list(oids):
			_export_database(f, new_conn, oid, reference_callback, name_predicate, done_oids)

	_refs()
	f.close()

def _export_database(f, conn, base_oid, reference_callback, name_predicate, done_oids):


	for conn_name, oid, p in _walk_database(conn,
											base_oid,
											reference_callback=reference_callback,
											name_predicate=name_predicate,
											done_oids=done_oids):
		# Walk to all the objects in the database and examine their references.
		# Whenever a reference is found, it will be recorded via the
		# reference_dumper.	 Whenever a new object is found, it will be yieled
		# to this loop.

		# Read the module and class from the pickle bytestream without actually
		# loading the object.
		module, klass = p.split(b'\n')[:2]
		module = module[1:]
		full_name = module + '.' + klass
		if name_predicate(full_name):
			f.write(b'%s [label="%s.%s"]\n' % (_node_name(oid, conn_name), module, klass))




def _walk_database(conn, root_oid, reference_callback=None, name_predicate=None, done_oids=None):
	conn_name = conn.db().database_name

	# oids is used to keep track of found oids that need to be visited.
	# done_oids is used to keep track of which oids have already been yielded.
	oids = [root_oid]
	if done_oids is None:
		# TODO: This could be an OOBTree, where the
		# values are LLTreeSet
		done_oids = set()
	while oids:
		# loop while references remain to objects we haven't exported yet
		oid = oids.pop(0)
		done_oid = (conn_name, oid)
		if done_oid in done_oids:
			continue
		done_oids.add(done_oid)

		try:
			# fetch the pickle
			p, serial = conn._storage.load(oid)
		except Exception:
			#import traceback; traceback.print_exc()
			print("Failed to find", repr(oid), "in", conn_name)
			logger.warn("broken reference for oid %s", repr(oid),
						 exc_info=True)
		else:
			roids = referencesf(p, pickle_db_name=conn_name, name_predicate=name_predicate)
			for roid, rdbname, rclass in roids:
				if reference_callback:
					reference_callback(oid, conn_name, roid, rdbname, rclass)
				# add the referenced object to the list of objects we need
				# to visit if it lives in this db
				if rdbname == conn_name:
					oids.append(roid)

			# yield the oid and pickle
			yield conn_name, oid, p

from ZODB.serialize import Unpickler
from ZODB.serialize import BytesIO

def referencesf(p, oids=None, pickle_db_name="", name_predicate=None):
	"""
	Return a list of (oid, dbname) found in a pickle

	A list may be passed in, in which case, information is
	appended to it.

	Weak references are not included.
	"""

	refs = []
	u = Unpickler(BytesIO(p))
	u.persistent_load = refs.append
	# If we use noload, we get an empty list where
	# we would expect a multi-database reference.
	# Using load we get the right thing at the cost of
	# instantiating some extra data, but not anything
	# persistent
	try:
		klass = u.load()
		u.load()
		if name_predicate and klass and not name_predicate(klass.__module__ + '.' + klass.__name__):
			return ()
		# TODO: We would like to filter out __parent__, usually,
		# so we only go down the tree. Without actually persistently
		# loading, that's  hard.
	except (AttributeError,ImportError):
		u = Unpickler(BytesIO(p))
		u.persistent_load = refs.append
		u.noload()
		u.noload()


	# Now we have a list of referencs.	Need to convert to list of
	# oids:

	if oids is None:
		oids = []

	for reference in refs:
		ref_db_name = pickle_db_name
		oid = None
		ref_class_name = None

		if isinstance(reference, tuple):
			oid = reference[0]
			ref_class_name = reference[1].__class__.__module__ + '.' + reference[1].__class__.__name__
		elif isinstance(reference, (bytes, str)):
			oid = reference
		else:
			assert isinstance(reference, list)

			if reference:
				ref_type, ref_args = reference
				if ref_type in ('n', 'm'):
					ref_db_name, oid = ref_args[0], ref_args[1]
					if len(ref_args) == 3:
						ref_class = ref_args[2]
						ref_class_name = ref_class.__module__ + '.' + ref_class.__name__
		if not oid:
			continue

		if not isinstance(oid, bytes):
			assert isinstance(oid, str)
			# this happens on Python 3 when all bytes in the oid are < 0x80
			oid = oid.encode('ascii')

		oids.append((oid, ref_db_name, ref_class_name))

	return oids
