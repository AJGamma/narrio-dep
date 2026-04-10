[www.notion.com](https://www.notion.com/blog/brainlabs-cure-for-execution-tax) Áine Dundas

Dan Gilbert has a name for the thing quietly draining companies everywhere: **execution tax**.

It's the gap between a decision and its outcome. Between *we should do this* and *this is done*. "Every meeting creates more work," explains Dan. "More notes. More summaries of notes. More sharing those notes. Action items captured---and quietly lost."

Dan is Global CEO of Brainlabs, a 1,000-person media agency operating across seven countries. Data-driven, scientific, laser-focused on driving client revenue. The kind of company where every hour spent chasing action items is an hour not spent on strategy.

He's watched AI transform the input/output ratio of engineering work. [The data bears it out](https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights/unlocking-the-value-of-ai-in-software-development): top-performing engineering teams using AI are seeing double-digit productivity gains and measurable jumps in quality. But for everyone else---the strategists, account managers, and operators---the gap between deciding and doing was still achingly wide.

So Dan asked the question that changed everything at Brainlabs: **When does the 10x moment arrive for the knowledge worker?**

He stopped waiting for someone else to answer it.

![](https://image.cubox.pro/cardImg/22x22j45coftdsf0p5h8o9ohmbwjx9izsrxzz2p3y92p1p2q4f?imageMogr2/quality/90/ignore-error/1)

Where does your company fall on the AI Transformation Model?

Most companies are stuck using AI as a thinking tool---helpful for individuals, but disconnected from how teams actually work. The AI Transformation Model maps the path from standalone chatbots to fully orchestrated AI operations, with measurable value unlocked at each stage.

Assess where you are and what comes next.

[Take assessment](https://notion.notion.site/official-the-ai-transformation-model)

> What if instead of us working for technology, AI actually did all of your execution work for you?
![](https://cubox.pro/c/filters:no_upscale()?imageUrl=https%3A%2F%2Fwww.notion.com%2F_next%2Fimage%3Furl%3Dhttps%253A%252F%252Fimages.ctfassets.net%252Fspoqsaf9291f%252F2XZ8zPpqceNwsE54czlQUV%252Fd34957513396327a2a0c8cf39b7c6ffd%252FDaniel-Gilbert_website_Brainlabs.png%26w%3D96%26q%3D75&valid=true)
Dan Gilbert

Global CEO, Brainlabs

<br />

## Laying the foundation for AI

<br />

About nine months ago, Dan saw where AI and agents were heading, and made a call: Brainlabs needed an AI foundation. A **single operating layer** where work gets created, captured, and executed.

Two wrong moves were obvious immediately.

The first: **Don't go native on a single LLM**. They're all changing too fast, each better at different things. Betting the company's infrastructure on one model would be like building an entire media strategy around one channel.

The second was subtler, and most of the industry fell for it: **AI as decoration**. Gemini in your email. Copilot in your slides. "Powered by AI" stamped on everything, whether it meant anything or not. AI can't be a bolt-on. You can't spin up an agent and expect it to fix everything. It has to be woven into how you build and operate---day to day. "We needed a home for AI," says Dan. "A foundation where AI infrastructure can live, that works at scale."

Brainlabs chose Notion. Not just as a wiki or a project tracker---as the context layer for the whole company. The connective tissue between thinking and doing. Notion, Dan says, turned out to be "[miracle material](https://www.notion.com/blog/steam-steel-and-infinite-minds-ai)"---the layer that finally made technology work for *them*, not the other way around.

![](https://image.cubox.pro/cardImg/3i907b549fz9phaqik4x4brftsvzt8y2mo41qdxtnwa5ul2lad?imageMogr2/quality/90/ignore-error/1)

Why context matters

A developer's context is clean---the terminal knows exactly what it's working on. A knowledge worker's is messier: Meetings, Slack threads, email chains, voice notes, and multiple tools all claiming to be the source of truth.

Agents can't operate on fragmented context. They need one layer where that messiness gets structured into something they can act on.

For Brainlabs, **Notion is that layer**---where ideas take shape, decisions get made, and tasks get assigned. The closer agents live to where work actually happens, the better they perform.

> Notion is our AI layer because it's where work is created or imagined---and we want our agents as close to the action as possible.
![](https://cubox.pro/c/filters:no_upscale()?imageUrl=https%3A%2F%2Fwww.notion.com%2F_next%2Fimage%3Furl%3Dhttps%253A%252F%252Fimages.ctfassets.net%252Fspoqsaf9291f%252F2XZ8zPpqceNwsE54czlQUV%252Fd34957513396327a2a0c8cf39b7c6ffd%252FDaniel-Gilbert_website_Brainlabs.png%26w%3D96%26q%3D75&valid=true)
Dan Gilbert

Global CEO, Brainlabs

<br />

## The "Get Stuff Done" factory

<br />

What Brainlabs is building is called **Get Stuff Done:** a "factory" of Notion [Custom Agents](https://www.notion.com/product/agents) that watches for action items across the organization and starts processing them automatically.

Here's what it looks like in practice:

A meeting ends. Twelve action items surface. Normally, five of them sit in someone's notes. Three get chased. Two get done.

With Get Stuff Done, a Custom Agent picks up every action item, creates a new task in a Notion database, assigns it to the right owner, and starts working on the ones that can be automated. The tasks don't move to a to-do list. They move to *done*.

Create a Slack channel for the new client? *Done* . Schedule a weekly sync in the calendar? *Done.* Draft a competitor analysis using Brainlabs' own research frameworks? *Done.*

Behind the scenes, four layers of automation handle the work:

1. Notion-native tasks (change an icon, update a database field) are actioned by a Notion Custom Agent.

2. [Notion Workers](https://github.com/makenotion/workers-template) handle tasks that need integrations with other platforms, such as creating a Slack channel, scheduling a Google Meet, or spinning up a project folder. They connect through an API to get it done, end-to-end.

3. More complex tasks get routed to Custom Agents that read from a library of Brainlabs-specific [Skills](https://www.notion.com/help/skills-for-notion-agent)---instructions trained on the company's data, tone, and frameworks. The agent selects the best LLM for the job, picks up the Skill, and completes the task.

4. Some tasks need humans in the loop. For those, team members work with Claude and the relevant Notion Skill to complete them---and Notion Workers pipe the result straight back into the task database, closing the loop and marking it *Done.*

The mental model is simple: input → factory manager agent → right level of automation → output. No chasing. No "I'll action that after the next meeting." Just execution.

<br />

![](https://cubox.pro/c/filters:no_upscale()?imageUrl=https%3A%2F%2Fwww.notion.com%2F_next%2Fimage%3Furl%3Dhttps%253A%252F%252Fimg.youtube.com%252Fvi%252FE6GtBUanWyQ%252Fmaxresdefault.jpg%26w%3D3840%26q%3D100&valid=true)

![](https://image.cubox.pro/cardImg/60zqb1rt27kx8unov8alc6ysxrynf2e5vqbrhy6favl7airne7?imageMogr2/quality/90/ignore-error/1)

What's the first thing you automated?

"Changing the icon on a Notion page. It sounds trivial. But watching that happen automatically---watching a task move from *Not Started* to *Done* without a human touching it---that was the moment I knew we were building something real."

<br />

## From doing less to doing better

<br />

Brainlabs' head of design built the company's entire brand design Skill in Notion. She's never written a line of code. When it worked, her reaction was immediate: *"I never have to build decks anymore."*

That reaction says everything. This isn't really about tasks or agents or automation layers. It's about giving people back time---time to do the work that actually matters, instead of the administrative tax they pay on the gap between thinking and doing.

Across Brainlabs, the word being used most isn't efficiency. It's *judgment*---the human capacity to make decisions, read a room, and apply context that no agent can fully replicate. That's what gets freed up when the coordination layer is automated.

Dan's ideal workday now? Strategy sessions. Client conversations. Teaching his team. The execution? Delegated to agents that never sleep. The emotional payoff, he says, wasn't efficiency metrics or time-to-completion dashboards. It was something simpler.

Beautiful days.

The question he'd leave you with: **What would your team do with an extra five to ten hours a week if the friction disappeared?**

Don't answer it as a thought experiment. Start building.

![](https://cubox.pro/c/filters:no_upscale()?imageUrl=https%3A%2F%2Fimages.ctfassets.net%2Fspoqsaf9291f%2FR3VnCYSRFuzzC06hc5qUP%2Fb08cc1ace428210f381c30a323a5855b%2Fezgif-44d923089de5e944.gif&valid=true)

> I started having days---genuinely beautiful days---where the gap between deciding something and it being done was measured in minutes, not weeks.
![](https://cubox.pro/c/filters:no_upscale()?imageUrl=https%3A%2F%2Fwww.notion.com%2F_next%2Fimage%3Furl%3Dhttps%253A%252F%252Fimages.ctfassets.net%252Fspoqsaf9291f%252F2XZ8zPpqceNwsE54czlQUV%252Fd34957513396327a2a0c8cf39b7c6ffd%252FDaniel-Gilbert_website_Brainlabs.png%26w%3D96%26q%3D75&valid=true)
Dan Gilbert

Global CEO, Brainlabs

*** ** * ** ***

*Dan Gilbert is Global CEO of* [Brainlabs](https://www.brainlabsdigital.com/)*, a global media agency powered by data and technology.*

[Read in Cubox](https://cubox.pro/web/card/7441756327673597374)
