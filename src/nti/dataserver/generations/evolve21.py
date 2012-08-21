#!/usr/bin/env python
"""
zope.generations generation 21 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 21

from nti.dataserver.generations import install


def evolve( context ):
	"""
	Evolve generation 20 to generation 21 by installing the default password policy
	utility.
	"""
	conn = context.connection

	dataserver_folder = conn.root()['nti.dataserver']
	install.install_password_utility( dataserver_folder )
