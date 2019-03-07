#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides a tween for integrating Pyramid with the ZCA notion of a site.
This sets up the default (root) site before traversal happens. It also
uses the host name to install applicable configuration, if found.

With the help of :func:`nti.dataserver.site.threadSiteSubscriber`,
traversal can then use listeners to set sub-sites as they are
encountered (see :mod:`~nti.appserver.traversal`), while also
maintaining the host-level configuration.

We consider the request to be properly created after this tween takes effect,
so it broadcasts a :class:`IObjectCreatedEvent` to that purpose.

Request Modifications
=====================

After this tween runs, the request has been modified in the following ways.

* It has a property called ``possible_site_names``, which is an
  iterable of the virtual site names to consider. This is also in the
  WSGI environment as ``nti.possible_site_names``. (See :func:`_get_possible_site_names`)

* It has a method called ``nti_gevent_spawn`` for replacing :func:`gevent.spawn`
  while maintaining the current request.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import platform

import gevent

import transaction

from zope import component
from zope import interface

from zope.component.hooks import getSite
from zope.component.hooks import setSite
from zope.component.hooks import setHooks
from zope.component.hooks import clearSite

from zope.lifecycleevent import created

from pyramid.threadlocal import manager
from pyramid.threadlocal import get_current_request

from pyramid.httpexceptions import HTTPBadRequest

from nti.base._compat import text_


def _get_possible_site_names(request):
    """
    Look for the current request, and return an ordered list
    of site names the request could be considered to be for.
    The list is ordered in preference from most specific to least
    specific. The HTTP origin is considered the most preferred, followed
    by the HTTP Host.

    :return: An ordered sequence of string site names. If there is no request
            or a preferred site cannot be found, returns an empty sequence.
    """

    result = []

    if b'origin' in request.headers:
        # TODO: The port splitting breaks on IPv6
        # Origin comes in as a complete URL, host and potentially port
        # Sometimes it comes in blank (unit tests, mostly, that don't use proper HTTP libraries)
        # so the below is robust against that, as well as deliberately
        # malformed input
        origin = request.headers[b'origin'].decode('ascii')
        __traceback_info__ = origin
        if origin and '//' in origin and ':' in origin:
            host = origin.split('//')[1].split(":")[0]
            result.append(host.lower())

    if request.host:
        # Host is a plain name/IP address, and potentially port
        host = request.host.split(':')[0].lower()
        if host not in result:  # no dups
            result.append(host)

    for blacklisted in ('localhost', '0.0.0.0'):
        if blacklisted in result:
            result.remove(blacklisted)

    return result


def _gevent_spawn(run, *args, **kwargs):
    """
    Preserves the current pyramid request.
    """
    tl_dict = manager.get().copy()

    def _run(*a, **kw):
        manager.push(tl_dict)
        return run(*a, **kw)
    return gevent.spawn(run, *args, **kwargs)

# Make zope site managers a bit more compatible with pyramid.
from zope.cachedescriptors.property import readproperty

from zope.site.site import LocalSiteManager as _ZLocalSiteManager


def _notify(self, *events):
    for _ in self.subscribers(events, None):
        pass

_ZLocalSiteManager.notify = _notify
_ZLocalSiteManager.has_listeners = True

# make the settings a readable property but still overridable
# on an instance, just in case
_ZLocalSiteManager.settings = readproperty(lambda s: get_current_request().nti_settings)


class site_tween(object):
    """
    Within the scope of a transaction, gets a connection and installs our
    site manager. Records the active user and URL in the transaction.

    Public for testing, mocking. The alternative to using a class is
    using a closure that captures the handler, but that's not
    mockable.

    .. warning ::
            This only sets the current ZCA site. It *does not*
            set the request's registry, or Pyramid's current registry
            (:func:`pyramid.threadlocal.get_current_registry`). These must be
            left as the global registry. Our sites extend this global registry
            so it would seem that all the settings would be available.
            However, Pyramid configures some things lazily and would thus
            place some configuration in local sites; moreover, this
            configuration is often not-persistent and causes errors committing
            transactions (and we don't want to save it anyway). This is
            specifically seen with renderers and renderer factories. Thus, one
            must be careful using pyramid APIs that touch the current registry if there is a chance
            that site-local configuration should be used. Fortunately, these APIs are rare.

    """

    __slots__ = ('handler',)

    def __init__(self, handler):
        self.handler = handler

    def __call__(self, request):
        # conn.sync() # syncing the conn aborts the transaction.
        site = request.nti_zodb_root_connection.root()['nti.dataserver']
        self._debug_site(site)
        self._add_properties_to_request(request)

        site = _get_site_for_request(request, site)
        request.environ['nti.current_site'] = site.__name__

        setSite(site)
        __traceback_info__ = self.handler
        # See comments in the class doc about why we cannot set the Pyramid
        # request/current site
        try:
            self._configure_transaction(request)
            created(request)
            return self.handler(request)
        finally:
            clearSite()

    def _add_properties_to_request(self, request):
        request.environ['nti.pid'] = os.getpid()  # helpful in debug tracebacks
        request.environ['nti.node'] = platform.node()
        names = tuple(_get_possible_site_names(request))
        request.environ['nti.possible_site_names'] = names
        request.environ['nti.gevent_spawn'] = _gevent_spawn
        # The "proper" way to add properties is with request.set_property, but
        # this is easier and faster.
        request.possible_site_names = names
        request.nti_settings = request.registry.settings  # shortcut
        request.nti_gevent_spawn = _gevent_spawn
        # In [15]: %%timeit
        #   ....: r = pyramid.request.Request.blank( '/' )
        #   ....: p(r)
        #   ....:
        # 100000 loops, best of 3: 7.8 us per loop
        #
        # In [16]: %%timeit # set_property uses type() and adds 50us
        #   ....: r = pyramid.request.Request.blank( '/' )
        #   ....: r.set_property( p )
        #   ....: r.p
        #   ....:
        # 10000 loops, best of 3: 57.4 us per loop

    def _configure_transaction(self, request):
        # NOTE: We have dropped support for pyramid_tm due to breaking changes in 0.7
        # and instead require our own .tweens.transaction_tween
        # Now (and only now, that the site is setup since that's when we can access the DB
        # and get the user) record info in the transaction
        uid = request.authenticated_userid
        if uid:
            transaction.get().setUser(text_(uid))

    def _debug_site(self, new_site):
        if __debug__:  # pragma: no cover
            old_site = getSite()
            # Not sure what circumstances lead to already having a site
            # here. Have seen it at startup (also with some of the new test machinery).
            # Force it back to none (?)
            # It is very bad to raise an exception here, it interacts
            # badly with logging
            try:
                assert old_site is None or old_site is new_site, \
                       "Should not have a site already in place"
            except AssertionError:
                logger.debug("Should not have a site already in place: %s",
                             old_site, exc_info=True)

from nti.site.site import get_site_for_site_names

from .interfaces import IMissingSitePolicy


def _get_site_for_request(request, parent_site):
    """
    In the context of a request, looks up the named site for the request.

    If this is not found, uses a registered utility object to decide
    whether to continue with the default site or require a properly
    configured site by forcing an error.

    """
    site_names = request.possible_site_names
    found_site = get_site_for_site_names(site_names, site=parent_site)
    if found_site is parent_site:
        # This design adds overhead when a site is not found. This should be
        # uncommon during production although common at development time.
        gsm = component.getGlobalSiteManager()
        found_site = gsm.getUtility(IMissingSitePolicy)(request, parent_site)
        # We could reduce the overhead a bit by looking up
        # the utility in the tween factory. The next step would be
        # to abstract  this entire function to be part of the policy
        # (which of course is looked up at factory time). But
        # the ZCA may not have been configured at the time the factory
        # is invoked so we'd have to be careful.
    return found_site


def _DevmodeMissingSitePolicy(request, parent_site):
    return parent_site
interface.directlyProvides(_DevmodeMissingSitePolicy, IMissingSitePolicy)


def _ProductionMissingSitePolicy(request, parent_site):
    raise HTTPBadRequest("Invalid site")
interface.directlyProvides(_ProductionMissingSitePolicy, IMissingSitePolicy)


def site_tween_factory(handler, registry):
    """
    Within the scope of a transaction, gets a connection and installs our
    site manager. Records the active user and URL in the transaction.

    """
    # Our site setup
    # If we wanted to, we could be setting sites up as we traverse as well;
    # traverse hooks are installed to do this
    setHooks()
    return site_tween(handler)
