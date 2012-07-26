from __future__ import print_function, unicode_literals

from zope import schema
from zope import interface

class IObjectClassifierMetaData(interface.Interface):
	spam_classification = schema.Int(title="Object classification" )
	spam_classification_time = schema.Float(title="Object classification time" )
		
