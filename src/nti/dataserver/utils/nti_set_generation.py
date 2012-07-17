#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from zope import component

from nti.dataserver import interfaces as nti_interfaces

from . import run_with_dataserver

import argparse

def main():
	arg_parser = argparse.ArgumentParser( description="Create a class with a section" )
	arg_parser.add_argument( 'env_dir', help="Dataserver environment root directory" )
	arg_parser.add_argument( 'generation', help="The generation number to set", type=int )
	arg_parser.add_argument( 'id',
							 nargs='?',
							 help="The name of the component to set",
							 default='nti.dataserver' )
	args = arg_parser.parse_args()

	env_dir = args.env_dir


	run_with_dataserver( environment_dir=env_dir, function=lambda: _set_generation(args) )


def _set_generation( args ):
	ds = component.getUtility( nti_interfaces.IDataserver )
	conn = ds.root._p_jar
	root = conn.root()
	root['zope.generations'][args.id] = args.generation
