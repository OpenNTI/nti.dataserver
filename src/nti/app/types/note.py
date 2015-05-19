#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid.view import view_config

from nti.appserver.ugd_edit_views import UGDPostView

from nti.dataserver.interfaces import INote

from nti.dataserver import authorization as nauth

from ..contentfile import ContentFileUploadMixin

_view_defaults = dict(  route_name='objects.generic.traversal',
                        renderer='rest' )
_c_view_defaults = _view_defaults.copy()
_c_view_defaults.update( permission=nauth.ACT_CREATE,
                         request_method='POST' )

@view_config( context=INote, **_c_view_defaults)
class NotePostView(ContentFileUploadMixin, UGDPostView):
    pass
