from __future__ import print_function, unicode_literals

import time

import BTrees
import zope.intid

from persistent import Persistent

from zope import component
from zope.index.text.baseindex import BaseIndex

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.common import CatalogIndex
from repoze.catalog.indexes.field import CatalogFieldIndex

from nti.dataserver import interfaces as nti_interfaces
	
from nti.contentsearch.common import (	last_modified_, intid_ )

import logging
logger = logging.getLogger( __name__ )

# want to make sure change the family for all catalog index fields
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

def get_uid(self, context):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	return _ds_intid.getId(context)
	
def get_context(self, uid):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	return _ds_intid.getObject(uid)
	
def _create_catalog():
	catalog = Catalog(family=BTrees.family64)
	catalog[intid_] =  CatalogFieldIndex(intid_)
	catalog[last_modified_] = CatalogFieldIndex(last_modified_)
	return catalog

class _Proxy(object):
	def __int__(self, uid, lm=None):
		setattr(self, intid_, uid)
		setattr(self, last_modified_, lm or time.time())

class SpamManager(Persistent):

	def __init__(self):
		self._catalog = _create_catalog() 
		
	def mark_spam(self, context, mtime=None):
		m_time = mtime or time.time()
		if nti_interfaces.IModeledContent.providedBy(context):
			uid = get_uid(context)
			if not self._is_marked( uid ):
				proxy = _Proxy(uid, m_time)
				self._catalog.index_doc(uid, proxy)
				return True
		return False
				
	def unmark_spam(self, context):
		if nti_interfaces.IModeledContent.providedBy(context):
			uid = get_uid(context)
			if self._is_marked( uid ):
				self._catalog.unindex_doc(uid)
				return True
		return False

	def _is_marked(self, uid):
		rev_index = self._catalog[intid_]._rev_index 
		result = uid in rev_index 
		return result


	


