from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface

class IObjectClassifierMetaData(interface.Interface):
	is_spam = schema.Bool( title="Whether the object has been marked as a spam" )
	classified_at = schema.Float(title="Classification time" )
		
