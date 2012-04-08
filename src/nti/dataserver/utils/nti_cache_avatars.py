#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import logging
logging.basicConfig(level=logging.WARN)

import os
import os.path
import sys
import hashlib
import urlparse
import time

from zope import component
from zope.component.hooks import setHooks
from zope.configuration import xmlconfig

from requests import async
import webob.datetime_utils

import nti.dataserver
from nti.utils import create_gravatar_url
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver._Dataserver import Dataserver

def main():
	if len(sys.argv) < 2:
		print( "Usage %s env_dir [out_dir=avatar]" % sys.argv[0] )
		sys.exit( 1 )

	out_dir = sys.argv[2] if len(sys.argv) > 2 else 'avatar'
	if not os.path.exists( out_dir ):
		os.mkdir( out_dir )

	setHooks()
	xmlconfig.file( 'configure.zcml', package=nti.dataserver )
	ds = Dataserver( sys.argv[1] )
	component.provideUtility( ds )

	component.getUtility( nti_interfaces.IDataserverTransactionRunner )( lambda: _downloadAvatarIcons( ds, out_dir ) )

def _downloadAvatarIcons( ds, targetDir ):
	_users = (x for x in ds.root['users'].values()
			  if hasattr( x, 'username'))
	seen = set()
	urls = set()

	def _add_gravatar_url( user, targetDir ):
		username = user.username if hasattr( user, 'username' ) else user
		if username in seen: return
		seen.add( username )
		url = user.avatarURL if hasattr( user, 'avatarURL' ) else create_gravatar_url( username )
		url = url.replace( 'www.gravatar', 'lb.gravatar' )
		url = url.replace( 's=44', 's=128' )
		urls.add( url )
		return url

	for user in _users:
		_add_gravatar_url( user, targetDir )
		if hasattr( user, 'friendsLists' ):
			for x in user.friendsLists.values():
				if not hasattr( x, 'username' ):
					continue
				_add_gravatar_url( x, targetDir )
				for friend in x:
					_add_gravatar_url( friend, targetDir )

	# Now fetch all the URLs in non-blocking async fashion
	responses = async.map( (async.get(u) for u in urls), size=8 )

	# Write all the successful ones to disk
	for response in responses:
		if response.status_code == 200:
			filename = urlparse.urlparse( response.url ).path.split( '/' )[-1]
			with open( os.path.join( targetDir, filename ), 'wb') as f:
				f.write( response.content )
				# Preserving last modified times
				if 'last-modified' in response.headers:
					last_modified = webob.datetime_utils.parse_date( response.headers['last-modified'] )
					last_modified_unx = time.mktime(last_modified.timetuple())
					f.flush()
					os.utime( f.name, (last_modified_unx,last_modified_unx) )
