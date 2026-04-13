<p>Everyone needs to make a schedule at some point, but most tools are complicated, heavyweight, and not easy to share. As someone working in a corporate engineering environment, I need to do create and share schedules constantly. 

It would be convenient to share a schedule as a simple text file to put in a mono-spaced email section or Microsoft Teams window. The usual options aren't great — a full Microsoft Project file is overkill, a spreadsheet doesn't paste well into chat, and a hand-drawn ASCII chart is tedious to maintain. What I wanted was something as simple as Markdown: a plain text format I could type quickly, that would render into something clear and readable and could be dropped straight into a Teams message. The result is <strong>ganttdown</strong>, a lightweight Gantt chart tool that turns a simple text file into a monospaced chart you can paste anywhere. It was vibe-coded with Claude.</p>

<p>The web version is available at <a href="https://ganttdown.dougfredericks.net">ganttdown.dougfredericks.net</a>.</p>

<h2>How It Works</h2>

<p>ganttdown reads a schedule written inside a <code>&lt;task&gt;</code> block. You can embed this block in any plain text or Markdown file — everything outside the block is ignored, so you can surround your schedule with notes, headings, or narrative text.</p>

<p>Each task is a single line with four fields in a fixed order:</p>

<pre><code>&lt;task#&gt;  &lt;name&gt;  &lt;YYYY-MM-DD or dep#&gt;  &lt;duration&gt;</code></pre>

<ul>
  <li><strong>Field 1</strong> — Task number using dotted hierarchy, e.g. <code>1</code>, <code>1.1</code>, <code>2.3</code></li>
  <li><strong>Field 2</strong> — Task name — everything between the task number and field 3</li>
  <li><strong>Field 3</strong> — Either a start date in <code>YYYY-MM-DD</code> format, or the number of a task this one depends on</li>
  <li><strong>Field 4</strong> — Duration in working days (Monday–Friday only)</li>
</ul>

<p>A complete schedule looks like this:</p>

<pre><code>&lt;task&gt;
// Phase 1
1.0  Project Kickoff  2026-04-13  1
1.1  Get Project Data 2026-04-13  5
1.2  Design           1.1         5

// Phase 2
2.1  Submit to client      1.2         10
2.2  Respond to comments   2.1         5
2.3  Construction          2.2         2
&lt;/task&gt;</code></pre>

<p>Lines beginning with <code>//</code> are comments and are ignored. Blank lines are also ignored. The parser figures out what each field is by its shape — a date looks like <code>2026-04-13</code>, a dependency looks like <code>1.1</code>, and a duration is a plain integer.</p>

<h2>The Output</h2>

<p>ganttdown produces a monospaced text chart with one column per working day, grouped by week. Dependencies are computed automatically — a task with a dependency starts the next working day after all its predecessors finish. Weekends are skipped in both durations and the chart grid.</p>

<img src="https://dougfredericks.net/wp-content/uploads/2026/04/Screenshot-2026-04-12-at-9.17.34-PM-300x76.png" alt="" width="300" height="76" class="alignnone size-medium wp-image-1447" />

<p>In text, which may look bad depending on the width of your screen, the schedule looks like this:</p>

<pre><code>#     Task Name             Dur    Dep    04/13/2026:04/20/2026:04/27/2026:05/04/2026:05/11/2026:05/1:
                                          M T W T F :M T W T F :M T W T F :M T W T F :M T W T F :M T :
                                          ----------:----------:----------:----------:----------:----:
1.0   Project Kickoff       1      n/a    #         :          :          :          :          :    :
1.1   Get Project Data      5      n/a    # # # # # :          :          :          :          :    :
1.2   Design                5      1.1              :# # # # # :          :          :          :    :

2.1   Submit to client      10     1.2              :          :# # # # # :# # # # # :          :    :
2.2   Respond to comments   5      2.1              :          :          :          :# # # # # :    :
2.3   Construction          2      2.2              :          :          :          :          :# # :</code></pre>

<h2>Using It in Microsoft Teams</h2>

<p>Teams renders text wrapped in triple backticks as a monospaced code block, which preserves the chart alignment. The web app has a <strong>Copy for Teams</strong> button that wraps the chart in triple backticks automatically — paste it straight into a Teams message and it renders correctly.</p>

<h2>Try It</h2>

<p>The web app is at <a href="https://ganttdown.dougfredericks.net">ganttdown.dougfredericks.net</a>. Type or paste your schedule into the input area, click Generate, and use the Copy for Teams button to grab the result.</p>
