#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import datetime

from zope.generations.utility import findObjectsProviding

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject

def _normalize_type_name(x, encode=True):
	result = ''
	if x:
		result =x[0:-1].lower() if x.endswith('s') else x.lower()
	return unicode(result) if encode else result
	
def _get_object_type(obj):
	result = obj.__class__.__name__
	return _normalize_type_name(result) if result else u''

def export_user_objects( username, object_types=(), export_dir="/tmp"):
	
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	export_dir = export_dir or "/tmp"
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)
		
	result = []
	object_types = set(map(lambda x: _normalize_type_name(x), object_types))
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		type_name = _get_object_type(obj)
		if type_name and (not object_types or type_name in object_types):			
			external = toExternalObject(obj)
			result.append(external)

	utc_datetime = datetime.datetime.utcnow()
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	name = "%s-objects-%s.json" % (username, s)
	outname = os.path.join(export_dir, name)
	with open(outname, "w") as fp:
		json.dump(result, fp, indent=4)
					
	print("%s object(s) were exported from user '%s' to '%s'" % (len(result), username, outname),
		 file=sys.stderr)
	
	return outname

def main():
	if len(sys.argv) < 2:
		print( "Usage %s env_dir username [export_dir] [*types]" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = sys.argv[1]
	username = sys.argv[2]
	if len(sys.argv) >=4:
		export_dir = sys.argv[3]
	else:
		export_dir = env_dir
	object_types = set(sys.argv[4:])
	run_with_dataserver( environment_dir=env_dir, function=lambda: export_user_objects(username, object_types, export_dir) )

if __name__ == '__main__':
	main()
