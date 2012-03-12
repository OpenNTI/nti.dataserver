
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
 	