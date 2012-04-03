import sys
import inspect

from repoze.catalog.query import Contains as IndexContains
from repoze.catalog.query import DoesNotContain as IndexDoesNotContain

import logging
logger = logging.getLogger( __name__ )

def allow_keywords(f):
	spec = inspect.getargspec(f)
	return True if spec.keywords else False
	
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
		if 'ranking' not in kwargs:
			kwargs['ranking'] = True
		if 'ranking_maxhits' not in kwargs:
			kwargs['ranking_maxhits'] = sys.maxint			
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
		if 'ranking' not in kwargs:
			kwargs['ranking'] = True
		if 'ranking_maxhits' not in kwargs:
			kwargs['ranking_maxhits'] = sys.maxint			
		return DoesNotContain(index_name, value, **kwargs)