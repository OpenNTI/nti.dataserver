#!/usr/bin/env python
"""
Utilities for working with zc.zlibstorage.
"""
from __future__ import print_function, unicode_literals

import repoze.zodbconn.resolvers
import zc.zlibstorage
from ZODB import DB
from ZODB.DemoStorage import DemoStorage
from ZEO.ClientStorage import ClientStorage

class ZlibStorageClientStorageURIResolver(repoze.zodbconn.resolvers.ClientStorageURIResolver):
	"""
	Wraps :class:`ClientStorage` with zc.zlibstorage when using the ``zlibzeo``
	URI scheme.
	"""

	def __call__(self,uri):
		# It expect to find 'zeo' so make that happen
		uri = uri.replace( b'zlibzeo://', b'zeo://' )
		key, args, kw, _ = super(ZlibStorageClientStorageURIResolver,self).__call__(uri)
		# key = (args, tuple(kw items), tuple(dbkw items))
		dbkw = dict(key[2])
		orig_kw = dict(key[1])
		def zlibfactory():
			# Client storage is very picky: a Unix path must be bytes, not unicode
			client = ClientStorage( args, **kw )
			if 'demostorage' in orig_kw:
				client = DemoStorage( base=client )

			zlib = zc.zlibstorage.ZlibStorage( client )
			return DB( zlib, **dbkw )
		return key, args, kw, zlibfactory

def install_zlib_client_resolver():
	"""
	Makes it possible for :func:`repoze.zodbconn.uri.db_from_uri` to connect
	to ZEO servers that are using zlib storage, through providing support for the
	use of the ``zlibzeo`` URI scheme.
	"""
	# The alternative to all this is to use a ZConfig file and ZConfig URI.
	repoze.zodbconn.resolvers.RESOLVERS['zlibzeo'] = ZlibStorageClientStorageURIResolver()
