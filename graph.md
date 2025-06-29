---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	planner(planner)
	executor(executor)
	helper(helper)
	composer(composer)
	critic(critic)
	__end__([<p>__end__</p>]):::last
	__start__ --> planner;
	composer --> critic;
	executor --> helper;
	helper --> composer;
	planner --> executor;
	critic --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc
