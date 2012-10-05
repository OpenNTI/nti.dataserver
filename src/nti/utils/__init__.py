#!/usr/bin/env python
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import hashlib
import urlparse

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')


from zope.dottedname import resolve as dottedname

_AVATAR_SERVICES = { 'gravatar': { True: b'secure.gravatar.com',
								   False: b'www.gravatar.com' },
					'libravatar': {True: b'seccdn.libravatar.org',
								   False: b'cdn.libravatar.org'} }

GENERATED_GRAVATAR_TYPES = ('retro', 'identicon', 'monsterid', 'wavatar' )
KNOWN_GRAVATAR_TYPES = GENERATED_GRAVATAR_TYPES + ('mm','404')

def create_gravatar_url( username,
						 defaultGravatarType='mm',
						 secure=False,
						 size=128,
						 service='gravatar'):
	"""
	Return a gravatar URL for the given username (which is assumed to be an email address).

	:keyword basestring defaultGravatarType: The gravatar type to use if no specific
		gravatar is available. Defaults to 'mm' for mystery man.
	:keyword bool secure: If `True` (default `False`) HTTPS URL will be generated.
	:keyword int size: The pixel dimensions of the image, between 1 and 512. Default 128.

	:return: A gravatar URL for the given username. See http://en.gravatar.com/site/implement/images/
	"""
	md5str = hashlib.md5( username.lower() ).hexdigest()

	scheme = b'https' if secure else b'http'
	netloc = _AVATAR_SERVICES[service][secure]
	path = b'/avatar/' + md5str
	params = ''
	query = b's=%s&d=%s' % (size,defaultGravatarType)
	fragment = ''
	return str(urlparse.urlunparse( (scheme,netloc,path,params,query,fragment) ))


import os
def setupChameleonCache(config=False):
	# Set up a cache for these things to make subsequent renders faster

	def _make_cache_dir():
		result = None
		# In preference order
		env_child = ( ('DATASERVER_ENV', ('var', 'chameleon_cache')),
					  ('DATASERVER_DIR', ('var', 'chameleon_cache')),
					  ('VIRTUAL_ENV', ('.chameleon_cache',) ) )
		for env_var, child in env_child:
			if env_var in os.environ:
				parent = os.environ[env_var]
				result = os.path.join( parent, *child )
				break
		if result is None:
			result = os.path.join( os.getcwd(), '.chameleon_cache' )

		logger.info( "Caching templates to %s", result )
		try:
			os.mkdir( result )
		except OSError:
			pass
		return result

	result = None
	if not 'CHAMELEON_CACHE' in os.environ:
		os.environ['CHAMELEON_CACHE'] = result = _make_cache_dir()
	else:
		result = os.environ['CHAMELEON_CACHE']

	if config:
		conf_mod = dottedname.resolve('chameleon.config')
		if conf_mod.CACHE_DIRECTORY is None: # previously imported before we set the environment
			result = conf_mod.CACHE_DIRECTORY = _make_cache_dir()

	return result
