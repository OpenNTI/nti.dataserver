#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse
from datetime import datetime

from zope import component

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

def main():
	arg_parser = argparse.ArgumentParser( description="Get the current active sessions" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	verbose = args.verbose
	run_with_dataserver( environment_dir=env_dir, function=lambda: _get_active_sessions(verbose) )
	sys.exit( 0 )


def _format_time(ts):
	result = datetime.fromtimestamp(ts)
	result = result.strftime("%Y-%m-%d %H:%M:%S")
	return result
		
def _get_active_sessions(verbose=False):
	
	dataserver = component.getUtility( nti_interfaces.IDataserver)
	_users = nti_interfaces.IShardLayout( dataserver ).users_folder
	usernames = _users.iterkeys()
		
	sss = component.getUtility( nti_interfaces.ISessionServiceStorage)
	for username in usernames:
		user = users.User.get_user( username )
		if not user:
			continue
		
		sessions = list(sss.get_sessions_by_owner(user)) 
		if sessions:
			if not verbose:
				print(user, len(sessions))
			else:
				for s in sessions:
					ct = _format_time(s.creation_time)
					lht = _format_time(s.last_heartbeat_time)
					print('%s\t%s\t%s\t%s\t%s' % (user.username, s.id, s.state, ct, lht))
				
			
if __name__ == '__main__':
	main()
	