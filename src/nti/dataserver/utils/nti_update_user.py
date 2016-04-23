#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Updates an user

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import pprint
import argparse

from zope import interface

from zope.schema import getFields

from nti.dataserver.users import User

from nti.dataserver.interfaces import IUser

from nti.dataserver.users.interfaces import TAG_HIDDEN_IN_UI
from nti.dataserver.users.interfaces import ICompleteUserProfile
from nti.dataserver.users.interfaces import IImmutableFriendlyNamed
from nti.dataserver.users.interfaces import IUserProfileSchemaProvider

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import set_site

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.schema.interfaces import find_most_derived_interface

disallowed_fields = ('password_recovery_email_hash', 'education', 'positions')

def _find_allowed_fields(user):
	profile_iface = IUserProfileSchemaProvider(user).getSchema()
	profile = profile_iface(user)
	profile_schema = find_most_derived_interface(profile,
												 profile_iface,
												 possibilities=interface.providedBy(profile))
	result = {}
	for k, v in profile_schema.namesAndDescriptions(all=True):
		if 	interface.interfaces.IMethod.providedBy(v) or \
			v.queryTaggedValue(TAG_HIDDEN_IN_UI) or \
			k in disallowed_fields:
			continue
		result[k] = v
	return result

def _update_user(username, options):
	__traceback_info__ = locals().items()

	set_site(options.site)

	user = User.get_user(username)
	if user is None or not IUser.providedBy(user):
		print("User does not exists", repr(user), file=sys.stderr)
		sys.exit(2)

	if options.mutable:
		interface.noLongerProvides(user, IImmutableFriendlyNamed)

	external = {}
	fields = _find_allowed_fields(user)
	for name, sch_def in fields.items():
		value = getattr(options, name, None)
		if value is not None:
			value = None if not value else unicode(value)
			external[name] = sch_def.fromUnicode(value) if value else None

	if external:
		update_from_external_object(user, external)

	if options.verbose:
		pprint.pprint(to_external_object(user))

	return user

def _create_args_parser():
	arg_parser = argparse.ArgumentParser(description="Set user attributes.")
	arg_parser.add_argument('username', help="The username to edit")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('--site',
							dest='site',
							action='store_true',
							help="Application SITE.")
	arg_parser.add_argument('--mutable',
							dest='mutable',
							action='store_true',
							help="Make user editable.")
	attributes = {}
	def get_schema_fields(iface, attributes):
		names = iface.names()
		fields = getFields(iface) or {}
		for name in names or ():
			sch_def = fields.get(name, None)
			if sch_def and name not in attributes and name not in disallowed_fields:
				attributes[name] = sch_def

		for base in iface.getBases() or ():
			get_schema_fields(base, attributes)

	get_schema_fields(ICompleteUserProfile, attributes)
	for name, sch in attributes.items():
		if not sch.readonly:
			help_ = sch.getDoc() or sch.title
			help_ = help_.replace('\n', '.')
			opt = '--%s' % name
			arg_parser.add_argument(opt, help=help_, dest=name, required=False)

	return arg_parser

def main(args=None):
	arg_parser = _create_args_parser()
	args = arg_parser.parse_args(args=args)

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		print("Invalid dataserver environment root directory", env_dir)
		sys.exit(2)

	username = args.username
	config_pacakges = ('nti.appserver',)
	run_with_dataserver(verbose=args.verbose,
						environment_dir=env_dir,
						xmlconfig_packages=config_pacakges,
						function=lambda: _update_user(username, args))
	sys.exit(0)

if __name__ == '__main__':
	main()
