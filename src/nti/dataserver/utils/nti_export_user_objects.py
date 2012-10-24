#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import argparse
import datetime
from collections import Mapping
from collections import defaultdict

from zope.component import getAdapter
from zope.generations.utility import findObjectsProviding, findObjectsMatching

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.dataserver.chat_transcripts import _DocidMeetingTranscriptStorage as DMTS

def _get_object_type(obj):
	result = obj.__class__.__name__
	return result.lower() if result else u''

def _is_transcript(type_name):
	return type_name in ('transcript', 'messageinfo')

def _clean_links(obj):
	if isinstance(obj, Mapping):
		obj.pop(StandardExternalFields.LINKS, None)
		map(_clean_links, obj.values())
	elif isinstance(obj, (list, tuple)):
		map(_clean_links, obj)
	return obj

def get_user_objects(user, object_types=()):
	
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		type_name = _get_object_type(obj)
		if (not object_types or type_name in object_types) and not _is_transcript(type_name):
			yield type_name, obj, obj

	if not object_types or 'transcript' in object_types or 'messageinfo' in object_types:
		for mts in findObjectsMatching( user, lambda x: isinstance(x, DMTS) ):
			adapted = getAdapter(mts, nti_interfaces.ITranscript)
			yield 'transcript', adapted, obj
			
def to_external_object(obj):
	external = toExternalObject(obj)
	_clean_links(external)
	return external

def export_user_objects( username, object_types=(), export_dir="/tmp"):
	user = users.Entity.get_entity( username )
	if not user:
		print( "User/Entity '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# create export dir
	export_dir = export_dir or "/tmp"
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types))

	result = defaultdict(list)
	for type_name, adapted, _ in get_user_objects( user, object_types):
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
			json.dump(objs, fp, indent=4)
		out_files.append(outname)

	return out_files

def main():
	arg_parser = argparse.ArgumentParser( description="Export user objects" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username" )
	arg_parser.add_argument( '-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory" )
	arg_parser.add_argument( '-t', '--types',
							 nargs="*",
							 dest='object_types',
							 help="The object type(s) to export" )
	
	args = arg_parser.parse_args()
	
	# gather parameters
	env_dir = args.env_dir
	username = args.username
	export_dir = args.export_dir or env_dir
	object_types = set(args.object_types) if args.object_types else ()

	# run export
	run_with_dataserver(environment_dir=env_dir, 
						function=lambda: export_user_objects(username, object_types, export_dir) )

if __name__ == '__main__':
	main()
