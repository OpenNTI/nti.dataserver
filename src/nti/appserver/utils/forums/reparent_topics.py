#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Temp utility to reparent topics

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

def reparent_topics(community, forum_name, list_forums=False, verbose=False):
	community = users.Community.get_community(community)
	if not community or not nti_interfaces.ICommunity.providedBy(community):
		print('Community not found')
		sys.exit(2)
	
	board = frm_interfaces.ICommunityBoard(community, None)
	if board is None:
		print('Community does not allow a board')
		sys.exit(2)

	if list_forums:
		for forum in board.keys():
			print(forum)
		return

	forum = board.get(forum_name)
	if forum is None:
		print('Forum not found')
		sys.exit(3)

	if forum.__parent__ != board:
		forum.__parent__ = board
		forum.__name__ = forum_name
		if verbose:
			print('Setting parent for forum %s' % forum_name)

	count = 0
	for name, topic in forum.items():
		if topic.__parent__ != forum:
			topic.__parent__ = forum
			topic.__name__ = name
			count += 1
			if verbose:
				print('Setting parent for topic %s' % name)
	return count

def main():
	arg_parser = argparse.ArgumentParser(description="Reparent topics")
	arg_parser.add_argument('community', help="The name of the community")
	arg_parser.add_argument( '--env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('-l', '--listforums', help="List forums", action='store_true', dest='list_forums')
	arg_parser.add_argument('-f', '--forum', help="Forum name", default=CommunityForum.__default_name__, dest='forum')
	args = arg_parser.parse_args()

	fourm = args.forum

	env_dir = os.getenv('DATASERVER_DIR', args.env_dir)
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	
	verbose = args.verbose
	community = args.community
	list_forums = args.list_forums
	run_with_dataserver(environment_dir=env_dir, function=lambda: reparent_topics(community, fourm, list_forums, verbose))
	sys.exit(0)

if __name__ == '__main__':
	main()

