#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from datetime import datetime

from pyramid.threadlocal import get_current_request

from zope import component

from nti.appserver.interfaces import IDisplayableTimeProvider

from nti.asynchronous.interfaces import IBaseQueue

from nti.asynchronous.scheduled.interfaces import IScheduledJob

from nti.dataserver.users import User

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import LocatedExternalList

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


def adjust_timestamp(timestamp, request=None):
    request = request if request else get_current_request()
    remote_user = User.get_user(request.remote_user)
    timezone_util = component.queryMultiAdapter((remote_user, request),
                                                IDisplayableTimeProvider)
    date = datetime.utcfromtimestamp(timestamp)
    return timezone_util.adjust_date(date)


class BaseQueueInterfaceObjectIO(InterfaceObjectIO):

    _ext_iface_upper_bound = IBaseQueue

    def toExternalObject(self, mergeFrom=None, **kwargs):
        result = super(BaseQueueInterfaceObjectIO, self).toExternalObject(mergeFrom, **kwargs)
        ext_self = self._ext_replacement()
        result['jobs'] = LocatedExternalList(ext_self.all())
        return result


class ScheduledJobInterfaceObjectIO(InterfaceObjectIO):

    _ext_iface_upper_bound = IScheduledJob
    _excluded_out_ivars_ = frozenset(('callable',
                                      'timestamp'))
    
    def toExternalObject(self, mergeFrom=None, **kwargs):
        result = super(ScheduledJobInterfaceObjectIO, self).toExternalObject(mergeFrom, **kwargs)
        ext_self = self._ext_replacement()
        result['callable'] = str(ext_self.callable)  # This could be a function so we keep it simple
        # Fix up timestamp to be more friendly
        result['execution_time'] = adjust_timestamp(ext_self.timestamp)
        return result

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        # TODO
        return super(ScheduledJobInterfaceObjectIO, self).updateFromExternalObject(parsed,
                                                                                   *unused_args,
                                                                                   **unused_kwargs)
