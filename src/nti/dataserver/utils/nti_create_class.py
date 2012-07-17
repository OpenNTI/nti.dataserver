#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import sys

from nti.dataserver import users
from nti.dataserver import classes
from nti.dataserver import providers
from . import run_with_dataserver

import argparse

_type_map = { 'user': users.User.create_user,
			  'provider': providers.Provider.create_provider }

def main():
	arg_parser = argparse.ArgumentParser( description="Create a class with a section" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'provider', help="The provider of the class" )
	arg_parser.add_argument( 'id', help="The id of the class" )
	arg_parser.add_argument( '--name', dest='name', help="The name of the class" )
	arg_parser.add_argument( '--section-id',
							 required=True,
							 help="The ID of the section",
							 dest="section_id" )
	arg_parser.add_argument( '-i', '--instructor',
							 dest='instructors',
							 nargs="+",
							 required='true',
							 help="The usernames of the instructors" )
	arg_parser.add_argument( '-e', '--enrolled',
							 dest='enrolled',
							 nargs="+",
							 help="The usernames of the students enrolled" )
	args = arg_parser.parse_args()

	env_dir = args.env_dir


	run_with_dataserver( environment_dir=env_dir, function=lambda: _create_class(args) )


def _create_class( args ):
	provider = providers.Provider.get_entity( args.provider )
	if not provider:
		print( "No provider found", args, file=sys.stderr )
		sys.exit( 2 )

	_do_create_class( provider,
					  args.id, args.name,
					  args.section_id,
					  args.instructors, args.enrolled )


def _do_create_class(
					  provider,
					  class_id,
					  class_name=None,
					  section_id=None,
					  section_instructors=(),
					  usernames_to_enroll=()):

	klass = provider.maybeCreateContainedObjectWithType( 'Classes', None )
	klass.containerId = 'Classes'
	klass.ID = class_id
	klass.Description = class_name or class_id

	if section_id:
		section = classes.SectionInfo()
		section.ID = section_id
		section.creator = provider
		section.Description = (class_name + ' ' + class_id + '-' + section_id) if class_name else (class_id + '-' + section_id)
		klass.add_section( section )
		section.InstructorInfo = classes.InstructorInfo()
		for user in usernames_to_enroll:
			section.enroll( user )
		for ins in section_instructors:
			section.InstructorInfo.Instructors.append( ins )

		section.Provider = provider.username

	provider.addContainedObject( klass )


	return klass
