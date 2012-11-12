from __future__ import unicode_literals, print_function

from zope import interface

class IStemmer(interface.Interface):
	def stem(token):
		"""get the stem of the specified token"""