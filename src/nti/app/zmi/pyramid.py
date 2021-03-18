#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides code for bridging pyramid views to zope views. Useful for
running things like the Zope Management Interface (ZMI) in the context
of a pyramid application.

TODO This is currently a WIP and not ready for any sort of production
deployment. If this is the approach we end up going (as oppossed to a
higher level integration at the wsgi layer) perhaps it makes sense to
shore up and move to nti.app.pyramid_zope. We are nowhere near that currently.

.. $Id$
"""

#from pyramid.interfaces import IViewMapper
#from pyramid.interfaces import IViewMapperFactory

from zope import component
from zope import interface

from zope.publisher.interfaces import IPublishTraverse

from zope.publisher.interfaces.browser import IBrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IBrowserPublisher

from zope.publisher.publish import mapply

from zope.publisher.skinnable import setDefaultSkin

from zope.security.checker import canAccess

from nti.base._compat import text_

from nti.appserver import httpexceptions as hexc

logger = __import__('logging').getLogger(__name__)

def configure_zmi_views(pyramid_config):
    """
    Find zope.publisher "views" and bridge them into pyramid views
    that can be traversed and called via our traditional pyramid
    stack. The zope views we care about right now are primarily those
    used by ZMI, but it's hard to target those specifically. As this
    looks for registered adapters we should be invoked after any
    configuration that sets up zmi is processed.

    TODO We capture things a bit more broadly then I think we would
    like right now.
    """

    # Rip through the component registry looking for zope "views".
    # These are multiadapters from (Interface, IDefaultBrowserLayer) to things
    # that we can ultimately invoke via zope.publisher.publish.mappy.
    # TODO right now we look for any adapters for things that isOrExtend Interface
    # and IDefaultBrowerLayer. We don't filter any further. Seems like we should at
    # least do some filtering based on the adapter we find???

    # TODO surely there is a better way to accomplish this
    sm = component.getSiteManager()
    toregister = [ v for v in sm.registeredAdapters() if len(v.required) == 2 \
                   and all([x.isOrExtends(y) for x,y \
                            in zip(v.required, [interface.Interface, IDefaultBrowserLayer])])]

    # Now we have a set of zope "views". We need to register them as pyramid views
    logger.info('Will bridge %i zope views to pyramid', len(toregister))
    for view in toregister:
        logger.debug('Registering view %s for %s name = %s', view.factory, view.required[0], view.name)

        # Of course calling what are zope views from pyramid isn't exactly straight forward.
        # The stacks are entirely different and there is bridging work that must happen.
        # We use a custom IViewMapper to control how we invoke these particular views (and
        # a corresponding IViewMapperFactory). This allows us to do things like bridge
        # our pyramid request to an zope IBrowserRequest, do any further traversing,
        # security checks, etc.

        # TODO note the lack of permission here. Zope views rely heavily on zope.security.checker
        # and friend to implement per attribute/method security checks. Our IViewMapper callable
        # handles some of that via the existing zope functions and has place holders for others.
        # We might be able to build a pyramid acl based on the zope.security permission on the __call__
        # method of the zope "view" if one exists, but, as we found out these "views" aren't always
        # views and they rely on further traversing to get so something with an actual
        # security check. More to come and investigate here...
        pyramid_config.add_view(view.factory,
                                name=view.name,
                                # The first thing we adapt form is our pyramid context
                                for_=view.required[0],
                                # TODO Given our custom mapper I'm not sure route is required here?
                                route_name='objects.generic.traversal',
                                mapper=_vmfactory)

class ZopeViewCaller(object):
    """
    A callable object whose instances can be used as the return value
    of an IViewMapper. This encapsulates the bulk of the logic involved
    with correctly invoking a zope view via pyramid.
    """
    
    def __init__(self, zview):
        self.view = zview

    def __call__(self, context, request):
        """
        TODO much of this was reversed engineered through trial and error
        over the course of several hours before I found and understood how
        all the zope pieces fit together with https://github.com/zopefoundation/zope.publisher/blob/9fa4a2cda8999c61f249995a7b421b4710135050/src/zope/publisher/publish.py#L129

        Some pieces from that have been added, but there are likely still things we aren't doing
        and some places where we could leverage existing zope code.
        """

        # The first thing we need to do is turn our pyramid request into an
        # IBrowserRequest that zope knows how to deal with. We have an incomplete
        # implementation. I believe most of the remaining bugs have to do with
        # missing/incomplete or poorly implemented features of the request.
        request = IBrowserRequest(request)

        # Now set our default skin on the request.
        setDefaultSkin(request)

        # Now we invoke our zope "view". This isn't necessarily something that returns
        # a response given a request, it could be, but isn't always. Rather it's an object
        # were we can begin the zope flow of traversing any remaining path components.
        ob = self.view(context, request)

        # Many zope views are registered with names like `@@` which stop our pyramid traversal
        # We may have subpaths that we can use to zope.traverse our object deeper. TODO
        # I suspect this loop and the loop after it can possibly generalized given a slightly
        # better understanding of IPUblishTraverse and IBrowserPublisher interfaces.
        subpath = list(request.subpath)
        while subpath:
            ob = IPublishTraverse(ob).publishTraverse(request, subpath.pop())

        # There are a couple things happening here. zope has the concept of browserDefaults
        # which act as a default view for a given object and request. Those browserDefaults
        # could be entirely different objects with additional subpaths that need traversed
        # Do that here.
        while True:
            bp = IBrowserPublisher(ob, None)
            if bp is None:
                break
            ob, path = bp.browserDefault(request)
            # TODO we could proxy here through zope.security.checker.ProxyFactory
            if not path:
                break
            path = list(path)
            while path:
                ob = IPublishTraverse(bp).publishTraverse(request, path.pop())

        # Ok now we are pretty sure we have a callable that we can invoke and get something
        # that resembles a response (or as a side effect sets the response on our request).
        # This callable maps most closely to how we think about views on the pyramid side of things.
        res = ob

        # TODO it's not clear to me if we need to make a security checker call explicitly here
        # going through IPublishtraverse seems to always return security proxied objects, and
        # the adapters registered are also usually security proxied. That said, I think there
        # are cases here were res isn't security proxied and we need to either wrap it ourselves
        # or check canAccess first. Need to revisit this.
        # if not canAccess(res, '__call__'):
        #   from IPython.core.debugger import Tracer; Tracer()()
        #   raise hexc.HTTPForbidden()
        
        # Things aren't as simple as simply calling res. There is black magic in zope.publisher.publish
        # that invokes the callable based on it's signature potentially supply kwargs from the request
        # params. That utlimately boils down to mapply.
        # TODO the second tuple is typically IBrowserRequest.getPositionalArguments which we don't
        # implement and most implementations return an empty tuple anyway. Need to probably implement
        # that on our bridged request.
        result = mapply(res, tuple(), request)

        # Calling res may return something that can be used as a response body, or it may
        # have just manipulated request.response directly.
        # TODO the code in zope.publisher.publish is more robust and has another layer of indirection
        # similar to pyramid renderers that we need to be using.
        if result:
            if isinstance(result, bytes):
                request.response.body = result
            else:
                request.response.text = text_(result)
        return request.response

#@interface.implementer(IViewMapper)
def _vm(view):
    return ZopeViewCaller(view)

#@interface.implementer(IViewMapperFactory)
def _vmfactory(**kwargs):
    return _vm
