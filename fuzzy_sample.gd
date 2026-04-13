# Construction Project Schedule

Some narrative text about the project. ganttdown ignores everything
outside the task block.

<task>
// Phase 1 - Site prep
1.0  Project Kickoff    2026-04-13  1
1.1  Site Survey        2026-04-13  5
1.2  Permits            1.1         5

// Phase 2 - Foundation
2.1  Excavation         1.2         5
2.2  Build foundation   2.1         5
2.3  Cure foundation    2.2         7

// Phase 3 - final things
0.1 Sign 2 forms 2.2 6
3 owner approval 2.3 7
</task>

More narrative text here, also ignored.
