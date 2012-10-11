#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse
from pprint import pprint

from zope import interface
from zope.schema import getFields

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.utils.schema import find_most_derived_interface
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

def _change_attributes(args):
	user = users.User.get_user( args.username )
	if not user:
		print( "No user found", args.username, file=sys.stderr )
		sys.exit( 2 )

	external = {}
	fields = _find_allowed_fields(user)
	for name, sch_def in fields.items():
		value = getattr(args, name, None)
		if value is not None:
			value = None if not value else unicode(value)
			external[name] = sch_def.fromUnicode(value) if value else None

	update_from_external_object(user, external)

	if args.verbose:
		pprint( to_external_object( user ) )

def _find_allowed_fields(user):
	profile_iface = user_interfaces.IUserProfileSchemaProvider( user ).getSchema()
	profile = profile_iface( user )
	profile_schema = find_most_derived_interface( profile, profile_iface, possibilities=interface.providedBy(profile) )

	result = {}
	for k, v in profile_schema.namesAndDescriptions(all=True):
		if interface.interfaces.IMethod.providedBy( v ):
			continue
		
		if v.queryTaggedValue( user_interfaces.TAG_HIDDEN_IN_UI ):
			continue

		result[k] = v
		
	return result

def _create_args_parser():
	arg_parser = argparse.ArgumentParser( description="Set user attributes." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to edit" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	
	attributes = {}
	def get_schema_fields(iface, attributes):
		names = iface.names()
		fields = getFields(iface) or {}
		for name in names or ():
			sch_def = fields.get(name, None)
			if sch_def and name not in attributes:
				attributes[name] = sch_def
		
		for base in iface.getBases() or ():
			get_schema_fields(base, attributes)
		
	get_schema_fields(user_interfaces.ICompleteUserProfile, attributes)
	for name, sch in attributes.items():
		if not sch.readonly:
			help_ = sch.getDoc() or sch.title
			help_ = help_.replace('\n', '.')
			opt = '--%s' % name
			arg_parser.add_argument( opt, help=help_, dest=name, required=False)
			
	return arg_parser
			
def main():
	arg_parser = _create_args_parser()
	args = arg_parser.parse_args()
	run_with_dataserver( environment_dir=args.env_dir, 
						 function=lambda: _change_attributes(args) )

if __name__ == '__main__':
	main()
