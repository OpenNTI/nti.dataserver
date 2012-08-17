#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
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

def get_object_type(obj):
	result = obj.__class__.__name__
	return result.lower() if result else u''

def get_user_objects(user, object_types=()):
	
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		type_name = get_object_type(obj)
		if not object_types or type_name in object_types:
			yield type_name, obj

	if not object_types or 'transcript' in object_types or 'messageinfo' in object_types:
		for mts in findObjectsMatching( user, lambda x: isinstance(x, DMTS) ):
			adapted = getAdapter(mts, nti_interfaces.ITranscript)
			yield 'transcript', adapted

def clean_links(obj):
	if isinstance(obj, Mapping):
		obj.pop(StandardExternalFields.LINKS, None)
		map(clean_links, obj.values())
	elif isinstance(obj, (list, tuple)):
		map(clean_links, obj)
	return obj

def export_user_objects( username, object_types=(), export_dir="/tmp"):
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# create export dir
	export_dir = export_dir or "/tmp"
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types))

	result = defaultdict(list)
	for type_name, obj in get_user_objects( user, object_types):
		external = toExternalObject(obj)
		clean_links(external)
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
	if len(sys.argv) < 2:
		print( "Usage %s env_dir username [export_dir] [*types]" % sys.argv[0] )
		sys.exit( 1 )

	# gather parameters
	env_dir = sys.argv[1]
	username = sys.argv[2]
	export_dir = sys.argv[3] if len(sys.argv) >=4 else env_dir
	object_types = set(sys.argv[4:])

	# run export
	run_with_dataserver(environment_dir=env_dir, 
						function=lambda: export_user_objects(username, object_types, export_dir) )

if __name__ == '__main__':
	main()
