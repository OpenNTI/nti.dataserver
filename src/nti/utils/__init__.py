#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import hashlib
import urlparse

def create_gravatar_url( username,
						 defaultGravatarType='mm',
						 secure=False,
						 size=128 ):
	"""
	:return: A gravatar URL for the given username. See http://en.gravatar.com/site/implement/images/
	:keyword basestring defaultGravatarType: The gravatar type to use if no specific
		gravatar is available. Defaults to 'mm' for mystery man.
	:keyword bool secure: If `True` (default `False`) HTTPS URL will be generated.
	:keyword int size: The pixel dimensions of the image, between 1 and 512. Default 128.
	"""
	md5str = hashlib.md5( username.lower() ).hexdigest()

	scheme = 'https' if secure else 'http'
	netloc = 'secure.gravatar.com' if secure else 'www.gravatar.com'
	path = '/avatar/' + md5str
	params = ''
	query = 's=%s&d=%s' % (size,defaultGravatarType)
	fragment = ''
	return urlparse.urlunparse( (scheme,netloc,path,params,query,fragment) )
