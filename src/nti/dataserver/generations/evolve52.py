#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 52 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 52

from zope.component.hooks import site
from zope.component.hooks import setHooks

from .install import install_username_blacklist

def do_evolve(context):

	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site( ds_folder ):
		logger.info( "Installing blacklist folder" )
		try:
			install_username_blacklist( ds_folder )
		except KeyError:
			# Shouldn't happen
			pass

	logger.info( 'nti.dataserver evolve52 complete.' )

def evolve(context):
	do_evolve(context)

