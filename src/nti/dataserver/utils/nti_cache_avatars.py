#!/usr/bin/env python
from __future__ import print_function, unicode_literals, absolute_import

from nti.monkey import gevent_patch_on_import # Must be very early
gevent_patch_on_import.patch()


logger = __import__('logging').getLogger(__name__)

import os
import os.path
import urlparse
import time
import argparse

import transaction
from zope import component

import webob.datetime_utils

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users.interfaces import IAvatarURL
from . import run_with_dataserver


import requests
import gevent.pool

def main():
	arg_parser = argparse.ArgumentParser( description="Cache all gravatar urls locally" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '-d', '--directory',
							 dest='export_dir',
							 default='avatar',
							 help="Output directory" )
	args = arg_parser.parse_args()

	out_dir = args.export_dir
	if not os.path.exists( out_dir ):
		os.mkdir( out_dir )
	run_with_dataserver(environment_dir=args.env_dir,
						verbose=args.verbose,
						function=lambda: _downloadAvatarIcons( out_dir ) )


def _downloadAvatarIcons( targetDir ):
	ds = component.getUtility( nti_interfaces.IDataserver )
	_users = (x for x in ds.root['users'].values()
			  if hasattr( x, 'username'))
	seen = set()
	urls = set()

	def _add_gravatar_url( user, targetDir ):
		username = user.username if hasattr( user, 'username' ) else user
		username = username.strip() # account for POSKeyErrors and almost ghosts
		if not username or username in seen:
			 return
		seen.add( username )
		url = IAvatarURL( user ).avatarURL
		url = url.replace( 'www.gravatar', 'lb.gravatar' )
		url = url.replace( 's=44', 's=128' )
		if url.startswith( 'data' ):
			return
		logger.debug( "Will fetch %s for %s", url, user )
		urls.add( url )
		return url

	for user in _users:
		try:
			_add_gravatar_url( user, targetDir )
			if hasattr( user, 'friendsLists' ):
				for x in user.friendsLists.values():
					if not hasattr( x, 'username' ):
						continue
					_add_gravatar_url( x, targetDir )
					for friend in x:
						_add_gravatar_url( friend, targetDir )
		except Exception:
			logger.debug( "Ignoring user %s", user, exc_info=True )


	# We can now dispose of the DS and its transaction
	# while we fetch
	transaction.doom()
	ds.close()
	_users = None

	# Now fetch all the URLs in non-blocking async fashion
	pool = gevent.pool.Pool( 8 )
	session = requests.Session() # Sharing a session means HTTP keep-alive works, which is MUCH faster
	def fetch(u):
		logger.info( 'fetching %s', u )
		try:
			response = session.get( u )
		except Exception:
			return
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

	pool.map( fetch, urls )
	pool.join()
