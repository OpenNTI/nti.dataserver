#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility to delete user objects.

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
from collections import defaultdict

import ZODB

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.nti_export_user_objects import get_user_objects, to_external_object

def delete_entity_objects(user, object_types=(), extenalize=False):

	# normalize object types
	object_types = set(map(lambda x: x.lower(), object_types or ()))

	captured_types = set()
	broken_objects = set()
	exported_objects = defaultdict(list)

	counter_map = defaultdict(int)
	for type_name, adapted, obj in list(get_user_objects(user, object_types)):
		external = to_external_object(adapted) if extenalize else None

		if ZODB.interfaces.IBroken.providedBy(obj):
			oid = getattr(obj, 'oid', None)
			pid = getattr(obj, '_p_oid', None)
			if pid:	broken_objects.add(pid)
			if oid:	broken_objects.add(oid)
			counter_map[type_name] = counter_map[type_name] + 1
		else:
			with user.updates():
				objId = obj.id
				containerId = obj.containerId
				obj = user.getContainedObject(containerId, objId)
				if obj is not None and user.deleteContainedObject(containerId, objId):
					counter_map[type_name] = counter_map[type_name] + 1
					captured_types.add(type_name)
					if external is not None:
						exported_objects[type_name].append(external)

	if broken_objects:
		for container in list(user.containers.values()):
			for t in list(container.items()):
				_, obj = t
				broken = getattr(obj, 'oid', None) in broken_objects or \
				  		 getattr(obj, '_p_oid', None) in broken_objects

				if not broken:
					strong = obj if not callable(obj) else obj()
					broken = strong is not None and \
							 getattr(strong, 'oid', None) in broken_objects and \
							 getattr(strong, '_p_oid', None) in broken_objects
					if broken:
						obj = strong

				if broken:
					user.containers._v_removeFromContainer(container, obj)

	return counter_map, exported_objects

def _remove_entity_objects(username, object_types=(), export_dir=None, verbose=False):
	entity = users.Entity.get_entity(username)
	if not entity:
		print("Entity '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	extenalize = export_dir is not None
	counter_map, exported_objects = delete_entity_objects(entity, object_types, extenalize)

	if export_dir:
		export_dir = os.path.expanduser(export_dir)
		if not os.path.exists(export_dir):
			os.makedirs(export_dir)

	if counter_map:
		if export_dir and exported_objects:
			utc_datetime = datetime.datetime.utcnow()
			s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
			for name, objs in exported_objects.items():
				name = "%s-%s-%s.json" % (username, name, s)
				outname = os.path.join(export_dir, name)
				with open(outname, "w") as fp:
					sio = StringIO()
					try:
						json.dump(objs, sio, indent=4)
						sio.seek(0)
						fp.write(sio.read())
					except:
						if verbose:
							sio.seek(0)
							print('Could not export to json\n%r' % sio.read())

		if verbose:
			for t, c in counter_map.items():
				print('%s %s object(s) deleted' % (c, t))
	elif verbose:
		print("No objects were removed for user '%s'" % username, file=sys.stderr)

def main():
	arg_parser = argparse.ArgumentParser(description="Export user objects")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory")
	arg_parser.add_argument('-t', '--types',
							 nargs="*",
							 dest='object_types',
							 help="The object type(s) to delete")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')

	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	env_dir = os.path.expanduser(args.env_dir)
	object_types = set(args.object_types) if args.object_types else ()
	export_dir = os.path.expanduser(args.export_dir)  if args.export_dir else None

	run_with_dataserver(environment_dir=env_dir,
						verbose=verbose,
						function=lambda: _remove_entity_objects(username, object_types, export_dir, verbose))

if __name__ == '__main__':
	main()
