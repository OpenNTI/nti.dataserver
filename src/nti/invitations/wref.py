#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weak references for content units.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from functools import total_ordering

from zope import component
from zope import interface

from nti.invitations.interfaces import IInvitation
from nti.invitations.interfaces import IInvitationsContainer

from nti.property.property import alias

from nti.schema.eqhash import EqHash

from nti.wref.interfaces import IWeakRef

logger = __import__('logging').getLogger(__name__)

# pylint:disable=I0011,W0212


@total_ordering
@EqHash('_code')
@component.adapter(IInvitation)
@interface.implementer(IWeakRef)
class InvitationWeakRef(object):

    __slots__ = ('_code',)

    code = alias('_code')

    def __init__(self, invitation):
        self._code = invitation.code

    def __call__(self):
        container = component.getUtility(IInvitationsContainer)
        return container.get_invitation_by_code(self._code)

    def __getstate__(self):
        return (1, self._code)

    def __setstate__(self, state):
        assert state[0] == 1
        self._code = state[1]

    def __str__(self):
        return self._code

    def __lt__(self, other):
        try:
            return self._code < other._code
        except AttributeError:  # pragma: no cover
            return NotImplemented

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__,
                           self._code)
