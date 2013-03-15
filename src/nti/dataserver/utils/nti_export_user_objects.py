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
import argparse
import datetime
from collections import defaultdict

import ZODB

from zope.component import getAdapter
from zope.generations.utility import findObjectsMatching

from nti.chatserver import interfaces as chat_interfaces

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

from nti.externalization.oids import to_external_ntiid_oid
from nti.externalization.externalization import to_json_representation_externalized

broken_object_type = u'broken.object'
transcript_object_type = u'transcript'

def _get_object_type(obj):
	result = obj.__class__.__name__ if not ZODB.interfaces.IBroken.providedBy(obj) else broken_object_type
	return result.lower() if result else u''

def _is_transcript(type_name):
	return type_name in ('transcript', 'messageinfo')

def _has_transcript(object_types):
	return 'transcript' in object_types or 'messageinfo' in object_types

def get_user_objects(user, object_types=(), broken=False):

	def condition(x):
		return 	isinstance(x, DMTS) or \
				(ZODB.interfaces.IBroken.providedBy(x) and broken) or \
				nti_interfaces.ITitledDescribedContent.providedBy(x) or \
				(nti_interfaces.IModeledContent.providedBy(x) and not chat_interfaces.IMessageInfo.providedBy(x))

	seen = set()

	for obj in findObjectsMatching(user, condition):
		if ZODB.interfaces.IBroken.providedBy(obj):
			yield broken_object_type, obj, obj
		else:
			oid = to_external_ntiid_oid(obj)
			if oid not in seen:
				seen.add(oid)
				type_name = _get_object_type(obj)
				if not object_types or type_name in object_types:
					if isinstance(obj, DMTS):
						adapted = getAdapter(obj, nti_interfaces.ITranscript)
						yield transcript_object_type, adapted, obj
					else:
						yield type_name, obj, obj

def to_external_object(obj):
	external = to_json_representation_externalized(obj)
	return external

def export_user_objects(username, object_types=(), broken=False, export_dir="/tmp"):
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
	for type_name, adapted, _ in get_user_objects(user, object_types, broken):
		external = to_external_object(adapted)
		result[type_name].append(external)

	counter = 0
	out_files = list()
	utc_datetime = datetime.datetime.utcnow()
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	for type_name, exported in result.items():
		counter = counter + len(exported)
		name = "%s-%s-%s.txt" % (username, type_name, s)
		outname = os.path.join(export_dir, name)
		with open(outname, "w") as fp:
			for external in exported:
				fp.write(external)
				fp.write("\n")
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
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('-b', '--broken', help="Return broken objects", action='store_true', dest='broken')

	args = arg_parser.parse_args()

	# gather parameters
	broken = args.broken
	env_dir = args.env_dir
	verbose = args.verbose
	username = args.username
	export_dir = args.export_dir or env_dir
	conf_packages = () if not args.site else ('nti.appserver',)
	object_types = set(args.object_types) if args.object_types else ()

	# run export
	run_with_dataserver(environment_dir=env_dir,
						verbose=verbose,
						xmlconfig_packages=conf_packages,
						function=lambda: export_user_objects(username, object_types, broken, export_dir))

if __name__ == '__main__':
	main()
