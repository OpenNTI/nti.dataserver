#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#from zope import component
#from zope import interface

from pyramid.view import view_config
#from pyramid import httpexceptions as hexc

from nti.app.base.abstract_views import AbstractAuthenticatedView

#from nti.app.contentfile import get_content_files

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.contentfolder.model import ContentFolder
from nti.contentfolder.interfaces import IContentFolder

from nti.dataserver import authorization as nauth

@view_config(route_name='objects.generic.traversal',
			 renderer='rest',
			 name="mkdir",
			 permission=nauth.ACT_UPDATE,
			 context=IContentFolder,
			 request_method='POST')
class MkdirView(AbstractAuthenticatedView, ModeledContentUploadRequestUtilsMixin):

	def _do_call(self):
		input_ = self.readInput()
		name = input_.get('name')
		if not name:
			raise ValueError("Invalid folder name.")
		title = input_.get('title')
		description = input_.get('description')
		new_folder = ContentFolder(name=name,
								   title=title,
								   description=description)
		self.context.append(new_folder)
		return new_folder
