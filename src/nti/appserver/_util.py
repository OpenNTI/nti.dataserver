#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Common utility classes and functions for the appserver.

.. $Id$
"""

from __future__ import print_function, absolute_import, division

logger = __import__('logging').getLogger(__name__)

import gc as GC

from gevent.util import format_run_info

from zope import interface

from zope.event import notify

from zope.location.interfaces import ILocation

from pyramid.security import remember

from nti.appserver.interfaces import UserLogonEvent

from nti.dataserver.interfaces import ICreated

from nti.dataserver import interfaces as nti_interfaces

from nti.dataserver.users.users import User

import zope.deferredimport
zope.deferredimport.initialize()
zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.renderers.caching",
    "nti.app.renderers.caching",
    # This was a class, just in case there are pickles this should stay
    # here even after all clients are updated
    "_UncacheableInResponseProxy",
    "uncached_in_response"
)


def logon_userid_with_request(userid, request, response=None):
    """
    Mark that the user has logged in. This is done by notifying
    a :class:`nti.appserver.interfaces.IUserLogonEvent`.

    :param basestring userid: The account name that should be logged in.
    :param request: Pyramid request that is active and responsible for the login.
    :param response: If given, then the response will be given the headers
           to remember the logon.
    :raise ValueError: If the userid does not belong to a valid user.
    """

    # Send the logon event
    dataserver = request.registry.getUtility(nti_interfaces.IDataserver)
    user = User.get_user(username=userid, dataserver=dataserver)
    if not user:
        raise ValueError("No user found for %s" % userid)
    logon_user_with_request(user, request, response=response)


def logon_user_with_request(user, request, response=None):
    """
    Mark that the user has logged in. This is done by notifying
    a :class:`nti.appserver.interfaces.IUserLogonEvent`.

    :param user: The user object that should be logged in.
    :param request: Pyramid request that is active and responsible for the login.
    :param response: If given, then the response will be given the headers
            to remember the logon. Otherwise, the request's response will.
    :raise ValueError: If the user is None.
    """

    # Send the logon event
    if not nti_interfaces.IUser.providedBy(user):
        raise ValueError("No valid user given")

    notify(UserLogonEvent(user, request))

    response = response or getattr(request, 'response')
    if response:
        encoded = user.username.encode('utf-8')
        response.headers.extend(remember(request, encoded))
        response.set_cookie(b'username', encoded)  # the web app likes this


def dump_obj_growth(limit=20):
    """
    Request information about the most common object types in the heap,
    and the growth rate since the previous call to this method.

    Returns a (unicode) string.
    """

    import objgraph

    from io import BytesIO
    out = BytesIO()
    GC.collect()
    out.write(b"\nObjects\n")
    objgraph.show_most_common_types(limit=limit, file=out)
    out.write(b'\nGrowth\n')
    objgraph.show_growth(limit=limit, file=out)

    return out.getvalue().decode("ascii")


def dump_stacks():
    """
    Request information about the running threads of the current process.

    :return: A sequence of text lines detailing the stacks of running
            threads and greenlets. (One greenlet will duplicate one thread,
            the current thread and greenlet.)
    """
    return format_run_info()


def dump_info(db_gc=False):
    """
    Dump diagnostic info to a string.
    """
    body = '\n'.join(dump_stacks())
    body += dump_obj_growth()
    body += '\n'.join(dump_database_cache(db_gc))
    return body


def dump_stacks_view(request):
    body = dump_info()
    print(body)
    request.response.text = body
    request.response.content_type = 'text/plain'
    return request.response


from zope import component

from ZODB.interfaces import IDatabase


def dump_database_cache(gc=False):
    """
    Request information about the various ZODB database caches
    and returns a sequence of text lines describing them.

    :keyword gc: If set to True, then each database will be
            asked to minimize its cache.
    """
    lines = ['Databases']
    db = component.queryUtility(IDatabase)
    if db is None:
        lines.append("\tNo database")
        return lines

    databases = db.databases or {'': db}
    for name, value in databases.items():
        lines.append("Database\tCacheSize")
        lines.append("%s\t%s" % (name, value.cacheSize()))

        lines.append("\tConnections")
        for row in value.cacheDetailSize():
            lines.append("\t\t%s" % row)

        lines.append("\tTypes")
        for kind, count in sorted(value.cacheDetail(), key=lambda x: x[1]):
            lines.append('\t\t%s\t%s' % (kind, count))

        lines.append("\tStorage Cache Stats")
        try:
            lines.append(
                repr(value._storage._cache.clients_local_first[0].stats())
            )
        except AttributeError:
            lines.append("\t\tNo storage cache stats")

        if gc:
            value.cacheMinimize()
            GC.collect()

    return lines


zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.externalization.internalization",
    "nti.app.externalization.internalization",
    "create_modeled_content_object",
    "class_name_from_content_type",
    "read_body_as_external_object",
    "update_object_from_external_object")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.externalization.error",
    "nti.app.externalization.error",
    "raise_json_error")


def link_belongs_to_user(link, user):
    link.__parent__ = user
    link.__name__ = ''
    interface.alsoProvides(link, ILocation)
    try:
        link.creator = user
        interface.alsoProvides(link, ICreated)
    except AttributeError:
        pass
    return link
