#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Creates an entity

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import pprint
import argparse

from zope import interface
from zope import component
from zope.component import hooks

from nti.dataserver.users import User
from nti.dataserver.users import Entity
from nti.dataserver.users import Community
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import INewUserPlacer
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.shards import AbstractShardPlacer
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement

from nti.externalization.externalization import to_external_object

from nti.site.site import get_site_for_site_names

_type_map = { 'user': User.create_user,
			  'community': Community.create_community }

def _create_user(factory, username, password, realname, communities=(), options=None):
	__traceback_info__ = locals().items()

	if options.shard:
		# Provide the unnamed, default utility to do this
		class FixedShardPlacer(AbstractShardPlacer):
			def placeNewUser( self, user, user_directory, *args ):
				self.place_user_in_shard_named(user, user_directory, options.shard)
		component.provideUtility(FixedShardPlacer(), provides=INewUserPlacer)
	elif options.site:
		cur_site = hooks.getSite()
		new_site = get_site_for_site_names( (options.site,), site=cur_site )
		if new_site is cur_site:
			print("Unknown site name", options.site)
			sys.exit(2)
		hooks.setSite(new_site)
	
	user = factory.im_self.get_entity(username)
	if user:
		print("Not overwriting existing entity", repr(user), file=sys.stderr)
		sys.exit(2)

	alias = options.alias
	if alias and not isinstance(alias, unicode):
		alias = unicode(alias.decode("UTF-8"))

	realname = options.name
	if realname and not isinstance(realname, unicode):
		realname = unicode(realname.decode("UTF-8"))

	args = {'username': username}
	if password:
		args['password'] = password
	ext_value = {}
	
	if options.email:
		ext_value['email'] = unicode(options.email)
	if realname:
		ext_value['realname'] = realname
	if alias:
		ext_value['alias'] = alias
	if options.birthdate:
		ext_value['birthdate'] = unicode(options.birthdate)

	args['external_value'] = ext_value
	user = factory(**args)
	if IUser.providedBy(user):
		for com_name in communities or ():
			community = Entity.get_entity(com_name, default='')
			if community:
				user.record_dynamic_membership(community)
				user.follow(community)

		if 	options.coppa and \
			not ICoppaUserWithoutAgreement.providedBy(user):
			logger.info("Applying coppa to %s", user)
			interface.alsoProvides(user, ICoppaUserWithoutAgreement )

	if options.verbose:
		pprint.pprint(to_external_object(user))

	return user

def create_user(args=None):
	arg_parser = argparse.ArgumentParser(description="Create a user-type object")
	arg_parser.add_argument('username', help="The username to create")
	arg_parser.add_argument('password', nargs='?')
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	arg_parser.add_argument('-t', '--type',
							 dest='type',
							 choices=_type_map,
							 default='user',
							 help="The type of user object to create")
	arg_parser.add_argument('-n', '--name',
							 dest='name',
							 help="The realname of the user")
	arg_parser.add_argument('-a', '--alias',
							 dest='alias',
							 help="The alias of the user")
	arg_parser.add_argument('--email',
							 dest='email',
							 help="The email address of the user")
	arg_parser.add_argument('--birthdate',
							 dest='birthdate',
							 help="The birthdate of the user in YYYY-MM-DD form")
	arg_parser.add_argument('-c', '--communities',
							 dest='communities',
							 nargs="+",
							 default=(),
							 help="The names of communities to add the user to. "
							 	  "Slightly incompatible with --site")
	arg_parser.add_argument('--coppa',
							 dest='coppa',
							 action='store_true',
							 default=False,
							 help="Creating a user to whom COPPA applies (under 13)")
	arg_parser.add_argument('--contact_email',
							 dest='contact_email',
							 help="The contact email address of the user")

	site_group = arg_parser.add_mutually_exclusive_group()

	site_group.add_argument('-s', '--shard',
							 dest='shard',
							 help="The name of the shard to put the user in."
							 	  "Overrides any automatic policy.")

	site_group.add_argument('--site',
							 dest='site',
							 help="Application SITE.")

	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)
	
	username = args.username
	password = args.password

	run_with_dataserver(environment_dir=env_dir,
						 xmlconfig_packages=('nti.appserver',),
						 verbose=args.verbose,
						 function=lambda: _create_user(_type_map[args.type], username,
													   password, args.name, 
													   args.communities, args))

def main(args=None):
	create_user(args)
	sys.exit(0)

if __name__ == '__main__':
	main()
