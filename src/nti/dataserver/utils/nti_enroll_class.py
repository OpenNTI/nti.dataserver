#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import sys

from nti.dataserver import users
from nti.dataserver import providers
from nti.externalization.externalization import to_external_object

from . import run_with_dataserver
import argparse

_type_map = { 'user': users.User.create_user,
			  'provider': providers.Provider.create_provider }

def main():
	arg_parser = argparse.ArgumentParser( description="Enroll in an existing class section" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'provider', help="The provider of the class" )
	arg_parser.add_argument( 'id', help="The id of the class" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '--section-id',
							 required=True,
							 help="The ID of the section",
							 dest="section_id" )
	arg_parser.add_argument( '-e', '--enrolled',
							 dest='enrolled',
							 nargs="+",
							 help="The usernames of the students to enroll" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir


	run_with_dataserver( environment_dir=env_dir, function=lambda: _enroll_class(args) )


def _enroll_class( args ):
	provider = providers.Provider.get_entity( args.provider )
	if not provider:
		print( "No provider found", args, file=sys.stderr )
		sys.exit( 2 )

	klass = _do_enroll_class( provider,
							  args.id,
							  args.section_id,
							  args.enrolled )

	if args.verbose:
		print( to_external_object( klass ) )


def _do_enroll_class(
					  provider,
					  class_id,
					  section_id=None,
					  usernames_to_enroll=()):

	klass = provider.getContainedObject( 'Classes', class_id )
	section = klass[section_id]
	for user in usernames_to_enroll:
		section.enroll( user )

	return klass
