from __future__ import print_function, unicode_literals

from sets import Set

import logging
logger = logging.getLogger( __name__ )

class WordList(Set):

	def __repr__(self):
		return '%s(%s), %s' % (self.__class__.__name__, Set.__repr__(self))
	
	def extend(self, words):
		try:
			self.update(words)
		except Exception:
			logger.exception("Could not add/extend words %r" % words) 
			raise
		