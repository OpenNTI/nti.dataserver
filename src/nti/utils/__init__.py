#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import hashlib
import urlparse

_AVATAR_SERVICES = { 'gravatar': { True: b'secure.gravatar.com',
								   False: b'www.gravatar.com' },
					'libravatar': {True: b'seccdn.libravatar.org',
								   False: b'cdn.libravatar.org'} }

GENERATED_GRAVATAR_TYPES = ('identicon', 'monsterid', 'wavatar', 'retro' )
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
