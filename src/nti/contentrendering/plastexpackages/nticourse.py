#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from datetime import datetime
from xml.dom.minidom import Document as XMLDocument

from nti.contentrendering import plastexids
from nti.contentfragments import interfaces as cfg_interfaces
from nti.contentrendering import interfaces as crd_interfaces
from nti.contentrendering.plastexpackages import interfaces

from plasTeX.Base import Command
from plasTeX.Base import Crossref
from plasTeX.Base import Environment
from plasTeX.Base import StartSection

from zope import component
from zope import interface

class coursename(Command):
    pass

class course(Environment, plastexids.NTIIDMixin):
    args = '[ options:dict ] title:str'

    counter = 'course'
    blockType = True
    forcePars = False
    _ntiid_cache_map_name = '_course_ntiid_map'
    _ntiid_allow_missing_title = False
    _ntiid_suffix = 'course.'
    _ntiid_title_attr_name = 'ref'
    _ntiid_type = 'NTICourse'

    def invoke(self, tex):
        res = super(course,self).invoke(tex)
        if self.macroMode == self.MODE_BEGIN:
            self.title = self.attributes['title']
        return res

    def digest(self, tokens):
        tok = super(course,self).digest(tokens)
        if self.macroMode == self.MODE_BEGIN:
            if not getattr(self, 'title', ''):
                raise ValueError("Must specify a title using \\caption")

            options = self.attributes.get( 'options', {} ) or {}
            __traceback_info__ = options, self.attributes

        return tok

class courseunitname(Command):
    pass

class courseunit(Environment, plastexids.NTIIDMixin):
    args = '[ options:dict ] title:str'

    counter = "courseunit"
    blockType = True
    forcePars = False
    _ntiid_cache_map_name = '_courseunit_ntiid_map'
    _ntiid_allow_missing_title = False
    _ntiid_suffix = 'course.unit.'
    _ntiid_title_attr_name = 'ref'
    _ntiid_type = 'NTICourseUnit'

    def invoke(self, tex):
        res = super(courseunit,self).invoke(tex)
        if self.macroMode == self.MODE_BEGIN:
            self.title = self.attributes['title']
        return res

    def digest(self, tokens):
        res = super(courseunit,self).digest(tokens)
        if self.macroMode == self.MODE_BEGIN:
            if not getattr(self, 'title', ''):
                raise ValueError("Must specify a title using \\caption")

            options = self.attributes.get( 'options', {} ) or {}
            __traceback_info__ = options, self.attributes

        return res

class courselessonname(Command):
    pass

class courselessonref(Crossref.ref):
    args = 'label:idref date:str'
    
    def invoke( self, tex ):
        res = super(courselessonref, self).invoke( tex )
        date = self.attributes['date'].split('/')
        self.date = datetime(int(date[2]), int(date[0]), int(date[1]))
        return res

class courselesson(StartSection):
    args = '* [ toc ] title label:id'
    blockType = True
    counter = 'courselesson'
    forcePars = False
    level = Command.CHAPTER_LEVEL

def ProcessOptions( options, document ):
	document.context.newcounter('course')
	document.context.newcounter('courselesson')
	document.context.newcounter('courseunit')

@interface.implementer(interfaces.ICourseExtractor)
@component.adapter(crd_interfaces.IRenderedBook)
class _CourseExtractor(object):

    def __init__( self, book=None ):
        # Usable as either a utility factory or an adapter
        pass

    def transform( self, book ):
        course_els = book.document.getElementsByTagName( 'course' )
        dom = book.toc.dom
        if course_els:
            dom.childNodes[0].appendChild(dom.createTextNode(u'    '))
            dom.childNodes[0].appendChild(self._process_course( course_els[0] ))
            dom.childNodes[0].appendChild(dom.createTextNode(u'\n'))
            dom.childNodes[0].setAttribute('isCourse', 'true')
        else:
            dom.childNodes[0].setAttribute('isCourse', 'false')
        book.toc.save()

    def _process_course( self, doc_el ):
        toc_el = XMLDocument().createElement('course')
        toc_el.setAttribute('label', unicode(doc_el.title) )
        toc_el.setAttribute('ntiid', doc_el.ntiid )
        units = doc_el.getElementsByTagName( 'courseunit' )
        for unit in units:
            toc_el.appendChild(XMLDocument().createTextNode(u'\n        '))
            toc_el.appendChild(self._process_unit(unit))
        toc_el.appendChild(XMLDocument().createTextNode(u'\n    '))
        return toc_el

    def _process_unit( self, doc_el ):
        toc_el = XMLDocument().createElement('unit')
        toc_el.setAttribute('label', unicode(doc_el.title) )
        toc_el.setAttribute('ntiid', doc_el.ntiid )
        lessons = doc_el.getElementsByTagName( 'courselessonref' )
        for lesson in lessons:
            toc_el.appendChild(XMLDocument().createTextNode(u'\n            '))
            toc_el.appendChild(self._process_lesson(lesson))
        toc_el.appendChild(XMLDocument().createTextNode(u'\n        '))
        return toc_el

    def _process_lesson( self, doc_el ):
        toc_el = XMLDocument().createElement('lesson')
        toc_el.setAttribute('date', doc_el.date.isoformat() + u'Z')
        toc_el.setAttribute('topic-ntiid', doc_el.idref['label'].ntiid )
        return toc_el
