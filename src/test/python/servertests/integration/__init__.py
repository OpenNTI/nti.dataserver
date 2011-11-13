import collections
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest import all_of
from hamcrest import any_of
from hamcrest import has_entry
from hamcrest.library.collection.issequence_containinginanyorder import contains_inanyorder
from hamcrest import has_item
from hamcrest import has_items
from hamcrest import has_key
from hamcrest import has_length

##########################

class ItemInChange(BaseMatcher):
	def __init__(self, change):
		self.change = change

	def _matches(self, item):
		oid = item
		if 'OID' in oid:
			oid = oid['OID']
		return self.change['Item']['OID'] == oid

	def describe_to(self, description):
		description.append('%s' % self.change['Item'])

class ContainedIn(BaseMatcher):

	def __init__(self, c ):
		super( ContainedIn, self ).__init__(  )
		self.container = c
		self._descr = 'collection containing <unknown object>'

	def matches( self, item, mismatch_description=None ):
		res = self._matches( item )
		if not res:
			self._descr = 'collection containing ' + str( item )
			if mismatch_description:
				self.describe_mismatch( item, mismatch_description )
		return res

	def _matches(self, item):
		isContainer = container().matches(self.container)
		if not isContainer:
			return False

		return contains(item).matches(self.container)

	def describe_mismatch(self, item, description):
		description.append_list('(',',',')', self.container['Items'])

	def describe_to( self, description ):
		description.append_text( self._descr )


##########################

def container():
	return has_key('Items')

def container_of_length(count):
	return all_of(container(), has_entry('Items', has_length(count)))

def contained_in(container):
	return ContainedIn(container)

def contains(item):
	return has_entry('Items', has_item(has_same_oid_as(item)))

def not_shared():
	return any_of( has_entry( 'sharedWith', None ), has_entry('sharedWith', []) )

def only_shared_with(target):
	if isinstance(target, list):
		return all_of(has_entry('sharedWith', contains_inanyorder(*target)), has_entry('sharedWith', has_length(len(target))))
	return has_entry('sharedWith', [target])

def shared_with(target):
	#strings are iterable
	if isinstance(target, list):
		return has_entry('sharedWith', contains_inanyorder(*target))
	return has_entry('sharedWith', has_item(target))

def has_same_oid_as(obj):
	oid = obj
	if hasattr(obj, 'id'):
		oid = obj.id
	elif 'OID' in obj:
		oid = obj['OID']
	return any_of(has_entry('OID', oid), has_entry('id', oid))

def in_change(change):
	return ItemInChange(change)

def sortchanges(changes, order='desc'):
	"""
	Sort changes by last modified time.  order is asc or desc
	"""
	def changesLastModified(change):
		if hasattr(change, 'lastModified'):
			return change.lastModified
		return change['Last Modified']
	return sorted(changes, key=changesLastModified, reverse=order=='desc')

def of_class(clazz):
	return has_entry('Class', clazz)

def note():
	return of_class('Note')

def highlight():
	return of_class('Highlight')

def of_change_type_circled():
	return of_change_type('Circled')

def of_change_type(ctype):
	return any_of(has_entry('ChangeType', ctype), has_entry('changeType', ctype))

def of_change_type_shared():
	return of_change_type('Shared')

def of_change_type_modified():
	return of_change_type('Modified')

def containing_no_friends():
	return has_entry('friends', [])

def containing_friend(friend):
	return has_entry('friends', has_item(has_entry('Username', friend)))

def containing_friends(friends):
	return all_of(*[containing_friend(friend) for friend in friends])

def contains_friendslist(fl):
	return has_key(fl)

def wraps_item(item):
	return any_of(has_entry('Item', has_same_oid_as(item)), has_entry('item', has_same_oid_as(item)))

def user(name):
	return has_entry('Username', name)

def accepting(name):
	return has_entry('accepting', has_item(user(name)))

def notification_count(c):
	return has_entry('NotificationCount', c)

##########################

def objectFromContainer(container, obj):
	matcher = has_same_oid_as(obj)
	for item in container['Items']:
		if matcher.matches(item):
			return item
	return None

def friendslistFromFriendsLists(lists, name):
	return lists[name]

def objectsFromContainer(c):
	return c['Items']

def unwrapObject(w):
	if hasattr(w, 'item'):
		return w.item
	return w['Item']

def get_notification_count(userObj):
	return userObj['NotificationCount']
