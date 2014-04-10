Notifications
<%def name="general(notable, action, parent_disp_name='display_name')">
<%
	dn = getattr(notable, 'display_name', None)
	if callable(dn):
	   dn = dn()
	if not dn:
	   dn = getattr(notable, 'snippet', None)
	if callable(dn):
	   dn = dn()
	pdn = getattr(notable.__parent__, parent_disp_name, parent_disp_name)
	if callable(pdn):
	   pdn = pdn()
%>
${notable.creator or 'Someone'} ${action} '${dn}' in '${pdn}'.
</%def>

% if discussion:
${general(discussion, 'started a discussion')}
% endif

% if note:
${general(note, 'shared a note', parent_disp_name='note_container_display_name')}
% endif

% if comment:
${general(comment, 'commented')}
% endif

% if feedback:
${general(feedback, 'left feedback', parent_disp_name=feedback.assignment_name)}
% endif

%if circled:
${general(circled, 'added you to a group', 'their contacts')}
%endif

% if grade:
${general(grade, 'assigned a grade', grade.assignment_name or 'a course')}
% endif

This message was sent to ${email_to}. If you don't want to receive
these emails in the future, please unsubscribe at ${unsubscribe_link}.
