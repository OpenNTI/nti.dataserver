#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse

from zope import component

from nti.appserver import site_policies

from nti.dataserver import users as ds_users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

def _process_users(usernames, site_policy, verbose=False):
	users = []
	for name in usernames:
		user = ds_users.User.get_user(name)
		if user is None:
			if verbose:
				print('User %s does not exists' % name)
		elif nti_interfaces.ICoppaUserWithoutAgreement.providedBy(user):
			users.append(user)
		elif verbose:
			print('User %s cannot be upgraded' % name)
			
	for user in users:
		site_policy.upgrade_user(user)
		if verbose:
			print('User %s has been upgraded' % user)
			
	return users
	
def _process_args(usernames, site_name, verbose=False):
	site_policy = component.queryUtility(site_policies.ISitePolicyUserEventListener, name=site_name)
	if site_policy is None:
		print('Could not find site policy "%s"' % site_name)
		sys.exit(-1)
		
	_process_users(usernames, site_policy, verbose)

def main():
	arg_parser = argparse.ArgumentParser( description="Upgrade coppa users" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'site_name', help="Site policy name")
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( 'users',
							 nargs="+",
							 help="The users to uprade" )
	
	args = arg_parser.parse_args()
	
	# gather parameters
	env_dir = args.env_dir
	usernames = args.users
	verbose = args.verbose
	site_name = args.site_name
	conf_packages = ('nti.appserver',)
	
	run_with_dataserver(environment_dir=env_dir, 
						verbose = verbose,
						xmlconfig_packages=conf_packages,
						function=lambda: _process_args(usernames, site_name, verbose) )
