#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A tween that exists to run green lets after application processing
has completed but before control is handed back to Pyramid (thus,
while the request socket is still open). This is useful
to do long-running processing "in the background" but having
unwound as much of the application stack as possible (thus doing
our best to reclaim and dereference resources).

Insert this tween above all other tweens like
:mod:`zodb_connection_tween`, :mod:`zope_site_tween` and
:mod:`transaction_tween` --- that is, all tweens that constitute part
of the application request handling proper.


To use it, `raise` an :class:`pyramid.httpexceptions.HTTPException`
implementing :class:`.IGreenletsToRun` (such as the class :class:`HTTPOkGreenletsToRun`
provided by this module). You may also return such a value.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gc

import gevent

from zope import interface

from pyramid.httpexceptions import HTTPOk
from pyramid.httpexceptions import HTTPException


class IGreenletsToRun(interface.Interface):
    greenlets = interface.Attribute("A sequence of greenlets to join")
    response = interface.Attribute("The pyramid response to return")


@interface.implementer(IGreenletsToRun)
class HTTPOkGreenletsToRun(HTTPOk):

    greenlets = ()
    response = None


class greenlet_runner_tween(object):
    """
    The greenlet runner.
    """

    __slots__ = ('handler')

    def __init__(self, handler, registry):
        self.handler = handler

    def __call__(self, request):
        try:
            result = self.handler(request)
        except HTTPException as e:
            if not IGreenletsToRun.providedBy(e):
                raise
            result = e

        if not IGreenletsToRun.providedBy(result):
            return result

        # Ok, our time to shine. First, drop our
        # local reference to the request, just for GPs
        del request
        # Next, these are relatively rare, so this is a reasonable
        # time to clean up weak refs and otherwise do gc
        gc.collect()
        # Finally, run the greenlets
        gevent.joinall(result.greenlets)
        return result.response
greenlet_runner_tween_factory = greenlet_runner_tween
