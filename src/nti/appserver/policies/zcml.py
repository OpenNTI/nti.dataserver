#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class

from zope import interface

from zope.component.zcml import utility

from zope.configuration.fields import GlobalObject

from nti.schema.field import TextLine

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.appserver.policies.site_policies import default_site_policy_factory

from nti.schema.interfaces import find_most_derived_interface

class ICreateSitePolicy(interface.Interface):

    factory = GlobalObject(title=u'A factory returning a configured policy',
                           required=False)

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

    default_sender_email = TextLine(title=u'An optional email sender',
                                    required=False)

    # If they provide a realname or alias they must also provide a username
    @interface.invariant
    def comm_username_if_display_name(self):
        _check_username_if_display_name(self.comm_username, self.com_alias, self.com_realname)


def _check_username_if_display_name(com_username=None, com_alias=None, com_realname=None, **kwargs):
    """
    If they provide a realname or alias they must also provide a username.
    """
    if not com_username and ( com_realname or com_alias ):
        raise interface.Invalid(u'com_username must be provided if com_alias or com_realname is specified.')

def create_site_policy(context, factory=default_site_policy_factory, **kwargs):

    # Ideally we could let the interface invariant handle this, but the configuration machinary
    # doesn't seem to do anything with invariants.
    _check_username_if_display_name(**kwargs)

    policy = factory(**kwargs)

    iface = find_most_derived_interface(policy, ISitePolicyUserEventListener)
    utility(context, provides=iface, component=policy)
