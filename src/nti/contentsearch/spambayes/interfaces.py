from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface

class IObjectClassifierMetaData(interface.Interface):
	is_spam = schema.Bool( title="Whether the object in context has been marked as a spam" )
	classfied_at = schema.Float(title="Classification time" )
		
