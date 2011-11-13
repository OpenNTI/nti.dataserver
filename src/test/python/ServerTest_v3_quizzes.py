import urllib
import urllib2
import sys
import os
import subprocess
import time
import unittest
import json
import plistlib
import cStringIO, StringIO
import re
import pdb
from datetime import datetime
from datetime import date
from logging import Logger
from wsgiref import handlers
from time import mktime
import ServerControl
import uuid
from servertests import DataServerTestCase

class URL_Default(ServerControl.URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
			self.responseCode = responseCode
	
	def setBody(self):
		try:
			self.body = self.parsedBody['Items']
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.body)
		except (KeyError, TypeError):
			self.body = self.parsedBody
	
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['Last Modified']
		except (KeyError, TypeError):
			self.lastModified = self.parsedBody
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess
	
class URL_QuizGroup(ServerControl.URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		self.parsedBody = parsedBody
		self.userObject = userObject
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		try:
			self.body = self.parsedBody['First_quiz']['Items']
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.body)
		except (KeyError, TypeError):
			self.body = self.parsedBody
	
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['Last Modified']
		except (KeyError, TypeError):
			self.lastModified = self.parsedBody
	
	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess
	
class URL_IDExtracter(ServerControl.URLFunctionality):
	
	def setParsedBody(self, parsedBody, userObject=None):
		if userObject == None:
			userObject = Set_ltesti_ID()
		self.parsedBody = parsedBody
		self.userObject = userObject
		self.setBody()
		self.setLastModified()
		self.setID()
	
	def setResponseCode(self, responseCode):
		self.responseCode = responseCode
	
	def setBody(self):
		ID = self.userObject.getID()
		try:
			self.body = self.parsedBody[ID]['Items']
			OIDRemove = OID_Remover()
			OIDRemove.removeOID(self.body)
		except (KeyError, TypeError):
			self.body = self.parsedBody
		
	def setLastModified(self):
		try:
			self.lastModified = self.parsedBody['Last Modified']
		except (KeyError, TypeError):
			self.lastModified = self.parsedBody

	def setID(self):
		try:
			self.id = self.parsedBody['ID']
		except (KeyError, TypeError):
			self.id = self.parsedBody
		
	def setIfModifiedSinceError(self, ifModifiedSinceError):
		self.ifModifiedSinceError = ifModifiedSinceError
		
	def setIfModifiedSinceSuccess(self, ifModifiedSinceSuccess):
		self.ifModifiedSinceSuccess = ifModifiedSinceSuccess

class OID_Remover(object):

	def removeOID(self, body):
		if isinstance(body, list):
			for index in body:
				if isinstance(index, dict or list):
					self.removeOID(index)
		elif isinstance(body, dict):
			keys = body.keys()
			for key in keys:
				if isinstance(body[key], dict or list):
					self.removeOID(body[key])
		try:		
			del body['OID']
		except (KeyError, TypeError):
			pass
		try:
			del body["Creator"]
		except (KeyError, TypeError):
			pass

class ServerTestCase_v3_quizzes_constants(object):

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

class Set_ltesti_ID(object):
	
	def setID(self, ID):
		Set_ltesti_ID.ID = ID
		
	def getID(self):
		return Set_ltesti_ID.ID

class Set_sjohnson_ID(object):
	
	def setID(self, ID):
		Set_sjohnson_ID.ID = ID
		
	def getID(self):
		return Set_sjohnson_ID.ID

class ServerTestCase(unittest.TestCase):

	def __init__(self, *args):
		unittest.TestCase.__init__(self, *args)
		self.longMessage = True
		self.maxDiff = 1
		Logger.propagate = False

	@classmethod
	def setUpClass(cls):
		Constants							 = ServerTestCase_v3_quizzes_constants()
		Constants.constants()
		ServerTestCase.URL					 = Constants.URL
		ServerTestCase.URL_post			     = Constants.URL_POST
		ServerTestCase.URL_NoFormat		     = Constants.URL_NO_FORMAT
		ServerTestCase.URL_MathXML           = Constants.URL_MATH_XML
		ServerTestCase.URL_json			     = Constants.URL_JSON
		ServerTestCase.URL_plist			 = Constants.URL_PLIST
		ServerTestCase.URL_resp_post		 = Constants.URL_RESP_POST
		ServerTestCase.URL_resp_NoFormat	 = Constants.URL_RESPONSE_NO_FORMAT
		ServerTestCase.URL_resp_MathXML      = Constants.URL_RESP_MATH_XML
		ServerTestCase.URL_resp_other		 = Constants.URL_RESP_OTHER
		ServerTestCase.default_questions	 = Constants.DEFAULT_QUESTIONS
		ServerTestCase.default_answer		 = Constants.DEFAULT_ANSWER
		ServerTestCase.put_questions		 = Constants.PUT_QUESTIONS
		ServerTestCase.put_answer			 = Constants.PUT_ANSWER
		ServerTestCase.put_questions_bad_ID  = Constants.PUT_QUESTION_BAD_ID
		ServerTestCase.openMathXMLQuestions  = Constants.OPEN_MATH_XML_QUESTION
		ServerTestCase.correct_answers		 = Constants.CORRECT_ANSWERS
		ServerTestCase.incorrect_answers	 = Constants.INCORRECT_ANSWERS
		ServerTestCase.NonExsist_answers	 = Constants.NON_EXSIST_ANSWERS
		ServerTestCase.OpenMathXMLAnswers    = Constants.OPEN_MATH_XML_ANSWERS
		ServerTestCase.skippedQuestion		 = Constants.SKIPPED_QUESTION
		ServerTestCase.correct_return		 = Constants.CORRECT_RETURN
		ServerTestCase.incorrect_return	     = Constants.INCORRECT_RETURN
		ServerTestCase.skipped_return		 = Constants.SKIPPED_RETURN
		ServerTestCase.mathXMLReturn         = Constants.MATH_XML_RETURN
		ServerTestCase.default_returnKey	 = Constants.DEFAULT_RETURN_KEY
		ServerTestCase.ID_returnKey		     = Constants.ID_RETURN_KEY
		ServerTestCase.First_quiz_key		 = Constants.FIRST_QUIZ_KEY
		ServerTestCase.LastModifiedKey		 = Constants.LAST_MODIFIED_KEY
		ServerTestCase.ItemsKey			     = Constants.ITEMS_KEY
		ServerTestCase.wrongInfo			 = Constants.WRONG_INFO
		ServerTestCase.highestOK			 = Constants.HIGHEST_OK
		
		default							     = ServerControl.DefaultValues()
		ServerTestCase.path				     = default.path
		ServerTestCase.username			     = default.username
		ServerTestCase.otherUser			 = default.otherUser
		ServerTestCase.password			     = default.password
		ServerTestCase.incorrectPassword	 = default.incorrectpassword
		ServerTestCase.TheVoid				 = default.void
		ServerTestCase.TinyNumber			 = default.TinyNumber
		ServerTestCase.LonelyNumber		     = default.LonelyNumber
		ServerTestCase.TheNumberTwo		     = default.TheNumberTwo
		ServerTestCase.TheNumberThree		 = default.TheNumberThree
		ServerTestCase.OK					 = default.OK
		ServerTestCase.SuccessfulAdd		 = default.SuccessfulAdd
		ServerTestCase.SuccessfulDelete	     = default.SuccessfulDelete
		ServerTestCase.NotModifiedSince	     = default.NotModifiedSince
		ServerTestCase.Unauthorized		     = default.Unauthorized
		ServerTestCase.Forbidden			 = default.Forbidden
		ServerTestCase.NotFound			     = default.NotFound
		ServerTestCase.NotAllowed			 = default.NotAllowed
		ServerTestCase.WrongType			 = default.WrongType
		
		ServerTestCase.ID_ltesti             = Set_ltesti_ID()
		ServerTestCase.ID_sjohnson           = Set_sjohnson_ID()
		ServerTestCase.tester				 = ServerControl.ServerController()
		ServerTestCase.resultTest			 = ServerControl.ServerController()
		ServerTestCase.json				     = ServerControl.JsonFormat()
		ServerTestCase.plist				 = ServerControl.PlistFormat()
		ServerTestCase.test				     = ServerControl.PostTest()
		
		DataServerTestCase.setUpClass()

	@classmethod
	def tearDownClass(cls):
#	   Stops the server
		DataServerTestCase.tearDownClass()
		
	def setUp(self):
		self.defaultSetterQuiz(ServerTestCase.tester)
		self.defaultSetterQuiz(ServerTestCase.resultTest)
		ServerTestCase.tester.setUpPut(ServerTestCase.URL_NoFormat)
		ServerTestCase.tester.setUpPut(ServerTestCase.URL_MathXML, ServerTestCase.openMathXMLQuestions)
		tester			  = ServerControl.ServerController()
		ServerTestCase.NoFormat_resp_ID = ServerTestCase.resultTest.setUpPost(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.correct_answers)
		ServerTestCase.NoFormat_resp_ID_old = ServerTestCase.NoFormat_resp_ID
		ServerTestCase.NoFormat_resp_ID = ServerTestCase.resultTest.setUpPost(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.correct_answers)
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID_old))
		ServerTestCase.Other_resp_ID = ServerTestCase.resultTest.setUpPost(ServerTestCase.URL_resp_other, dict=ServerTestCase.correct_answers, 
																		username=ServerTestCase.otherUser)
		ServerTestCase.URL_NoID   = ServerTestCase.tester.addID(ServerTestCase.URL_post, str(uuid.uuid4()))
		ServerTestCase.URL_resp_NoID = ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_post, str(uuid.uuid4()))
		ServerTestCase.ID_ltesti.setID(ServerTestCase.NoFormat_resp_ID)
		ServerTestCase.ID_sjohnson.setID(ServerTestCase.Other_resp_ID)
		ServerTestCase.URL_nonExsitsQuiz = ServerTestCase.tester.addID(ServerTestCase.URL, str(uuid.uuid4()))
#		print ServerTestCase.mathXMLReturn
										
	def tearDown(self):
		ServerTestCase.tester.tearDownDelete(ServerTestCase.URL_NoFormat)
		ServerTestCase.tester.tearDownDelete(ServerTestCase.URL_MathXML)
		ServerTestCase.tester.tearDownDelete(ServerTestCase.URL_NoID)
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_post, ServerTestCase.ID_ltesti.getID()))
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_post, ServerTestCase.ID_sjohnson.getID()))
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.tester.newID))
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_MathXML, ServerTestCase.tester.newID))
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_other, ServerTestCase.tester.newID), 
												username=ServerTestCase.otherUser)
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_MathXML, ServerTestCase.NoFormat_resp_ID))
		ServerTestCase.resultTest.tearDownDelete(ServerTestCase.resultTest.addID(ServerTestCase.URL_resp_other, ServerTestCase.Other_resp_ID), 
												username=ServerTestCase.otherUser)

#	   *************************
#	   *** Packaged Defaults ***
#	   *************************

	def defaultSetterQuiz(self, object):
		object.create(ServerTestCase.username, ServerTestCase.password, ServerTestCase.default_questions, ServerTestCase.ID_ltesti)
		
	def defaultSetterQuizResponse(self, object):
		object.create(ServerTestCase.username, ServerTestCase.password, ServerTestCase.correct_answers, ServerTestCase.ID_ltesti)

#	   *************
#	   * Get tests *
#	   *************

	def test_Server200DefaultGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		tester.getTest(ServerTestCase.URL_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_NoFormat)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.default_answer, lastModified=modifiedTime, 
						ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to read")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '1'

	def test_Server200DefaultGetGroupTestCase(self):
		bodyDataExtracter = URL_QuizGroup()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		tester.getTest(ServerTestCase.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.default_answer, lastModified=modifiedTime, 
						ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to read")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '2'

	def test_Server200JsonFormatGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		tester.getTest(ServerTestCase.URL_json, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_json)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.default_answer, lastModified=modifiedTime, 
						ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to read")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		#print '3'	  

	def test_Server200PlistFormatGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		tester.getTest(ServerTestCase.URL_plist, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_NoFormat)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.default_answer, lastModified=modifiedTime, 
						ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL to read")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		#print '4'

	def test_Server401IncorrectPasswordGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		tester.getTest(ServerTestCase.URL_NoFormat, password=ServerTestCase.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_NoFormat)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.TheVoid, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized to read')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		#print '5'

	def test_Server404NonExsistantQuizGetTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		tester.getTest(ServerTestCase.URL_NoID, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_NoID)
		expectedValues.setValues(code=ServerTestCase.NotFound, body=ServerTestCase.TheVoid, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		#print '6'

#		**************
#		* Post Tests *
#		**************

	def test_Server405DefaultPostTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.NotAllowed)
		tester.postTest(ServerTestCase.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not allowed')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'Modification time changed')
		#print '7'

	def test_Server405JsonFormatPostTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.NotAllowed)
		tester.postTest(ServerTestCase.URL_post, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not allowed')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'Modification time changed')
		#print '8'
		
	def test_Server405PlistFormatPostTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.NotAllowed)
		tester.postTest(ServerTestCase.URL_post, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not allowed')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'Modification time changed')
		#print '9'

#		*************
#		* Put Tests *
#		*************

	def test_Server200DefaultPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		  = tester.getBody(ServerTestCase.URL_post)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_json, dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID    = tester.getLastModified(ServerTestCase.URL_json)
		modifiedTime      = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime expected to be greater that modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		#print '10'

	def test_Server200JsonFormatPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.json)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_json, dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_json)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		#print '11'
		
	def test_Server200BadIDPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		  = tester.getBody(ServerTestCase.URL_post)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_json, dict=ServerTestCase.put_questions_bad_ID, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID    = tester.getLastModified(ServerTestCase.URL_json)
		modifiedTime   = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		#print '12'

	def test_Server401JsonFormatIncorrectPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_json)
		oldGroup		  = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.json)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_json, dict=ServerTestCase.put_questions, password=ServerTestCase.incorrectPassword, 
					bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID    = tester.getLastModified(ServerTestCase.URL_json)
		modifiedTime   = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.default_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '13'

	def test_Server201JsonFormatNonExsistantIDPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.json)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_NoID, dict=ServerTestCase.put_questions, 
							bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_NoID)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime expected to be greater that modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		#print '14'

	def test_Server500JsonFormatWrongDatatypePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_json)
		oldGroup		 = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.json)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_json, dict=ServerTestCase.wrongInfo, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_json)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.WrongType, body=ServerTestCase.default_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Supposed to be bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '15'

	def test_Server200PlistFormatPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.plist)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_plist, dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_NoFormat)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		#print '16'

	def test_Server401PlistFormatIncorrectPasswordPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_NoFormat)
		oldGroup		  = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.plist)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_plist, dict=ServerTestCase.put_questions, password=ServerTestCase.incorrectPassword, 
					bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID    = tester.getLastModified(ServerTestCase.URL_NoFormat)
		modifiedTime   = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.default_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized')
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '17'

	def test_Server201PlistFormatNonExsistantIDPutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.plist)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_NoID, dict=ServerTestCase.put_questions, 
							bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_NoID)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.put_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime expected to be greater that modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		self.assertNotEqual(oldGroup, bodyDataExtracter.body, 'not supposed to be equal')
		#print '18'

	def test_Server500PlistFormatWrongDatatypePutTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuiz(tester)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_NoFormat)
		oldGroup		 = tester.getBody(ServerTestCase.URL_post, format=ServerTestCase.plist)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_post)
		tester.putTest(ServerTestCase.URL_plist, dict=ServerTestCase.wrongInfo, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_NoFormat)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.WrongType, body=ServerTestCase.default_answer)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Supposed to be bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, modifiedTimeID, 'Expected to be Equal')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '19'

#		****************
#		* Delete Tests *
#		****************

	def test_Server204DefaultDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulDelete, body=ServerTestCase.NotFound)
		tester.deleteTest(ServerTestCase.URL_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		#print '20'

	def test_Server405DeleteGroupTestCase(self):
		bodyDataExtracter = URL_QuizGroup()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.default_answer)
		tester.deleteTest(ServerTestCase.URL_post, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '21'

	def test_Server204JsonFormatDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulDelete, body=ServerTestCase.NotFound)
		tester.deleteTest(ServerTestCase.URL_NoFormat, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		#print '22'

	def test_Server204PlistFormatDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulDelete, body=ServerTestCase.NotFound)
		tester.deleteTest(ServerTestCase.URL_NoFormat, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		#print '23'

	def test_Server401IncorrectPasswordDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.Unauthorized)
		tester.deleteTest(ServerTestCase.URL_NoFormat, password=ServerTestCase.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '24'

	def test_Server404NonExsistantIDDeleteTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.NotFound, body=ServerTestCase.NotFound, lastModified=ServerTestCase.NotFound)
		tester.deleteTest(ServerTestCase.URL_NoID, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body, 'Body is supposed to exist as this')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '25'

#		**************************
#		*** Quiz Results Tests ***
#		**************************

#		************
#		* Get Test *
#		************

	def test_Server200DefaultGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '26'
		
	def test_Server200DefaultGetResponseGroupTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(ServerTestCase.URL_resp_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceError, expectedValues.ifModifiedSinceError, 'If-Modified_Since result supposed to be 304')
		self.assertEqual(bodyDataExtracter.ifModifiedSinceSuccess, expectedValues.ifModifiedSinceSuccess, 'If-Modified_Since result supposed to be 200')
		#print '27'
		
	def test_Server200JsonFormatGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), bodyDataExtracter=bodyDataExtracter,
								format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		#print '28'
		
	def test_Server200PlistFormatGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), bodyDataExtracter=bodyDataExtracter,
								format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		#print '29'
		
	def test_Server200OtherGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(ServerTestCase.URL_resp_other, ServerTestCase.Other_resp_ID), bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_other, ServerTestCase.Other_resp_ID))
		expectedValues.setValues(code=ServerTestCase.OK, body=ServerTestCase.correct_return, lastModified=modifiedTime, 
								ifModifiedSinceError=ServerTestCase.NotModifiedSince, ifModifiedSinceSuccess=ServerTestCase.OK)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		#print '30'
		
	def test_Server401IncorrectPasswordGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
								password=ServerTestCase.incorrectPassword, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		expectedValues.setValues(code=ServerTestCase.Unauthorized, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'User supposed to be Unauthorized')
		self.assertEqual(bodyDataExtracter.lastModified, expectedValues.lastModified, 'Expected to be Equal')
		#print '31'

	def test_Server404NonExsistantIDGetResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		tester.getTest(ServerTestCase.URL_resp_NoID, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_NoID)
		expectedValues.setValues(code=ServerTestCase.NotFound, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, 'URL supposed to be Not Found')
		#print '32'
		
#		*************
#		* Post Test *
#		*************

	def test_Server201DefaultCorrectAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
#		print oldGroup
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.correct_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		try:
			self.assertRaises(KeyError, ServerTestCase.test.postException, oldGroup, bodyDataExtracter.id)
		except TypeError:
			 self.fail(str(oldGroup) + ' does not have a key value so that a value can be found in class ServerControl.PostTest')
		#print '33'
		
	def test_Server201DefaultIncorrectAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.incorrect_answers, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.incorrect_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTimeOld unexpectedly greater than modifiedTime')
		try:
			self.assertRaises(KeyError, ServerTestCase.test.postException, oldGroup, bodyDataExtracter.id)
		except TypeError:
			 self.fail(str(oldGroup) + ' does not have a key value so that a value can be found in class ServerControl.PostTest')
		#print '34'
		
	def test_Server201IncrementingIDPostResponseTestCase(self):
		self.assertEqual(str(int(ServerTestCase.NoFormat_resp_ID_old) + ServerTestCase.LonelyNumber), ServerTestCase.NoFormat_resp_ID, 'The ID didnt increase by one')
		#print '35'
		
	def test_Server201DefaultOpenMathXMLAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_MathXML)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_MathXML)
		tester.postTest(ServerTestCase.URL_resp_MathXML, dict=ServerTestCase.OpenMathXMLAnswers, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_MathXML, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_MathXML)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.mathXMLReturn)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '36'
		
	def test_Server201JsonFormatCorrectAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.correct_return)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '37'
		
	def test_Server201JsonFormatIncorrectAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.incorrect_answers, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat,)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.incorrect_return)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '38'
		
	def test_Server201JsonFormatSkippedQuestionPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.skippedQuestion, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.skipped_return)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '39'
		
	def test_Server500JsonFormatNonExsistKeyPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.WrongType, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.NonExsist_answers, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "The problem wasnt with the missing key")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '40'
		
	def test_Server401JsonFormatIncorrectPasswordPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, password=ServerTestCase.incorrectPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do a bad password")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '41'
		
	def test_Server403JsonFormatOtherUserPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.Forbidden, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_other, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json, userObject=Set_sjohnson_ID())
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '42'
		
	def test_Server404JsonFormatNonExsistantIDPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		tester.postTest(ServerTestCase.URL_nonExsitsQuiz, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.NotFound, body=ServerTestCase.NotFound)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to non-exsistant quiz")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '43'
		
	def test_Server500JsonFormatWrongInfoPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.WrongType, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.wrongInfo, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '44'
		
	def test_Server201PlistFormatCorrectAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.correct_return)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '45'
		
	def test_Server201PlistFormatIncorrectAnswersPostResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.incorrect_answers, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat, ID=bodyDataExtracter.id)
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.SuccessfulAdd, body=ServerTestCase.incorrect_return, lastModified=modifiedTimeID)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreaterEqual(modifiedTime, modifiedTimeID, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		self.assertLess(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '46'
		
	def test_Server401PlistFormatIncorrectPasswordPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, password=ServerTestCase.incorrectPassword, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do a bad password")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '47'
		
	def test_Server403PlistFormatOtherUserPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.Forbidden, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_other, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist, userObject=Set_sjohnson_ID())
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to wrong user")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '48'
		
	def test_Server404PlistFormatNonExsistantQuizPostResponseTestCase(self): 
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		tester.postTest(ServerTestCase.URL_nonExsitsQuiz, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.NotFound, body=ServerTestCase.NotFound)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do to non-exsistant quiz")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '49'
		
	def test_Server500PlistFormatWrongInfoPostResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		expectedValues.setValues(code=ServerTestCase.WrongType, body=ServerTestCase.correct_return)
		tester.postTest(ServerTestCase.URL_resp_NoFormat, dict=ServerTestCase.wrongInfo, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_resp_post)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "supposed to not allow access do bad info")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '50'
		
#		*************
#		* Put Tests *
#		*************

	def test_Server405DefaultPutResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.putTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
							dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter)
		modifiedTimeID   = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.correct_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertGreaterEqual(modifiedTime, modifiedTimeID)
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '51'

	def test_Server405JsonFormatPutResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.putTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
								dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID   = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.correct_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertGreaterEqual(modifiedTime, modifiedTimeID)
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '52'
 
	def test_Server405JsonFormatIncorrectPasswordPutResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTime	  = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		oldGroup		  = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.putTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
					dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTimeID    = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		modifiedTime   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.correct_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertGreaterEqual(modifiedTime, modifiedTimeID)
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '53'
		
	def test_Server405PlistFormatPutResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		oldGroup		 = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.putTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
								dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID   = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		modifiedTime  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.correct_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertGreaterEqual(modifiedTime, modifiedTimeID)
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '54'
 
	def test_Server405PlistFormatIncorrectPasswordPutResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTime	  = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		oldGroup		  = tester.getBody(ServerTestCase.URL_resp_NoFormat)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		tester.putTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
					dict=ServerTestCase.put_questions, bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTimeID    = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID))
		modifiedTime   = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.correct_return, lastModified=modifiedTime)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertGreaterEqual(modifiedTime, modifiedTimeID)
		self.assertEqual(modifiedTimeOld, modifiedTime, 'modifiedTime unexpectedly not greater than modifiedTimeID')
		#print '55'
		
#		****************
#		* Delete Tests *
#		****************
		
	def test_Server204DefaultDeleteResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_json)
		tester.deleteTest(tester.addID(ServerTestCase.URL_json, ServerTestCase.NoFormat_resp_ID), bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulDelete, body=ServerTestCase.NotFound)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '56'
		
	def test_Server405DeleteGroupResponseTestCase(self):
		bodyDataExtracter = URL_IDExtracter()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.NotAllowed, body=ServerTestCase.correct_return, lastModified=modifiedTimeOld)
		tester.deleteTest(ServerTestCase.URL_resp_NoFormat, bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '57'
		
	def test_Server204JsonFormatDeleteResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_json)
		tester.deleteTest(tester.addID(ServerTestCase.URL_json, ServerTestCase.NoFormat_resp_ID), 
						bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.json)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulDelete, body=ServerTestCase.NotFound)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '58'
		
	def test_Server204PlistFormatDeleteResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	 = tester.getLastModified(ServerTestCase.URL_json)
		tester.deleteTest(tester.addID(ServerTestCase.URL_json, ServerTestCase.NoFormat_resp_ID), 
						bodyDataExtracter=bodyDataExtracter, format=ServerTestCase.plist)
		modifiedTime	 = tester.getLastModified(ServerTestCase.URL_post)
		expectedValues.setValues(code=ServerTestCase.SuccessfulDelete, body=ServerTestCase.NotFound)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertGreater(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '59'
		
	def test_Server401OtherDeleteResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.correct_return, lastModified=modifiedTimeOld)
		tester.deleteTest(tester.addID(ServerTestCase.URL_resp_other, ServerTestCase.Other_resp_ID), 
						password=ServerTestCase.incorrectPassword,bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '60'
		
	def test_Server401IncorrectPasswordDeleteResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		expectedValues.setValues(code=ServerTestCase.Unauthorized, body=ServerTestCase.correct_return, lastModified=modifiedTimeOld)
		tester.deleteTest(tester.addID(ServerTestCase.URL_resp_NoFormat, ServerTestCase.NoFormat_resp_ID), 
								password=ServerTestCase.incorrectPassword,bodyDataExtracter=bodyDataExtracter)
		modifiedTime	  = tester.getLastModified(ServerTestCase.URL_resp_NoFormat)
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(bodyDataExtracter.body, expectedValues.body,'Body is supposed to exist as this')
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '61'

	def test_Server404NonExsistantIDDeleteResponseTestCase(self):
		bodyDataExtracter = URL_Default()
		tester			  = ServerControl.ServerController()
		expectedValues    = ServerControl.URLFunctionality()
		self.defaultSetterQuizResponse(tester)
		modifiedTimeOld	  = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoID, ServerTestCase.NoFormat_resp_ID))
		expectedValues.setValues(code=ServerTestCase.NotFound, body=ServerTestCase.NotFound, lastModified=ServerTestCase.NotFound)
		tester.deleteTest(tester.addID(ServerTestCase.URL_resp_NoID, ServerTestCase.NoFormat_resp_ID), bodyDataExtracter=bodyDataExtracter)
		modifiedTime	 = tester.getLastModified(tester.addID(ServerTestCase.URL_resp_NoID, ServerTestCase.NoFormat_resp_ID))
		self.assertEqual(bodyDataExtracter.responseCode, expectedValues.responseCode, "Didn't open URL")
		self.assertEqual(modifiedTime, modifiedTimeOld, 'Wrong modification time')
		#print '62'

def testAll():
	return testQuizTest() + testResponseTest()

def testQuizTest():
	return testGetTest() + testPostTest() + testPutTest() + testDeleteTest()

def testGetTest():
	return testStandardGetTest() + testVariableGetTest()
		
def testDefaultGetTest():
	return ['test_Server200DefaultGetTestCase']

def testStandardGetTest():
	return ['test_Server200DefaultGetTestCase',  'test_Server200DefaultGetGroupTestCase', 'test_Server200JsonFormatGetTestCase', 'test_Server200PlistFormatGetTestCase']

def testVariableGetTest():
	return ['test_Server401IncorrectPasswordGetTestCase', 'test_Server404NonExsistantQuizGetTestCase']

def testDefaultPostTest():
	return ['test_Server405DefaultPostTestCase']
	
def testPostTest():
	return ['test_Server405DefaultPostTestCase', 'test_Server405JsonFormatPostTestCase', 'test_Server405PlistFormatPostTestCase']

def testPutTest():
	return testJsonPutTest() + testPlistPutTest()

def testJsonPutTest():
	return testJsonStandardPutTest() + testJsonVariablePutTest()
			
def testPlistPutTest():
	return testPlistStandardPutTest() + testPlistVariablePutTest()

def testDefaultPutTest():
	return ['test_Server200DefaultPutTestCase']
	
def testJsonStandardPutTest():
	return ['test_Server200DefaultPutTestCase', 'test_Server200JsonFormatPutTestCase', 'test_Server200BadIDPutTestCase']

def testJsonVariablePutTest():
	return ['test_Server401JsonFormatIncorrectPasswordPutTestCase', 'test_Server201JsonFormatNonExsistantIDPutTestCase', 'test_Server500JsonFormatWrongDatatypePutTestCase']
	
def testPlistStandardPutTest():
	return ['test_Server200PlistFormatPutTestCase']

def testPlistVariablePutTest():
	return ['test_Server401PlistFormatIncorrectPasswordPutTestCase', 'test_Server201PlistFormatNonExsistantIDPutTestCase', 
			'test_Server500PlistFormatWrongDatatypePutTestCase']

def testDeleteTest():
	return testDefaultDeleteTest() + testJsonDeleteTest() + testPlistDeleteTest()

def testJsonDeleteTest():
	return testJsonStandardDeleteTest()

def testPlistDeleteTest():
	return testPlistStandardDeleteTest() + testPlistVariableDeleteTest()
	
def testDefaultDeleteTest():
	return ['test_Server204DefaultDeleteTestCase']
	
def testJsonStandardDeleteTest():
	return ['test_Server405DeleteGroupTestCase', 'test_Server204JsonFormatDeleteTestCase']

def testPlistStandardDeleteTest():
	return ['test_Server204PlistFormatDeleteTestCase']

def testPlistVariableDeleteTest():
	return ['test_Server401IncorrectPasswordDeleteTestCase', 'test_Server404NonExsistantIDDeleteTestCase']

def testResponseTest():
	return testGetResponseTest() + testPostResponseTest() + testPutResponseTest() + testDeleteResponseTest()

def testGetResponseTest():
	return testStandardGetResponseTest() + testVariableGetResponseTest()

def testStandardGetResponseTest():
	return ['test_Server200DefaultGetResponseTestCase', 'test_Server200DefaultGetResponseGroupTestCase', 
			'test_Server200JsonFormatGetResponseTestCase', 'test_Server200PlistFormatGetResponseTestCase',
			'test_Server200OtherGetResponseTestCase']
	
def testVariableGetResponseTest():
	return ['test_Server401IncorrectPasswordGetResponseTestCase', 'test_Server404NonExsistantIDGetResponseTestCase']

def testPostResponseTest():
	return testJsonPostResponseTest() + testPlistPostResponseTest()
	
def testJsonPostResponseTest():
	return testStandardJsonPostResponseTest() + testVariableJsonPostResponseTest()
	
def testStandardJsonPostResponseTest():
	return ['test_Server201DefaultCorrectAnswersPostResponseTestCase', 'test_Server201DefaultIncorrectAnswersPostResponseTestCase',
			'test_Server201IncrementingIDPostResponseTestCase', 'test_Server201DefaultOpenMathXMLAnswersPostResponseTestCase',
			'test_Server201JsonFormatCorrectAnswersPostResponseTestCase', 'test_Server201JsonFormatIncorrectAnswersPostResponseTestCase',
		  	'test_Server201JsonFormatSkippedQuestionPostResponseTestCase', 'test_Server500JsonFormatNonExsistKeyPostResponseTestCase']
	
def testVariableJsonPostResponseTest():
	return ['test_Server401JsonFormatIncorrectPasswordPostResponseTestCase', 'test_Server403JsonFormatOtherUserPostResponseTestCase', 
			'test_Server404JsonFormatNonExsistantIDPostResponseTestCase', 'test_Server500JsonFormatWrongInfoPostResponseTestCase']
	
def testPlistPostResponseTest():
	return testPlistStandardPostResponseTest() + testPlistVariablePostResponseTest()
	
def testPlistStandardPostResponseTest():
	return ['test_Server201PlistFormatCorrectAnswersPostResponseTestCase', 'test_Server201PlistFormatIncorrectAnswersPostResponseTestCase']
	
def testPlistVariablePostResponseTest():
	return ['test_Server401PlistFormatIncorrectPasswordPostResponseTestCase', 'test_Server403PlistFormatOtherUserPostResponseTestCase', 
			'test_Server404PlistFormatNonExsistantQuizPostResponseTestCase', 'test_Server500PlistFormatWrongInfoPostResponseTestCase']
	
def testPutResponseTest():
	return testStandardPutResponseTest() + testVariablePutResponseTest()
	
def testStandardPutResponseTest():
	return ['test_Server405DefaultPutResponseTestCase', 'test_Server405JsonFormatPutResponseTestCase']
	
def testVariablePutResponseTest():
	return ['test_Server405JsonFormatIncorrectPasswordPutResponseTestCase', 'test_Server405PlistFormatPutResponseTestCase', 
			'test_Server405PlistFormatIncorrectPasswordPutResponseTestCase']

def testDeleteResponseTest():
	return testStandardDeleteResponseTest() + testVariableDeleteResponseTest()

def testStandardDeleteResponseTest():
	return ['test_Server204DefaultDeleteResponseTestCase', 'test_Server405DeleteGroupResponseTestCase', 
		'test_Server204JsonFormatDeleteResponseTestCase', 'test_Server204PlistFormatDeleteResponseTestCase']

def testVariableDeleteResponseTest():
	return ['test_Server401OtherDeleteResponseTestCase', 'test_Server401IncorrectPasswordDeleteResponseTestCase', 'test_Server404NonExsistantIDDeleteResponseTestCase']
	
#	fix this test: 'test_Server405PlistFormatNonExsistantQuizPostResponseTestCase'
	
if __name__ == '__main__':
	which_shell_to_run = ['test_Server200PlistFormatGetTestCase']
	unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(map(ServerTestCase, which_shell_to_run)))
	
