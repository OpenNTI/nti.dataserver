#!/usr/bin/env python
#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
#from hamcrest import is_not
from hamcrest import has_property
from hamcrest import all_of
from hamcrest import contains
from hamcrest import has_item
from hamcrest import greater_than

from nti.app.externalization.internalization import class_name_from_content_type
from nti.appserver.ugd_edit_views import UGDPutView as _UGDPutView
from nti.appserver.ugd_edit_views import UGDPostView as _UGDPostView
from nti.appserver.ugd_edit_views import UGDDeleteView as _UGDDeleteView

from nti.app.testing.layers import NewRequestLayerTest
from pyramid.threadlocal import get_current_request
import pyramid.httpexceptions as hexc


from nti.dataserver import users

from nti.coremetadata.mixins import ZContainedMixin
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.externalization.representation import to_external_representation

from nti.ntiids import ntiids

from zope import interface
import nti.dataserver.interfaces as nti_interfaces
from nti.contentlibrary import interfaces as lib_interfaces

class TestContentType(unittest.TestCase):
	def test_content_type(self):
		assert_that( class_name_from_content_type( None ), is_( none() ) )
		assert_that( class_name_from_content_type( 'text/plain' ), is_( none() ) )

		assert_that( class_name_from_content_type( 'application/vnd.nextthought+json' ), is_( none() ) )

		assert_that( class_name_from_content_type( 'application/vnd.nextthought.class+json' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.version.class+json' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.class' ),
					 is_( 'class' ) )
		assert_that( class_name_from_content_type( 'application/vnd.nextthought.version.flag.class' ),
					 is_( 'class' ) )

# def test_user_pseudo_resources_exist():
# 	user = users.User( 'jason.madden@nextthought.com' )
# 	# Fake out an ACL for this user since those are required now
# 	user.__acl__ = (1,)
# 	class Parent(object):
# 		request = None


# 	def _test( name ):
# 		p = Parent()
# 		p.request = pyramid.testing.DummyRequest()
# 		assert_that( _UserResource( p, user )[name], is_not( none() ) )

# 	for k in ('Objects', 'NTIIDs', 'Library', 'Pages', 'Classes'):
# 		yield _test, k

from zope.keyreference.interfaces import IKeyReference

@interface.implementer(IKeyReference) # IF we don't, we won't get intids
class ContainedExternal(ZContainedMixin):

	def toExternalObject( self ):
		return str(self)

class _Context(object):
	resource = None
	__acl__ = ()

@interface.implementer(nti_interfaces.ILastModified, nti_interfaces.IContained, nti_interfaces.IZContained, IKeyReference)
class _ContainedObject(object):
	__name__ = None
	__parent__ = None
	lastModified = 0
	containerId = None
	id = None
	__acl__ = ()
	def updateFromExternalObject( self, *args, **kwargs ):
		return True # Yes, we modified

	def updateLastMod(self, t=None):
		self.lastModified = 1 if t is None else t

from zope.component import eventtesting
from zope.lifecycleevent import IObjectModifiedEvent, IObjectRemovedEvent, IObjectAddedEvent
from nti.appserver._dataserver_pyramid_traversal import _NTIIDsContainerResource
class TestUGDModifyViews(NewRequestLayerTest):

	def _establish_context( self, view, user=None, ext_value=None, add_contained_object=False ):

		if user is None:
			user = users.User.create_user( self.ds, username='jason.madden@nextthought.com', password='temp001' )
			assert user.__parent__

		resource = user
		if add_contained_object:
			con_obj = _ContainedObject()
			con_obj.containerId = u'abc'
			con_obj.id = u'123'
			user.addContainedObject( con_obj )
			resource = con_obj
			con_obj.lastModified = 0
			user.getContainer( con_obj.containerId ).lastModified = 0

		view.request.context = _Context()
		view.request.context.resource = resource
		view.request.content_type = 'application/vnd.nextthought+json'
		view.request.body = to_external_representation( ext_value or {}, 'json' )

		eventtesting.clearEvents()
		user.lastModified = 0

		return user, resource

	@WithMockDSTrans
	def test_put_summary_obj(self):
		#"We can put an object that summarizes itself before we get to the renderer"
		view = _UGDPutView( get_current_request() )
		self._establish_context( view )

		result = view()
		assert_that( result, is_( dict ) )


	@WithMockDSTrans
	def test_put_to_user_fires_events(self):
		#"If we put to the User, events fire"""

		view = _UGDPutView( get_current_request() )

		user, _ = self._establish_context( view, ext_value={ 'password': 'uniqPass123', 'old_password': 'temp001' } )

		view()

		# One event, for the object we modified
		assert_that( eventtesting.getEvents(  ), has_length( 3 ) )
		assert_that( eventtesting.getEvents( IObjectModifiedEvent ), has_length( 2 ) )
		mod_event = eventtesting.getEvents( IObjectModifiedEvent )[0]
		assert_that( mod_event, has_property( 'descriptions',
											  has_item(
												  all_of(
													  has_property( 'interface', is_( nti_interfaces.IUser ) ),
													  has_property( 'attributes', contains( 'password' ) ) ) ) ) )

		assert_that( user, has_property( 'lastModified', greater_than( 0 ) ) )

	@WithMockDSTrans
	def test_put_to_contained_object_fires_events(self):
		#"Putting to a contained object fires events to update the object and the container modification times"""

		view = _UGDPutView( get_current_request() )

		user, con_obj = self._establish_context( view, add_contained_object=True )

		view()

		# One event, for the object we modified has a ripple effect
		assert_that( eventtesting.getEvents(  ), has_length( 1 ) )
		assert_that( eventtesting.getEvents( IObjectModifiedEvent ), has_length( 1 ) )
		assert_that( con_obj, has_property( 'lastModified', greater_than( 0 ) ) )
		assert_that( user.getContainer( con_obj.containerId ), has_property( 'lastModified', greater_than( 0 ) ) )

		# The user itself wasn't modified
		assert_that( user, has_property( 'lastModified', 0 ) )

	@WithMockDSTrans
	def test_delete_to_contained_object_fires_events(self):
		#"Deleting a contained object fires events to update the object and the container modification times"""
		self.beginRequest()
		view = _UGDDeleteView( get_current_request() )

		user, con_obj = self._establish_context( view, add_contained_object=True )

		view()

		# Removing the object has a ripple effect and fires a number of events
		# ObjectRemoved, zope...IntIdRemoved, zc...IntIdRemoved, nti...IntIdRemoved, ContainerModified
		assert_that( eventtesting.getEvents(  ), has_length( 5 ) )
		assert_that( eventtesting.getEvents( IObjectRemovedEvent ), has_length( 1 ) )
		assert_that( user.getContainer( con_obj.containerId ), has_property( 'lastModified', greater_than( 0 ) ) )

		# The user itself wasn't modified
		assert_that( user, has_property( 'lastModified', 0 ) )

	@WithMockDSTrans
	def test_post_existing_friendslist_id(self):
		#"We get a good error posting to a friendslist that already exists"
		self.beginRequest()
		view = _UGDPostView( get_current_request() )

		user, _ = self._establish_context( view, ext_value={'Class': 'FriendsList',
															'ID': 'Everyone',
															'Username': 'Everyone',
															'ContainerId': 'FriendsLists'} )
		view.getRemoteUser = lambda: user
		view() # First time fine
		# Fires events the first time
		# ObjectCreated, ObjectAdded, zc...IntIdAdded, zope...IntIdAdded, nti...IntIdAdded, ContainerModified
		assert_that( eventtesting.getEvents(  ), has_length( 9 ) )
		assert_that( eventtesting.getEvents( IObjectAddedEvent ), has_length( 1 ) )

		with self.assertRaises(hexc.HTTPConflict):
			view()


	@WithMockDSTrans
	def test_ntiid_uses_library(self):
		self.beginRequest()
		child_ntiid = ntiids.make_ntiid( provider='ou', specific='test2', nttype='HTML' )

		class NID(object):
			interface.implements(lib_interfaces.IContentUnit)
			ntiid = child_ntiid
			__parent__ = None
			__name__ = child_ntiid
		class Lib(object):
			def pathToNTIID( self, ntiid ): return [NID()] if ntiid == child_ntiid else None

		get_current_request().registry.registerUtility( Lib(), lib_interfaces.IContentPackageLibrary )
		get_current_request().registry.registerUtility( self.ds, nti_interfaces.IDataserver )
		cont = _NTIIDsContainerResource( None, None )
		cont.request = get_current_request()

		assert_that( cont.traverse(child_ntiid, ()), is_( NID ) )
