#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Link providers admin views

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope.annotation import IAnnotations

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.appserver import logon

from nti.appserver.link_providers import link_provider

from nti.appserver.utils import MessageFactory as _

from nti.appserver.utils import _JsonBodyView

from nti.dataserver import users
from nti.dataserver import authorization as nauth

_view_defaults = dict(route_name='objects.generic.traversal',
                      renderer='rest',
                      permission=nauth.ACT_READ,
                      request_method='GET')
_view_admin_defaults = _view_defaults.copy()
_view_admin_defaults['permission'] = nauth.ACT_MODERATE

_post_view_defaults = _view_defaults.copy()
_post_view_defaults['request_method'] = 'POST'

_admin_view_defaults = _post_view_defaults.copy()
_admin_view_defaults['permission'] = nauth.ACT_MODERATE


class _ResetGenerationLink(_JsonBodyView):

    link_id = u''
    link_name = u''

    def __call__(self):
        values = self.readInput()
        username = values.get('username') or values.get('user')
        if not username:
            raise hexc.HTTPUnprocessableEntity(_('Must specify a username'))
        user = users.User.get_user(username)
        if not user:
            raise hexc.HTTPUnprocessableEntity(_('User not found'))

        annotations = IAnnotations(user)
        link_dict = annotations.get(link_provider._GENERATION_LINK_KEY, None)
        if link_dict is not None:
            link_dict[self.link_id] = ''
            logger.info("Resetting %s for user %s" % (self.link_name, user))
        return hexc.HTTPNoContent()


@view_config(name="reset_initial_tos_page", **_admin_view_defaults)
class ResetInitialTOSPage(_ResetGenerationLink):
    link_id = logon.REL_INITIAL_TOS_PAGE
    link_name = u'initial terms-of-service page'


@view_config(name="reset_welcome_page", **_admin_view_defaults)
class ResetWelcomePage(_ResetGenerationLink):
    link_id = logon.REL_INITIAL_WELCOME_PAGE
    link_name = u'initial welcome page'

del _view_defaults
del _post_view_defaults
del _admin_view_defaults
del _view_admin_defaults
