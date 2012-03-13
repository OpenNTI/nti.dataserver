LOGIN TESTS 
-----------

Unit to test: Types of login
Test case data: 
	- check if login buttons appear after an email is typed. 
	- check if user can login with facebook. 
	- check if user can login with gmail.
	- nextthought email and password. 
	- use yahoo account. 
	- check logout
	
ACCOUNT TESTS
-------------
Unit to test: Password changes 
Test case data: 
	- check if user is being prompted for old password before changing it. 
	- check if user is allowed to use the same password when changing his password. 
	- check if special characters are allowed.

Unit to test: Lists changes 
Test case data: 
	- check if user can move a 'friend' from the 'accepting' list to 'ignoring' list. 
	- check if user can move a 'friend' from the 'ignoring' list to 'accepting' list. 
	- check if user can add a 'friend' to both lists at the same time. 
	- check if user can add a 'friend' or 'group' to the 'following' list. 
	- check if user can view activities of friends in the 'following' list on the stream page. 
	
READER TESTS
------------

Unit to test: Highlights. 

Test case data: Be able to highlight: 
	- paragraphs. 
	- pictures. 
	- videos. 
	- chapter quotes. 
	- review questions. 

Test case data: Check if all the different types of highlights can be shared with: 
	- one friend. 
	- multiple friends.
	- one group
	- multiple groups. 
	
Test case data: Be able to delete a highlight/shared highlight. 
			
Unit to test: Notes.
Test case data: Be able to create a note for: 
	- paragraphs.
	- pictures. 
	- videos.
	- chapter quotes.
	- review questions. 
	
Test case data: Check location of created notes. 
	
Test case data:Be able to share notes with: 
	- one friend/multiple friends. 
	- one group/multiple groups. 

Test case data: Be able to delete  notes/shared notes. 


ACTIVITY STREAM TESTS 
---------------------
Unit to test: if activity stream is up to date. 
Test case data: Check if activity stream shows updated records:
		- The creation of a highlight.
		- The creation of a note. 
		- Sharing of a note/highlight with one/multiple friends. 
		
GROUP TESTS
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

 CHAT TESTS
-----------

Unit to test:  launching chat
test case data: launch chat from the following modes:
- reader mode
- stream mode
- group mode
- from note
- from class

Unit to test:  1-1 chat
test case data: send and receive 1-1
- test by double clicking user in chat window
- test via text box
- test via "compose message"
- send basic whiteboard image
- send line break via "compose message"
- check messaging around closing user 1 window and having user 2 send on the same session

Unit to test:  Group chat
test case data: send and receive group chat and ensure all parties receive
- test by clicking "open chat for group" icon 
- test via text box
- test via "compose message"
- test via class room 
- send basic whiteboard image
- send line break via "compose message"
- check messaging around closing one user 1 window and others still chatting
- ensure group chat works when starting from a shared note

Unit to test:  Start Many 1-1 chats
test case data: start many 1-1 chats
- open chat with multiple people and ensure chats make it to the right users

Unit to test:  Chat Misc	
test case data: Chat Misc
- ensure flagged messages
- ensure chat window is in front of the videos 

CLASSROOM TESTS 
---------------

Unit to test: Class addition. 
test case data: be able to create a classroom. 
	- check that the class ID is valid. 
	- check if user can add description 
	- check if user can add one section. 
	- check if user can add a large number of sections. 
	- check if user can delete a section. 
	- check if the class was successfully created. 
	- check if all class components were saved (for example: different sections, descriptions, etc...). 
 
Unit to test: Class management. 
test case data: be able to edit a classroom. 
	- ensure that the class ID can be changed. 
	- ensure that the  description can be edited.
	- ensure that a section can be added. 
	- ensure that a section can be deleted. 

MYSTUFF TESTS
-------------

Unit to test: My stuff updates. 
test case data: Check if Mystuff display an updated list of: 
	- highlights. 
	- notes. 
	- messages.

