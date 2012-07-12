#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import datetime
from collections import Mapping

from zope import component
from zope.generations.utility import findObjectsMatching

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields

def clean_links(obj):
	if isinstance(obj, Mapping):
		obj.pop(StandardExternalFields.LINKS, None)
		map(clean_links, obj.values())
	elif isinstance(obj, (list, tuple)):
		map(clean_links, obj)
	return obj

def export_users(export_dir="/tmp", users_2_export=()):
	
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)
		
	utc_datetime = datetime.datetime.utcnow()
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	outfile = os.path.join(export_dir, 'users-%s.json' % s)
	with open(outfile, "w") as fp:	
		ds = component.getUtility( nti_interfaces.IDataserver )
		for user in findObjectsMatching(ds.root, lambda x: nti_interfaces.IUser.providedBy( x )):
			if not users_2_export or user.username in users_2_export:
				external = toExternalObject(user)
				clean_links(external)
				json.dump(external, fp, indent=4)
			
	return True
	
def main():

	if len(sys.argv) < 2:
		print( "Usage %s env_dir [export_dir]" % sys.argv[0] )
		sys.exit( 1 )

	# gather parameters
	env_dir = sys.argv[1]
	export_dir = sys.argv[2] if len(sys.argv) >=3 else env_dir
	users_2_export = sys.argv[3:]

	# run export
	run_with_dataserver( environment_dir=env_dir, function=lambda: export_users(export_dir, users_2_export) )

if __name__ == '__main__':
	main()
