import re
import sys
import inspect

from repoze.catalog.query import Contains as IndexContains
from repoze.catalog.query import DoesNotContain as IndexDoesNotContain

from nti.contentsearch.common import (sharedWith_, containerId_, collectionId_, id_, oid_, ntiid_,
									  ID, LAST_MODIFIED, CONTAINER_ID, COLLECTION_ID, OID, NTIID, CREATOR)
from nti.contentsearch.common import (last_modified_fields)

import logging
logger = logging.getLogger( __name__ )

# ----------------------------------

def allow_keywords(f):
	spec = inspect.getargspec(f)
	return True if spec.keywords else False
	
def set_default_indexng3(params):
	# make we always rank so we can limit results		
	params['ranking'] = True
		
	# check for limit param
	if 'limit' in params:
		value = params.pop('limit')
		params['ranking_maxhits'] = int(value) if value else sys.maxint 
	
	if 'ranking_maxhits' not in params:
		params['ranking_maxhits'] = sys.maxint
			
	return params

class Contains(IndexContains):

	def __init__(self, index_name, value, **kwargs):
		IndexContains.__init__(self, index_name, value)
		self.params = dict(kwargs)
	
	def _apply(self, catalog, names):
		index = self._get_index(catalog)
		if allow_keywords(index.applyContains):
			return index.applyContains(self._get_value(names), **self.params)
		else:
			return index.applyContains(self._get_value(names))
		
	def negate(self):
		return DoesNotContain(self.index_name, self._value, **self.params)
	
	@classmethod
	def create_for_indexng3(cls, index_name, value, **kwargs):
		set_default_indexng3(kwargs)
		return Contains(index_name, value, **kwargs)

class DoesNotContain(IndexDoesNotContain):
	def __init__(self, index_name, value, **kwargs):
		IndexDoesNotContain.__init__(self, index_name, value)
		self.params = dict(kwargs)

	def _apply(self, catalog, names):
		index = self._get_index(catalog)
		if allow_keywords(index.applyDoesNotContain):
			return index.applyDoesNotContain(self._get_value(names), **self.params)
		else:
			return index.applyDoesNotContain(self._get_value(names))

	def negate(self):
		return Contains(self.index_name, self._value, **self.params)
	
	@classmethod
	def create_for_indexng3(cls, index_name, value, **kwargs):
		set_default_indexng3(kwargs)			
		return DoesNotContain(index_name, value, **kwargs)

# ---------------------------------

_all_re = re.compile('([\?\*])')
def is_all_query(query):
	mo = _all_re.search(query)
	return mo and mo.start(1) == 0

# ---------------------------------

_mappings = {sharedWith_.lower()   : sharedWith_, 
			 containerId_.lower()  : CONTAINER_ID,
			 collectionId_.lower() : COLLECTION_ID,
			 CREATOR.lower()       : CREATOR,
			 id_ : ID,
			 oid_: OID,
			 ntiid_ : NTIID }
for n in last_modified_fields:
	_mappings[n.lower()] = LAST_MODIFIED
	
def map_to_key_names(name, stored_names=()):
	name = unicode(name) if name else u''
	if not stored_names: return name
	name = _mappings.get(name.lower(), name)
	return name if name in stored_names else None

def get_subqueries(qo, stored_names=(), map_func=map_to_key_names):
	result = []
	for n, v in qo.get_subqueries():
		n = map_func(n, stored_names)
		if n and v is not None:
			result.append((n,v))
	return result

def parse_query(catalog, fieldname, qo):
	is_all = is_all_query(qo.term)	
	limit = qo.limit
	queryobject = Contains.create_for_indexng3(fieldname, qo.term)
	return is_all, catalog.query(queryobject, limit=limit)