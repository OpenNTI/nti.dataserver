===========================
 Assessment Implementation
===========================

.. toctree::
	:maxdepth: 3

The implementations of the assessment interfaces.

Parts
=====

At the lowest level are the individual assessment parts.

.. automodule:: nti.assessment.parts

Solution
--------

Each part has solutions.

.. automodule:: nti.assessment.solution

Hints
-----

Parts may have hints.

.. automodule:: nti.assessment.hint

Question
========

Parts make up questions.

.. automodule:: nti.assessment.question

Grading
=======

Responses capture the student input.

.. automodule:: nti.assessment.response

Submission
----------

They are submitted.

.. automodule:: nti.assessment.submission

Graders
-------

Responses are graded.

.. automodule:: nti.assessment.graders

LaTeX
-----

LaTeX input is a special case of symbolic math handling. It is first
parsed.

.. automodule:: nti.assessment._latexplastexconverter

Then it is graded.

.. automodule:: nti.assessment._latexplastexdomcompare

Assessed
--------

The results are recorded in assessed objects.

.. automodule:: nti.assessment.assessed
