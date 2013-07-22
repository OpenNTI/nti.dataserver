#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
repoze.zodbconn 0.14 has a bug parsing multiple uris

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import io
import os

import ZConfig

try:
	from urllib.parse import urlsplit
except ImportError: #pragma NO COVER
	from urlparse import urlsplit

# Capability test for older Pythons (2.x < 2.7.4, 3.x < 3.2.4)
(scheme, netloc, path, query, frag) = urlsplit('scheme:///path/#frag')
_BROKEN_URLSPLIT = frag != 'frag'

class ZConfigURIResolver(object):

	schema_xml_template = b"""
	<schema>
		<import package="ZODB"/>
		<multisection type="ZODB.database" attribute="databases" />
	</schema>
	"""

	def __call__(self, uri):
		(_, _, path, _, frag) = urlsplit(uri)
		if _BROKEN_URLSPLIT: #pragma NO COVER
			# urlsplit used not to allow fragments in non-standard schemes,
			# stuffed everything into 'path'
			(scheme, netloc, path, query, frag
			) = urlsplit('http:' + path)
		path = os.path.normpath(path)
		schema_xml = self.schema_xml_template
		schema = ZConfig.loadSchemaFile(io.BytesIO(schema_xml))
		config, _ = ZConfig.loadConfig(schema, path)
		for database in config.databases:
			if not frag:
				# use the first defined in the file
				break
			elif frag == database.name:
				# match found
				break
		else:
			raise KeyError("No database named %s found" % frag)
		return (path, frag), (), {}, database.open

def _path_zconfig_resolver():
	from repoze.zodbconn import resolvers
	resolvers.ZConfigURIResolver = ZConfigURIResolver
	
def patch():
	logger.info( "Monkey-patching repoze.zodbconn zconfig uri resolver" )
	_path_zconfig_resolver()


