#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Change a user attribute

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import pprint
import argparse

from zope import component
from zope import interface
from zope.schema import getFields

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.utils.schema import find_most_derived_interface
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

def _find_allowed_fields(user):
	profile_iface = user_interfaces.IUserProfileSchemaProvider(user).getSchema()
	profile = profile_iface(user)
	profile_schema = find_most_derived_interface(profile, profile_iface, possibilities=interface.providedBy(profile))

	result = {}
	for k, v in profile_schema.namesAndDescriptions(all=True):
		if 	interface.interfaces.IMethod.providedBy( v ) or \
			v.queryTaggedValue( user_interfaces.TAG_HIDDEN_IN_UI ) :
			continue
		result[k] = v
		
	return result

def _change_attributes(args):

	if args.site:
		from pyramid.testing import setUp as psetUp
		from pyramid.testing import DummyRequest

		request = DummyRequest()
		config = psetUp(registry=component.getGlobalSiteManager(),
						request=request,
						hook_zca=False)
		config.setup_registry()
		request.headers['origin'] = 'http://' + args.site if not args.site.startswith('http') else args.site
		request.possible_site_names = (args.site if not args.site.startswith('http') else args.site[7:],)

	user = users.User.get_user( args.username )
	if not user:
		print("No user found", args.username, file=sys.stderr)
		sys.exit(2)

	restore_iface = False
	if args.force:
		if user_interfaces.IImmutableFriendlyNamed.providedBy(user):
			restore_iface = True
			interface.noLongerProvides(user, user_interfaces.IImmutableFriendlyNamed)
		
	external = {}
	fields = _find_allowed_fields(user)
	if args.verbose:
		pprint.pprint("Allowed Fields")
		pprint.pprint(list(fields.keys()))
	for name, sch_def in fields.items():
		value = getattr(args, name, None)
		if value is not None:
			value = None if not value else unicode(value)
			external[name] = sch_def.fromUnicode(value) if value else None

	if args.verbose:
		pprint.pprint("External change")
		pprint.pprint(external)
	update_from_external_object(user, external)

	if restore_iface:
		interface.alsoProvides(user, user_interfaces.IImmutableFriendlyNamed)

	if args.verbose:
		pprint.pprint("Updated user")
		pprint.pprint(to_external_object(user, name="summary"))

def _create_args_parser():
	arg_parser = argparse.ArgumentParser( description="Set user attributes." )
	arg_parser.add_argument('username', help="The username to edit")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('-f', '--force', help="Force update of immutable fields", action='store_true', dest='force')
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('--site',
							dest='site',
							help="Change the the user attributes as if done by a request in this application SITE")
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
	conf_packages = () if not args.site else ('nti.appserver',)
	
	import os
	
	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	
	run_with_dataserver( environment_dir=env_dir, 
						 xmlconfig_packages=conf_packages,
						 verbose=args.verbose,
						 function=lambda: _change_attributes(args) )

if __name__ == '__main__':
	main()
