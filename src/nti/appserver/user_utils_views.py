from __future__ import print_function, unicode_literals

from pyramid.view import view_config

import zope.intid
from zope import component
from zope.catalog.field import IFieldIndex
from zope.catalog.interfaces import ICatalog

from nti.dataserver import authorization as nauth
from nti.dataserver.users import index as user_index

import logging
logger = logging.getLogger( __name__ )

@view_config(route_name='objects.generic.traversal',
			 name='user_info_extract',
			 request_method='GET',
			 renderer='csv',
			 permission=nauth.ACT_MODERATE)
class UserInfoExtract(object):
	"""
	Primary reading glossary view.
	"""
	def __init__( self, request ):
		self.request = request

	def _get_docids(self, ent_catalog):
		email_idx = ent_catalog.get('email', None)
		if IFieldIndex.providedBy(email_idx):
			rev_index = getattr(email_idx, '_rev_index', {})
			return list(rev_index.keys())
		else:
			return ()
		
	def _get_fieldinfo(self, docid, ent_catalog, indexname):
		idx = ent_catalog.get(indexname, None)
		if IFieldIndex.providedBy(idx):
			rev_index = getattr(idx, '_rev_index', {})
			result = rev_index.get(docid, None)
		else:
			result = u''
		return result
	
	def __call__(self):	
		header = ['username', 'realname', 'alias', 'email']
		
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		docids = self._get_docids(ent_catalog)
		
		rows = []
		for iid in docids:
			u = _ds_intid.queryObject(iid, None)
			if u is not None:
				alias = self._get_fieldinfo(iid, ent_catalog, 'alias')
				email = self._get_fieldinfo(iid, ent_catalog, 'email')
				realname = self._get_fieldinfo(iid, ent_catalog, 'realname')
				rows.append((u.username, realname, alias, email))
				
				
		return {'header': header, 'rows': rows }
