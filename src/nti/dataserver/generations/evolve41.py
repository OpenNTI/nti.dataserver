#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 41 evolver, which migrats user preferences

$Id: evolve40.py 18080 2013-04-10 18:32:02Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 41

import zope.intid

from zope import component
from zope import interface
from zope.component.hooks import site, setHooks

from zope.security.interfaces import IPrincipal
from zope.security.interfaces import IParticipation

from zope.security.management import newInteraction, endInteraction

from zc import intid as zc_intid

from nti.dataserver import interfaces as nti_interfaces

@interface.implementer(IParticipation)
class _Participation(object):

    __slots__ = 'interaction', 'principal'

    def __init__(self, principal):
        self.interaction = None
        self.principal = principal

def migrate_preferences(user):
    principal = IPrincipal(user)
    newInteraction(_Participation(principal))
    try:
        pass
    finally:
        endInteraction()

def evolve(context):
    setHooks()
    ds_folder = context.connection.root()['nti.dataserver']
    lsm = ds_folder.getSiteManager()

    ds_intid = lsm.getUtility(provided=zope.intid.IIntIds)
    component.provideUtility(ds_intid, zope.intid.IIntIds)
    component.provideUtility(ds_intid, zc_intid.IIntIds)

    with site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"
        users = ds_folder['users']
        for user in users.values():
            if nti_interfaces.IUser.providedBy(user):
                migrate_preferences(user)
