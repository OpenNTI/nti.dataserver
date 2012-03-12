A. WEB APP TESTS
----------------

I.Login Tests 
-------------

TEST CASE ID : A.I.1 

Test Case name: Multiple Logins

Unit to Test :  Multiple logins on the same browser need to be prohibited. 

Test data: 
	user 1: nathalie.kaligirwa
	password: temp001 
	user 2: pacifique.mahoro
	password: pacifique.mahoro
	
Execution steps: 
	1. open browser (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/ (note: I am assuming we will be testing on local, but I can change it to excelsior.nextthought.com if needed). 
	2. log in as user 1 using provided credentials.
	3. copy URL from browser 
	4. open new tab
	5. paste URL log out user 1, and login user 2.
	
Expected result: User 1 should be logged out as soon as user 2 is logged in the same browser. 

Actual result: Both users are still logged in and able to navigate the application on the same browser.

Pass/Fail: Fail

Comments: The problem has to do with cookies that need to be cleared out (contact Greg Higgins for details). 


TEST CASE ID: A.I.2 

Test Case name: Facebook Login 

Unit to Test: User should be able to login through facebook. 

Test data: 
	user 1: personal facebook email (note: Do we need to create a facebook user to test this feature? For now, please use your own facebook credentials). 

Execution steps: 
	1.Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2.Enter personal facebook email
	3.Click on 'Sign in With Facebook' tab. 

Expected result: user should be redirected to facebook's Login page, or log user in immediately. 

Actual Result: user is redirected to a facebook page with an error message 'An error occured. Please try again later'. 

Pass/Fail: Fail

Comments: Issue has to do with the version of the application being tested (contact Jason Madden for details). 


TEST CASE ID: A.I.3 

Test Case name: Login Fields missing

Unit to Test: When a correct email is typed, the password field and Sign in with gmail has to automatically appear. 

Test Data:
	user 1 email: nathalie.kaligirwa@nextthought.com 
	password: temp001

Execution steps: 
	1.Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's email. 
	
Expected result: password field and 'Sign in with Gmail' tab should appear as soon as user finishes entering email. 

Actual result: password field and 'Sign in with Gmail' tab do not appear. 

Pass/Fail: Fail

Comments: When the page is refreshed, the password field and 'Sign in with Gmail' appear.


II. Accounts Tests
------------------

TEST CASE ID: A.II.1 

Test Case name:  Password Change

Unit to Test: User should be prompted for his old password before changing it to a new one. 

Test Data:
	user 1 email: nathalie.kaligirwa@nextthought.com 
	password: temp001

Execution steps: 
	1. Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's credentials and hit enter. 
	3. Click on avatar icon on top-right hand of the page.
	4. Choose 'account' from pop-up menu.
	5. Click on 'change password' link. 
	
Expected result: With the fields to enter and verify new password, the user should be prompted for his old password. 

Actual result: Only the fiels to enter and verify new password are present. 

Pass/Fail: Fail 

Comments: Double-check if this is the intended behavior. 


TEST CASE ID: A.II.2 

Test Case name: Password Change with old password. 

Unit To Test: The user should not be able to change the password with the old password value. (ex: changing from temp001 to temp001). 

Test Data:
	user 1 email: nathalie.kaligirwa@nextthought.com 
	password: temp001

Execution steps: 
	1. Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's credentials and hit enter. 
	3. Click on avatar icon on top-right hand of the page.
	4. Choose 'account' from pop-up menu.
	5. Click on 'change password' link. 
	6. Enter temp001 in the 'new password' and 'verify password field' 
	7. Click save

Expected result: User should be warned that he is entering a new password that is the same as his current password and be forced to enter a different value. 

Actual result: User is able to save the changes. 

Pass/Fail: Fail 

Comments: Double-check if it is the intended behavior to simplify password changes verifications. 

TEST CASE ID: A.II.3

Test Case name: Warning when moving a friend from the 'accepting' list to the 'ignore' list. 

Unit to Test: When moving a 'friend' from the 'accepting' list to the 'ignore' list, the friend should be either moved to that list or a message should warn the user that the friend is already on the 'accepting' list. 

Test Data:
	user 1 email: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	friend name: pacifique mahoro

Execution steps: 
	1. Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's credentials and hit enter. 
	3. Click on avatar icon on top-right hand of the page.
	4. Choose 'account' from pop-up menu.
	5. Click on arrow icon next to  'Accepting' 
	6. Enter friend name (pacifique mahoro) in the 'Search to add' field. 
	7. Choose friend name (pacifique mahoro) from dynamic list. 
	8. Click on the 'save' button. 
	9. Click on avatar icon on top-right hand of the page.
   10. Choose 'account' from pop-up menu.
   11. Click on arrow icon next to 'Ignoring' 
   12. Enter friend name (pacifique mahoro) in the 'Search to add' field. 
   13. Choose friend name (pacifique mahoro) from dynamic list. 
   14. Click on the 'save' button. 
   15. Click on avatar icon on top-right hand of the page.
   16. Choose 'account' from pop-up menu.
   17. Click on arrow icon next to 'Ignoring' 
  
Expected result: friend name 'Pacifique Mahoro' should be in the 'ignoring' list or a warning message should have informed the user that 'pacifique mahoro' is currently on the accepting list. 

Actual result: 'pacifique mahoro' was silently not added to the 'ignoring' list. 

Comments: For now it is not a big issue because the user has only a few friends. But if the list of followed friends grows, then there should be some kind of procedure to inform the user that he is moving a friend


III. Reader Tests
-----------------

TEST CASE ID: A.III.1 

Test Case name: Multiple highlights

Unit to Test: A text can be highlighted several times, but should not cover the text. 

Test data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra 

Execution steps: 
	1. Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's credentials and hit enter. 
	3. Under 'Library' select 'Prealgebra' book. 
	4. Select a random text.
	5. Choose 'save highlight' from pop-up menu. 
	6. Re-highlight the same text several times. 
	
Expected results: Multiple highlights should not add layer of color if the text was previously highlighted. 

Actual result: Multiple highlights add multiple layers of color and eventually blocks the user from reading the text. 

Fail/Pass: Fail 

Comments: none. 

TEST CASE ID: A.III.2 

Test case name: Note is being added at the bottom of the chapter text. 

Unit to Test: Check location of notes created for a highlighted text. 

Test data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra 

Execution steps: 
	1. Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's credentials and hit enter. 
	3. Under 'Library' select 'Prealgebra' book. 
	4. On upper-right corner of the reader, click on 'prealgebra'. 
	5. Choose Prealgebra > Properties of Arithmetic > Why Start with Arithmetic from drop-down menu. 
	6. Select three lines on the third paragraph (starts with 'Arithmetic refers to the basics...'). 
	7. Select save highlight from pop-up menu. 
	8. Click anywhere in the highlighted text. 
	9. Choose 'add note' from the pop-up menu. 
   10. Type some words in the pop-up window. 
   11. Save the note. 
   
Expected results: The created note should be located right below the last line of the text. 

Actual results: The note is saved at the end of the paragraph. 

Fail/Pass: Fail 

Comments: none. 

TEST CASE ID: A.III.3

Test case name: Note is being added in the middle of the of the highlighted text. 

Unit to Test: Check location of notes created for a highlighted text. Note should be at the end of the highlighted text.

Test data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp011 
	
	book: Prealgebra 
	
Execution Steps: 
	1. Open broswer (Google Chrome), enter https:localhost:8081/NextThoughtWebApp/  
	2. Type in user 1's credentials and hit enter. 
	3. Under 'Library' select 'Prealgebra' book. 
	4. On upper-right corner of the reader, click on 'prealgebra'. 
	5. Choose Prealgebra > Ratios, Conversions, and Rates > WWhat is a ratio from drop-down menu. 
	6. Select three lines on the first paragraph (starts with 'Ratios behave a lot like fractions...'). 
	7. Select save highlight from pop-up menu. 
	8. Click anywhere in the highlighted text. 
	9. Choose 'add note' from the pop-up menu. 
   10. Type some words in the pop-up window. 
   11. Save the note. 

Expected results: The created note should be located right below the highlighted text.
   
Actual Results: The created note is located right below the first line of the highlighted text. 

Fail/Pass: Fail

Comments: In some cases, the note is added right in the middle of the paragraph. 


TEST CASE ID: A.III.4 
Test case name:
Unit to test: Check location if notes are added at the end of the highlighted text. 
Test data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra 

Execution steps: 
Expected results: 
Actual Results: Notes are being added at random locations within the highlighted text. 
Fail/Pass: 
Comments:

TEST CASE ID: A.III.5
Test case name: 
Unit to Test: Check if created notes are overlapping at the end of section. 
Test case data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra 
	
Execution steps: 
Expected results: Notes should have spacing between them. 
Actual results: Notes are overlapping. 
Fail/Pass: 
Comments: 

TEST CASE ID: A.III.6 
Test case name: 
Unit to test:Check the space between questions when a note is added (on the exercises sections). 
Test data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra 
	
Execution steps: 
Expected results: The spacing between two questions should not be too large. 
Actual results: Adding a note creates a huge space between the questions. 
Fail/Pass:
Comments: 

TEST CASE ID: A.III.7 
Test case name: 
Unit to test: Check if the space at the end of the page is not being modified by the addition of a note (for example, the lines being 'squashed' together). 
Test case data:
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra (Still trying to recreate it).
	
Execution steps: 
Expected results: The page size should increase to make room for notes (dynamically changed I am assuming). 
Actual results: Size between lines is being reduced.
Fail/Pass:
Comments: 

TEST CASE ID: A.III.8
Test case name: Adding a note shouldn't change the numbering of questions. 
Test case data:
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra>Properties of Arithmetic>Exercises  
	
Execution steps: 
Expected results: The page size should increase to make room for notes (dynamically changed I am assuming). 
Actual results: Size between lines is being reduced.
Fail/Pass:
Comments: 

TEST CASE ID: A.III.9 
Test case name: Videos should not block the pop-up window for chatting or creating a note. 
Test case data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra>Properties of Arithmetic>Addition
	
Execution steps: 
Expected results: pop-up window fully visible even when in front of video. 
Actual results: pop-up window is blocked by the video. 
Fail/Pass:
Comments: This issue happens only on Chrome because of the settings applied to videos. We have no control over it.

TEST CASE ID: A.III.10 
Test case name:
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra 
	
Unit to test: Check if left-side menu changes (Who and What checkboxes) are kept after a refresh.
Test case data: 
	
Execution steps: 
Expected results: Changes to Who and What checkboxes should be maintained after a page refresh. 
Actual Results: Left-side menu (What and Who) changes are reset to default (all checkboxes selected) after the page is refreshed. 
Fail/Pass: 
Comments: 

TEST CASE ID: A.III.11 
Test case name: 
Unit to test: Overlapping notes. 
Test case data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra > front page. 

Execution steps: 
Expected results: Notes should have space between them (<br> </br>). 
Actual Results:  Notes are overlapping. 
Fail/Pass: 
Comments: 

TEST CASE ID: A.III.12
Test case name: 
Unit to test: Format of messages in mathcounts exercises. 
test case data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra > front page. 

Execution steps: 
Expected results: 
Actual Results:  Notes are overlapping. 
Fail/Pass: 
Comments:  

TEST CASE ID: A.III.13
Test case name: 
Unit to test: If note for a chapter quotation is being created. 
test case data: 
	user 1: nathalie.kaligirwa@nextthought.com 
	password: temp001
	
	book: Prealgebra > Exponents

Execution steps: Select chapter quotation at the beginning of chapter
Expected results: Note should be added below the highlighted quotation. 
Actual Results:  Note is not being created anywhere on the page. 
Fail/Pass: 
Comments: I tried it on three different chapter quotations and I get the same behavior.   


Group tests
-----------

Unit to test: names of group
Test case data: 
- Check if group name can be left empty.
- Check if group name can have unlimited number of characters. 
- Check if space character is an acceptable name. 
- Check if special characters are legal. 
- Use an existing group name. 

Unit to test: group members. 
Test case data: 
- Add a large number of group members (e.g: 300000). 
- Add the same group member twice. 
- Check if group can have 0 members.  

Unit to test: Sorting and columns settings.
Test case data: 
- Check if ascending and descending sorting works. 
- Check if 'columns' menu allows to change displayed columns.
- Check if changes to 'columns' menu are being saved. 
- Check if all columns checkboxes have names. 
- When no columns are displayed, check if there is still a menu to change the columns settings. 

