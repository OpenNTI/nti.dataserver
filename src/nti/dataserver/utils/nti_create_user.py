#!/usr/bin/env python
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import sys

from zope import interface
from zope import component

from nti.dataserver import shards as nti_shards
from nti.dataserver import users
from nti.dataserver import providers
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from . import run_with_dataserver

import argparse

_type_map = { 'user': users.User.create_user,
			  'provider': providers.Provider.create_provider,
			  'community': users.Community.create_community }

def main():
	arg_parser = argparse.ArgumentParser( description="Create a user-type object" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to create" )
	arg_parser.add_argument( 'password', nargs='?' )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '-t', '--type',
							 dest='type',
							 choices=_type_map,
							 default='user',
							 help="The type of user object to create" )
	arg_parser.add_argument( '-n', '--name',
							 dest='name',
							 help="The realname of the user" )
	arg_parser.add_argument( '-c', '--communities',
							 dest='communities',
							 nargs="+",
							 default=(),
							 help="The names of communities to add the user to. Slightly incompatible with --site" )
	arg_parser.add_argument( '--coppa',
							 dest='coppa',
							 action='store_true',
							 default=False,
							 help="Creating a user to whom COPPA applies (under 13)" )

	site_group = arg_parser.add_mutually_exclusive_group()
	site_group.add_argument( '-s', '--shard',
							 dest='shard',
							 help="The name of the shard to put the user in. Overrides any automatic policy." )

	site_group.add_argument('--site',
							 dest='site',
							 help="Create the user as if done by a request in this application SITE. Use this when site policy should be invoked to set interfaces, establish communities, etc" )

	args = arg_parser.parse_args()

	env_dir = args.env_dir
	username = args.username
	password = args.password

	conf_packages = () if not args.site else ('nti.appserver',)

	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=conf_packages,
						 verbose=args.verbose,
						 function=lambda: _create_user(_type_map[args.type], username, password, args.name, args.communities, args ) )
	sys.exit( 0 )

def _create_user( factory, username, password, realname, communities=(), options=None ):
	__traceback_info__ = locals().items()

	if options.shard:
		# Provide the unnamed, default utility to do this
		class FixedShardPlacer(nti_shards.AbstractShardPlacer):
			def placeNewUser( self, user, user_directory, *args ):
				self.place_user_in_shard_named( user, user_directory, options.shard )

		component.provideUtility( FixedShardPlacer(), provides=nti_interfaces.INewUserPlacer )
	elif options.site:
		# The easiest way to make this happen is to do what the test cases
		# do, and mock out a pyramid setup with a current request.
		# (TODO: pyramid has some support for running things as scripts, we should
		# probably look into that)
		from pyramid.testing import setUp as psetUp
		#from pyramid.testing import tearDown as ptearDown
		from pyramid.testing import DummyRequest

		request = DummyRequest()
		config = psetUp(registry=component.getGlobalSiteManager(),
						request=request,
						hook_zca=False)
		config.setup_registry()
		request.headers['origin'] = 'http://' + options.site if not options.site.startswith( 'http' ) else options.site

	user = factory.im_self.get_entity( username )
	if user:
		print( "Not overwriting existing entity", repr(user), file=sys.stderr )
		sys.exit( 2 )

	args = {'username': username}
	if password:
		args['password'] = password
	user = factory( **args )
	if nti_interfaces.IUser.providedBy( user ):
		names = user_interfaces.IFriendlyNamed( user )
		if realname:
			names.realname = realname
		for com_name in communities:
			community = users.Entity.get_entity( com_name, default='' )
			if community:
				user.join_community( community )
				user.follow( community )

		if options.coppa and not nti_interfaces.ICoppaUserWithoutAgreement.providedBy( user ):
			logger.info( "Applying coppa to %s", user )
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
