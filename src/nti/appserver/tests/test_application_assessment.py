#!/usr/bin/env python
from __future__ import print_function, unicode_literals

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_item
from hamcrest import has_key
from hamcrest import has_entries
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property

from hamcrest import is_not
does_not = is_not

from nti.testing.matchers import verifiably_provides

import os
import os.path

from zope import component

from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary
from nti.assessment import interfaces as asm_interfaces, submission as asm_submission

from nti.appserver import interfaces as app_interfaces
from nti.externalization.externalization import toExternalObject
from nti.externalization.interfaces import StandardExternalFields
from nti.dataserver.mimetype import  nti_mimetype_with_class
from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from .test_application import TestApp

class TestApplicationAssessment(SharedApplicationTestBase):
	child_ntiid =  b'tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.1'

	question_ntiid = child_ntiid

	@classmethod
	def _setup_library( cls, *args, **kwargs ):
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


	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_fetch_assessment_question_by_ntiid(self):
		unauth_testapp = TestApp( self.app )
		# These inherit the same ACLs as the content they came with
		# So, no authentication requires auth
		res = self.fetch_by_ntiid( self.question_ntiid, unauth_testapp, status=401, )

		# provide auth, we can get it.
		# It is the default return if we specify no content type
		res = self.fetch_by_ntiid( self.question_ntiid )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'Question' ) )


		# and if we specify plain json
		res = self.fetch_by_ntiid( self.question_ntiid,
								   headers={b'Accept': b'application/json'} )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'Question' ) )


	@WithSharedApplicationMockDS(testapp=True, users=True)
	def test_fetch_assessment_question_by_ntiid_accept_pageinfo(self):
		# If we fetch the URL of a question, but specify that we accept PageInfo,
		# that's what we get back
		page_info_mt = nti_mimetype_with_class( 'pageinfo' )
		page_info_mt_json = page_info_mt + '+json'

		res = self.fetch_by_ntiid( self.question_ntiid,
								   headers={b'Accept': str(page_info_mt_json)} )

		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Class', 'PageInfo' ) )

		# The content info we return points to an actual physical page
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entries( 'rel', 'content',
																			   'href', '/WithAssessment/tag_nextthought_com_2011-10_MN-HTML-MiladyCosmetology_introduction.html' ) ) ) )

	@WithSharedApplicationMockDS(testapp=True,users=True)
	def test_fetch_assessment_question_by_ntiid_accept_link(self):
		# Asking for a link isn't supported
		self.fetch_by_ntiid( self.question_ntiid,
							 headers={b'Accept': b'application/vnd.nextthought.link+json'},
							 status=400 )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_fetch_pageinfo_with_questions(self):
		for accept_type in (b'application/json',b'application/vnd.nextthought.pageinfo',b'application/vnd.nextthought.pageinfo+json'):
			__traceback_info__ = accept_type
			res = self.fetch_by_ntiid( 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0',
									   headers={b"Accept": accept_type} )
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

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_posting_assesses_mimetype_only(self):
		sub = asm_submission.QuestionSubmission( questionId=self.child_ntiid, parts=('correct',) )
		ext_obj = toExternalObject( sub )

		ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
		# Submit mimetype only, just to be sure it works
		ext_obj.pop( 'Class' )
		res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', ext_obj )
		self._check_submission( res )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_posting_assesses_class_only(self):
		sub = asm_submission.QuestionSubmission( questionId=self.child_ntiid, parts=('correct',) )
		ext_obj = toExternalObject( sub )

		ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'
		# Submit Class only, just to be sure it works
		ext_obj.pop( 'MimeType' )
		res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', ext_obj )
		self._check_submission( res )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_posting_multiple_choice(self):
		# The correct answer is at index 1, and has the value 'Steam distillation". We should be able to submit all
		# three forms
		for submittedResponse in ( 1, "1", "Steam distillation", ):
			sub = asm_submission.QuestionSubmission( questionId='tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.21', parts=(submittedResponse,) )
			ext_obj = toExternalObject( sub )
			ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'

			res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', ext_obj )
			self._check_submission( res )
			assert_that( res.json_body, has_entry( 'parts', has_item( has_entries( 'assessedValue', 1.0, 'submittedResponse', submittedResponse ) ) ) )

		# The correct answer is at index 3, and has the value '1000 BC". We should be able to submit all
		# three forms
		for submittedResponse in ( 3, "3", "1000 BC", ):
			sub = asm_submission.QuestionSubmission( questionId='tag:nextthought.com,2011-10:MN-NAQ-MiladyCosmetology.naq.10', parts=(submittedResponse,) )
			ext_obj = toExternalObject( sub )
			ext_obj['ContainerId'] = 'tag:nextthought.com,2011-10:mathcounts-HTML-MN.2012.0'

			res = self.testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', ext_obj )
			self._check_submission( res )
			assert_that( res.json_body, has_entry( 'parts', has_item( has_entries( 'assessedValue', 1.0, 'submittedResponse', submittedResponse ) ) ) )
