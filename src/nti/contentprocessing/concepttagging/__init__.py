from __future__ import print_function, unicode_literals

from zope import component

from nti.contentprocessing.concepttagging import interfaces as cpct_interfaces

def concept_tag(content, name=u''):
	tagger = component.getUtility(cpct_interfaces.IConceptTagger, name=name)
	result = tagger(content)
	return result
