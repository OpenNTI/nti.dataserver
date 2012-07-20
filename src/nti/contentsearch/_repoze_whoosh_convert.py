#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import re
import numbers
from datetime import datetime

from whoosh import fields
import repoze.catalog.query as repquery

class QueryConverter(object):
	
	bools = {'And': 'AND', 'Or': 'OR'}
	iteratives 	=  (repquery.Any, repquery.NotAny, repquery.All, repquery.NotAll)
	translations = {'ntiid': 'ntiid', 'content': 'content',
					'lastmodified': 'last_modified', 'lm': 'last_modified',
					'keywords': 'keywords', 'kw': 'keywords', 
					'creator': 'creator', 'containerid': 'containerId'}
	months = ('','january','february','march','april','may','june','july',
				'august','september','october','november','december')

	# keywords:keywords,content:content,quick:quick,last_modified:last_modified
	
	def __init__(self, schema=None, catalog=None):
		self.schema = schema
		if schema == 'default':
			self.schema = fields.Schema( 
							collectionId = fields.ID(stored=True),
                           	oid = fields.ID(stored=True, unique=True),
                            containerId = fields.ID(stored=True),
                            creator = fields.ID(stored=True),
                            last_modified = fields.DATETIME(stored=True),
                            content = fields.TEXT(stored=True, spelling=True),
                            sharedWith = fields.KEYWORD(stored=False),
                            color = fields.TEXT(stored=False),
                            quick = fields.NGRAM(maxsize=10),
                            keywords = fields.KEYWORD(stored=True),
                            ntiid = fields.ID(stored=True))

	def convert_base_query(self,q):

		def date_convert(timestamp):
			d = datetime.fromtimestamp(timestamp)
			y,m,d = str(d.year), self.months[d.month], str(d.day)
			return d + ' ' + m + ' ' + y

		def translate(index):
			stripped = re.sub('[^A-Za-z]','',index).lower()
			return self.translations.get(stripped, index)

		def process(val):
			if isinstance(val, numbers.Real):
				return str(val)
			elif ' ' in val:
				return "'" + val + "'"
			else:
				return val

		for it in self.iteratives:
			if isinstance(q,it):
				symbol = 'OR' if it in (repquery.Any, repquery.NotAny) else 'AND'
				output = ''
				for i,v in enumerate(q.value):
					output += self.convert_base_query(repquery.Eq(q.index_name,v))
					if i < len(q.value) - 1: output += ' ' + symbol + ' '
				if it in (repquery.NotAny, repquery.NotAll):
					output = 'NOT (' + output + ')'
				return output
		index, val = translate(q.index_name), q._value
		date_conversion = False
		if self.schema:
			sd = {x[0]: x[1:] for x in self.schema.items()}
			if index in sd and isinstance(sd[index][0],fields.DATETIME):
				val = date_convert(val)
				date_conversion = True
		if not date_conversion: val = process(val)
		head = index + ':'
		negate = False
		if isinstance(q,repquery.Eq):
			tail = process(q._value)
		elif isinstance(q,repquery.NotEq):
			negate = True
			tail = process(q._value)
		elif isinstance(q,repquery.Lt):
			tail = '{TO ' + val + '}'
		elif isinstance(q,repquery.Le):
			tail = '{TO ' + val + ']'
		elif isinstance(q,repquery.Gt):
			tail = '{' + val + ' TO}'
		elif isinstance(q,repquery.Ge):
			tail = '[' + val + ' TO}'
		elif isinstance(q,repquery.Contains):
			tail = '*' + val + '*'
		elif isinstance(q,repquery.DoesNotContain):
			negate = True
			tail = '*' + val + '*'
		elif isinstance(q,repquery.InRange):
			tail = '[' + val + ' TO ' + val + ']'
		elif isinstance(q,repquery.NotInRange):
			negate = True
			tail = '[' + val + ' TO ' + val + ']'
		return ('NOT (' + head + tail + ')') if negate else (head + tail)

	def convert_bool_query(self,q):
		output = ''
		children = list(q.iter_children())
		for i,c in enumerate(children):
			wrapper = ('(',')') if len(list(c.iter_children())) > 0 else ('','')
			output += wrapper[0] + self.convert_query(c) + wrapper[1]
			if i < len(children) - 1: output += ' ' + self.bools[str(q)] + ' '
		return output

	def convert_query(self,q):
		if str(q) in self.bools: return self.convert_bool_query(q)
		else: return self.convert_base_query(q)

