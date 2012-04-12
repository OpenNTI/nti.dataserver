#!/usr/bin/env python
from __future__ import print_function, unicode_literals


import sys


from zope import component


from nti.dataserver import users
from . import run_with_dataserver

def main():
	if len(sys.argv) < 2:
		print( "Usage %s env_dir username [password]" % sys.argv[0] )
		sys.exit( 1 )

	env_dir = sys.argv[1]
	username = sys.argv[2]
	password = sys.argv[3] if len(sys.argv) > 3 else None


	run_with_dataserver( environment_dir=env_dir, function=lambda: _create_user(username,password) )


def _create_user( username, password ):
	user = users.User.get_user( username )
	if user:
		print( "Not overwriting existing user", repr(user), file=sys.stderr )
		sys.exit( 2 )
	users.User.create_user( username=username, password=password )
