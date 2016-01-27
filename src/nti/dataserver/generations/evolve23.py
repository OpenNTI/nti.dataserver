#!/usr/bin/env python
"""
zope.generations generation 23 evolver for nti.dataserver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 23

from nti.dataserver.users import interfaces as user_interfaces

def evolve(context):
	"""
	Evolve generation 22 to generation 23 by tweaking a name.
	"""
	conn = context.connection
	dataserver_folder = conn.root()['nti.dataserver']
	users_folder = dataserver_folder['users']
	if users_folder.get('MathCounts'):
		mc = users_folder['MathCounts']
		user_interfaces.IFriendlyNamed(mc).alias = 'MATHCOUNTS'
