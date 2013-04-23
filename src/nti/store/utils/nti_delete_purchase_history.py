#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Delete a purchase history 

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import sys
import argparse

from zope import lifecycleevent
from zope.annotation import IAnnotations

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.store
from .. import interfaces

def _delete_history(username, purchase_id, verbose=False):
	user = users.User.get_user(username)
	if not user:
		print("User '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	su = interfaces.IPurchaseHistory(user)

	# bwc
	if hasattr(su, "purchases"):
		for p in su.purchases.values():
			lifecycleevent.removed(p)
	elif hasattr(su, "clear"):
		su.clear()

	IAnnotations(user).pop("%s.%s" % (su.__class__.__module__, su.__class__.__name__), None)

	if verbose:
		print("Purchase history has been removed")

def main():
	arg_parser = argparse.ArgumentParser(description="Delete user's purchase history")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	env_dir = os.path.expanduser(args.env_dir)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=(nti.store,),
						function=lambda: _delete_history(username, verbose))

if __name__ == '__main__':
	main()
