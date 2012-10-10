#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import sys
import argparse
from pprint import pprint

from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.externalization.externalization import to_external_object

from nti.dataserver.utils import run_with_dataserver

def _opt_email_communication( username, opt_in, verbose):
	user = users.User.get_user( username )
	if not user:
		print( "No user found", username, file=sys.stderr )
		sys.exit( 2 )

	profile = user_interfaces.IUserProfile( user )
	opt_in = setattr( profile, 'opt_in_email_communication', opt_in )
	
	if verbose:
		pprint( to_external_object( user ) )

def main():
	arg_parser = argparse.ArgumentParser( description="Opt email communication." )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'username', help="The username to edit" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument( '-i', '--in', help="Opt in", action='store_true', dest='opt_in')
	arg_parser.add_argument( '-o', '--out', help="Opt out", action='store_true', dest='opt_out')
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	opt_in = args.opt_in
	out_out = args.opt_out
	verbose = args.verbose
	username = args.username
	
	if not opt_in and not out_out:
		print( "Choose either opt-in or opt-out ", args, file=sys.stderr )
		sys.exit( 2 )
	elif opt_in and out_out:
		print( "Choose either opt-in or opt-out, not both", args, file=sys.stderr )
		sys.exit( 2 )
	elif out_out:
		opt_in = False
		
	run_with_dataserver( environment_dir=env_dir, function=lambda: _opt_email_communication(username, opt_in, verbose) )


if __name__ == '__main__':
	main()