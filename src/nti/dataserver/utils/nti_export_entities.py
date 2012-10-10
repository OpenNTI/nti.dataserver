#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os
import sys
import json
import argparse
import datetime

from nti.dataserver.users import entity
from nti.dataserver.utils import run_with_dataserver
from nti.externalization.externalization import toExternalObject
			
def to_external_object(obj):
	external = toExternalObject(obj)
	return external

def export_entities( entities, export_dir="/tmp", verbose=False):
	
	# create export dir
	export_dir = export_dir or "/tmp"
	export_dir = os.path.expanduser(export_dir)
	if not os.path.exists(export_dir):
		os.makedirs(export_dir)

	utc_datetime = datetime.datetime.utcnow()
	s = utc_datetime.strftime("%Y-%m-%d-%H%M%SZ")
	outname = "entities-%s.json" % s
	outname = os.path.join(export_dir, outname)
	
	objects = []
	for entityname in entities:
		e = entity.Entity.get_entity( entityname )
		if not e and verbose:
			print( "Entity '%s' does not exists" % entityname, file=sys.stderr )
		objects.append(to_external_object(e))
	
	with open(outname, "w") as fp:
		json.dump(objects, fp, indent=4)
	
def main():
	arg_parser = argparse.ArgumentParser( description="Export user objects" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( 'entities',
							 nargs="*",
							 help="The entities to process" )
	arg_parser.add_argument( '-d', '--directory',
							 dest='export_dir',
							 default=None,
							 help="Output export directory" )
	args = arg_parser.parse_args()
	
	# gather parameters
	env_dir = args.env_dir
	entities = args.entities
	verbose = args.verbose
	export_dir = args.export_dir or env_dir

	# run export
	run_with_dataserver(environment_dir=env_dir, 
						function=lambda: export_entities(entities, export_dir, verbose) )

if __name__ == '__main__':
	main()
