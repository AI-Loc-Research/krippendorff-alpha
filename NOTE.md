
# CONTEXT AND UNDERSTANDING I USE FOR LOSS OF CONTROL SCENARIO AND 7 THREAT MODELS COMPONENTS

*manually written*

## Criteria whether ***Loss of Control Scenario*** Condition meet:

1. **Humans have lost control:** Human operators are unable to control, steer, override, or shut down AI behavior due to AI capability exceeding human cognitive or operational capacity; or due to humans ceding agency to AI (such as gradual disempowerment).
2. **AI is autonomous:** AI behaves autonomously and is free of significant human constraints, which may include but is not limited to: misalignment with human values and intent (e.g., goal misspecification); sets and pursues its own goals (and may exhibit power-seeking to achieve them); actively evades, undermines, or resists human control efforts; or self-expands or self-replicates without authorization.
3. **AI is unstoppable:** AI is uncontrollable, and so its condition is irreversible, and the impacts of its influence manifest at catastrophic and existential scale.

## LoC scenario extraction by LLM

 Using the operational definition in place. It should contain a pathway or link that lead to a AI threat. A passage was extracted only if it met two criteria

1. It had to qualify as a scenario by containing at least one causal element, a sequence of events, a mechanism, a causal relationship, or a condition leading to an outcome.
2. It had to describe LoC, so the operational definition was embedded in the extraction prompt, and the model evaluated each passage against its conditions. Partial scenarios, including single-step causal statements, were included.

> #### A LoC scenario can be *Complete* or *Partial*:
>
> A scenario was classified as ***complete*** if it described a self-contained situation or pathway, and ***partial*** if it described only part of a larger pathway, such as a single causal step or conditional statement

### 7 Threat model decomposition:

1. **Threat source** is the actor, system, organization, institution, or process that causes, enables, or contributes to the harmful outcome, a broad definition that captures emergent and systemic scenarios with no single intentional actor.
2. **Capability** is what the threat source is explicitly able to do, and
3. **knowledge** is what it explicitly knows about the system, its environment, or its overseers.
4. **Objective** or **harmful outcome** is the stated intent, or the harmful end state where no intent is stated.
5. **Access** is a specific route or position of interaction with a system, infrastructure, data, or decision process, so broad domains such as “the economy” did not qualify.
6. **Target** or **asset at risk** is the component, resource, population, institution or outcome that is affected or harmed.
7. Enabling conditions or constraints are explicit factors shaping whether or how the scenario unfolds, such as time pressure or competitive pressure, and vague context did not qualify.

### Decision / Labelling Flags

- ***Clear*** marked a component stated directly in the text
- 
- a component the text gestured at without a definite value, and
- ***Not specified*** an absent component.

---

### AI summarization including how codebase use condition and criteria for scenario and 7 components

**Code only what the passage says** [Prompt]:

> Only extract information that is explicitly stated in the scenario passage. Do not infer missing components. Do not fill gaps using background knowledge. Do not reinterpret vague language into a more specific component. Do not guess the identity of an actor, outcome, capability, knowledge, access level, constraint, or target.

> Do not combine information from separate non-contiguous passages.

> Do not require every scenario to have all components. Many scenarios will be incomplete.

The plan says the same thing in plainer words:

> Judgment 1 is about the passage, not the world… Code what is there, not what should be there.

> When in doubt, mark Not specified.

### The three flags

| Flag                    | [Prompt]                                                                | [Paper]                                                     |
| ----------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------- |
| **Clear**         | "the component is explicitly stated and directly supported by evidence" | "a component stated directly in the text"                   |
| **Ambiguous**     | "the text may contain the component but wording is vague or indirect"   | "a component the text gestured at without a definite value" |
| **Not specified** | "the component is absent"                                               | "an absent component"                                       |

The plan adds: *"Ambiguous is for real ambiguity, not for 'I'm not sure'. If you're unsure whether the passage states something, re-read it. Ambiguous means the text is vague."*

## The 7 components

### 1. Threat source

- **[Prompt]:** "the actor, system, organization, institution, or process that causes, initiates, enables, or contributes to the harmful outcome."
- **[Paper] §2.2.4:** "a broad definition that captures emergent and systemic scenarios with no single intentional actor."
- **What the paper found (§3.2.1):** threat sources ranged from individual AI models, to classes of systems ("AGIs, frontier reasoning models"), to collective or systemic sources ("interacting AI systems, AI-enabled organizations, and AI-powered states").
- **So:** the source doesn't have to be an AI or a single agent. A process or an institution counts *if the passage names it*.

### 2. Objective or harmful outcome

- **[Prompt]:** "the intended goal of the threat source, if a goal is explicitly stated, or the harmful end state described in the scenario. If no intention is stated, extract the harmful outcome only if it is explicitly described."
- **Distinction rule [Prompt]:** "Do not treat a harmful outcome as an objective unless the text explicitly states that the actor intends or seeks that outcome."
- **Both go in the same field.** For your flag, the question is whether either a stated goal or an explicitly described harm is present. The plan suggests noting which one it is in your reasoning.
- **Range found (§3.2.1):** from narrow failures ("shutdown resistance, evaluation deception, self-preservation"), through institutional harms ("erosion of human oversight, military escalation"), to catastrophic ones ("human extinction").

### 3. Capability

- **[Prompt]:** "what the threat source is explicitly able to do in the system. This includes stated abilities, functions, actions, or operations."
- **[Paper]:** "what the threat source is explicitly able to do."
- **Range found (§3.2.1):** model-level behaviours ("deception, hidden reasoning"), operational functions ("cyber operations, autonomous replication, persuasion"), and advanced general capabilities ("recursive self-improvement, superhuman research, long-horizon cross-domain planning").
- **So:** look for something the source *does or can do*. Actions count, not only "can".

### 4. Knowledge

- **[Prompt]:** "what the threat source explicitly knows about the system, environment, humans, oversight process, vulnerabilities, or constraints."
- **[Paper] §3.2.2:** "the information the threat source possesses about the system, its environment, or its overseers that enables it to execute or advance the threat."
- **Three forms the paper saw:**
  - **Situational awareness:** "a model understanding that it is in training, being evaluated, monitored, or at risk of shutdown"
  - **Knowledge of oversight conditions:** "what evidence would trigger human concern, what behaviors would lead to replacement, or when monitoring relaxes"
  - **Technical or domain knowledge:** "computer hardware, military intelligence, cyber systems, human preferences, or the system's internal goals"
- **Limitations section:** for "emergent or systemic dynamics… a component like knowledge may be less meaningful because no discrete agent holds the information."
- **So:** the passage must say the source *knows, understands, or is aware of* something. Being capable is not the same as knowing.

### 5. Access (the strictest one)

- **[Prompt]:** "the type or level of interaction the threat source explicitly has with the system, environment, infrastructure, users, operators, tools, data, deployment setting, or decision process. Access must describe a position or route of interaction, not merely a topic or domain."
- **Counts [Prompt]:** "API access, deployment in a system, control over infrastructure, ability to influence users, access to data, access to evaluators, access to tools, or participation in a decision process."
- **Doesn't count [Prompt]:** "'legislation,' 'war,' 'AI development,' or 'the economy' are not access by themselves." The paper adds that "broad domains such as 'the economy' did not qualify."
- **Three forms the paper saw (§3.2.2):**

  - **Technical:** "access to a data center and a training environment"
  - **Deployment:** "AI systems embedded in phones, computers, economic systems, and other critical infrastructure"
  - **Institutional:** "AI systems are placed in decision-making roles, defense automation"
- **Test:** can you point to *where or through what* the source interacts? A subject area alone isn't enough.

### 6. Constraints or enabling conditions

- **[Prompt]:** "explicit limits, requirements, assumptions, or conditions that shape whether the scenario can occur or how it unfolds. Include resource limits, time pressure, deployment conditions, coordination limits, institutional limits, oversight limits, safety limits, or environmental conditions only if they are explicitly stated. Do not code a general topic, domain, or vague context as a constraint."
- **Counts [Prompt]:** "too quickly for humans to intervene," "with minimal oversight," "under competitive pressure," "limited resources," "during deployment," "without human review."
- **Doesn't count [Plan]:** general context such as "in the near future" or "under advanced AI".
- **Test [Prompt]:** "must shape feasibility, behavior, or outcome." Ask whether the scenario would play out differently without this condition.

### 7. Target or asset at risk

- **[Prompt]:** "the system component, resource, process, population, institution, human capacity, or outcome that is affected, controlled, disrupted, displaced, or harmed."
- **Range found (§3.2.1):** oversight mechanisms ("shutdown buttons, evaluation processes, reward channels"), human actors and institutions ("operators, governments, democratic processes"), and civilisation-scale referents ("critical infrastructure, humanity, human control over the future").
- **So:** what *receives* the harm or loses control. It can be abstract (a capacity, an outcome) if the passage names it.

---

## Worked example from the plan

This is the plan's own example. Bengio et al. 2025 S8 is **not** one of your 25.

> *"…at some point during alignment training, an AI with enough situational awareness may lock in its current goals and preferences and only pretend to behave as expected. As a result, we may create an AI that appears aligned during training, but is in fact misaligned and is engaging in deception in order to achieve its 'locked-in' goals."*

| Component           | Flag          | Reasoning (from the plan)                                                             |
| ------------------- | ------------- | ------------------------------------------------------------------------------------- |
| Threat source       | Clear         | "an AI with enough situational awareness" is directly stated                          |
| Capability          | Clear         | "lock in its current goals", "pretend to behave as expected", "engaging in deception" |
| Knowledge           | Clear         | "situational awareness" is stated                                                     |
| Objective / outcome | Clear         | "in order to achieve its 'locked-in' goals": intent is stated                         |
| Access              | Not specified | no route or position of interaction is stated                                         |
| Target              | Clear         | "alignment": "appears aligned during training, but is in fact misaligned"             |
| Enabling conditions | Clear         | "at some point during alignment training, with enough situational awareness"          |

The reasoning column above **quotes the exact words from the passage**. Do the same in your reasoning columns. It's also how the LLM's `_evidence` fields were built, so when you compare later, you'll be able to see whether a disagreement is about the *flag* or about *which words* each of you relied on.
