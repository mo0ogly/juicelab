# Supporting and assessing the JuiceLab course

Use this guide with the [student assessment](ASSESSMENT.md) and journals for the
thirteen challenges. It supports reasoning review, class debriefing and measuring
change. It does not establish an observed learning gain.

## Shared eight-point rubric

| Dimension | 0 points | 1 point | 2 points |
| --- | --- | --- | --- |
| Observation and limits | Conclusion without an identifiable exhibit | Relevant exhibit, unclear scope | Precise exhibit; observation, hypothesis and missing evidence distinguished |
| Explanation | No relevant rule | Correct concept without a case connection | Rule connects the case’s actor, action and object |
| Protection | None or client-only protection | Plausible but incomplete server protection | Rule-linked protection using verified identity and the target object |
| Verification and transfer | No defined check | One expected result or partial transfer | Allowed and denied cases, expected outcomes and planned evidence; adaptation to new case |

This manual rubric is separate from quiz marks, hint scores and badges. Do not
insert it into historical events or the automatic average. Saved journals and
word counts alone do not establish understanding.

## Before-case answers

1. The rules, owners and described server check are supplied. Hiding a button is
   an interface measure. Actual access by Alice to R24 is unproven: no request,
   response or access trace is supplied.
2. Being logged in is insufficient. The server must decide whether this person
   can read this booking, based on ownership or their role and agency.
3. Derive identity from a verified session and check the required relationship
   with the requested object on each read. Do not allow client-supplied values
   to change ownership. Alternative architectures are acceptable if they enforce
   the same rules server-side.
4. Allowed: Alice reads R17. Denied: Alice requests R24, receiving no data for it.
   Either 403 or a documented existence-hiding 404 can be appropriate. Also test
   agents for their own agency and another agency. Evidence must link controlled
   identity, object, outcome and a dated trace.

## After-case answers

1. The review identifies missing relationship checks and a specification accepting
   client-supplied ownership. These justify checking; no actual effect is proved.
2. A “patient” role does not grant access to every record. Access depends on
   ownership or an authorised care relationship. The registration service assigns
   ownership under this scenario’s rules.
3. Enforce those relationships server-side. Ignore or reject an owner supplied by
   an unauthorised client, deriving it from authorised context. Common middleware
   can help, supplemented by necessary business checks.
4. Camille can read D31 and must receive no D42 data. Test assigned and unassigned
   clinicians separately. For creation, check that final ownership follows the
   registration contract. Plan dated evidence without real medical data. Expected
   transfer is relationship-based authorisation, not a memorised route.

## Supporting the class

Read progress, hints, journals and quiz results together in the existing matrix.
High hint consumption suggests possible support needs; it is not an automatic
individual diagnosis. Read a justification and ask for a reformulation before
concluding. Group observed misconceptions for class debriefing without publicly
displaying named students’ difficulties. Journal answers are evidence for this
rubric; totals or badges alone are insufficient. Existing alert rules are unchanged.

## Measurement protocol for the next session

1. Before the course, distribute only the student exercise, state time and help
   rules, and retain responses under pseudonyms.
2. After the course, collect independent answers to the second case under the
   same help rules. Do not distribute answers beforehand.
3. Use the same rubric, preferably without seeing earlier marks. Choose a sample
   before marking for a second marker; retain disagreements and their resolution.
4. Record pseudonym, variant, date, actual duration, four rubric dimensions,
   total out of eight, hints and declared external help. Keep missing responses
   distinct from zero scores. Restrict access to original responses.
5. Compare complete pairs only; report their count, missing responses, individual
   changes and median change, plus each dimension. Improvement across these cases
   alone is not a causal effect of JuiceLab: variant difficulty, marking and
   familiarity can contribute. Counterbalance case order between groups in a
   later session to examine a variant effect instead of assuming it is absent.

The protocol is ready for use; no cohort results are invented. Time allowances
remain teacher decisions, without an automatic blocking threshold.

Technical reference: [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html),
permissions on every request, object-specific access and server-side enforcement.
