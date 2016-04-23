#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse
from urlparse import urlparse

from nti.common.dataurl import encode
from nti.common.mimetypes import guess_type

from nti.dataserver.interfaces import IEntity

from nti.dataserver.users import Entity

from nti.dataserver.users.interfaces import IProfileAvatarURL

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site

from nti.ntiids.ntiids import is_valid_ntiid_string
from nti.ntiids.ntiids import find_object_with_ntiid

def _find_profile(entity):
	result = None
	try:
		for value in entity.__annotations__.values():
			if IProfileAvatarURL.providedBy(value):
				result = value
				break
	except AttributeError:
		pass
	result = IProfileAvatarURL(entity) if result is None else result
	return result

def _set_avatar(username, url=None, image=None, background=False, site=None):
	set_site(site)

	if is_valid_ntiid_string(username):
		entity = find_object_with_ntiid(username)
	else:
		entity = Entity.get_entity(username)
	if entity is None or not IEntity.providedBy(entity):
		raise ValueError("Cannot find entity")

	profile = _find_profile(entity)
	field = 'backgroundURL' if background else 'avatarURL'
	if not image and not url:
		setattr(profile, field, None)
	elif url:
		setattr(profile, field, url)
	elif image:
		mime_type = guess_type(image)[0] or b'text/plain'
		with open(image, 'rb') as fp:
			data = fp.read()
		data = encode(raw_bytes=data, 
					  charset=b"utf-8",
					  mime_type=mime_type)
		setattr(profile, field, data)
	return profile

def set_entity_avatar(args=None):
	arg_parser = argparse.ArgumentParser(description="Create a user-type object")
	arg_parser.add_argument('-v', '--verbose',
							help="Be verbose",
							action='store_true',
							dest='verbose')

	arg_parser.add_argument('username', help="The username ")

	arg_parser.add_argument('-b', '--background',
							dest='background',
							action='store_true',
							help="set background image")

	site_group = arg_parser.add_mutually_exclusive_group()
	site_group.add_argument('-u', '--url',
							 dest='url',
							 help="The image url")

	site_group.add_argument('-i', '--image',
							 dest='image',
							 help="The image file")

	arg_parser.add_argument('-s', '--site',
							 dest='site',
							 help="Application SITE.")

	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)

	image = os.path.expanduser(args.image) if args.image else None
	if image and (not os.path.exists(image) or not os.path.isfile(image)):
		raise IOError('Invalid image file')

	url = args.url
	if url:
		parsed = urlparse(url)
		if not parsed.scheme or not parsed.netloc or not parsed.path:
			raise ValueError("Invalid image URL")

	username = args.username
	package = 'nti.appserver'
	run_with_dataserver(verbose=args.verbose,
						environment_dir=env_dir,
						xmlconfig_packages=(package,),
						function=lambda: _set_avatar(username,
													 url=url,
													 image=image,
													 site=args.site,
													 background=args.background))
def main(args=None):
	set_entity_avatar(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
