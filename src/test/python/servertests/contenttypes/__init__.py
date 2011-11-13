import pdb
import inspect
import UserDict
import collections

#########################

__all__ = ['toExternalObject', 'DSObject','Sharable', 'Highlight', 'Note', 'adaptDSObject','adapt_ds_object']

#########################

def toExternalObject(obj):
	if isinstance(obj, collections.Mapping):
		return obj
	elif isinstance(obj, DSObject):
		return obj.toDataServerObject()
	else:
		return None

#########################

def getter(name, def_value=None):
	def function(self):
		if self.really_contains( name ):
			return self[name]
		self.really_set( name, def_value() if isinstance(def_value,type) else def_value )
		return self[name]
	return function

def setter(name):
	def function(self, val):
		self[name] = val
	return function

class MetaDSObject(type):
	def __new__(mcs, clsname, clsbases, clsdict):
		t = type.__new__(mcs, clsname, clsbases, clsdict)
		fields = getattr(t, '_fields', None)
		if fields is not None:
			# _fields is a mapping between field name and
			# a value, either boolean for readonly, or a
			# tuple (readonly, default_value). def_value my be a type
			# to construct a new one on access.
			# create properties for our fields
			for name, value in fields.items():
				readonly = value
				def_value = None
				if isinstance( value, tuple ):
					readonly, def_value = value

				if readonly:
					setattr(t, name, property(getter(name, def_value)))
				else:
					setattr(t, name, property(getter(name, def_value), setter(name)))
		# create a reverse mapping
		mapping = getattr(t, '_ds_field_mapping', None)
		if mapping:
			inverted = {}
			for key, val in mapping.items():
				inverted[val] = key
			t._inverted_ds_field_mapping = inverted
		return t

# -----------------------------------

class DSObject(object, UserDict.DictMixin):

	__metaclass__ = MetaDSObject

	# defines a mapping from testing framework fields -> internal dataserver fields
	_ds_field_mapping = {'id' : 'OID', 'container': 'ContainerId', 'creator': 'Creator', \
						 'lastModified': 'Last Modified'}

	# mapping of fields we expose to readonly
	_fields = {'container': True, 'id': True, 'creator': True, 'lastModified' : True}

	def __init__(self, data=None, **kwargs):
		self._data = data or {}

		#Set our class name if we now it
		if hasattr(self, "DATASERVER_CLASS"):
			self._data['Class'] = getattr( self, 'DATASERVER_CLASS' )

		if kwargs:
			for field in self._fields:
				if field in kwargs:
					val = kwargs[field]
					field = self._ds_field_mapping.get(field, field)
					self._data[field] = val

	# Oddly, we claim to contain everything
	# we have a field for, even if it has never been set.
	# Our [] implementation will return a value for
	# everything we declare a field for, even if never set.
	# These all need to be consistent: __contains__, keys,
	# iterkeys(), items, __getitem__, __setitem__

	def __contains__( self, key ):
		return key in self._fields

	def really_contains( self, key ):
		return key in self._data

	def really_set( self, key, value ):
		self._data[key] = value

	def __getitem__(self, key):
		if key not in self._fields:
			raise KeyError('Unsupported key %s' % key)

		key = self._ds_field_mapping[key] if key in self._ds_field_mapping else key
		return self._data[key] if key in self._data else None

	def _field_readonly( self, field ):
		value = self._fields[field]
		if isinstance( value, tuple ):
			value = value[0]
		return value

	def __setitem__(self, key, val):
		if key not in self._fields or self._field_readonly( key ):
			raise KeyError('Cannot set uneditable field %s' % key)

		key = self._ds_field_mapping[key] if key in self._ds_field_mapping else key
		self._data[key] = val

	def __delitem__(self, key):
		raise RuntimeError("cannot delete property")

	def keys(self):
		return self._fields.keys()


	def toDataServerObject(self):
		external = {}
		for key, val in self._data.iteritems():
			#val may be an array in which case we need to call toDataserverObject
			#on each value
			if isinstance(val, list):
				val = [v.toDataServerObject() if hasattr(v, 'toDataServerObject') else v \
					   for v in val]
			elif hasattr(val, 'toDataServerObject'):
				val = val.toDataServerObject()

			external[key] = val
		return external

	def updateFromDataServerObject(self, dsDict):
		self._data = adaptDSObject(dsDict)

	def _assign_to_list(self, mapkey, val, defType=list):
		if isinstance(val, list):
			collection = val
		elif isinstance(val, basestring):
			collection = [val]
		elif isinstance(val, collections.Iterable):
			collection = self._data[mapkey] if mapkey in self._data else defType()
			collection.extend(val)
		else:
			collection = [val]
		self._data[mapkey] = collection

	def __str__( self ):
		return "%s(%s)" % (self.__class__.__name__,self._data)

	def __repr__( self ):
		return self.__str__()

	@classmethod
	def fields(cls):
		"""
		return the fields for this object
		"""
		return list(cls._fields.keys())


# -----------------------------------

class FriendsList(DSObject):
	DATASERVER_CLASS = 'FriendsList'

	_ds_field_mapping = {'name': 'Username', 'friends' : 'friends'}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'name': True, 'friends' : False}
	_fields.update(DSObject._fields)

	def __setitem__(self, key, val):
		if key == 'friends':
			self._assign_to_list(self._ds_field_mapping['friends'], val)
		elif key == 'name' or key == 'username':
			self._data[self._ds_field_mapping['name']] = val
		else:
			super(FriendsList, self).__setitem__(key, val)

# -----------------------------------

class Sharable(DSObject):

	_ds_field_mapping = {'sharedWith' : 'sharedWith'}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'sharedWith' : (False,list)}
	_fields.update(DSObject._fields)

	def __setitem__(self, key, val):
		if key == 'sharedWith':
			self._assign_to_list(self._ds_field_mapping['sharedWith'], val)
		else:
			super(Sharable, self).__setitem__(key, val)

	def shareWith(self, targetOrTargets):
		targets = targetOrTargets
		if not isinstance(targets, list):
			targets = [targets]
		self.sharedWith.extend(targets)

	def revokeSharing(self, targetOrTargets):
		targets = targetOrTargets
		if not isinstance(targets, list):
			targets = [targets]

		for target in targets:
			self.sharedWith.remove(target)

# -----------------------------------

class Threadable(DSObject):
	_ds_field_mapping = {'references':'references', 'inReplyTo':'inReplyTo'}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'references' : (False, list), 'inReplyTo' : False}
	_fields.update(DSObject._fields)

	def __setitem__(self, key, val):
		if key == 'references':
			self._assign_to_list(self._ds_field_mapping['references'], val)
		else:
			super(Threadable, self).__setitem__(key, val)

class Highlight(Sharable):
	DATASERVER_CLASS = 'Highlight'

	_ds_field_mapping = {}
	_ds_field_mapping.update(Sharable._ds_field_mapping)

	_fields = {'startHighlightedText': False}
	_fields.update(Sharable._fields)

# -----------------------------------

class Note(Sharable, Threadable):

	DATASERVER_CLASS = "Note"

	_ds_field_mapping = {}
	_ds_field_mapping.update(Sharable._ds_field_mapping)
	_ds_field_mapping.update(Threadable._ds_field_mapping)

	_fields = {'text': False, 'body': False}
	_fields.update(Sharable._fields)
	_fields.update(Threadable._fields)

# -----------------------------------

class Change(DSObject):
	DATASERVER_CLASS = 'Change'

	_ds_field_mapping = {'changeType': 'ChangeType', 'item': 'Item'}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'changeType': True, 'item': True}
	_fields.update(DSObject._fields)

# -----------------------------------

class Canvas(DSObject):
	DATASERVER_CLASS = 'Canvas'

	_ds_field_mapping = {}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'shapeList':False}
	_fields.update(DSObject._fields)

# -----------------------------------

class CanvasAffineTransform(DSObject):
	DATASERVER_CLASS = 'CanvasAffineTransform'

	_ds_field_mapping = {}

	_fields = {'a' : False, 'b' : False, 'c' : False, 'd' : False, 'tx' : False, 'ty' : False}

# -----------------------------------

class CanvasShape(DSObject):
	DATASERVER_CLASS = 'CanvasShape'

	_ds_field_mapping = {}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'transform' : CanvasAffineTransform()}
	_fields.update(DSObject._fields)

# -----------------------------------
class CanvasPolygonShape(CanvasShape):
	DATASERVER_CLASS = 'CanvasPolygonShape'

	_ds_field_mapping = {}
	_ds_field_mapping.update(DSObject._ds_field_mapping)

	_fields = {'sides' : False}
	_fields.update(CanvasShape._fields)

# -----------------------------------

DS_TYPE_REGISTRY = {}
for v in dict(locals()).itervalues():
	if inspect.isclass(v) and issubclass(v, DSObject):
		if hasattr(v, 'DATASERVER_CLASS'):
			DS_TYPE_REGISTRY[v.DATASERVER_CLASS] = v

def adaptDSObject(dsobject):

	# if we arent a list or a dict we are just a plain value
	if not (isinstance(dsobject, list) or isinstance(dsobject, dict)):
		return dsobject

	# if our ds object is an array we need to convert all the subparts
	if isinstance(dsobject, list):
		objects = []
		for dsobj in dsobject:
			objects.append(adaptDSObject(dsobj))
		return objects

	# most of the time we get back dictionaries
	# our dictionaries can wrap objects in two ways.  Via Items and Item
	# adapt those as necessary
	# its not just items and item we need to adapt.  Some things like
	# friends lists need each key adapted.
	for key in dsobject:
		dsobject[key] = adaptDSObject(dsobject[key])

	# any children we have have been adapted.  Now adapt ourselves
	className = dsobject.get('Class', None)
	clazz = DS_TYPE_REGISTRY.get(className, None)

	adaptedObject = clazz(data=dsobject) if clazz else dsobject
	return adaptedObject

adapt_ds_object = adaptDSObject
