#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from nti.monkey import relstorage_patch_all_except_gevent_on_import
relstorage_patch_all_except_gevent_on_import.patch()

logger = __import__('logging').getLogger(__name__)

import sys
import argparse

from nti.dataserver import users
from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.generations.install import install_shard

def main():
	arg_parser = argparse.ArgumentParser( description="Make an existing database connection available as a user shard" )
	arg_parser.add_argument( 'shard_name', help="The name of the shard, matches the database name" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	args = arg_parser.parse_args()

	import os
	
	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )
	
	shard_name = args.shard_name
	init_shard(env_dir, shard_name)
	sys.exit(0)

def init_shard(env_dir, shard_name):
	run_with_dataserver( environment_dir=env_dir, function=lambda: _init_shard(shard_name) )
	
def _init_shard( shard_name ):
	dataserver = users._get_shared_dataserver()
	install_shard( dataserver.root_connection, shard_name )
