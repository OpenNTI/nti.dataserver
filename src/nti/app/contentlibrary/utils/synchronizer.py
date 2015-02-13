#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import argparse

from nti.dataserver.utils import run_with_dataserver
from nti.dataserver.utils.base_script import create_context

from ..synchronize import synchronize

def main():
	arg_parser = argparse.ArgumentParser( description="Synchronize all libraries" )
	arg_parser.add_argument('-v', '--verbose', help="Be verbose", action='store_true',
							dest='verbose')
	args = arg_parser.parse_args()

	env_dir = os.getenv('DATASERVER_DIR')
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise IOError("Invalid dataserver environment root directory")

	context = create_context(env_dir)
	conf_packages = ('nti.appserver',)
	
	run_with_dataserver( environment_dir=env_dir,
						 xmlconfig_packages=conf_packages,
						 verbose=args.verbose,
						 context=context,
						 function=lambda: synchronize())
	
	sys.exit( 0 )

if __name__ == '__main__':
	main()
