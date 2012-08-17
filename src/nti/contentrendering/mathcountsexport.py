#!/usr/bin/env python
"""
Utility to take the XHTML export of the MATHCOUNTS InDesign files and dump it to TeX
$Revision: 8588 $
"""
from __future__ import unicode_literals, print_function

from zope import interface
import nti.contentrendering
from nti.contentrendering import interfaces
from nti.contentfragments import interfaces as frg_interfaces

import io
import pyquery
from lxml import etree
import sys
import re
import urllib

def _text_of( p ):
	return etree.tostring( p, encoding=unicode, method='text' )

class _ElementPlainTextContentFragment(frg_interfaces.PlainTextContentFragment):
	children = ()
	def __new__( cls, element ):
		return super(_ElementPlainTextContentFragment,cls).__new__( cls, _text_of( element ) )

	def __init__( self, element=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_ElementPlainTextContentFragment,self).__init__( _text_of( element ) )
		self.element = element


class _Container(frg_interfaces.LatexContentFragment):

	children = ()

	def add_child( self, child ):
		if self.children == ():
			self.children = []
		self.children.append( child )


class _WrappedElement(_Container):
	wrapper = None

	def __new__( cls, text ):
		return super(_WrappedElement,cls).__new__( cls, '\\' + cls.wrapper + '{' + text + '}' )

	def __init__( self, text=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_WrappedElement,self).__init__( self, '\\' + self.wrapper + '{' + text + '}' )

class _WrappedElement2Arg(_Container):
	wrapper = None

	def __new__( cls, text1, text2 ):
		return super(_WrappedElement2Arg,cls).__new__( cls, '\\' + cls.wrapper + '{' + text1 + '}{' + text2 + '}' )

	def __init__( self, text1=None, text2=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		super(_WrappedElement2Arg,self).__init__( self, '\\' + self.wrapper + '{' + text1 + '}{' + text2 +'}' )

class _Footnote(_WrappedElement):
	wrapper = 'footnote'

class _Chapter(_WrappedElement):
	wrapper = 'chapter'

class _ChapterStar(_WrappedElement):
	wrapper = 'chapter*'

class _Section(_WrappedElement):
	wrapper = 'section'

class _SubSection(_WrappedElement):
	wrapper = 'subsection'

class _Label(_WrappedElement):
	wrapper = 'label'

class _NAQuestionRef(_WrappedElement):
	wrapper = 'naquestionref'

class _Title(_WrappedElement):
	wrapper = 'title'

class _TextIT(_WrappedElement):
	wrapper = 'textit'

class _TextBF(_WrappedElement):
	wrapper = 'textbf'

class _MATHCOUNTSWorksheet(_WrappedElement2Arg):
	wrapper = 'mathcountsworksheet'

	def __new__( cls, text ):
		text2 = "tag:nextthought.com,2011-10:mathcounts-HTML-mathcounts2013." + re.sub(r'[\s-]', '_', text.lower())
		return super(_MATHCOUNTSWorksheet,cls).__new__( cls, text, text2 )

	def __init__( self, text=None ):
		# Note: __new__ does all the actual work, because these are immutable as strings
		text2 = "tag:nextthought.com,2011-10:mathcounts-HTML-mathcounts2013." + re.sub(r'[\s-]', '_', text.lower())
		super(_MATHCOUNTSWorksheet,self).__init__( text, text2 )

class _href(_Container):

	def __new__( cls, url, text=None ):
		return super(_href,cls).__new__( cls, '\\href{' + url + '}' )

	def __init__( self, url, text=None ):
		super(_href,self).__init__( self, '\\href{' + url + '}' )
		# Note: __new__ does all the actual work, because these are immutable as strings
		self.add_child( '{' )
		self.add_child( text )
		self.add_child( '}' )

class _img(_Container):

	def __new__( cls, path, _options=None ):
		options = ''
		path = re.sub(r'_fmt[0-9]*.jpeg', '', urllib.unquote(path))
		path = re.sub(r'\s', '-', path)
		path = re.sub(r'^-', 'a-', path)
		if _options is not None:
			options = '[' + _options + ']'
		return super(_img,cls).__new__( cls, r'\includegraphics' + options + r'{' + path + r'}' )

	def __init(self, path, _options=None ):
		options = ''
		path = urllib.unquote(path)
		_is_math(path)
		if _options is not None:
			options = '[' + _options + ']'
		super(_img,self).__init__( self, r'\includegraphics' + options + r'{' + path + r'}' )


def _file_to_pyquery( file_path ):
	return  pyquery.PyQuery( url='file://' + file_path )

def _p_to_content( p, include_tail=True):
	accum = []
	kids = p.getchildren()
	if not kids:
		if include_tail:
			# If we fail to include this check, we get
			# duplicate text in and out of the link
			accum.append( _ElementPlainTextContentFragment( p ) )
		elif p.text and p.text.strip():
			accum.append( frg_interfaces.PlainTextContentFragment( p.text.strip() ) )
	else:
		def _tail(e):
			if e is not None and e.tail and e.tail.strip():
				accum.append( frg_interfaces.PlainTextContentFragment( e.tail.strip() ) )
		# complex element with nested children to deal with.
		if p.text and p.text.strip():
			accum.append( frg_interfaces.PlainTextContentFragment( p.text ) )
		for kid in kids:
			if kid.tag == 'i':
				accum.append( _TextIT(kid.text) )
			elif kid.tag == 'b':
				accum.append( _TextBF(kid.text) )
			elif kid.tag == 'a':
				# anchors and links
				if kid.get( 'href' ):
					# \href[options]{URL}{text}
					# TODO: We're not consistent with when we recurse
					# The tail of the <a> is not part of the link, so make sure
					# not to treat it as such.
					href = _href( _url_escape(kid.get( 'href' )),
								  _p_to_content( kid, include_tail=False ) )

					accum.append( href )
					for c in href.children:
						accum.append( c )
				else:
					accum.append( _ElementPlainTextContentFragment( kid ) )
					kid = None
			elif kid.tag == 'p':
				accum.append( _p_to_content( kid ) )
			elif kid.tag == 'span':
				accum.append( _p_to_content( kid ) )
			elif kid.tag == 'img':
				accum.append( _img(kid.attrib.get('src')) )
			_tail(kid)
		if include_tail:
			_tail(p)


	return frg_interfaces.LatexContentFragment( ' '.join( [frg_interfaces.ILatexContentFragment( x ) for x in accum] ) )

class _Problem(object):
	
	def __init__(self):
		self.number = None
		self.question = None
		self.answer = None
		self.solution = None
		self.difficulty = None

class _Worksheet(object):

	def __init__(self):
		self.title = None
		self.header = None
		self.problems = []

def _extract_problems( doc, worksheets ):
	stories = doc(b"div.story")

	for story in stories:
		worksheet_title = (pyquery.PyQuery(story))(b"p.problem-titles").text()
		if worksheet_title is None:
			continue
		worksheet = _Worksheet()
		worksheet.title = worksheet_title
		worksheet_header = (pyquery.PyQuery(story))(b"p.regular-text").text()
		if worksheet_header is not None:
			worksheet.header = worksheet_header
		for problem in (pyquery.PyQuery(story))(b"p.problems"):
			_t = re.search(r'^[0-9]*\.', problem.getchildren()[0].text)
			if _t is not None:
				node = _Problem()
				node.number = int(_t.group(0).rstrip('.'))
				node.question = re.sub(r'^[0-9]*\. ', '', _p_to_content(problem))
				worksheet.problems.extend([node])
			else:
				accum = '\\newline \\newline'
                                for child in problem.getchildren():
					accum = ' '.join([accum, _p_to_content(child)])
				worksheet.problems[len(worksheet.problems)-1].question = ' '.join([worksheet.problems[len(worksheet.problems)-1].question, accum])
		
		worksheets.extend([worksheet])

	return worksheets

def _extract_stretchs( docs, worksheets ):
	for doc in docs:
		worksheets = _extract_problems( doc, worksheets )
	return worksheets

def _extract_answers( doc, worksheets ):
	answers = doc(b"p.answers")

	for answer in answers:
		_t = re.search(r'^[0-9]*\.', _text_of(answer))
		if _t is not None:
			probnum = int(_t.group(0).rstrip('.'))
			for worksheet in worksheets:
				found = False
				for problem in worksheet.problems:
					if probnum == problem.number:
						_a = _text_of(answer).split(' ')
						problem.answer = unicode(_a[1])
						problem.difficulty = _a[2][1:2]
						found = True
						break
				if found:
					break
	return worksheets

def _extract_solutions( doc, worksheets ):
	paragraphs = doc(b"p")

	for paragraph in paragraphs:
		_t = re.search(r'^[0-9]*\.', _text_of(paragraph))
		if _t is not None:
			probnum = int(_t.group(0).rstrip('.'))
			for worksheet in worksheets:
				found = False
				for problem in worksheet.problems:
					if probnum == problem.number:
						problem.solution = re.sub(r'^[0-9]*\. ', '', _p_to_content(paragraph))
						found = True
						break
				if found:
					break
	return worksheets

def _output_master_file( worksheets ):
	header_content = """
\\documentclass[a4paper]{book}
\\usepackage{ntilatexmacros}
\\usepackage{ntiassessment}
\\usepackage{mathcounts}
\\usepackage{graphicx}
\\title{MATHCOUNTS 2012-2013}
\\author{MATHCOUNTS Foundation}
"""
	tex = []
	tex.extend([header_content])
	tex.extend(['\\begin{document}'])
	for worksheet in worksheets:
		tex.extend(['\\include{' + re.sub(r'\s', '-', worksheet.title.lower()) + '}'])
	tex.extend(['\\end{document}\n'])
	with io.open('mathcounts2013.tex', 'w') as file:
		file.write('\n'.join(tex))


def _output_tex( worksheets ):
	_output_master_file( worksheets )

	for worksheet in worksheets:
		tex = []
		qset = []
		tex.extend([_MATHCOUNTSWorksheet( worksheet.title )])
		if worksheet.header is not None:
			tex.extend([ worksheet.header ])
		tex.extend([_SubSection( 'Questions' )])
		for problem in worksheet.problems:
			qset.extend([_NAQuestionRef('qid.' + unicode(problem.number))])
			tex.extend(['%% Question ' + unicode(problem.number) + '.'])
			tex.extend(['\\begin{naquestion}[individual=true]'])
			tex.extend([_Label('qid.' + unicode(problem.number))])
			tex.extend(['\\begin{naqsymmathpart}'])
			tex.extend([problem.question])
			tex.extend(['\\begin{naqsolutions}'])
			tex.extend(['\\naqsolution[1] ' + problem.answer])
			tex.extend(['\\end{naqsolutions}'])
			tex.extend(['\\begin{naqsolexplanation}'])
			tex.extend([problem.solution])
			tex.extend(['\\end{naqsolexplanation}'])
			tex.extend(['\\end{naqsymmathpart}'])
			tex.extend(['\\end{naquestion}'])
		tex.extend(['\n\n\\begin{naquestionset}'])
		tex.extend(qset)
		tex.extend(['\\end{naquestionset}\n'])
		with io.open(re.sub(r'\s', '-', worksheet.title.lower()) + '.tex', 'w') as file:
			file.write('\n'.join(tex))

def main():
	from zope.configuration import xmlconfig
	xmlconfig.file( 'configure.zcml', package=nti.contentrendering )

	workbook_file = sys.argv[1]
	answers_file = sys.argv[2]
	solutions_file = sys.argv[3]
	stretch_files = [sys.argv[4], sys.argv[5], sys.argv[6]]

	workbook_pq = _file_to_pyquery( workbook_file )
	answers_pq = _file_to_pyquery( answers_file )
	solutions_pq = _file_to_pyquery( solutions_file )
	stretch_pqs = []
	stretch_pqs.extend([_file_to_pyquery( stretch_files[0] )])
	stretch_pqs.extend([_file_to_pyquery( stretch_files[1] )])
	stretch_pqs.extend([_file_to_pyquery( stretch_files[2] )])

	worksheets = []
	worksheets = _extract_problems( workbook_pq, worksheets )
	worksheets = _extract_stretchs( stretch_pqs, worksheets )
	worksheets = _extract_answers( answers_pq, worksheets ) 
	worksheets = _extract_solutions( solutions_pq, worksheets ) 

	_output_tex( worksheets )

if __name__ == '__main__': # pragma: no cover
	main()
