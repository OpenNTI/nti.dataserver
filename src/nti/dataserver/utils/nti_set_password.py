#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Change a user password.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import getpass
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces

def _set_pass(username, password):
	user = users.User.get_user(username)
	if not user or not nti_interfaces.IUser.providedBy(user):
		print("User not found", username, file=sys.stderr)
		sys.exit(2)

	user.password = password

def main():
	arg_parser = argparse.ArgumentParser(description="Interactively change the password of an existing user account")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username whose password to change")
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	username = args.username

	password = getpass.getpass("Password: ")
	passwrd2 = getpass.getpass("Confirm : ")
	if not password or password != passwrd2:
		print("Password not provided or not matched", file=sys.stderr)
		sys.exit(1)

	run_with_dataserver(environment_dir=env_dir, function=lambda: _set_pass(username, password))
	sys.exit(0)

if __name__ == '__main__':
	main()
