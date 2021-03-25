#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

from zope import component

from nti.appserver.interfaces import IAuthenticatedUserLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider

from nti.dataserver.interfaces import IMissingUser
from nti.dataserver.interfaces import IUser


def safe_links(provider):
    try:
        return provider.get_links()
    except NotImplementedError:
        return ()


def _find_providers_and_links(for_, iface, keeporder=True):
    providers = []
    subscribers = component.subscribers(for_, iface)
    for order, provider in enumerate(subscribers):
        rels = set()
        rels.update(getattr(provider, 'rels', ()))
        # legacy
        rels.add(getattr(provider, 'rel', None))
        rels.add(getattr(provider, '__name__', None))
        rels.discard(None)
        # register w/ priority
        priority = getattr(provider, 'priority', 0)
        providers.append((rels, priority, provider, order))

    result = []
    ignored = set()
    providers = sorted(providers, key=lambda t: t[1], reverse=True)
    for rels, _, provider, order in providers:
        try:
            provider_links = provider.get_links()
        except NotImplementedError:
            ignored.update(rels or ())
        else:
            name = getattr(provider, '__name__', '')
            if name not in ignored:
                links = [x for x in provider_links if x.rel not in ignored]
                if links:
                    result.append((provider, links, order))

    if keeporder:
        result = sorted(result, key=lambda t: t[2])
    return [(p, lnks) for p, lnks, _ in result]

def find_providers_and_links(user, request, keeporder=True):
    if IUser.providedBy(user):
        return _find_providers_and_links((user, request),
                                         IAuthenticatedUserLinkProvider,
                                         keeporder=keeporder)
    elif user is None or IMissingUser.providedBy(user):
        return _find_providers_and_links((request,),
                                         IUnauthenticatedUserLinkProvider,
                                         keeporder=keeporder)


def unique_link_providers(user, request, with_links=False):
    """
    Given a user and the request, find and return all the link
    providers for that user.

    This takes into account the site hierarchy, allowing sub-site configurations
    to override the base configuration based on matching rel.

    :return: An iterable of link objects.
    """
    seen_names = set()
    providers = find_providers_and_links(user, request, True)
    # Subscribers are returned in REVERSE order, that is, from
    # all the bases FIRST...so to let the lower levels win, we reverse again
    # not pyramid.threadlocal.get_current_registry or request.registry, it
    # ignores the site
    for provider, prov_links in reversed(providers):
        # Our objects have a __name__ and they only produce one link
        name = getattr(provider, '__name__', None)
        if name:
            if name in seen_names:
                continue
            seen_names.add(name)
        if with_links:
            yield (provider, prov_links)
        else:
            yield provider


def provide_links(user, request):
    """
    Given a user and the request, find and provide all the links
    for that user.

    This takes into account the site hierarchy, allowing sub-site configurations
    to override the base configuration based on matching rel.

    :return: An iterable of link objects.
    """

    seen_rels = set()
    for _, links in unique_link_providers(user, request, True):
        for link in links:
            if link.rel in seen_rels:
                # In the case of our objects, of course, rel is the same
                # as the name configured in ZCML, and we only provide one link
                continue
            seen_rels.add(link.rel)
            yield link
