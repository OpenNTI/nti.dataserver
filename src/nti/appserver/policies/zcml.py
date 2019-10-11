#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import component

from zope import interface

from zope.component.zcml import utility

from nti.schema.field import TextLine

from nti.appserver.policies.interfaces import ICommunitySitePolicyUserEventListener

from nti.appserver.policies.site_policies import adult_community_site_policy_factory

from nti.schema.interfaces import find_most_derived_interface

class ICreateSitePolicy(interface.Interface):

    brand = TextLine(title=u'The site BRAND',
                     required=False)

    display_name = TextLine(title=u'The site\'s display name',
                            required=False)

    com_username = TextLine(title=u'The username for the site community',
                            required=False)

    com_alias = TextLine(title=u'The alias for the site community',
                         required=False)

    com_realname = TextLine(title=u'The realname for the site community',
                            required=False)

    # If they provide a realname or alias they must also provide a username
    @interface.invariant
    def comm_username_if_display_name(self):
        _check_username_if_display_name(self.comm_username, self.com_alias, self.com_realname)
        

def _check_username_if_display_name(username, alias, realname):
    """
    If they provide a realname or alias they must also provide a username.
    """
    if not username and ( realname or alias ):
        raise interface.Invalid(u'com_username must be provided if com_alias or com_realname is specified.')

def create_site_policy(context,
                             brand=None,
                             display_name=None,
                             com_username=None,
                             com_alias=None,
                             com_realname=None):

    # Ideally we could let the interface invariant handle this, but the configuration machinary
    # doesn't seem to do anything with invariants.
    _check_username_if_display_name(com_username, com_alias, com_realname)
    
    policy = adult_community_site_policy_factory(brand,
                                                 display_name,
                                                 com_username,
                                                 com_alias,
                                                 com_realname)

    iface = find_most_derived_interface(policy, ICommunitySitePolicyUserEventListener)    
    utility(context, provides=iface, component=policy)
