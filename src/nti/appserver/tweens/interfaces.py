#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces related to tweens.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface


class IMissingSitePolicy(interface.Interface):
    """
    Called during request handling when no hostname-based
    site can be found.

    This will be registered as a global unnamed utility. Typically
    there will be two implementations, one registered in devmode
    that allows any incoming hostname to be used by returning the
    fallback site, and one registered for production sites that
    enforces the use of a configured site.
    """

    def __call__(request, parent_site):
        """
        If no hostname-based site has been configured, this
        will be called early on during the handling of a request (before
        application code is invoked).

        It can either allow request processing to continue by returning
        the site to use (often simply `parent_site`) or halt
        request processing by raising an (pyramid HTTP) exception such as
        :class:`pyramid.httpexceptions.HTTPBadRequest`.

        :param request: The request being processed. Will already have
                                        the `possible_site_names` attribute set.
        :param parent_site: The root persistent site containing the dataserver.
        :return: The site to use
        """
