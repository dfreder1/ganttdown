// Sample ganttdown schedule

@task: 1.0  name: Project Kickoff  start: 04/13/2026  dur: 1
@task: 1.1  name: Requirements     start: 04/13/2026  dur: 5
@task: 1.2  name: Design           dur: 5             dep: 1.1

@task: 2.1  name: Development      dur: 10            dep: 1.2
@task: 2.2  name: Testing          dur: 5             dep: 2.1
@task: 2.3  name: Deploy           dur: 2             dep: 2.2
