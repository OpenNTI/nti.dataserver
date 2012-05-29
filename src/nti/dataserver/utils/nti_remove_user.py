#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import sys

from nti.dataserver import users
from . import run_with_dataserver

from nti.contentsearch.utils.nti_remove_user_content import remove_user_content

def main():
	if len(sys.argv) < 2:
		print( "Usage %s env_dir username" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = sys.argv[1]
	username = sys.argv[2]

	run_with_dataserver( environment_dir=env_dir, function=lambda: _remove_user(username) )

def _remove_user( username ):
	user = users.User.get_user( username )
	if not user:
		print( "User '%s' does not exists" % username, file=sys.stderr )
		sys.exit( 2 )

	remove_user_content( username=username )
	#TODO: remove sessions
	users.User.delete_user( username=username )
