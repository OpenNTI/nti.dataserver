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

def remove_user_objects( username, object_types=(), export_dir=None ):
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types))

	captured_types = defaultdict(list)
	if export_dir:
		export_dir = os.path.expanduser(export_dir)
		if not os.path.exists(export_dir):
			os.makedirs(export_dir)

	counter = 0
	for type_name, adapted, obj in get_user_objects( user, object_types):
		external = to_external_object(adapted) if export_dir else None
		with user.updates():
			_id = getattr(obj, 'id', None )
			containerId = getattr(obj, 'containerId', None )
			if containerId and _id and user.deleteContainedObject( containerId, _id ):
				if external is not None:
					captured_types[type_name].append(external)
				counter = counter +  1

	if captured_types:
		remove_user_content(username, captured_types.keys())
		if export_dir:
			utc_datetime = datetime.datetime.utcnow()
			s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
			for name, objs in captured_types.items():
				name = "%s-%s-%s.json" % (username, name, s)
				outname = os.path.join(export_dir, name)
				with open(outname, "w") as fp:
					json.dump(objs, fp, indent=4)
	else:
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
	
	args = arg_parser.parse_args()
	
	env_dir = args.env_dir
	username = args.username
	export_dir = args.export_dir
	object_types = set(args.object_types) if args.object_types else ()
	
	run_with_dataserver( environment_dir=env_dir, function=lambda: remove_user_objects(username, object_types, export_dir) )

if __name__ == '__main__':
	main()
