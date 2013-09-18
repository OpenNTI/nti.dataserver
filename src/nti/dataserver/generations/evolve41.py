#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 41 evolver, which migrats user preferences

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 41

import zope.intid

from zope import component
from zope import interface
from zope.component.hooks import site, setHooks

from zope.annotation import IAnnotations

from zope.preference import interfaces as pref_interfaces

from zope.security.interfaces import IPrincipal
from zope.security.interfaces import IParticipation

from zope.security.management import newInteraction, endInteraction

from zc import intid as zc_intid

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

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
        ep = user_interfaces.IEntityPreferences(user)
        kalturaPreferFlash = ep.get('kalturaPreferFlash')
        if kalturaPreferFlash is not None:
            webapp = component.getUtility(pref_interfaces.IPreferenceGroup, name='WebApp')
            webapp.preferFlashVideo = kalturaPreferFlash

        presence = ep.get('presence', {})
        current = presence.get('active')
        if current and current in presence:
            current = presence.get(presence, {})
            cp_active = component.getUtility(pref_interfaces.IPreferenceGroup, name='ChatPresence.Active')
            status = presence.get('status')
            if status:
                cp_active.status = unicode(status)

        for key in ('Available', 'Away', 'DND'):
            entry = presence.get(key.lower(), {})
            status = entry.get('status')
            pref_grp = component.getUtility(pref_interfaces.IPreferenceGroup, name='ChatPresence.%s' % key)
            if status:
                pref_grp.status = unicode(status)
        
        # remove prefrerence annotation
        IAnnotations(user).pop("%s.%s" % (ep.__class__.__module__, ep.__class__.__name__), None)
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
