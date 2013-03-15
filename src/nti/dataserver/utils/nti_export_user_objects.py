#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility to export user objects.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import json
import argparse
import datetime
from cStringIO import StringIO
from collections import Mapping, defaultdict

import ZODB

from zope.component import getAdapter
from zope.generations.utility import findObjectsMatching

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.links_external import render_link
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

def _get_object_type(obj):
	result = obj.__class__.__name__ if not ZODB.interfaces.IBroken.providedBy(obj) else 'broken'
	return result.lower() if result else u''

def _is_transcript(type_name):
	return type_name in ('transcript', 'messageinfo')

def _has_transcript(object_types):
	return 'transcript' in object_types or 'messageinfo' in object_types

def _clean_links(obj):
	if isinstance(obj, Mapping):
		links = obj.get(StandardExternalFields.LINKS, None)
		if links is not None:
			obj[StandardExternalFields.LINKS] = \
					 [render_link(link) if nti_interfaces.ILink.providedBy(link) else link \
					  for link in obj[StandardExternalFields.LINKS]]

		url = obj.get('url', None)
		if nti_interfaces.ILink.providedBy(url):
			obj['url'] = render_link(url)

		map(_clean_links, obj.values())
	elif isinstance(obj, (list, tuple)):
		map(_clean_links, obj)
	return obj

def get_user_objects(user, object_types=()):

	def condition(x):
		return 	isinstance(x, DMTS) or \
				ZODB.interfaces.IBroken.providedBy(x) or \
				(nti_interfaces.IModeledContent.providedBy(x) and not chat_interfaces.IMessageInfo.providedBy(x))

	for obj in findObjectsMatching(user, condition):
		type_name = _get_object_type(obj)
		if not object_types or type_name in object_types:
			if ZODB.interfaces.IBroken.providedBy(obj):
				yield 'broken', obj, obj
			elif isinstance(obj, DMTS):
				adapted = getAdapter(obj, nti_interfaces.ITranscript)
				yield 'transcript', adapted, obj
			else:
				yield type_name, obj, obj

def to_external_object(obj):
	external = toExternalObject(obj)
	_clean_links(external)
	return external

def export_user_objects(username, object_types=(), export_dir="/tmp"):
	user = users.Entity.get_entity(username)
	if not user:
		print("User/Entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	# create export dir
	export_dir = export_dir or "/tmp"
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types))

	result = defaultdict(list)
	for type_name, adapted, _ in get_user_objects(user, object_types):
		external = to_external_object(adapted)
		result[type_name].append(external)

	counter = 0
	out_files = list()
	utc_datetime = datetime.datetime.utcnow()
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	for type_name, objs in result.items():
		counter = counter + len(objs)
		name = "%s-%s-%s.json" % (username, type_name, s)
		outname = os.path.join(export_dir, name)
		with open(outname, "w") as fp:
			sio = StringIO()
			try:
				json.dump(objs, sio, indent=4)
				sio.seek(0)
				fp.write(sio.read())
			except:
				sio.seek(0)
				print('Could not export to json\n%r' % sio.read())
		out_files.append(outname)

	return out_files

def main():
	arg_parser = argparse.ArgumentParser(description="Export user objects")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('--site',
							dest='site',
							action='store_true',
							help="Application SITE. Use this to get link info")
	arg_parser.add_argument('-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory")
	arg_parser.add_argument('-t', '--types',
							 nargs="*",
							 dest='object_types',
							 help="The object type(s) to export")

	args = arg_parser.parse_args()

	# gather parameters
	env_dir = args.env_dir
	username = args.username
	export_dir = args.export_dir or env_dir
	conf_packages = () if not args.site else ('nti.appserver',)
	object_types = set(args.object_types) if args.object_types else ()

	# run export
	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=conf_packages,
						function=lambda: export_user_objects(username, object_types, export_dir))

if __name__ == '__main__':
	main()
