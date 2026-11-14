# Assessing reasoning before and after JuiceLab

This exercise complements the thirteen-challenge course. Complete it on paper or
in local notes, without a paid account, AI service or interaction with an app.
Use the same pseudonym for both attempts. The manual eight-point mark is separate
from automatic lab scores.

## Before the course

A fictional booking app applies these rules: customers can read their own
bookings; an agent can read bookings for their agency; nobody may change a
booking’s owner. Alice owns R17, Bob owns R24, and they belong to different
agencies. The interface hides the R24 button from Alice. A server review finds
that reading checks only for a logged-in session. No access logs or execution
results are provided.

Write four short answers:

1. What do these exhibits establish, and what effect remains to be checked?
2. Which authorisation rule is missing, and why is the hidden button insufficient?
3. Which server-side protection would you propose, without an attack procedure?
4. Describe one allowed check and one forbidden check, with expected outcomes.
   Explain what would provide evidence of their execution.

## After the course

A fictional healthcare app applies these rules: people can read their own
appointments; clinicians can read appointments for patients under their care;
only the registration service assigns record ownership. Camille owns D31;
D42 belongs to Nour, and Camille has no care relationship with Nour. The interface
hides D42 from Camille. A server review finds a check for the “patient” role,
without a relationship check between the logged-in person and the requested
record. The creation specification also accepts an owner field from the browser.
No execution results are provided.

Answer the same four questions for these new exhibits. Add what you transfer
from JuiceLab: one concept, one protection and its limit. Do not describe a
proposed check as already executed.

## Assessment criteria

Each dimension earns zero, one or two points: precise observations and limits;
explanation of the rule; appropriate protection; quality of verification and
transfer. Reasoned answers can receive partial credit. Length and speed do not
earn points by themselves. Your teacher states the time slot before each attempt;
record actual time spent rather than an assumed duration.

Between attempts, use hints when needed and complete your journal. Include no
passwords, tokens, real personal data or evidence from systems outside the
authorised lab.
