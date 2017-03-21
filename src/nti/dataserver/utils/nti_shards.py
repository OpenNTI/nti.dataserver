#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import patch_relstorage_all_except_gevent_on_import
patch_relstorage_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from nti.dataserver import users

from nti.dataserver.generations.install import install_shard

from nti.dataserver.interfaces import IShardLayout

from nti.dataserver.utils import run_with_dataserver

def _init_shard(shard_name):
	dataserver = users._get_shared_dataserver()
	install_shard(dataserver.root_connection, shard_name)

def init_shard(env_dir, shard_name):
	run_with_dataserver(environment_dir=env_dir,
						function=lambda: _init_shard(shard_name))

def _list_shards():
	dataserver = users._get_shared_dataserver()
	root_layout = IShardLayout(dataserver.root_connection)
	shards = root_layout.shards
	for name, shard in shards.items():
		print(name, "id %s" % id(shard),
			  "created %s" % shard.createdTime,
			  "lastModified %s" % shard.lastModified)

def list_shards(env_dir):
	run_with_dataserver(environment_dir=env_dir,
						function=lambda: _list_shards())

def main():
	arg_parser = argparse.ArgumentParser(
		description="Make an existing database connection available as a user shard")

	arg_parser.add_argument('-v', '--verbose',
							help="Be verbose", action='store_true', dest='verbose')

	site_group = arg_parser.add_mutually_exclusive_group()
	site_group.add_argument('-l', '--list',
							dest='list',
							help='List shards', action='store_true')

	site_group.add_argument('-c', '--create',
							dest='create',
							help='Create shard', action='store_true')

	arg_parser.add_argument('-n', '--name',
							dest='name',
							help="The shard name")
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')

	if args.create:
		shard_name = args.name
		if not shard_name:
			raise IOError("Must specify a shard name")
		init_shard(env_dir, shard_name)
	elif args.list:
		list_shards(env_dir)

	sys.exit(0)
