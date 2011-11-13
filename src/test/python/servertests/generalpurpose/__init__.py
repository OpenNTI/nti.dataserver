'''
Created on Oct 4, 2011

@author: ltesti
'''
import uuid


class TestConstants(object):

	def __init__(self, *args, **kwargs):
		
		#Universal constants
		self.username             = 'ltesti'
		self.otherUser            = 'sjohnson'
		self.unauthorizedUser	  = 'incorrect'
		self.emptyUser			  = ''
		self.noUser				  = None
		self.password             = 'temp001'
		self.incorrectPassword    = 'incorrect'
		self.emptyPassword		  = ''
		self.noPassword			  = None
		self.URL				  = 'http://localhost:8080/dataserver'
		self.message              = None
		self.void                 = None
		self.TinyNumber           = 0
		self.LonelyNumber         = 1
		self.TheNumberTwo         = 2
		self.TheNumberThree       = 3
		self.WRONG_INFO			  = 10
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
	
	#The constants used in ServerTestV2
	def __init__(self, *args, **kwargs):
		super(V2Constants, self ).__init__(*args, **kwargs)
		
		#URL constants
		UUID = str(uuid.uuid4())
		self.URL_USER							= self.URL + '/users/ltesti'
		self.URL_OTHER_USER						= self.URL + '/users/sjohnson'
		self.URL_USER_TYPE      				= self.URL_USER + '/TestType'
		self.URL_USER_POST						= self.URL_USER + '/TestType/TestGroup'
		self.URL_USER_NO_FORMAT					= self.URL_USER + '/TestType/TestGroup/TestID'
		self.URL_OTHER_USER_POST				= self.URL_OTHER_USER + '/TestType/TestGroup'
		self.URL_OTHER_USER_NO_FORMAT			= self.URL_OTHER_USER + '/TestType/TestGroup/TestID'
		
		#Unset URL constants
		self.URL_USER_NONEXIST_TYPE_NO_ID		= self.URL_USER + '/' + UUID + '/TestGroup'
		self.URL_USER_NONEXIST_TYPE				= self.URL_USER + '/' + UUID + '/TestGroup/TestID'
		self.URL_USER_NONEXIST_GROUP_NO_ID		= self.URL_USER + '/TestType/' + UUID
		self.URL_USER_NONEXIST_GROUP			= self.URL_USER + '/TestType/' + UUID + '/TestID'
		self.URL_USER_NONEXIST_ID	  			= self.URL_USER + '/TestType/TestGroup/' + UUID
		
		#URL access constants
		self.DEFAULT_INFO		  				= {"DefaultKey":"StartingInfo"}
		self.POST_PUT_INFO		  				= {"PostPutKey":"NewInfo"}
		self.DEFAULT_RETURN	      				= 'StartingInfo'
		self.POST_PUT_RETURN	  				= 'NewInfo'
		self.INCORRECT_USER_PASS  				= 'incorrect'
		self.EMPTY_USER_PASS	  				= ''
		self.NO_USER_PASS		  				= None
		
class V3Constants_Quizzes(TestConstants):

	def __init__(self, *args, **kwargs):
		super(V3Constants_Quizzes, self ).__init__(*args, **kwargs)
		
		#URL constants
		UUID = str(uuid.uuid4())
		self.URL_POST			    			= self.URL + '/quizzes'
		self.URL_NO_FORMAT		    			= self.URL + '/quizzes/TestQuiz'
		self.URL_MATH_XML           			= self.URL + '/quizzes/XML'
		self.URL_NONEXIST_ID					= self.URL + '/quizzes/' + UUID
		
		#URL access constants
		self.DEFAULT_INFO   	    			= {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(Default\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "Answers": ["\(Question\)", "\(question\)"], 'Class':'QuizQuestion'} } }
		self.DEFAULT_RETURN		    			= { "1" : {"Text": "Question 1", "ID":"1", "Answers": ["\(Default\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "ID": "2", "Answers": ["\(Question\)", "\(question\)"], 'Class':'QuizQuestion'} }
		self.POST_PUT_INFO			    		= {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(red\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "Answers": ["\(10\)", "\(10.0\)"], 'Class':'QuizQuestion'} } }
		self.POST_PUT_RETURN					= { "1" : {"Text": "Question 1", "ID":"1", "Answers": ["\(red\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "ID": "2", "Answers": ["\(10\)", "\(10.0\)"], 'Class':'QuizQuestion'} }
		self.POST_PUT_BAD_ID_INFO	    		= {"Items": { "1" : {"Text": "Question 1", 'ID' : '3', "Answers": ["\(red\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", 'ID' : '19992', "Answers": ["\(10\)", "\(10.0\)"], 'Class':'QuizQuestion'} } }
		self.DEFAULT_INFO_OPEN_MATH_XML_INFO	= {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(x + 10\)"], 'Class':'QuizQuestion'}}}
		self.DEFAULT_INFO_OPEN_MATH_XML_RETURN	= { "1" : {"Text": "Question 1", 'ID':'1', "Answers": ["\(x + 10\)"], 'Class':'QuizQuestion'}}

class V3Constants_Results(TestConstants):

	def __init__(self, *args, **kwargs):
		super(V3Constants_Results, self ).__init__(*args, **kwargs)

		#URL constants
		UUID = str(uuid.uuid4())
		self.URL_SETUP_FORMAT	    			= self.URL + '/quizzes/TestQuiz'
		self.URL_SETUP_MATH_XML					= self.URL + '/quizzes/MathXMLQuiz'
		self.URL_USER							= self.URL + '/users/ltesti'
		self.URL_OTHER_USER						= self.URL + '/users/sjohnson'
		self.URL_USER_POST						= self.URL_USER + '/quizresults'
		self.URL_USER_NO_FORMAT  				= self.URL_USER + '/quizresults/TestQuiz'
		self.URL_USER_MATH_XML      			= self.URL_USER + '/quizresults/MathXMLQuiz'
		self.URL_OTHER_USER_NO_FORMAT	   		= self.URL_OTHER_USER + '/quizresults/TestQuiz'
		self.URL_USER_NONEXIST_ID				= self.URL_USER + '/quizresults/' + UUID 
		
		#URL access constants
		self.SETUP_INFO   	   					= {"Items": { "1" : {"Text": "Question 1", "Answers": ["\(Default\)"], 'Class':'QuizQuestion'},
														"2" : {"Text": "Question 2", "Answers": ["\(Question\)", "\(question\)"], 'Class':'QuizQuestion'} } }
		self.SETUP_MATH_XML						= {"Items": { "1" : {"Text": "Question 1", "Answers": ['\\(x + 10\\)'], 'Class':'QuizQuestion'}}}
		self.DEFAULT_INFO						= {'1': 'Default', '2': 'Question'}
		self.INCORRECT_INFO			   			= {'1': 'postPut', '2': '11'}
		self.OPEN_MATH_XML_INFO		  			= {'1': '<OMOBJ xmlns="http://www.openmath.org/OpenMath" version="2.0" cdbase="http://www.openmath.org/cd"><OMA><OMS ' + \
														'cd="arith1" name="plus"/><OMV name="x"/><OMI>10</OMI></OMA></OMOBJ>'}
		self.SKIPPED_QUESTION_INFO    			= {'1': 'Default'}
		self.DEFAULT_RETURN			   			= [('Question 1', ['\\(Default\\)'], True), ('Question 2', ['\\(Question\\)', '\\(question\\)'], True)]
		self.INCORRECT_RETURN	    			= [('Question 1', ['\\(Default\\)'], False), ('Question 2', ['\\(Question\\)', '\\(question\\)'], False)]
		self.SKIPPED_QUESTION_RETURN		    			= [('Question 1', ['\\(Default\\)'], True)]
		self.MATH_XML_RETURN        			= [('Question 1', ['\\(x + 10\\)'], True)]
		self.POST_PUT_RETURN					= None
		
		