#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse
from pprint import pprint

from zope.schema import getFields

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object

from nti.dataserver.utils import run_with_dataserver

def change_attributes( username, data, verbose):
	user = users.User.get_user( username )
	if not user:
		print( "No user found", username, file=sys.stderr )
		sys.exit( 2 )

	profile = user_interfaces.ICompleteUserProfile( user )
	for k,v in data.items():
		setattr(profile, k, v)
		
	if verbose:
		pprint( to_external_object( user ) )

def parse_schema(iface, attributes):
	names = iface.names()
	fields = getFields(iface) or {}
	for name in names or ():
		sch_def = fields.get(name, None)
		if sch_def and name not in attributes:
			attributes[name] = sch_def
	
	for base in iface.getBases() or ():
		parse_schema(base, attributes)
		
def main():
	arg_parser = argparse.ArgumentParser( description="Opt email communication." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to edit" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	
	attributes = {}
	parse_schema(user_interfaces.ICompleteUserProfile, attributes)
	for name, sch in attributes.items():
		if not sch.readonly:
			help_ = sch.getDoc() or sch.title
			help_ = help_.replace('\n', '.')
			opt = '--%s' % name
			arg_parser.add_argument( opt, help=help_, dest=name, required=False)
		
	args = arg_parser.parse_args()
	
	data = {}
	for name, sch_def in attributes.items():
		value = getattr(args, name, None)
		if value is not None:
			value = None if not value else unicode(value)
			data[name] = sch_def.fromUnicode(value) if value else None
	
	if not data:
		print( "Nothing to set", args, file=sys.stderr )
		sys.exit( 2 )
		
	env_dir = args.env_dir	
	username = args.username	
	verbose = args.verbose
	run_with_dataserver( environment_dir=env_dir, 
						 function=lambda: change_attributes(username, data, verbose) )

if __name__ == '__main__':
	main()