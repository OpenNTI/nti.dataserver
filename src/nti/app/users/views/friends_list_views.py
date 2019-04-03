#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid.view import view_config

from nti.appserver.ugd_edit_views import UGDPutView

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IFriendsList


@view_config(route_name='objects.generic.traversal',
             renderer='rest',
             context=IFriendsList,
             name='++fields++friends',
             permission=nauth.ACT_UPDATE,
             request_method='PUT')
class _FriendsListsFriendsFieldUpdateView(UGDPutView):

    inputClass = (list, dict)

    def _get_object_to_update(self):
        return self.request.context

    def _transformInput(self, externalValue):
        if isinstance(externalValue, (list,tuple)):
            return {"friends": externalValue}

        newFriends = None
        additions = set(externalValue.get('additions') or ())
        removals = set(externalValue.get('removals') or ())
        if additions != removals:
            newFriends = set([x.username for x in self.request.context])
            for x in (additions - removals):
                if x not in newFriends:
                    newFriends.add(x)
            newFriends = newFriends - (removals - additions)

        return {"friends": newFriends}
