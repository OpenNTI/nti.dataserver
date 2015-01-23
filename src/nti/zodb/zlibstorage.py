#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with zc.zlibstorage.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

try:
	from repoze.zodbconn import resolvers
except ImportError: # pypy?
	class resolvers(object):
		ClientStorageURIResolver = object
		RESOLVERS = {}

from nti.utils import make_cache_dir

class ZlibStorageClientStorageURIResolver(resolvers.ClientStorageURIResolver):
	"""
	Wraps :class:`ZEO.ClientStorage.ClientStorage` 
	with zc.zlibstorage when using the ``zlibzeo`` URI scheme.
	"""

	def __call__(self,uri):
		# Defer these imports until we are actually used
		from ZODB import DB
		from ZODB.DemoStorage import DemoStorage
		from ZEO.ClientStorage import ClientStorage
		from zc.zlibstorage import ZlibStorage


		# It expect to find 'zeo' so make that happen
		uri = uri.replace( b'zlibzeo://', b'zeo://' )
		key, args, storage_kw, _ = super(ZlibStorageClientStorageURIResolver,self).__call__(uri)
		# key = (args, tuple(kw items), tuple(dbkw items))
		dbkw = dict(key[2])
		orig_kw = dict(key[1])

		def zlibfactory():
			# Wraps uri in :class:`zc.slibstorage.ZlibStorage` and returns a :class:`ZODB.DB`

			# Delay setting the client name until the very end so whatever is going to
			# set environment variables will have done so.
			if 'var' not in storage_kw:
				storage_kw['var'] = make_cache_dir( 'zeo' )
			if 'client' not in storage_kw:
				name = os.environ.get( "DATASERVER_ZEO_CLIENT_NAME" )
				if name:
					storage_kw['client'] = name # storage name is automatically part of it
			if 'cache_size' not in storage_kw:
				storage_kw['cache_size'] = 200 * 1024 * 1024 # ClientCache docs say 200MB is good

			# Client storage is very picky: a Unix path must be bytes, not unicode
			client = ClientStorage( *args, **storage_kw )
			if 'demostorage' in orig_kw: # pragma: no cover
				client = DemoStorage( base=client )

			zlib = ZlibStorage( client )
			return DB( zlib, **dbkw )

		return key, args, storage_kw, zlibfactory

class ZlibStorageFileStorageURIResolver(resolvers.FileStorageURIResolver):

	def __call__(self, uri):
		from zc.zlibstorage import ZlibStorage

		# It expect to find 'file' so make that happen
		uri = uri.replace( b'zlibfile://', b'file://' )
		key, args, storage_kw, _factory = super(ZlibStorageFileStorageURIResolver,self).__call__(uri)
		def zlibfactory():
			db = _factory()
			db.storage = ZlibStorage( db.storage )
			return db

		return key, args, storage_kw, zlibfactory


def install_zlib_client_resolver():
	"""
	Makes it possible for :func:`repoze.zodbconn.uri.db_from_uri` to connect
	to ZEO servers that are using zlib storage, through providing support for the
	use of the ``zlibzeo`` URI scheme, and likewise for zlibfile://
	"""
	# The alternative to all this is to use a ZConfig file and ZConfig URI.
	resolvers.RESOLVERS['zlibzeo'] = ZlibStorageClientStorageURIResolver()
	resolvers.RESOLVERS['zlibfile'] = ZlibStorageFileStorageURIResolver()
