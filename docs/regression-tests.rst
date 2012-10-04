LOGIN TESTS 
-----------

Unit to test: Types of login
Test case data: 
	- check if login buttons become active after a username and password are typed.  

	
ACCOUNT TESTS
-------------
Unit to test: Password changes 
Test case data: 
	- check if user is being prompted for old password before changing it. 
	- check if user is allowed to use the same password when changing his password. 
	- check if special characters are not allowed.
	- check if only whitespaces are not allowed.
	- check if a new password too similar to an old one is prohibited.
	

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
	- lists
	- Math Formulas. 

Test case data: Be able to delete a highlight. 
			
Unit to test: Notes.
Test case data: Be able to create a note in the gutter next to: 
	- paragraphs.
	- pictures. 
	- videos.
	- review questions. 
	
Test case data: Check location of created notes. 
	
Test case data:Be able to share notes with: 
	- one friend/multiple friends. 
	- one group/multiple groups. 

Test case data: Be able to delete notes/shared notes. 


ACTIVITY STREAM TESTS 
---------------------
Unit to test: if activity stream is up to date. Meaning if something is shared with a friend, an instant notification should appear under notifications. 

Test case data: Check if activity stream shows updated records:
		- The creation of a highlight.
		- The creation of a note. 
		- Sharing of a note/highlight with one/multiple friends. 
		- If a user is added to someone's contacts. 

Test case data: Check if clicking on a notification does the right action.
		- clicking on a note notification should open the note.
		- clicking on a 'added as a contact' notification should open a menu to select a group and add your friend to it. 
		- clicking on a redaction should do nothing (for now).
		- hovering over a note notification should show a fly-out of the note. 

Test case data: Check if the different buttons on a note work
		- Reply button opens a reply field.
		- Share button shows the list of people the note is shared to. 
		- Start a chat button opens a new chat session. 
		
		
GROUP TESTS
-----------

Unit to test: names of group
Test case data: 
- Check if group name can be left empty.
- Check if group name can have unlimited number of characters. 
- Check if space character is an acceptable name. 
- Check if special characters are legal. 


Unit to test: group members. 
Test case data: 
- Add the same group member twice. 
- Remove a user from a group
- Add a user to a group

 CHAT TESTS
-----------

Unit to test:  launching chat
test case data: launch chat from the following modes:
- from note
- from group

Unit to test:  1-1 chat
test case data: send and receive 1-1
- test by clicking friends name under Contacts. 
- test via notes
- send basic whiteboard image
- check messaging around closing user 1 window and having user 2 send on the same session

Unit to test:  Group chat
test case data: send and receive group chat and ensure all parties receive
- test by clicking "Group Chat'  
- send basic whiteboard image
- check messaging around closing one user 1 window and others still chatting
- ensure group chat works when starting from a shared note

Unit to test:  Start Many 1-1 chats
test case data: start many 1-1 chats
- open chat with multiple people and ensure chats make it to the right users

Unit to test:  Chat Misc	
test case data: Chat Misc
- ensure chat window is in front of the videos 


SEARCH TESTS
------------

Unit to test: Search efficiency. 
test case data: Check if search can match up: 
	- sentences. 
	- partial matches
	
test case data: Check if clicking on a search result redirects to that page.Check for both: 
	- 'content' search results. 
	- 'user generated' search results (meaning notes and highlights).
	 

##############IGNORE THESE TESTS#########################################
MYSTUFF TESTS
-------------

Unit to test: My stuff updates. 
test case data: Check if Mystuff displays an updated list of: 
	- highlights. 
	- notes. 
	- messagesNotes (chats).
	
test case data: Check if clicking on a list item (highlights/notes/messageNotes) redirects you to the right page. 

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

test case data: make sure the user can manage ressources through:
	- uploading ressources. 
	- deleting ressources. 

test case data: make sure the user can: 
	- enter a study group by clicking on its 'select' link.
	- 
