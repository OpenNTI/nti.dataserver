#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Join community utility

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import csv
import sys
import pprint
import argparse

from zope import component

from nti.dataserver.users import Entity
from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.users.interfaces import IFriendlyNamed
from nti.dataserver.users.interfaces import IDisallowActivityLink

from nti.externalization.externalization import to_external_object

from nti.dataserver.utils import run_with_dataserver

def _tx_string(s):
	if s is not None and isinstance(s, unicode):
		s = s.encode('utf-8')
	return s

def list_communities():
	print(file=sys.stderr)
	writer = csv.writer( sys.stderr )
	header = ["username","realname","alias","public","joinable", "profile"]
	writer.writerow(header)
	
	dataserver = component.getUtility(IDataserver)
	users_folder = IShardLayout(dataserver).users_folder
	for entity in users_folder.values():
		if not ICommunity.providedBy(entity):
			continue
		fn = IFriendlyNamed(entity)
		row = [entity.username, fn.realname, fn.alias, str(entity.public),
			   str(entity.joinable), str(not IDisallowActivityLink.providedBy(entity))]
		writer.writerow([_tx_string(x) for x in row])
	print(file=sys.stderr)

def join_communities(user, communities=(), follow=False, exitOnError=False):
	not_found = set()
	for com_name in communities:
		comm = Entity.get_entity(com_name)
		if not comm or not ICommunity.providedBy(comm):
			not_found.add(com_name)
			if exitOnError:
				break
		else:
			user.record_dynamic_membership(comm)
			if follow:
				user.follow(comm)

	return tuple(not_found)

def _process_args(args):
	if args.list:
		list_communities()
	elif args.username:
		user = Entity.get_entity(args.username)
		if not user or not IUser.providedBy(user):
			print("No user found", args, file=sys.stderr)
			sys.exit(2)
	
		not_found = join_communities(user, args.communities, args.follow, True)
		if not_found:
			print("No community found", args, file=sys.stderr)
			sys.exit(3)
	
		if args.verbose:
			pprint.pprint(to_external_object(user))
	else:
		print("No username specified", args, file=sys.stderr)
		sys.exit(2)

def main():
	arg_parser = argparse.ArgumentParser( description="Join one or more existing communities" )
	arg_parser.add_argument('--list',
							dest='list',
							action='store_true',
							default=False,
							help="List all communities")	
	
	arg_parser.add_argument('-u', '--username',
							 dest='username',
							 help="The username that should join communities",
							 default=None)

	arg_parser.add_argument('-v', '--verbose', help="Be verbose", 
							action='store_true', dest='verbose')
		
	arg_parser.add_argument('-f', '--follow', help="Also follow the communities", 
							action='store_true', dest='follow')

	arg_parser.add_argument('-c', '--communities',
							dest='communities',
							nargs="+",
							help="The usernames of the communities to join")
	args = arg_parser.parse_args()
	
	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory", env_dir)
	
	run_with_dataserver(environment_dir=env_dir, 
						function=lambda: _process_args(args))

if __name__ == '__main__':
	main()
