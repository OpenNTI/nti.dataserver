#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


from nti.dataserver import users
from nti.dataserver.generations.install import install_shard

from . import run_with_dataserver
import argparse

def main():
	arg_parser = argparse.ArgumentParser( description="Make an existing database connection available as a user shard" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'shard_name', help="The name of the shard, matches the database name" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()

	env_dir = args.env_dir


	run_with_dataserver( environment_dir=env_dir, function=lambda: _init_shard(args) )


def _init_shard( args ):
	dataserver = users._get_shared_dataserver()
	install_shard( dataserver.root_connection, args.shard_name )
