#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property

from hamcrest import is_not

does_not = is_not


import os
import os.path


from nti.dataserver import  classes


from nti.dataserver.tests import mock_dataserver

import anyjson as json



from zope import component



from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary
from nti.assessment import interfaces as asm_interfaces, submission as asm_submission
from nti.tests import verifiably_provides
from nti.appserver import interfaces as app_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.dataserver.mimetype import  nti_mimetype_with_class
from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from .test_application import TestApp

class TestApplicationAssessment(SharedApplicationTestBase):
	child_ntiid =  'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

	@classmethod
	def _setup_library( self, *args, **kwargs ):
		return FileLibrary( os.path.join( os.path.dirname(__file__), 'ExLibrary' ) )

	@WithSharedApplicationMockDS
	def test_registered_utility(self):
		qmap = component.getUtility( asm_interfaces.IQuestionMap )
		assert_that( qmap,
					 verifiably_provides( app_interfaces.IFileQuestionMap ) )
		assert_that( qmap,
					 has_length( 25 ) )
		assert_that( qmap,
					 has_key( self.child_ntiid ) )
		assert_that( qmap.by_file,
					 has_key( has_property( 'absolute_path',
											os.path.join( os.path.dirname(__file__), 'ExLibrary', 'WithAssessment', 'tag_nextthought_com_2011-10_mathcounts-HTML-MN_2012_0.html' ) ) ) )


	@WithSharedApplicationMockDS
	def test_fetch_assessment_question(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )
		# These inherit the same ACLs as the content they came with
		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, status=401 )

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'Question' ) )


		# And if we ask for pageinfo, we can resolve the page it belonged on
		page_info_mt = nti_mimetype_with_class( 'pageinfo' )
		page_info_mt_json = page_info_mt + '+json'

		res = testapp.get( '/dataserver2/NTIIDs/' + self.child_ntiid,
						   headers={'Accept': str(page_info_mt_json)},
						   extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 303 ) ) # redirect

		res = testapp.get( res.location, headers={'Accept': str(page_info_mt_json)}, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'PageInfo' ) )

	@WithSharedApplicationMockDS
	def test_fetch_pageinfo_with_questions(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		for accept_type in ('application/json','application/vnd.nextthought.pageinfo','application/vnd.nextthought.pageinfo+json'):
			__traceback_info__ = accept_type
			res = testapp.get( '/dataserver2/NTIIDs/tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0',
							   headers={"Accept": accept_type},
							   extra_environ=self._make_extra_environ() )
			assert_that( res.status_int, is_( 200 ) )
			assert_that( res.last_modified, is_( not_none() ) )

			assert_that( res.content_type, is_( 'application/vnd.nextthought.pageinfo+json' ) )
			assert_that( res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.pageinfo' ) )
			assert_that( res.json_body, has_entry( 'AssessmentItems', has_item( has_entry( 'NTIID', self.child_ntiid ) ) ) )
			assert_that( res.json_body, has_entry( 'Last Modified', greater_than( 0 ) ) )

	def _check_submission( self, res ):
		assert_that( res.json_body, has_entry( StandardExternalFields.CLASS, 'AssessedQuestion' ) )
		assert_that( res.json_body, has_entry( StandardExternalFields.CREATED_TIME, is_( float ) ) )
		assert_that( res.json_body, has_entry( StandardExternalFields.LAST_MODIFIED, is_( float ) ) )
		assert_that( res.json_body, has_entry( StandardExternalFields.MIMETYPE, 'application/vnd.nextthought.assessment.assessedquestion' ) )

	@WithSharedApplicationMockDS
	def test_posting_assesses_mimetype_only(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		sub = asm_submission.QuestionSubmission( questionId=self.child_ntiid, parts=('correct',) )
		ext_obj = toExternalObject( sub )

		ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
		# Submit mimetype only, just to be sure it works
		ext_obj.pop( 'Class' )
		data = json.serialize( ext_obj )
		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
		self._check_submission( res )

	@WithSharedApplicationMockDS
	def test_posting_assesses_class_only(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		sub = asm_submission.QuestionSubmission( questionId=self.child_ntiid, parts=('correct',) )
		ext_obj = toExternalObject( sub )

		ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
		# Submit Class only, just to be sure it works
		ext_obj.pop( 'MimeType' )
		data = json.serialize( ext_obj )
		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
		self._check_submission( res )

	@WithSharedApplicationMockDS
	def test_posting_multiple_choice(self):

		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
		testapp = TestApp( self.app )

		# The correct answer is at index 1, and has the value 'Steam distillation". We should be able to submit all
		# three forms
		for submittedResponse in ( 1, "1", "Steam distillation", ):
			sub = asm_submission.QuestionSubmission( questionId='tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.21', parts=(submittedResponse,) )
			ext_obj = toExternalObject( sub )

			ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
			data = json.serialize( ext_obj )
			res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
			self._check_submission( res )
			assert_that( res.json_body, has_entry( 'parts', has_item( has_entries( 'assessedValue', 1.0, 'submittedResponse', submittedResponse ) ) ) )

		# The correct answer is at index 3, and has the value '1000 BC". We should be able to submit all
		# three forms
		for submittedResponse in ( 3, "3", "1000 BC", ):
			sub = asm_submission.QuestionSubmission( questionId='tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.10', parts=(submittedResponse,) )
			ext_obj = toExternalObject( sub )

			ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
			data = json.serialize( ext_obj )
			res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com', data, extra_environ=self._make_extra_environ() )
			self._check_submission( res )
			assert_that( res.json_body, has_entry( 'parts', has_item( has_entries( 'assessedValue', 1.0, 'submittedResponse', submittedResponse ) ) ) )
