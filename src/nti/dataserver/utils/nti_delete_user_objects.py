#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import argparse
import datetime
from collections import defaultdict

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.contentsearch.utils.nti_remove_user_content import remove_user_content

from nti.dataserver.utils.nti_export_user_objects import get_user_objects, to_external_object

def remove_user_objects( username, object_types=(), export_dir=None, verbose=False):
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types))

	captured_types = set()
	exported_objects = defaultdict(list)
	if export_dir:
		export_dir = os.path.expanduser(export_dir)
		if not os.path.exists(export_dir):
			os.makedirs(export_dir)

	counter = defaultdict(int)
	for type_name, adapted, obj in list(get_user_objects( user, object_types)):
		external = to_external_object(adapted) if export_dir else None
		with user.updates():
			objId = obj.id
			containerId = obj.containerId
			obj = user.getContainedObject( containerId, objId )
			if obj is not None and user.deleteContainedObject( containerId, objId ):
				counter[type_name] = counter[type_name] +  1
				captured_types.add(type_name)
				if external is not None:
					exported_objects[type_name].append(external)

	if counter:
		remove_user_content(username, captured_types)
		if export_dir and exported_objects:
			utc_datetime = datetime.datetime.utcnow()
			s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
			for name, objs in exported_objects.items():
				name = "%s-%s-%s.json" % (username, name, s)
				outname = os.path.join(export_dir, name)
				with open(outname, "w") as fp:
					json.dump(objs, fp, indent=4)
					
		if verbose:
			for t,c in counter.items():
				print('%s %s object(s) deleted' % (c, t))
	elif verbose:
		print( "No objects were removed for user '%s'" % username, file=sys.stderr)

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
							 help="The object type(s) to delete" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	
	args = arg_parser.parse_args()
	
	verbose = args.verbose
	username = args.username
	env_dir = os.path.expanduser(args.env_dir)
	object_types = set(args.object_types) if args.object_types else ()
	export_dir = os.path.expanduser(args.export_dir)  if args.export_dir else None
	
	run_with_dataserver(environment_dir=env_dir, 
						function=lambda: remove_user_objects(username, object_types, export_dir, verbose) )

if __name__ == '__main__':
	main()
