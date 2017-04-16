#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for writing Pyramid exception views that work with
:func:`pyramid.tweens.excview_tween_factory`. These are second-chance
view callables that get run when an uncaught exception percolates up
to Pyramid (an exception that is generally not a subclass of
:class:`pyramid.httpexceptions.HTTPException`).

General notes on exception views:

* They are called when an exception would otherwise make it
  all the way up to the WSGI layer, typically resulting in a
  HTTP 500 status.

* Their very existence will mask the original exception (unless they
  re-raise it; the original exception is their ``context`` argument).
  Likewise, any exception they raise will be propagated to the
  WSGI layer.

* When they are called, the request they are given has its original
  ``response`` (if any) wiped out.

* When they are called, the request has a property ``exc_info``
  that contains the value of :func:`sys.exc_info` when the exception
  was caught. Likewise, the caught exception, which is also the context
  of the view, is in the property ``exception``.

* They are called when the stack has unwound, meaning any tweens
  that sit below them have been released. This may mean that
  transaction support and database connections are gone, if set
  up by tweens that tear them down directly and not with a response
  callback or request finished callback.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from pyramid.httpexceptions import exception_response


class AbstractRateLimitedExceptionView(object):
    """
    An abstract base class that limits the rate at which
    auxilliary actions are taken when \"handling\" a request.

    This object has the properties ``context`` and ``request``.

    You *may* override the method :meth:`_do_aux_action` to take
    auxiliary actions; it will be called no more often than
    :attr:`aux_period` seconds globally, within this process, for all
    instances of this class. That means that if you subclass this
    class and register it for, say, :class:`LookupError`, then when
    :class:`LookupError` or a subclass like
    :class:`ComponentLookupError` is raised, no more often than
    ``aux_period`` will ``_do_aux_action`` be called. Likewise, if you
    *do not* subclass this class, then the limit will apply across all
    registrations that do not subclass. The default is to do nothing.
    Exceptions raised by this method will be ignored.

    You *may* override the method :meth:`_do_create_response` to
    create the response returned to the caller. The default
    is to return a simple HTTP 500; exceptions raised by this method
    will be ignored (resulting in a HTTP 500).
    """

    #: The interval of time between calls to :meth:`_do_aux_action`
    #: The default is to take the aux action no more than once every
    #: two minutes.
    aux_period = 120

    def __init__(self, context, request):
        self.context = context
        self.request = request

    _last_aux_time = property(lambda self: getattr(type(self), '_last_aux_time_', 0),
                              lambda self, nv: setattr(type(self), '_last_aux_time_', nv),
                              doc="The last time we called the aux action. This is kept per-class.")

    def __call__(self):
        now = time.time()
        if now > self._last_aux_time + self.aux_period or not self._last_aux_time:
            # Order is important here to keep this atomic,
            # aux could cause a greenlet switch
            self._last_aux_time = now
            try:
                self._do_aux_action()
            except StandardError:
                logger.exception("Failed to perform aux action.")

        try:
            response = self._do_create_response()
        except StandardError:
            logger.exception("Failed to create response")
            response = self.__create_default_response()

        return response

    def _do_aux_action(self):  # pragma: no cover
        pass

    def _do_create_response(self):
        """
        Create and return the response object.
        """
        return self.__create_default_response()

    def __create_default_response(self):
        return exception_response(500)


from zope.exceptions.exceptionformatter import format_exception


class EmailReportingExceptionView(AbstractRateLimitedExceptionView):
    """
    Reports exceptions via email (if :mod:`paste.exceptions` is
    configured to do so) in a rate limited fashion, while still
    allowing us to customize the response.

    This depends on a properly configured instance of
    :class:`paste.exceptions.errormiddleware` being in the traceback.
    """

    def _find_exception_handler(self):
        """
        Grovel through the traceback looking for an errormiddleware
        and return a function of two args, (exc_info, environ).
        """

        # The traceback is from the top down, in a linked
        # list until tb_next is None. Each traceback object
        # has tb_frame, which has tb_locals. We will find
        # paste when `self` is in tb_locals with an `exception_handler`
        # attribute

        tb = self.request.exc_info[2]
        while tb is not None:
            if hasattr(tb.tb_frame.f_locals.get('self'), 'exception_handler'):
                return tb.tb_frame.f_locals['self'].exception_handler
            tb = tb.tb_next

        # Nark, didn't find it.
        del tb

        # Best we can do now is report it to the logs; we're in
        # the throttled block here, so this shouldn't be overwhelming
        def failed(exc_info, environ):
            fmt = format_exception(*exc_info)
            fmt = [x.decode('ascii', 'ignore') if isinstance(x, bytes) else x
                   for x in fmt]
            fmt = '\n\t'.join(fmt)
            logger.warn("Failed to find errormiddleware, not reporting exception:\n%s",
                        fmt)
        return failed

    def _do_aux_action(self):
        handler = self._find_exception_handler()
        handler(self.request.exc_info, self.request.environ)


# TODO: Best place for this?
from pyramid.view import view_config

from ZODB.POSException import StorageError


@view_config(context=StorageError)
class ZODBStorageErrorExceptionView(EmailReportingExceptionView):
    """
    Reporter and handler for ZODB StorageErrors.
    """


@view_config(context='redis.exceptions.ResponseError')
@view_config(context='redis.exceptions.ConnectionError')
class RedisErrorExceptionView(EmailReportingExceptionView):
    """
    Reporter and handler for certain Redis Errors.
    """


def _cleanup(base=None, seen=None):
    """
    At the end of a test, reset all aux times to 0
    """
    if seen is None:
        seen = set()
    if base is None:
        base = AbstractRateLimitedExceptionView
    if base in seen:
        return

    setattr(base, '_last_aux_time_', 0)
    for sub in base.__subclasses__():
        _cleanup(sub, seen)


import zope.testing.cleanup
zope.testing.cleanup.addCleanUp(_cleanup)
