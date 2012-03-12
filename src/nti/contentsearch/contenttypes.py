import time
import uuid
import collections

from datetime import datetime

from zope import interface

from nti.contentsearch import interfaces
from nti.contentsearch.interfaces import IUserIndexableContent
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_content
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CLASS, \
										COLLECTION_ID, ITEMS, SNIPPET, QUERY, HIT_COUNT)

from whoosh.fields import ID
from whoosh.fields import TEXT
from whoosh.fields import NGRAM
from whoosh.fields import Schema
from whoosh.fields import KEYWORD
from whoosh.fields import NUMERIC
from whoosh.fields import DATETIME

from whoosh.searching import Hit

from whoosh import analysis
from whoosh import highlight

from whoosh.query import (Or, Term)
from whoosh.qparser import QueryParser
from whoosh.qparser import GtLtPlugin
from whoosh.qparser.dateparse import DateParserPlugin

import logging
logger = logging.getLogger( __name__ )

##########################

def content_type_class(typeName='Notes'):
	className = typeName[0:-1] if typeName.endswith('s') else typeName
	if className in IndexableContentMetaclass.indexables and getattr( IndexableContentMetaclass.indexables[className], '__indexable__', False ):
		result = IndexableContentMetaclass.indexables[className]
	else:
		result = UserIndexableContent
	return result

##########################

class IndexableContentMetaclass(type):
	"""
	A metaclass for classes that represent indexable types.

	This class declares one property, `indexables`, which is an
	iterable of the string local names of all known
	content types (those that use this metaclass).

	.. warning::

		If you are going to implement other interfaces, the metaclass
		definition *must* be the first statement in the class, above
		the :func:`interface.implements` statement.

	"""
	# A metaclass might be overkill for this??

	indexables = {} # Todo: should weak ref the values.

	# If we wanted to keep the actual classes, say in a
	# dictionary, we would need to do so with weak references.

	def __new__(mcs, name, bases, cls_dict):
		new_type = type.__new__( mcs, name, bases, cls_dict )
		# elide internal classes. In the future, we may want
		# finer control with a class dictionary attribute.
		if not name.startswith( '_' ):
			#interface.classImplements( new_type, IContentTypeAware )
			mcs.indexables[name] = new_type
		return new_type

def get_datetime(x=None):
	f = time.time()
	if x:
		f = float(x) if isinstance(x, basestring) else x
	return datetime.fromtimestamp(f)


def get_keywords(records):
	result = ''
	if records:
		result = ','.join(records)
	return unicode(result)

##########################

def get_highlighted_content(query, text, analyzer=None, maxchars=300, surround=20):
	"""
	whoosh highlight based on words
	"""
	terms = frozenset([query])
	analyzer = analyzer or analysis.SimpleAnalyzer()
	fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
	formatter = highlight.UppercaseFormatter()
	return highlight.highlight(text, terms, analyzer, fragmenter, formatter)

##########################

def echo(x):
	return unicode(x) if x else u''

def get_text_from_mutil_part_body(body):

	if not body or isinstance(body, basestring):
		return get_content(body)
	elif isinstance(body, collections.Iterable):

		gbls = globals()

		def add_to_items(d, key):
			data = d[key] if d and key in d else None
			if data: items.append(str(data))

		def add_from_dict(item):
			name = item[CLASS] if CLASS in item else None
			if name in gbls and IUserIndexableContent.implementedBy(gbls[name]):
				try:
					obj = gbls[name]()
					d = obj.get_index_data(item)
					add_to_items(d, 'content')
					add_to_items(d, 'text')
				except:
					pass

		items = []
		if isinstance(body, dict):
			add_from_dict(body)
		else:
			for item in body:
				if isinstance(item, basestring) and item:
					items.append(item)
				elif isinstance(item, dict):
					add_from_dict(item)

		return get_content(' '.join(items))
	else:
		return get_content(str(body))


##########################

class MetaIndexableContent(IndexableContentMetaclass):
	def __new__(mcs, name, bases, cls_dict):
		t = super(MetaIndexableContent,mcs).__new__(mcs, name, bases, cls_dict)

		inverted = {}
		fields = getattr(t, 'fields', None)
		if not fields:
			schema = getattr(t, 'schema', None)
			if schema:
				for name in schema.stored_names():
					inverted[name] = name.capitalize()
		else:
			for k, v in fields.items():
				name = v[0]
				inverted[name] = k

		if inverted:
			inverted['last_modified'] = LAST_MODIFIED
			t.inverted_fields = inverted

			def f(self, name):
				return self.inverted_fields[name] if name in self.inverted_fields else ''
			t.external_name = f

		return t

class _IndexableContent(object):
	__metaclass__ = MetaIndexableContent
	interface.implements(interfaces.IIndexableContent)

	def __init__(self):
		super(_IndexableContent,self).__init__()

	def get_schema(self):
		return None

	def index_content(self, writer, externalValue, auto_commit=True, **commit_args):
		raise NotImplementedError()

	def update_content(self, writer, externalValue, auto_commit=True, **commit_args):
		raise NotImplementedError()

	def delete_content(self, writer, externalValue, auto_commit=True, **commit_args):
		return False

	############################

	@property
	def search_field(self):
		return self.get_default_search_field()

	def get_default_search_field(self):
		return "content"

	@property
	def quick_field(self):
		return self.get_quick_search_field()

	def get_quick_search_field(self):
		return "quick"

	@property
	def limit(self):
		return self.get_search_limit()

	def get_search_limit(self):
		return 10

	@property
	def maxdist(self):
		return self.get_max_distance()

	def get_max_distance(self):
		return 15

	@property
	def suggest_limit(self):
		return self.get_max_distance()

	def get_suggestion_limit(self):
		return 15

	def get_search_plugins(self):
		return (GtLtPlugin, DateParserPlugin)

	############################

	def search(self, searcher, query, limit=None, sortedby=None, search_field=None):

		limit = limit or self.limit
		search_field = search_field or self.search_field

		qp = QueryParser(search_field, schema=self.get_schema())
		for pg in self.get_search_plugins():
			qp.add_plugin(pg())

		try:
			parsedQuery = qp.parse(unicode(query))
			return self.execute_query_and_externalize(searcher, parsedQuery, query, limit, sortedby)
		except:
			logger.debug("Error while searching '%s'. Returning empty result", query, exc_info=True)
			return empty_search_result(query)

	def quick_search(self, searcher, query, limit=None, sortedby=None, search_field=None):
		limit = limit or self.limit
		search_field = search_field or self.quick_field
		qp = QueryParser(search_field, schema=self.get_schema())
		try:
			parsedQuery = qp.parse(unicode(query))
			return self.execute_query_and_externalize(searcher, parsedQuery, query, limit, sortedby)
		except:
			logger.debug("Error while quick-searching '%s'. Returning empty result", query, exc_info=True)
			return empty_search_result(query)

	def suggest_and_search(self, searcher, query, limit=None, sortedby=None, search_field=None):

		search_field = search_field or self.search_field

		if ' ' in query:
			suggestions = []
			result = self.search(searcher, query, limit, sortedby, search_field)
		else:
			suggestions = searcher.suggest(	search_field, query, maxdist=self.maxdist,\
											limit=self.suggest_limit, prefix=len(query))

			if len(suggestions)>0:
				result = self.search(searcher, suggestions[0], limit, sortedby, search_field)
			else:
				result = self.search(searcher, query, limit, sortedby, search_field)

		result['Suggestions'] = suggestions
		return result

	def suggest(self, searcher, word, limit=None, maxdist=None, prefix=None, search_field=None):

		prefix = prefix or len(word)
		maxdist = maxdist or self.maxdist
		limit = limit or self.suggest_limit
		search_field = search_field or self.search_field

		try:
			records = searcher.suggest(search_field, word, limit=limit, prefix=prefix)
			result = {}
			result[QUERY] = word
			result[ITEMS] = records
			result[LAST_MODIFIED] = 0
			result[HIT_COUNT] = len(records)
		except:
			logger.debug("Error while performing suggestion for '%s'. Returning empty result", word, exc_info=True)
			result = empty_suggest_result(word)

		return result

	def execute_query_and_externalize(self, searcher, parsed_query, query, limit, sortedby=None):

		stored_field = self.search_field in self.get_schema().stored_names()
		field_found_in_query = self.search_field in list(t[0] for t in parsed_query.iter_all_terms())

		search_hits = self.execute_search(searcher, parsed_query, limit, sortedby)
		search_hits.fragmenter = highlight.ContextFragmenter(maxchars=300, surround=20)
		search_hits.formatter = highlight.UppercaseFormatter()

		result = {}
		result[QUERY] = query

		maxLM = 0
		hit_count = 1
		items = self._create_search_items_collection()
		for hit in search_hits:

			d = {}
			item_id = self.get_data_from_search_hit(hit, d)
			lm = d[LAST_MODIFIED] if d.has_key(LAST_MODIFIED) else 0
			maxLM = max(lm, maxLM)

			snippet = ''
			if stored_field:
				if field_found_in_query:
					snippet = hit.highlights(self.search_field)
				else:
					snippet = get_highlighted_content(query, hit[self.search_field])
			d[SNIPPET] = snippet

			items[item_id or hit_count] = d
			hit_count += 1

		result[ITEMS] = items
		result[HIT_COUNT] = len(items)
		result[LAST_MODIFIED] = maxLM

		return result

	def execute_search(self, searcher, parsed_query, limit, sortedby=None):
		reader = searcher.reader()
		supports_sortby = hasattr(reader, "fieldcache")

		if supports_sortby and sortedby:
			return searcher.search(parsed_query, sortedby=sortedby, limit=limit)
		else:
			return searcher.search(parsed_query, limit=limit)

	def externalize(self, hit_or_doc):
		result = {}
		result['Type'] = self.__class__.__name__

		schema = self.get_schema()
		if schema:
			for k, v in hit_or_doc.items():
				if k == self.hit_last_modified():
					v = epoch_time(v)
				result[self.external_name(k)] = v

		return result

	def get_data_from_search_hit(self, hit, d):
		d[CLASS] = 'Hit'
		if self.hit_last_modified() in hit:
			d[LAST_MODIFIED] = epoch_time(hit[self.hit_last_modified()])
		else:
			d[LAST_MODIFIED] = 0
		return str(hit.docnum) if hit.__class__ == Hit else None

	def hit_last_modified(self):
		"""
		returns the last modified field name in a hit
		"""
		return 'last_modified'

	def _create_search_items_collection(self):
		return {}

##########################

# TODO: All these tiny meta classes can probably go away.

class MetaBook(MetaIndexableContent):
	def __new__(mcs, name, bases, cls_dict):
		t = super(MetaBook, mcs).__new__(mcs, name, bases, cls_dict)
		t.inverted_fields['ntiid'] = 'ContainerId'
		return t

class Book(_IndexableContent):

	"""
	Base clase for any a book index.
	The schema fields are as follows

	ntiid: Internal nextthought ID for the chapter/section
	title: chapter/section title
	last_modified: chapter/section last modification since the epoch
	keywords: chapter/section key words
	content: chapter/section text
	quick: chapter/section text used for type-ahead
	related: ntiids of related sections
	ref: chapter reference
	"""

	__metaclass__ = MetaBook

	schema = Schema(ntiid=ID(stored=True, unique=True),
					title=TEXT(stored=True, spelling=True),
				  	last_modified=DATETIME(stored=True),
				  	keywords=KEYWORD(stored=True), 
				 	quick=NGRAM(maxsize=10),
				 	related=KEYWORD(stored=True),
				 	section=TEXT(),
				 	content=TEXT(stored=True, spelling=True))

	def search(self, searcher, query, limit=None, sortedby=None, search_field=None):

		limit = limit or self.limit
		search_field = search_field or self.search_field

		qp = QueryParser(search_field, schema=self.get_schema())
		for pg in self.get_search_plugins():
			qp.add_plugin(pg())

		try:
			parsed_query = qp.parse(unicode(query))
			parsed_query = Or([parsed_query] + [Term(u"keywords", query)])
			return self.execute_query_and_externalize(searcher, parsed_query, query, limit, sortedby)
		except:
			logger.debug("Error while searching '%s'. Returning empty result", query, exc_info=True)
			return empty_search_result(query)
			
	def get_schema(self):
		return self.schema

	def index_content( self, writer, externalValue, auto_commit=True):
		raise RuntimeError("Cannot index book")

	def update_content( self, writer, externalValue, auto_commit=True):
		raise RuntimeError("Cannot update book index")

	def delete_content( self, writer, externalValue, auto_commit=True):
		raise RuntimeError("Cannot delete book index")

	def get_search_limit(self):
		return 15

	def execute_search(self, searcher, parsed_query, limit, sortedby=None):
		return super(Book, self).execute_search(searcher,
												parsed_query, 
												limit or self.get_search_limit(),
												sortedby)

	def get_data_from_search_hit(self, hit, d):
		super(Book, self).get_data_from_search_hit(hit, d)
		d['Type'] = 'Content'
		d[self.external_name('title')] = hit['title']
		d[self.external_name('ntiid')] = hit['ntiid']
		return hit['ntiid']

##########################

class UserIndexableContent(_IndexableContent):
	interface.implements(interfaces.IUserIndexableContent)

	__indexable__ = False

	def get_schema(self):
		return None

	def get_index_data(self, externalValue, *args, **kwargs):
		return None

	def _set_common_data(self, d, source, add_oid=False, quick=True):

		if len(d)>0:
			if not d.has_key('containerId') and hasattr(source, "containerId"):
				d['containerId'] = unicode(str(source.containerId))

			if not d.has_key('last_modified'):
				d['last_modified'] = get_datetime()

			if not d.has_key('collectionId'):
				d['collectionId'] = unicode("prealgebra")

		if add_oid and not d.has_key('oid'):

			d['oid']= unicode(str(uuid.uuid1()))

		if quick and d.has_key(self.search_field):
			d[self.quick_field] = d[self.search_field]


##########################

class MetaHighlight(MetaIndexableContent):
	def __new__(cls, name, bases, cls_dict):
		t = super(MetaHighlight, cls).__new__(cls, name, bases, cls_dict)
		t.inverted_fields['oid'] = 'TargetOID'
		return t

class Highlight(UserIndexableContent):

	"""
	Base clase for any Highlight indexable content.
	The schema fields are as follows

	collectionId: Book/Collection name
	ntiid: NTI id
	oid: object id
	creator: username
	last_modified: Last modification since the epoch
	content: Content type
	sharedWith: text to index
	color: note color
	quick: text used for type-ahead

	"""

	__metaclass__ = MetaHighlight

	__indexable__ = True

	_schema = Schema(	collectionId=ID(stored=True),
						oid=ID(stored=True, unique=True),
						containerId=ID(stored=True),
						creator=ID(stored=True),
				  		last_modified=DATETIME(stored=True),
				  		content=TEXT(stored=True, spelling=True),
				  		sharedWith=KEYWORD(stored=False), 
				  		color=TEXT(stored=False),
				 		quick=NGRAM(maxsize=10),
				 		keywords=KEYWORD(stored=True),
				 		ntiid=ID(stored=True))

	fields = {
			"CollectionID": ("collectionId", echo),
			"OID": ("oid", echo),
			"ContainerId":("containerId", echo),
			"Creator": ("creator", echo),
			"Last Modified": ("last_modified", get_datetime),
			"startHighlightedFullText" : ("content", get_content),
			"sharedWith": ("sharedWith", get_keywords),
			"color": ("color", echo),
			"keywords": ("keywords", get_keywords),
			"NTIID": ("ntiid", echo)
			}

	indexname_postfix = '__highlights'

	def __init__(self):
		super(Highlight,self).__init__()

	def get_schema(self):
		return self._schema

	def index_content(self, writer, externalValue, auto_commit=True, **commit_args):
		try:
			d = self.get_index_data(externalValue, self.fields.iteritems())
			if d and d.has_key('containerId'):
				writer.add_document(**d)
		except Exception, e:
			writer.cancel()
			logger.debug("Error while indexing content '%s'", externalValue, exc_info=True)
			raise e
		else:
			if auto_commit:
				writer.commit(**commit_args)

	def update_content(self, writer, externalValue, auto_commit=True, **commit_args):
		try:
			d = self.get_index_data(externalValue, self.fields.iteritems())
			if d and d.has_key('containerId'):
				writer.update_document(**d)
		except Exception, e:
			writer.cancel()
			logger.debug("Error while updating content '%s'", externalValue, exc_info=True)
			raise e
		else:
			if auto_commit:
				writer.commit(**commit_args)

	def delete_content(self, writer, externalValue, auto_commit=True, **commit_args):
		d = self.get_index_data(externalValue, self.fields.iteritems() )
		try:
			if d and d.has_key("oid"):
				writer.delete_by_term('oid', unicode(d['oid']))
		except Exception, e:
			writer.cancel()
			logger.debug("Error while deleting content '%s'", externalValue, exc_info=True)
			raise e
		else:
			if auto_commit:
				writer.commit(**commit_args)

	def get_index_data(self, externalValue, items=None):

		items = items or self.fields.iteritems()

		data = externalValue
		if isinstance(data, basestring):
			return {"oid" : unicode(data)}
		elif not isinstance(data, collections.Mapping):
			return None

		if data.has_key(ITEMS):
			data = data[ITEMS]

		d = {}
		for k,t in items:
			name = t[0]
			func = t[1]
			if data.has_key(k):
				value = data[k]
				if value:
					d[name] = func(value)

		self._set_common_data(d, externalValue)

		return d if len(d) > 0 else None

	def execute_search(self, searcher, parsed_query, limit, sortedby=None):
		return searcher.search(parsed_query, limit=limit)

	def get_data_from_search_hit(self, hit, d):
		_IndexableContent.get_data_from_search_hit(self, hit, d)
		d['Type'] = self.__class__.__name__
		d[self.external_name('oid')] = hit.get('oid', '')
		d[self.external_name('ntiid')] = hit.get('ntiid', '')
		d[self.external_name('creator')] = hit.get("creator", '')
		d[self.external_name('containerId')] = hit.get('containerId', '')
		d[self.external_name('collectionId')] = hit.get('collectionId', '')
		return hit.get('oid', None)

##########################

class MetaNote(MetaHighlight):
	def __new__(cls, name, bases, cls_dict):
		t = super(MetaNote, cls).__new__(cls, name, bases, cls_dict)
		t.inverted_fields['content'] = 'Body'
		return t

class Note(Highlight):

	"""
	Base clase for any user notes indices.
	The schema fields are as follows

	collectionId: Book/Collection name
	creator: username
	last_modified: Last modified epoc
	content: text to index
	sharedWith: Shared list keyword
	references: Note references
	quick: text used for type-ahead
	id: internal id

	"""

	__metaclass__ = MetaNote

	__indexable__ = True

	indexname_postfix = '_notes'

	_schema = Schema(	collectionId=ID(stored=True),
						oid=ID(stored=True, unique=True),
						containerId=ID(stored=True),
						creator=ID(stored=True),
				  		last_modified=DATETIME(stored=True),
				  		content=TEXT(stored=True, spelling=True),
				  		sharedWith=KEYWORD(stored=False), 
				  		references=KEYWORD(stored=False), 
				 		quick=NGRAM(maxsize=10),
				 		id=NUMERIC(int, stored=False),
				 		keywords=KEYWORD(stored=True),
				 		ntiid=ID(stored=True) )

	fields = {
			"CollectionID": ("collectionId", echo),
			OID: ("oid",  echo),
			"ContainerId":("containerId", echo),
			CREATOR: ("creator", echo),
			LAST_MODIFIED: ("last_modified", get_datetime),
			"body" : ("content", get_text_from_mutil_part_body),
			"sharedWith": ("sharedWith", get_keywords),
			"references": ("references", get_keywords),
			"id": ("id", echo),
			"keywords": ("keywords", get_keywords),
			NTIID: ("ntiid", echo)
			}

class MessageInfo(Note):

	"""
	Base clase for any user chat message indices.
	The schema fields are as follows

	containerId: Room id / Transcript id
	content: message text
	creator: message creator
	recipients: message recipients
	sharedWith: message shared with list
	quick: text used for type-ahead
	oid: message internal id
	id: message id
	"""

	__indexable__ = True

	indexname_postfix = '_chat_messages'

	_schema = Schema(	containerId=ID(stored=True), 
				  		content=TEXT(stored=True, spelling=True),
				  		creator=ID(stored=True),
				  		channel=ID(stored=False),
				  		references=KEYWORD(stored=False), 
				  		recipients=KEYWORD(stored=False), 
				  		sharedWith=KEYWORD(stored=False), 
				 		quick=NGRAM(maxsize=10),
				 		oid=ID(stored=True, unique=True),
				 		id=ID(stored=True, unique=True),
				 		last_modified=DATETIME(stored=True),
				 		keywords=KEYWORD(stored=True),
				 		ntiid=ID(stored=True))

	fields = {
			"ContainerId": ("containerId", echo),
			"Body": ("content", get_text_from_mutil_part_body),
			CREATOR: ("creator", echo),
			"channel": ("channel", echo),
			"references": ("references", get_keywords),
			"recipients": ("recipients", get_keywords),
			"sharedWith": ("sharedWith", get_keywords),
			LAST_MODIFIED: ("last_modified", get_datetime),
			"ID": ("id",  echo),
			OID: ("oid",  echo),
			"keywords": ("keywords", get_keywords),
			NTIID: ("ntiid", echo)
			}

	def get_index_data(self, externalValue, items=None):
		result = super(MessageInfo, self).get_index_data(externalValue, items)
		result.pop('collectionId', None)
		return result

	def get_data_from_search_hit(self, hit, d):
		result = super(MessageInfo, self).get_data_from_search_hit(hit, d)
		d[self.external_name('id')] = hit.get('id', '')
		d.pop(COLLECTION_ID, None)
		return result

##########################

class _Illustration(UserIndexableContent):
	_schema = None
	__indexable__ = False

	def get_index_data(self, externalValue, *args, **kwargs):
		return {}

class Canvas(_Illustration):
	def get_index_data(self, externalValue, *args, **kwargs):
		data = externalValue
		if not isinstance(data, collections.Mapping) or 'shapeList' not in data:
			return None

		items = []
		shapeList = data['shapeList']
		for shape in shapeList:
			txt = get_text_from_mutil_part_body(shape)
			if txt: items.append(txt)

		return {'text': ' '.join(items)} if items else {}


class CanvasShape(_Illustration):
	pass

class CanvasCircleShape(CanvasShape):
	pass

class CanvasPolygonShape(CanvasShape):
	pass

class CanvasTextShape(CanvasShape):
	pass

