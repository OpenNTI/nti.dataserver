#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from nti.appserver.policies.interfaces import IRequireSetPassword

from nti.coremetadata.interfaces import IEntity

from nti.dataserver.users.interfaces import IPasswordChangedEvent


@component.adapter(IEntity, IPasswordChangedEvent)
def _handle_password_changed(entity, _unused_event):
    """
    Ensure that the IRequireSetPassword interface, if applied, is
    removed.
    """
    if IRequireSetPassword.providedBy(entity):
        interface.noLongerProvides(entity, IRequireSetPassword)
