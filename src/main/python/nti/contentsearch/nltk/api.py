# Natural Language Toolkit: Tokenizer Interface
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Tokenizer Interface
"""

import types
from util import string_span_tokenize


def overridden(method):
	"""
	@return: True if C{method} overrides some method with the same
	name in a base class.  This is typically used when defining
	abstract base classes or interfaces, to allow subclasses to define
	either of two related methods:
	
	    >>> class EaterI:
	    ...     '''Subclass must define eat() or batch_eat().'''
	    ...     def eat(self, food):
	    ...         if overridden(self.batch_eat):
	    ...             return self.batch_eat([food])[0]
	    ...         else:
	    ...             raise NotImplementedError()
	    ...     def batch_eat(self, foods):
	    ...         return [self.eat(food) for food in foods]
	
	@type method: instance method
	"""
	# [xx] breaks on classic classes!
	if isinstance(method, types.MethodType) and method.im_class is not None:
		name = method.__name__
		funcs = [cls.__dict__[name]
					for cls in _mro(method.im_class) if name in cls.__dict__]
		return len(funcs) > 1
	else:
		raise TypeError('Expected an instance method.')

def _mro(cls):
	"""
	Return the I{method resolution order} for C{cls} -- i.e., a list
	containing C{cls} and all its base classes, in the order in which
	they would be checked by C{getattr}.  For new-style classes, this
	is just cls.__mro__.  For classic classes, this can be obtained by
	a depth-first left-to-right traversal of C{__bases__}.
	"""
	if isinstance(cls, type):
		return cls.__mro__
	else:
		mro = [cls]
		for base in cls.__bases__: mro.extend(_mro(base))
		return mro

class TokenizerI(object):
	"""
	A processing interface for I{tokenizing} a string, or dividing it
	into a list of substrings.
	
	Subclasses must define:
	  - either L{tokenize()} or L{batch_tokenize()} (or both)
	"""
	
	def tokenize(self, s):
		"""
		Divide the given string into a list of substrings.
		
		@return: C{list} of C{str}
		"""
		if overridden(self.batch_tokenize):
			return self.batch_tokenize([s])[0]
		else:
			raise NotImplementedError()

	def span_tokenize(self, s):
		"""
		Identify the tokens using integer offsets (start_i, end_i),
		where s[start_i:end_i] is the corresponding token.
		
		@return: C{iter} of C{tuple} of C{int}
		"""
		raise NotImplementedError()

	def batch_tokenize(self, strings):
		"""
		Apply L{self.tokenize()} to each element of C{strings}.  I.e.:
		
			>>> return [self.tokenize(s) for s in strings]
		
		@rtype: C{list} of C{list} of C{str}
		"""
		return [self.tokenize(s) for s in strings]

	def batch_span_tokenize(self, strings):
		"""
		Apply L{self.span_tokenize()} to each element of C{strings}.  I.e.:
		
			>>> return [self.span_tokenize(s) for s in strings]
		
		@rtype: C{iter} of C{list} of C{tuple} of C{int}
		"""
		for s in strings:
			yield list(self.span_tokenize(s))

class StringTokenizer(TokenizerI):
	"""
	A tokenizer that divides a string into substrings by splitting
	on the specified string (defined in subclasses).
	"""
	
	def tokenize(self, s):
		return s.split(self._string)
	
	def span_tokenize(self, s):
		for span in string_span_tokenize(s, self._string):
			yield span
