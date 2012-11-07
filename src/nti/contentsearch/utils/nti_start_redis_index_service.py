#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import argparse

from nti.dataserver.utils import run_with_dataserver

import nti.contentsearch
from nti.contentsearch._repoze_redis_store import _RepozeRedisStorageService

def main():
	arg_parser = argparse.ArgumentParser( description="Remove index zombies" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( '-v', '--verbose', help="Be verbose", action='store_true', dest='verbose')
	args = arg_parser.parse_args()
	
	env_dir = args.env_dir
	verbose = args.verbose
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=(nti.contentsearch,),
						 function=lambda: start_service(verbose) )
		
			
def start_service(verbose=False):
	g = _RepozeRedisStorageService(autostart=False).start()
	g.switch()
				
if __name__ == '__main__':
	main()
