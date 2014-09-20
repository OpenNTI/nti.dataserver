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

import os
import argparse

from zope import component

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.utils import run_with_dataserver

def _set_generation(args):
	ds = component.getUtility(IDataserver)
	conn = ds.root._p_jar
	root = conn.root()
	old_value = root['zope.generations'].get( args.id )
	if old_value is None:
		raise ValueError('Invalid key, location does not exist (%s)', args.id)
	root['zope.generations'][args.id] = args.generation

def main():
	arg_parser = argparse.ArgumentParser( description="Set generation" )
	arg_parser.add_argument('generation', help="The generation number to set", type=int)
	arg_parser.add_argument('id',
							nargs='?',
							help="The name of the component to set",
							default='nti.dataserver')
	arg_parser.add_argument('--env_dir', help="Dataserver environment root directory")
	args = arg_parser.parse_args()

	env_dir = args.env_dir
	if not env_dir:
		env_dir = os.getenv( 'DATASERVER_DIR' )
	if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
		raise ValueError( "Invalid dataserver environment root directory", env_dir )

	run_with_dataserver(environment_dir=env_dir, 
						function=lambda: _set_generation(args) )

if __name__ == '__main__':
	main()

