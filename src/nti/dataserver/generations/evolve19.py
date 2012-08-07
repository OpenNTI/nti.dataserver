#!/usr/bin/env python
"""
zope.generations generation 19 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 19

from nti.dataserver.generations import install


def evolve( context ):
	"""
	Evolve generation 18 to generation 19 by installing the global flag tracking
	utility.
	"""
	conn = context.connection

	dataserver_folder = conn.root()['nti.dataserver']
	install.install_flag_storage( dataserver_folder )
