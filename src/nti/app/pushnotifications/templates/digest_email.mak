Hi ${display_name}!
% if notable_text:
${notable_text}

% else:
Here's what you may have missed on ${site_name} since ${since_when}.

% endif
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
You received a grade.
% endif

% if unsubscribe_link:
This message was sent to ${email_to}. If you don't want to receive
these emails in the future, please unsubscribe at ${unsubscribe_link}.

% endif