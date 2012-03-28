import time
import inspect
import collections
from datetime import datetime

from whoosh import fields
from whoosh import highlight
from whoosh.searching import Hit
from whoosh.qparser import QueryParser
from whoosh.qparser import GtLtPlugin
from whoosh.qparser.dateparse import DateParserPlugin

from nti.contentsearch.common import echo
from nti.contentsearch.common import get_attr
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_content
from nti.contentsearch.common import get_collection
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight

from nti.contentsearch.common import (	NTIID, CREATOR, LAST_MODIFIED, TYPE, CLASS, ID, 
										COLLECTION_ID, ITEMS, SNIPPET, HIT, HIT_COUNT, SUGGESTIONS, 
										CONTENT, CONTAINER_ID, TARGET_OID, BODY)

from nti.contentsearch.common import (	color_, quick_, channel_, content_, keywords_, references_, body_,
										id_, recipients_, sharedWith_, oid_ , ntiid_, title_, last_modified_,
										creator_, startHighlightedFullText_, containerId_, collectionId_)
	
from nti.contentsearch.common import (	oid_fields, ntiid_fields, creator_fields, container_id_fields,
										last_modified_fields)
		
import logging
logger = logging.getLogger( __name__ )

# ----------------------------------

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
			if 	name in gbls and inspect.isclass(gbls[name]) and \
				hasattr(gbls[name], '__indexable__'):
				try:
					obj = gbls[name]()
					d = obj.get_index_data(item)
					add_to_items(d, content_)
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

get_highlighted_content = word_content_highlight

# ----------------------------------

_default_word_max_dist = 15
_default_search_limit = None
_default_suggest_limit = None
_default_search_plugins =  (GtLtPlugin, DateParserPlugin)

class _SearchableContent(object):
	
	__indexable__ = False
	
	@property
	def schema(self):
		return self.get_schema()
	
	def get_schema(self):
		return getattr(self, '_schema', None)
	
	def external_name(self, name):
		"""
		external name for the schema field name
		"""
		if name ==  ntiid_:
			return NTIID
		elif name ==  oid_:
			return TARGET_OID
		elif name == title_:
			return name.capitalize()
		elif name == last_modified_:
			return LAST_MODIFIED
		else:
			return name
	
	# ---------------
	
	def _prepare_query(self, field, query, plugins=_default_search_plugins):
		qp = QueryParser(field, schema=self.get_schema())
		for pg in plugins or ():
			qp.add_plugin(pg())
		parsed_query = qp.parse(unicode(query))
		return parsed_query
	
	def search(self, searcher, query, limit=_default_search_limit, *args, **kwargs):
		parsed_query = self._prepare_query(content_, query)
		return self.execute_query_and_externalize(searcher, content_, parsed_query, query, limit, *args, **kwargs)
		
	def ngram_search(self, searcher, query, limit=_default_search_limit, *args, **kwargs):
		parsed_query = self._prepare_query(quick_, query)
		return self.execute_query_and_externalize(searcher, quick_, parsed_query, query, limit, *args, **kwargs)
	
	quick_search = ngram_search
	
	def suggest_and_search(self, searcher, query, limit=_default_search_limit, *args, **kwargs):
		if ' ' in query:
			suggestions = []
			result = self.search(searcher, query, limit)
		else:
			result = self.suggest(searcher, query, limit, *args, **kwargs)
			suggestions = result.get(ITEMS, None)
			if suggestions:
				result = self.search(searcher, suggestions[0], limit, *args, **kwargs)
			else:
				result = self.search(searcher, query, limit, *args, **kwargs)

		result[SUGGESTIONS] = suggestions
		return result

	def suggest(self, searcher, word, limit=_default_suggest_limit, *args, **kwargs):
		prefix = kwargs.get('prefix', None) or len(word)
		maxdist = kwargs.get('maxdist', None) or _default_word_max_dist
		result = empty_suggest_result(word)
		records = searcher.suggest(content_, word, maxdist=maxdist, prefix=prefix)
		records = records[:limit] if limit and limit > 0 else records
		result[ITEMS] = records
		result[HIT_COUNT] = len(records)
		return result

	def execute_query_and_externalize(self, searcher, search_field, parsed_query, query, limit, *args, **kwargs):

		stored_field = search_field in self.get_schema().stored_names()
		field_found_in_query = search_field in list(t[0] for t in parsed_query.iter_all_terms())
		search_hits = searcher.search(parsed_query, limit=limit)
	
		surround = kwargs.get('surround', 20)
		maxchars = kwargs.get('maxchars', 300)
		search_hits.formatter = highlight.UppercaseFormatter()
		search_hits.fragmenter = highlight.ContextFragmenter(maxchars=maxchars, surround=surround)
		
		result = empty_search_result(query)
		items = result[ITEMS]
		
		lm = 0
		for hit_count, hit in enumerate(search_hits):
			d = {}
			item_id = self.get_data_from_search_hit(hit, d)
			lm = max (lm, d.get(LAST_MODIFIED, 0))
	
			snippet = None
			if stored_field:
				if field_found_in_query:
					snippet = hit.highlights(search_field)
				else:
					snippet = get_highlighted_content(query, 
													  hit.get(content_, u''),
													  maxchars=maxchars, 
													  surround=surround)
			else:
				snippet = ngram_content_highlight(query, 
												  hit.get(content_, u''),
												  maxchars=maxchars, 
												  surround=surround)
			
			if not snippet:
				snippet = hit.get(content_, u'')

			d[SNIPPET] = snippet
			items[item_id or hit_count] = d

		result[LAST_MODIFIED] = lm
		result[HIT_COUNT] = len(items)
		return result

	def get_data_from_search_hit(self, hit, d):
		"""
		return a dictionary with that that represents a search hit
		"""
		d[CLASS] = HIT
		d[LAST_MODIFIED] = epoch_time(hit[last_modified_]) if last_modified_ in hit else 0
		return str(hit.docnum) if hit.__class__ == Hit else None
	
	
# ----------------------------------

def create_book_schema():
	"""
	Book index schema

	ntiid: Internal nextthought ID for the chapter/section
	title: chapter/section title
	last_modified: chapter/section last modification since the epoch
	keywords: chapter/section key words
	content: chapter/section text
	quick: chapter/section text ngrams
	related: ntiids of related sections
	ref: chapter reference
	"""
	
	schema = fields.Schema(	ntiid = fields.ID(stored=True, unique=True),
							title = fields.TEXT(stored=True, spelling=True),
				  			last_modified = fields.DATETIME(stored=True),
				  			keywords = fields.KEYWORD(stored=True), 
				 			quick = fields.NGRAM(maxsize=10),
				 			related = fields.KEYWORD(stored=True),
				 			section = fields.TEXT(),
				 			content = fields.TEXT(stored=True, spelling=True))
	return schema

class Book(_SearchableContent):
	"""
	Base clase for any a book index.
	"""
	
	_schema = create_book_schema()
	
	def get_data_from_search_hit(self, hit, d):
		super(Book, self).get_data_from_search_hit(hit, d)
		d[TYPE] = CONTENT
		d[self.external_name(title_)] = hit[title_]
		d[self.external_name(ntiid_)] = hit[ntiid_]
		d[CONTAINER_ID] = hit[ntiid_]
		return hit[ntiid_]

# ----------------------------------

class UserIndexableContent(_SearchableContent):

	__indexable__ = False
	
	def external_name(self, name):
		if name ==  'creator':
			return CREATOR
		elif name ==  'containerId':
			return CONTAINER_ID
		elif name == collectionId_:
			return COLLECTION_ID
		else:
			return super(UserIndexableContent, self).external_name(name)
		
	def get_index_data(self, data, *args, **kwargs):
		"""
		return a dictonary with the info to be stored in the index
		"""
		result = {}
		if isinstance(data, basestring):
			result[oid_] = data
		else:
			result[oid_] = echo(get_attr(data, oid_fields))
			result[ntiid_] = echo(get_attr(data, ntiid_fields)) or result[oid_]
			result[creator_] = echo(get_attr(data, creator_fields))
			result[containerId_] = echo(get_attr(data, container_id_fields))
			result[collectionId_] = echo(get_collection(result[containerId_]))
			result[last_modified_] = get_datetime(get_attr(data, last_modified_fields))
		return result

	def get_data_from_search_hit(self, hit, d):
		super(UserIndexableContent, self).get_data_from_search_hit(hit, d)
		d[TYPE] = self.__class__.__name__
		d[self.external_name(oid_)] = hit.get(oid_, '')
		d[self.external_name(ntiid_)] = hit.get(ntiid_, '')
		d[self.external_name(creator_)] = hit.get(creator_, '')
		d[self.external_name(containerId_)] = hit.get(containerId_, '')
		d[self.external_name(collectionId_)] = hit.get(collectionId_, '')
		return hit.get(oid_, None)
	
	# ---------------
	
	def index_content(self, writer, data, auto_commit=True, **commit_args):
		d = self.get_index_data(data)
		if d.has_key(oid_) and d.has_key(containerId_):
			try:
				writer.add_document(**d)
				if auto_commit:
					writer.commit(**commit_args)
				return True
			except Exception, e:
				writer.cancel()
				raise e
		return False

	def update_content(self, writer, data, auto_commit=True, **commit_args):
		d = self.get_index_data(data)
		if d.has_key(oid_) and d.has_key(containerId_):
			try:
				writer.update_document(**d)
				if auto_commit:
					writer.commit(**commit_args)
				return True
			except Exception, e:
				writer.cancel()
				raise e
		return False
		
	def delete_content(self, writer, data, auto_commit=True, **commit_args):
		d = self.get_index_data(data)
		if d.has_key(oid_) and d.has_key(containerId_):
			try:
				writer.delete_by_term(oid_, unicode(d[oid_]))
				if auto_commit:
					writer.commit(**commit_args)
				return True
			except Exception, e:
				writer.cancel()
				raise e
		return False
	
# ----------------------------------

def create_highlight_schema():
	"""
	Highlight index schema

	collectionId: Book/Library that the highlight belongs to
	ntiid: Highlight nti id
	oid: Highlight object id
	creator: Highlight creator username
	last_modified: Highlight last modification time
	content: Highlight text
	sharedWith: Highlight shared users
	color: Highlight color
	quick: Highlight text ngrams
	keywords: Highlight key words
	"""
	
	schema = fields.Schema(	collectionId = fields.ID(stored=True),
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
	return schema

class Highlight(UserIndexableContent):
	"""
	Base clase for Highlight indexable content.
	"""
	
	__indexable__ = True
	_schema = create_highlight_schema()

	def get_index_data(self, data, *args, **kwargs):
		result = UserIndexableContent.get_index_data(self, data, *args, **kwargs)
		result[color_] = echo(get_attr(data, color_))
		result[keywords_] = get_keywords(get_attr(data, keywords_))
		result[sharedWith_] = get_keywords(get_attr(data, sharedWith_))
		result[content_] = get_content(get_attr(data, startHighlightedFullText_))
		result[quick_] = result[content_]
		return result
	
# ----------------------------------

def create_note_schema():
	"""
	Note index schema

	collectionId: Book/Library that the note belongs to
	ntiid: Note nti id
	oid: Note object id
	creator: Note creator username
	last_modified: Note last modification time
	content: Note text content
	references: Note references
	sharedWith: Highlight shared users
	id: Note id
	quick: Note text ngrams
	keywords: Note key words
	"""
	
	schema = fields.Schema(	collectionId=fields.ID(stored=True),
							oid = fields.ID(stored=True, unique=True),
							containerId = fields.ID(stored=True),
							creator = fields.ID(stored=True),
				  			last_modified = fields.DATETIME(stored=True),
				  			content = fields.TEXT(stored=True, spelling=True),
				  			sharedWith = fields.KEYWORD(stored=False), 
				  			references = fields.KEYWORD(stored=False), 
				 			quick = fields.NGRAM(maxsize=10),
				 			id = fields.NUMERIC(int, stored=False),
				 			keywords = fields.KEYWORD(stored=True),
				 			ntiid = fields.ID(stored=True))
	return schema

class Note(Highlight):
	"""
	Base clase for Note indexable content.
	"""
	
	__indexable__ = True
	_schema = create_note_schema()
	
	def get_index_data(self, data, *args, **kwargs):
		result = UserIndexableContent.get_index_data(self, data, *args, **kwargs)
		result[keywords_] = get_keywords(get_attr(data, keywords_))
		result[references_] = get_keywords(get_attr(data, references_))
		result[sharedWith_] = get_keywords(get_attr(data, sharedWith_))
		result[content_] = get_text_from_mutil_part_body(get_attr(data, body_))
		result[quick_] = result[content_]
		return result

# ----------------------------------

def create_messageinfo_schema():
	"""
	MessageInfo/Chat index schema

	collectionId: Book/Library that the chat/message belongs to
	ntiid: Chat/message nti id
	oid: Chat/message object id
	creator: Chat/message creator username
	last_modified: Chat/message last modification time
	content: Chat/message text content
	references: Chat/message references
	sharedWith: Chat/message shared users
	id: Chat/message id
	quick: Chat/message text ngrams
	keywords: Chat/message key words
	"""
	
	schema = fields.Schema(	containerId = fields.ID(stored=True), 
				  			content = fields.TEXT(stored=True, spelling=True),
				  			creator = fields.ID(stored=True),
				  			channel = fields.ID(stored=False),
				  			references = fields.KEYWORD(stored=False), 
				  			recipients = fields.KEYWORD(stored=False), 
				  			sharedWith = fields.KEYWORD(stored=False), 
				 			quick = fields.NGRAM(maxsize=10),
				 			oid = fields.ID(stored=True, unique=True),
				 			id = fields.ID(stored=True, unique=True),
				 			last_modified = fields.DATETIME(stored=True),
				 			keywords = fields.KEYWORD(stored=True),
				 			ntiid = fields.ID(stored=True),
				 			collectionId=fields.ID(stored=True))
	return schema

class MessageInfo(Note):
	"""
	Base clase for any user chat message indices.
	"""

	__indexable__ = True
	_schema = create_messageinfo_schema()

	def get_index_data(self, data, *args, **kwargs):
		result = UserIndexableContent.get_index_data(self, data, *args, **kwargs)
		result[id_] = echo(get_attr(data, ID))
		result[channel_] = echo(get_attr(data, channel_))
		result[keywords_] = get_keywords(get_attr(data, keywords_))
		result[references_] = get_keywords(get_attr(data, references_))
		result[sharedWith_] = get_keywords(get_attr(data, sharedWith_))
		result[recipients_] = get_keywords(get_attr(data, recipients_))
		result[content_] = get_text_from_mutil_part_body(get_attr(data, BODY))
		result[quick_] = result[content_]
		return result
	
	def get_data_from_search_hit(self, hit, d):
		result = super(MessageInfo, self).get_data_from_search_hit(hit, d)
		d[ID] = hit.get(id_, u'')
		return result

# ----------------------------------

class _Illustration(UserIndexableContent):
	__indexable__ = False
	
	def get_index_data(self, data, *args, **kwargs):
		return {}

class Canvas(_Illustration):
	
	def get_index_data(self, data, *args, **kwargs):
		items = []
		shapeList = get_attr(data, 'shapeList', [])
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

# ----------------------------------

_indexables = {}
for k,v in globals().items():
	if inspect.isclass(v) and getattr(v, '__indexable__', False):
		name = k[0:-1] if k.endswith('s') else k
		_indexables[k.lower()] = v()
		
def get_indexables():
	return _indexables.keys()

def get_indexable_object(type_name='Notes'):
	name = type_name[0:-1] if type_name.endswith('s') else type_name
	result = _indexables.get(name.lower(), None)
	return result
