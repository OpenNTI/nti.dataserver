'''
Created on Oct 4, 2011

@author: ltesti
'''

class TestConstants(object):

	def __init__(self, *args, **kwargs):
		self.username             = 'ltesti'
		self.otherUser            = 'sjohnson'
		self.password             = 'temp001'
		self.incorrectpassword    = 'incorrect'
		self.message              = None
		self.void                 = None
		self.TinyNumber           = 0
		self.LonelyNumber         = 1
		self.TheNumberTwo         = 2
		self.TheNumberThree       = 3
		self.OK                   = 200
		self.SuccessfulAdd        = 201
		self.SuccessfulDelete     = 204
		self.NotModifiedSince     = 304
		self.Unauthorized         = 401
		self.Forbidden            = 403
		self.NotFound             = 404
		self.NotAllowed           = 405
		self.WrongType            = 500
		
class V2Constants(TestConstants):
	
	def __init__(self, *args, **kwargs):
		super(V2Constants, self ).__init__(*args, **kwargs)
		
		self.URL				  = "http://localhost:8080"
		self.URL_DS				  = self.URL 	+ '/dataserver'
		self.URL_USERS			  = self.URL_DS + '/users'
		self.URL_TYPE             = self.URL_USERS + '/ltesti/TestType'
		self.URL_POST			  = self.URL_USERS + '/ltesti/TestType/TestGroup'
		self.URL_JSON			  = self.URL_USERS + '/ltesti/TestType/TestGroup/jsonID'
		self.URL_PLIST			  = self.URL_USERS + '/ltesti/TestType/TestGroup/plistID'
		self.URL_OTHER_POST	      = self.URL_USERS + '/sjohnson/TestType/TestGroup'
		self.URL_OTHER_PUT		  = self.URL_USERS + '/sjohnson/TestType/TestGroup/TestID'
		self.NON_EXSIST_TYPE_URL  = self.URL_USERS + '/ltesti/doesNotExist/TestGroup/TestID'
		self.NON_EXSIST_GROUP_URL = self.URL_USERS + '/ltesti/TestType/doesNotExist/TestID'
		self.NON_EXSIST_ID_URL	  = self.URL_USERS + '/ltesti/TestType/TestGroup/doesNotExist'
		self.DEFAULT_INFO		  = {"DefaultKey":"StartingInfo"}
		self.POST_PUT_INFO		  = {"PostPutKey":"NewInfo"}
		self.DEFAULT_RETURN_KEY   = 'DefaultKey'
		self.POST_PUT_RETURN_KEY  = 'PostPutKey'
		self.DEFAULT_RETURN	      = 'StartingInfo'
		self.POST_PUT_RETURN	  = 'NewInfo'
		self.INCORRECT_USER_PASS  = 'incorrect'
		self.EMPTY_USER_PASS	  = ''
		self.NO_USER_PASS		  = None
		
class V3Constants(TestConstants):

	def __init__(self, *args, **kwargs):
		super(V2Constants, self ).__init__(*args, **kwargs)
		
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
