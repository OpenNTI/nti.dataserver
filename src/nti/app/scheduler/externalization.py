#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from nti.asynchronous.interfaces import IBaseQueue

from nti.asynchronous.scheduled.interfaces import IScheduledJob

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import LocatedExternalList

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class BaseQueueInterfaceObjectIO(InterfaceObjectIO):

    _ext_iface_upper_bound = IBaseQueue

    def toExternalObject(self, mergeFrom=None, **kwargs):
        result = super(BaseQueueInterfaceObjectIO, self).toExternalObject(mergeFrom, **kwargs)
        ext_self = self._ext_replacement()
        result['jobs'] = LocatedExternalList(ext_self.all())
        return result

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        # TODO
        return super(BaseQueueInterfaceObjectIO, self).updateFromExternalObject(parsed,
                                                                                *unused_args,
                                                                                **unused_kwargs)


class ScheduledJobInterfaceObjectIO(InterfaceObjectIO):

    _ext_iface_upper_bound = IScheduledJob
    _excluded_out_ivars_ = ('callable',)
    
    def toExternalObject(self, mergeFrom=None, **kwargs):
        result = super(ScheduledJobInterfaceObjectIO, self).toExternalObject(mergeFrom, **kwargs)
        ext_self = self._ext_replacement()
        result['callable'] = str(ext_self.callable)  # This could be a function in some cases so we keep it simple
        return result

    def updateFromExternalObject(self, parsed, *unused_args, **unused_kwargs):
        # TODO
        return super(ScheduledJobInterfaceObjectIO, self).updateFromExternalObject(parsed,
                                                                                   *unused_args,
                                                                                   **unused_kwargs)
