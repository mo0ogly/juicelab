# JuiceLab Angular teaching layer

Source of the standalone coach components merged by the supported delivery build.
See [the main README](../../../../../README.md),
[French pedagogy](../../../../../docs/PEDAGOGY-FR.md) and
[English pedagogy](../../../../../docs/PEDAGOGY.md).

The public catalogue selects thirteen course challenges. Public briefing and
journal packs contain learning goals and questions, without solution procedures.
Hints, quiz answer keys and walkthroughs remain in server-side private packs.
New optional briefing fields are learning_objectives_fr/en, prerequisites_fr/en
and deliverable_fr/en. Legacy packs without them remain readable. Briefing load
failures show the existing unavailable message, distinct from loading state.

The hint display uses cumulative 5/10/20/35/50 costs with a zero floor, matching
the teacher proof. Journals save to local state then use the existing sync path;
local saving alone does not prove dashboard receipt. Manual reasoning assessment
is documented in the teacher guide and is separate from automatic quiz scoring.

Use [INSTALL.md](../../../../../INSTALL.md) and
[DOCKER.md](../../../../../docs/DOCKER.md) for the supported delivery path.
The earlier plugin-source, public answer-pack and floor50 instructions were
obsolete. This README does not certify quiz gating or a deployed version.
