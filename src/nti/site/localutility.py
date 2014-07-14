#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helpers for working with local utilities.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

def install_utility(utility, utility_name, provided, local_site_manager):
	"""
	Call this to install a local utility. Often you will
	do this from inside a handler for the registration of another
	dependent utility (:class:`.IRegistration`).

	The utility should be :class:`IContained` because it
	will be held inside the site manager.

	:param str utility_name: The *traversal* name of the utility, not
		the component registration name. This currently only handles
		the default, unnamed registration.
	"""

	# Contain the utilities we are about to install.
	# Note that for queryNextUtility, etc, to work properly if they
	# use themselves as the context (which seems to be what people do)
	# these need to be children of the SiteManager object: qNU walks from
	# the context to the enclosing site manager, and then looks through ITS
	# bases

	local_site_manager[utility_name] = utility

	local_site_manager.registerUtility( utility,
										provided=provided )

def install_utility_on_registration(utility, utility_name, provided, event):
	"""
	Call this to install a local utility in response to the registration
	of another object.

	The utility should be :class:`IContained` because it
	will be held inside the site manager.
	"""

	registration = event.object
	local_site_manager = registration.registry

	install_utility(utility, utility_name, provided, local_site_manager)


def uninstall_utility_on_unregistration(utility_name, provided, event):
	"""
	When a dependent object is unregistered, this undoes the
	work done by :func:`install_utility`.

	:param str utility_name: The *traversal* name of the utility, not
		the component registration name. This currently only handles
		the default, unnamed registration.

	"""

	registration = event.object
	local_site_manager = registration.registry

	child_component = local_site_manager[utility_name]

	looked_up = local_site_manager.getUtility(provided)
	assert looked_up is child_component

	local_site_manager.unregisterUtility( child_component,
										  provided=provided)
	del local_site_manager[utility_name]
