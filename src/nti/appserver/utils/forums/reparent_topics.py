#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Temp utility to reparent topics

$Id: forum_admin_views.py 24101 2013-09-06 21:47:52Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces


def reparent_topics(community, verbose=False):
	community = users.Community.get_community(community)
	if not community or not nti_interfaces.ICommunity.providedBy(community):
		print('Community not found')
		sys.exit(2)
	
	board = frm_interfaces.ICommunityBoard(community, None)
	if board is None:
		print('Community does not allow a board')
		sys.exit(2)
		
	forum = frm_interfaces.ICommunityForum(community, None)
	if forum.__parent__ is None:
		forum.__parent__ = board
		forum.__name__ = CommunityForum.__default_name__
		if verbose:
			print('Setting parent for forum %s' % CommunityForum.__default_name__)

	count = 0
	for name, topic in forum.items():
		if topic.__parent__ is None:
			topic.__parent__ = forum
			topic.__name__ = name
			count += 1
			if verbose:
				print('Setting parent for topic %s' % name)
	return count

def main():
	arg_parser = argparse.ArgumentParser(description="Reparent topics")
	arg_parser.add_argument('env_dir', help="Dataserver environment root directory")
	arg_parser.add_argument('community', help="The name of the community")
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	community = args.shard_name
	verbose = args.verbose
	run_with_dataserver(environment_dir=env_dir, function=lambda: reparent_topics(community, verbose))
	sys.exit(0)

if __name__ == '__main__':
	main()

