#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration between the ZCA ``site`` system, configured site
policies, and the Dataserver.

In the Zope world, sites are objects that can express configuration by
holding onto an instance of IComponents known as its *site manager*.
Typically they are arranged in a tree, with the global site at the
root of the tree. Site managers inherit configuration from their
parents (bases, which may or may not be their ``__parent__``). Often,
they are persistent and part of the traversal tree. One site is the
current site and the ZCA functions (e.g.,
:meth:`.IComponentArchitecture.queryUtility`) apply to that site.

Our application has one persistent site, the dataserver site,
containing persistent utilities (such as the dataserver); see
:mod:`nti.dataserver.generations.install` This site, or a desndent of
it, must always be the current site when executing application code.

In our application, we also have the concept of site policies,
something that is applied based on virtual hosting. A site policy is
also an ``IComponents``, registered in the global site as a utility named
for the hostname to which it should apply (e.g., ``mathcounts.nextthought.com``).
These are not necessarily persistent and part of the traversal tree.

This there are two things to accomplish: make the dataserver site the current site, and
also construct a site that descends from that site and contains any applicable policies.

$Id$
"""

# turn off warning for not calling superclass, calling indirect superclass and accessing protected methods.
# we're deliberately doing both
# pylint: disable=W0233,W0231,W0212
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import setSite

from .interfaces import IMainApplicationFolder

from zope.component.interfaces import ISite
from zope.site.interfaces import INewLocalSite
from zope.site.interfaces import IRootFolder
from zope.traversing.interfaces import IBeforeTraverseEvent

from zope.proxy import non_overridable
from zope.proxy import ProxyBase

from .transient import BasedSiteManager


class _ProxyTraversedSite(ProxyBase):
	"""
	We need to be able to control the site manager used
	by sites we traverse to in order to ensure that host
	configuration is at the right place in the resolution order.
	But a site can be literally any type of object. So we fake out the
	siteManager methods but proxy everything else.
	"""

	def __new__( cls, base, site_manager ):
		return ProxyBase.__new__( cls, base )

	def __init__( self, base, site_manager ):
		ProxyBase.__init__( self, base )
		self.__site_manager = site_manager

	@non_overridable
	def getSiteManager(self):
		return self.__site_manager

	@non_overridable
	def setSiteManager(self, new_man):
		raise ValueError()

@component.adapter(ISite,IBeforeTraverseEvent)
def threadSiteSubscriber( new_site, event ):
	"""
	Set the current ``zope.component.hooks`` site to
	the ``new_site`` object found during traversal,
	being careful to maintain any previously installed host (site-name)
	configurations as lower priority than the new site.

	Sites encountered during traversal are expected to have the
	main application site (e.g., ``nti.dataserver``) in their base chain
	so we have access to its configuration and persistent utilities.
	This implies that sites encountered during traversal are either
	synthetic (generated by a traversal adapter to use some particular
	``IComponents``)  or themselves persistent.

	Because of this, when we encounter the root or dataserver folders
	as sites, we take no action.

	We expect that something else takes care of clearing the site.
	"""

	if (IMainApplicationFolder.providedBy( new_site )
		or IRootFolder.providedBy( new_site ) ):
		# TODO: Since we get these events, we could
		# actually replace nti.appserver.tweens.zope_site_tween
		# with this. That's probably the longterm answer.
		return

	# We support exactly three cases:
	# 1. No current site
	# 2. The current site is the site established by get_site_for_site_names
	# 3. The current site is a site previously added by this function.
	# Anything else is forbidden.
	# It turns out that case two and three are exactly the same:
	# we always want to proxy, putting the preserved host components
	# at the end of the new proxy RO.
	current_site = getSite()
	if current_site is None:
		# Nothing to do
		setSite( new_site )
	elif hasattr( current_site.getSiteManager(), 'host_components' ):
		# A site synthesized by get_site_for_site_names
		host_components = current_site.getSiteManager().host_components
		# We need to keep host_components in the bases
		# for the new site. Where to put it is tricky
		# if we want to support multiple layers of overriding
		# of host registrations. Fortunately, the zope.interface.ro
		# machinery does exactly the right thing if we tack host
		# components (which are probably not already in the list)
		# on to the end. If they are in the list already, they
		# stay where they were.
		new_bases = new_site.getSiteManager().__bases__ + (host_components,)
		# TODO: We don't need to proxy the site manager, right?
		# it's almost never special by itself...
		new_site_manager = BasedSiteManager( new_site.__parent__,
											  new_site.__name__,
											  new_bases )
		new_site_manager.host_components = host_components
		new_fake_site = _ProxyTraversedSite( new_site,
											 new_site_manager )

		setSite( new_fake_site )
	else:
		raise ValueError("Unknown kind of site", current_site)


@component.adapter(INewLocalSite)
def new_local_site_dispatcher(event):
	"""
	Dispatches just like an object event,
	that way we can do things based on the type of the
	site manager.

	Note that if the containing ISite is (re)moved, an
	ObjectEvent will be fired for (sitemanager, site-event);
	that is, you subscribe to the site manager and the object moved
	event, but the event will have the ISite as the object property.
	"""
	component.handle(event.manager, event)
