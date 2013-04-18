#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Delete a purchase attempt 

$Id: nti_reindex_entity_content.py 17262 2013-03-18 17:20:50Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import sys
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver

import nti.store
from .. import purchase_history

def _delete_purchase(username, purchase_id, verbose=False):
	user = users.User.get_user(username)
	if not user:
		print("User '%s' does not exists" % username, file=sys.stderr)
		sys.exit(2)

	purchase = purchase_history.get_purchase_attempt(purchase_id, user)
	if not purchase:
		print("Purchase attempt '%s' does not exists" % purchase_id, file=sys.stderr)
		sys.exit(2)

	purchase_history.remove_purchase_attempt(purchase, user)
	if verbose:
		print("Purchase attempt '%s' has been removed" % purchase_id)

def main():
	arg_parser = argparse.ArgumentParser(description="Reindex entity content")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('username', help="The username")
	arg_parser.add_argument('purchase_id', help="The purchase attempt ID")
	arg_parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	verbose = args.verbose
	username = args.username
	purchase_id = args.purchase_id
	env_dir = os.path.expanduser(args.env_dir)

	run_with_dataserver(environment_dir=env_dir,
						xmlconfig_packages=(nti.store,),
						function=lambda: _delete_purchase(username, purchase_id, verbose))

if __name__ == '__main__':
	main()
