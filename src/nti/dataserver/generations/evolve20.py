#!/usr/bin/env python
"""
zope.generations generation 20 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 20

import BTrees.OOBTree
from nti.dataserver import containers
from nti.dataserver import shards as ds_shards


def evolve( context ):
	"""
	Evolve generation 19 to generation 20 by installing the shard database.
	And adjusting the root keys.
	"""
	conn = context.connection

	dataserver_folder = conn.root()['nti.dataserver']

	shards = containers.LastModifiedBTreeContainer()
	dataserver_folder['shards'] = shards
	shards[conn.db().database_name] = ds_shards.ShardInfo()
	assert conn.db().database_name != 'unnamed', "Must give a name"
	assert shards[conn.db().database_name].__name__

	conn_root = conn.root()
	for k in ('changes','library','vendors'):

		if k in dataserver_folder:
			del dataserver_folder[k]
		elif k in conn_root:
			del conn_root[k]

	for k in ('users', 'providers' ):
		if k in dataserver_folder and not isinstance( dataserver_folder[k], containers.CaseInsensitiveLastModifiedBTreeFolder ):
			old_v = dataserver_folder[k]
			folder = containers.CaseInsensitiveLastModifiedBTreeFolder()
			old_data = old_v._SampleContainer__data
			old_v._SampleContainer__data = BTrees.OOBTree.OOBTree()

			del dataserver_folder[k]
			dataserver_folder[k] = folder

			folder._SampleContainer__data = old_data

			for v in folder._SampleContainer__data.values():
				v.__parent__ = folder
