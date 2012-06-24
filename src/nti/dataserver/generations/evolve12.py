#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zope.generations generation 12 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 12


from zope.component.interfaces import ISite
from zope.site import LocalSiteManager, SiteManagerContainer
from zope.site.folder import Folder, rootFolder
from zope.location.location import locate
from zope.generations.utility import findObjectsMatching

from nti.dataserver import enclosures


def evolve( context ):
	"""
	Evolve generation 11 to generation 12 by adjusting the site manager to use IFolder and
	IRootFolder.

	Fix SimplePersistentEnclosure objects to have a name for their container.
	"""
	root = context.connection.root()
	site_manager_container = root['nti.dataserver']

	### Create the new objects as install.py does
	# The root folder
	root_folder = rootFolder()
	# The root is generally presumed to be an ISite, so make it so
	root_sm = LocalSiteManager( None ) # No parent site, so parent == global
	root_folder.setSiteManager( root_sm )
	assert ISite.providedBy( root_folder )

	dataserver_folder = Folder()
	locate( dataserver_folder, root_folder, name='dataserver2' )


	# Move the site manager over
	lsm = site_manager_container.getSiteManager()
	dataserver_folder.setSiteManager( lsm )

	# Move the data objects over
	# This should automatically update the parentage info, and events will
	# fire (not that anyone is listening)
	# Note that the site manager has some of its own keys, so whitelist the
	# keys to move
	for k in ('users', 'vendors', 'library', 'quizzes', 'providers', 'changes' ):
		obj = lsm[k]
		del lsm[k]
		dataserver_folder[k] = obj
		assert obj.__parent__ is dataserver_folder

	# Now update the installed objects
	root['nti.dataserver_root'] = root_folder
	root['nti.dataserver'] = dataserver_folder

	# Finally fix up the enclosure names
	for enclosure in findObjectsMatching( dataserver_folder, lambda x: isinstance(x,enclosures.SimpleEnclosureMixin) ):
		if enclosure._enclosures is not None and enclosure._enclosures.__name__ is None:
			enclosure._enclosures.__name__ = ''
