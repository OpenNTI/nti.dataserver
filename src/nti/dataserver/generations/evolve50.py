#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 50 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 50

from zope import component
from zope import interface
from zope.component.hooks import site, setHooks

from nti.dataserver.users.interfaces import IImmutableFriendlyNamed

COM_USERNAMES = ('litworld.nextthought.com', 
				 'symmys.nextthought.com',
				 'Carnegie Mellon University')
	
def evolver(users, communities=COM_USERNAMES):
	count = 0
	for name in communities:
		try:
			community = users[name]
			for user in community:
				if IImmutableFriendlyNamed.providedBy(user):
					interface.noLongerProvides(user, IImmutableFriendlyNamed)
					count += 0
		except KeyError:
			pass
	return count

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']
	
	logger.info('Evolution %s started', generation)
	
	with site(ds_folder):
		assert 	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		users = ds_folder['users']
		count = evolver(users)
	
	logger.info('Evolution %s done. %s users updated', generation, count)

def evolve(context):
	"""
	Evolve generation 49 to 50 by removing IImmutableFriendlyNamed from some users
	"""
	do_evolve(context)
