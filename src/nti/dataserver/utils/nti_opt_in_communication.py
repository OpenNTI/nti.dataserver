#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse
from datetime import datetime
from collections import namedtuple

from zope import component
from zope.catalog.interfaces import ICatalog

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.users import index as user_index
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

_fields = ('username', 'email', 'createdTime', 'lastModified', 'lastLoginTime', 'is_copaWithAgg', 'opt_in')
_UserInfo = namedtuple('_UserInfo', ' '.join(_fields))

def _parse_time(t):
	if not t:
		return str(None)
	else:
		return datetime.fromtimestamp(t).isoformat()
	
def _get_user_info(user):
	
	# get profile info
	profile = user_interfaces.IUserProfile( user )
	email = getattr( profile, 'email', None )
	opt_in = getattr( profile, 'opt_in_email_communication', False )
	
	# get user info
	createdTime = _parse_time(getattr( user, 'createdTime', 0 ))
	lastModified = _parse_time(getattr( user, 'lastModified', 0 ))
	is_copaWithAgg = nti_interfaces.ICoppaUserWithAgreement.providedBy(user)
	
	lastLoginTime = getattr( user, 'lastLoginTime', None )
	lastLoginTime = _parse_time(lastLoginTime.value) if lastLoginTime is not None else None

	return _UserInfo(user.username, email, createdTime, lastModified, lastLoginTime, is_copaWithAgg, opt_in)
	
def _seek_users(useindex=False, verbose=False):
	
	if verbose:
		print('\t'.join(_fields))
	else:
		print('\t'.join(_fields[:-1]))
	
	ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
	if not useindex:
		dataserver = component.getUtility( nti_interfaces.IDataserver)
		_users = nti_interfaces.IShardLayout( dataserver ).users_folder
		users = _users.values()
	else:
		users = ent_catalog.searchResults( topics='opt_in_email_communication')
		
	for user in users:
		if not nti_interfaces.IUser.providedBy(user):
			continue
		
		info = _get_user_info(user)
		out_t = (str(x) for x in info)
		
		if verbose:
			print('\t'.join(out_t))
		elif useindex or info.opt_in:
			print('\t'.join(out_t[:-1]))
			
def main():
	arg_parser = argparse.ArgumentParser( description="Return the users that have the opt_in_email_communication set" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-d', '--debug', help="Don't use entity index", action='store_true', dest='debug')
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('--site',
							dest='site',
							action='store_true',
							help="Application SITE. Use this when site policy should be invoked to get interface field values" )

	args = arg_parser.parse_args()

	env_dir = args.env_dir
	verbose = args.verbose
	useindex = not args.debug
	conf_packages = () if not args.site else ('nti.appserver',)
	run_with_dataserver( environment_dir=env_dir, 
						 xmlconfig_packages=conf_packages,
						 verbose=verbose,
						 function=lambda: _seek_users(useindex, verbose) )
	sys.exit( 0 )


		
if __name__ == '__main__':
	main()
	