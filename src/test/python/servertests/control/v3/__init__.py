import time
import uuid

from servertests.control import NoFormat
from servertests.control import PostTest
from servertests.control import JsonFormat
from servertests.control import UserObject
from servertests.control import PlistFormat
from servertests.control import DefaultValues
from servertests.control import ServerController

from servertests import DataServerTestCase

##########################

class V3Constants(object):

	def constants(self):
		self.URL					= 'http://localhost:8080/dataserver'
		self.URL_POST			    = 'http://localhost:8080/dataserver/quizzes'
		self.URL_NO_FORMAT		    = 'http://localhost:8080/dataserver/quizzes/First_quiz'
		self.URL_MATH_XML           = 'http://localhost:8080/dataserver/quizzes/XML'
		self.URL_JSON			    = 'http://localhost:8080/dataserver/quizzes/First_quiz?format=json'
		self.URL_PLIST			    = 'http://localhost:8080/dataserver/quizzes/First_quiz?format=plist'
		self.URL_RESP_POST		    = 'http://localhost:8080/dataserver/users/ltesti/quizresults/First_quiz'
		self.URL_RESPONSE_NO_FORMAT = 'http://localhost:8080/dataserver/users/ltesti/quizresults/First_quiz'
		self.URL_RESP_MATH_XML      = 'http://localhost:8080/dataserver/users/ltesti/quizresults/XML'
		self.URL_RESP_OTHER		    = 'http://localhost:8080/dataserver/users/sjohnson/quizresults/First_quiz'
		self.DEFAULT_QUESTIONS	    = {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(Default\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "Answers": ["\(Question\)", "\(question\)"], 'Class':'QuizQuestion'} } }
		self.DEFAULT_ANSWER		    = { "1" : {"Text": "Question 1", "ID":"1", "Answers": ["\(Default\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "ID": "2", "Answers": ["\(Question\)", "\(question\)"], 'Class':'QuizQuestion'} }
		self.PUT_QUESTIONS		    = {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(red\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "Answers": ["\(10\)", "\(10.0\)"], 'Class':'QuizQuestion'} } }
		self.PUT_QUESTION_BAD_ID    = {"Items": { "1" : {"Text": "Question 1", 'ID' : '3', "Answers": ["\(red\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", 'ID' : '19992', "Answers": ["\(10\)", "\(10.0\)"], 'Class':'QuizQuestion'} } }
		self.OPEN_MATH_XML_QUESTION	= {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(x + 10\)"], 'Class':'QuizQuestion'}}}
		self.PUT_ANSWER			    = { "1" : {"Text": "Question 1", "ID":"1", "Answers": ["\(red\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "ID": "2", "Answers": ["\(10\)", "\(10.0\)"], 'Class':'QuizQuestion'} }
		self.CORRECT_ANSWERS	    = {'1': 'Default', '2': 'Question'}
		self.INCORRECT_ANSWERS	    = {'1': 'postPut', '2': '11'}
		self.NON_EXSIST_ANSWERS	    = {'1': 'Default', '3': 'Question'}
		self.OPEN_MATH_XML_ANSWERS  = {'1': '<OMOBJ xmlns="http://www.openmath.org/OpenMath" version="2.0" cdbase="http://www.openmath.org/cd"><OMA><OMS ' + \
										'cd="arith1" name="plus"/><OMV name="x"/><OMI>10</OMI></OMA></OMOBJ>'}
		self.SKIPPED_QUESTION	    = {'1': 'Default'}
		self.CORRECT_RETURN		    = [{'Question': {'Text': 'Question 1', 'ID': '1', 'Answers': ['\\(Default\\)'], 'Class': 'QuizQuestion'}, 'Assessment': True, 
										'Response': 'Default', 'Class': 'QuizQuestionResponse'}, {'Question': {'Text': 'Question 2', 'ID': '2', 
										'Answers': ['\\(Question\\)', '\\(question\\)'], 'Class': 'QuizQuestion'}, 'Assessment': True, 'Response': 'Question', 
																									'Class': 'QuizQuestionResponse'}]
		self.INCORRECT_RETURN	    = [{'Question': {'Text': 'Question 1', 'ID': '1', 'Answers': ['\\(Default\\)'], 'Class': 'QuizQuestion'}, 'Assessment': False, 
										'Response': 'postPut', 'Class': 'QuizQuestionResponse'}, {'Question': {'Text': 'Question 2', 'ID': '2', 
										'Answers': ['\\(Question\\)', '\\(question\\)'], 'Class': 'QuizQuestion'}, 'Assessment': False, 'Response': '11', 
										'Class': 'QuizQuestionResponse'}]
		self.SKIPPED_RETURN		    = [{'Question': {'Text': 'Question 1', 'ID': '1', 'Answers': ['\\(Default\\)'], 'Class': 'QuizQuestion'}, 'Assessment': True, 
										'Response': 'Default', 'Class': 'QuizQuestionResponse'}]
		self.MATH_XML_RETURN        = [{'Question': {'Text': 'Question 1', 'ID': '1', 'Answers': ['\\(x + 10\\)'], 'Class': 'QuizQuestion'}, 'Assessment': True, 
									'Response': '<OMOBJ xmlns="http://www.openmath.org/OpenMath" version="2.0" cdbase="http://www.openmath.org/cd"><OMA><OMS ' + \
									'cd="arith1" name="plus"/><OMV name="x"/><OMI>10</OMI></OMA></OMOBJ>', 'Class': 'QuizQuestionResponse'}]

		self.DEFAULT_RETURN_KEY	    = 'Items'
		self.ID_RETURN_KEY		    = ('Items', 'Items')
		self.FIRST_QUIZ_KEY		    = ('First_quiz', 'Items')
		self.LAST_MODIFIED_KEY	    = 'Last Modified'
		self.ITEMS_KEY			    = 'Items'
		self.WRONG_INFO			    = 10
		self.HIGHEST_OK             = 300

class V3TestCase(DataServerTestCase):

	@classmethod
	def setUpClass(cls):
		constants					= V3Constants()
		constants.constants()
		
		cls.URL					 	= constants.URL
		cls.URL_post			    = constants.URL_POST
		cls.URL_NoFormat		    = constants.URL_NO_FORMAT
		cls.URL_MathXML           	= constants.URL_MATH_XML
		cls.URL_json			    = constants.URL_JSON
		cls.URL_plist			 	= constants.URL_PLIST
		cls.URL_resp_post		 	= constants.URL_RESP_POST
		cls.URL_resp_NoFormat	 	= constants.URL_RESPONSE_NO_FORMAT
		cls.URL_resp_MathXML      	= constants.URL_RESP_MATH_XML
		cls.URL_resp_other		 	= constants.URL_RESP_OTHER
		cls.default_questions	 	= constants.DEFAULT_QUESTIONS
		cls.default_answer		 	= constants.DEFAULT_ANSWER
		cls.put_questions		 	= constants.PUT_QUESTIONS
		cls.put_answer			 	= constants.PUT_ANSWER
		cls.put_questions_bad_ID  	= constants.PUT_QUESTION_BAD_ID
		cls.openMathXMLQuestions  	= constants.OPEN_MATH_XML_QUESTION
		cls.correct_answers		 	= constants.CORRECT_ANSWERS
		cls.incorrect_answers	 	= constants.INCORRECT_ANSWERS
		cls.NonExsist_answers	 	= constants.NON_EXSIST_ANSWERS
		cls.OpenMathXMLAnswers    	= constants.OPEN_MATH_XML_ANSWERS
		cls.skippedQuestion		 	= constants.SKIPPED_QUESTION
		cls.correct_return		 	= constants.CORRECT_RETURN
		cls.incorrect_return	    = constants.INCORRECT_RETURN
		cls.skipped_return		 	= constants.SKIPPED_RETURN
		cls.mathXMLReturn         	= constants.MATH_XML_RETURN
		cls.default_returnKey	 	= constants.DEFAULT_RETURN_KEY
		cls.ID_returnKey		    = constants.ID_RETURN_KEY
		cls.First_quiz_key		 	= constants.FIRST_QUIZ_KEY
		cls.LastModifiedKey		 	= constants.LAST_MODIFIED_KEY
		cls.ItemsKey			    = constants.ITEMS_KEY
		cls.wrongInfo			 	= constants.WRONG_INFO
		cls.highestOK			 	= constants.HIGHEST_OK
		
		default						= DefaultValues()
		cls.path				    = default.path
		cls.username			    = default.username
		cls.otherUser			 	= default.otherUser
		cls.password			    = default.password
		cls.incorrectPassword	 	= default.incorrectpassword
		cls.TheVoid				 	= default.void
		cls.TinyNumber			 	= default.TinyNumber
		cls.LonelyNumber		    = default.LonelyNumber
		cls.TheNumberTwo		    = default.TheNumberTwo
		cls.TheNumberThree		 	= default.TheNumberThree
		cls.OK					 	= default.OK
		cls.SuccessfulAdd		 	= default.SuccessfulAdd
		cls.SuccessfulDelete	    = default.SuccessfulDelete
		cls.NotModifiedSince	    = default.NotModifiedSince
		cls.Unauthorized		    = default.Unauthorized
		cls.Forbidden			 	= default.Forbidden
		cls.NotFound			    = default.NotFound
		cls.NotAllowed			 	= default.NotAllowed
		cls.WrongType			 	= default.WrongType
		
		cls.UserObject             	= UserObject()
		cls.json				    = JsonFormat()
		cls.plist				 	= PlistFormat()
		cls.test				    = PostTest()
		
		DataServerTestCase.setUpClass()

	@classmethod
	def tearDownClass(cls):
		DataServerTestCase.tearDownClass()
		
	def setUp(self):
		super(V3TestCase, self).setUp()
		self.LIST_NAME='TestFriendsList-%s@nextthought.com' % time.time()
		
		# a set of puts and deletes that are set before each test
		quiz = self.controller_quiz()
		response = self.controller_response()
		
		quiz.setUpPut(self.URL_NoFormat)
		quiz.setUpPut(self.URL_MathXML, self.openMathXMLQuestions)
		
		self.NoFormat_resp_ID = response.setUpPost(self.URL_resp_NoFormat, data=self.correct_answers)
		self.NoFormat_resp_ID_old = self.NoFormat_resp_ID
		self.NoFormat_resp_ID = response.setUpPost(self.URL_resp_NoFormat, data=self.correct_answers)
		
		response.tearDownDelete(response.addID(self.URL_resp_NoFormat, self.NoFormat_resp_ID_old))
		
		self.Other_resp_ID = response.setUpPost(self.URL_resp_other, data=self.correct_answers, username=self.otherUser)
		self.URL_NoID   = quiz.addID(self.URL_post, str(uuid.uuid4()))
		self.URL_resp_NoID = response.addID(self.URL_resp_post, str(uuid.uuid4()))
		self.UserObject.setUserID(self.NoFormat_resp_ID)
		self.UserObject.setOtherUserID(self.Other_resp_ID)
		self.URL_nonExsitsQuiz = quiz.addID(self.URL, str(uuid.uuid4()))
										
	def tearDown(self):
		quiz = self.controller_quiz()
		response = self.controller_response()
		
		quiz.tearDownDelete(self.URL_NoFormat)
		quiz.tearDownDelete(self.URL_MathXML)
		quiz.tearDownDelete(self.URL_NoID)
		
		response.tearDownDelete(response.addID(self.URL_post, self.UserObject.getUserID()))
		response.tearDownDelete(response.addID(self.URL_post, self.UserObject.getOtherUserID()))
		response.tearDownDelete(response.addID(self.URL_resp_NoFormat, quiz.newID))
		response.tearDownDelete(response.addID(self.URL_resp_MathXML, quiz.newID))
		response.tearDownDelete(response.addID(self.URL_resp_other, quiz.newID), username=self.otherUser)
		response.tearDownDelete(response.addID(self.URL_resp_NoFormat, self.NoFormat_resp_ID))
		response.tearDownDelete(response.addID(self.URL_resp_MathXML, self.NoFormat_resp_ID))
		response.tearDownDelete(response.addID(self.URL_resp_other, self.Other_resp_ID), username=self.otherUser)
		
	#********************
	#*** Set Defaults ***
	#********************
		
	def controller_quiz(self):
		tester = ServerController()
		self.defaultSetterQuiz(tester)
		return tester
	
	def controller_response(self):
		tester = ServerController()
		self.defaultSetterQuizResponse(tester)
		return tester
	
	def defaultSetterQuiz(self, obj):
		obj.create(self.username, self.password, self.default_questions, self.UserObject)
		
	def defaultSetterQuizResponse(self, obj):
		obj.create(self.username, self.password, self.correct_answers, self.UserObject)
