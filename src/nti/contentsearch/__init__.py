from brownie.caching import LFUCache

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class NoOpCM(object):

	singleton = None
	
	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(NoOpCM, cls).__new__(cls, *args, **kwargs)
		return cls.singleton
	
	def __enter__(self,*args):
		return self

	def __exit__(self,*args):
		pass
	
# -----------------------------

class LFUMap(LFUCache):

	def __init__(self, maxsize, on_removal_callback=None):
		super(LFUMap, self).__init__(maxsize=maxsize)
		self.on_removal_callback = on_removal_callback
		
	def __delitem__(self, key):
		if self.on_removal_callback:
			value = dict.__getitem__(self, key)
		super(LFUMap, self).__delitem__(key)
		if self.on_removal_callback:
			self.on_removal_callback(key, value)
	

# -----------------------------

