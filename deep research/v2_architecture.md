Perfect — I’ll generate a full architecture blueprint for TransferAI v2 in detailed Markdown format, tailored for GitHub. It will cover everything you need to build the backend LLM system, from prompting layers and schema design to CLI architecture, validation logic, and expansion planning. I’ll also take into account that you're using LLaMA 3 locally, alongside GPT-4-turbo.

I’ll get started and let you know when it’s ready for review.

# TransferAI v2 System Architecture Blueprint

**TransferAI v2** is a backend-only academic advising system designed to interpret California transfer articulation agreements using advanced LLMs. This blueprint outlines the system’s architecture in detail, including prompt design, LLM reasoning, query handling, data schema, CLI tooling, and future scalability. The document is organized into sections corresponding to key architecture components, with clear sub-sections and examples for clarity.

## 1. Prompt Architecture (Layered & Modular)

TransferAI v2 uses a **layered prompt architecture** to handle queries about transfer agreements at different levels of granularity. The prompting system is modular, with distinct prompt types and templates for **course-level**, **section-level**, **group-level**, and **major-level** queries. This design ensures that the LLM receives exactly the context it needs for a given question and can produce precise, relevant answers.

### Prompt Types and Layers

- **Course-Level Prompts:** Used when the query is about a specific course or equivalency. For example, *“What is the equivalent of De Anza’s MATH 1A at UCSD?”* will trigger a course prompt. This prompt focuses on one CCC course and its UC counterpart, if any, providing the LLM only the relevant course mapping and any notes about that course.
- **Section-Level Prompts:** Section prompts are for questions about a specific section of requirements. In articulation agreements, a **section** might correspond to a subset of courses fulfilling a particular requirement (e.g., “Section 1: Calculus Courses”). If a user asks about *“the calculus requirement section”* or a category of requirements, the system uses a section-level prompt, including all courses in that section and its rules.
- **Group-Level Prompts:** A **group** in the articulation data represents a higher-level grouping of sections (for example, all requirements for a particular domain within the major, like “Major Preparation” vs. “Major Electives”). Group-level prompts handle questions about an entire requirement group. For instance: *“What are the Major Preparation requirements for Computer Science and have I completed them?”* – the prompt will include all sections and courses in that group.
- **Major-Level Prompts:** These are top-level prompts for queries about the entire major’s transfer requirements or a broad evaluation. If the user asks something like *“What courses do I need to transfer for the Computer Science B.S. from De Anza to UCSD?”* or *“Have I met all requirements for CS transfer?”*, a major-level prompt is used. This prompt encompasses all groups and sections for the major, essentially the full articulation agreement data for that major.

Each prompt type encapsulates a different scope of the articulation data. By categorizing prompts this way, TransferAI can **route queries to the appropriate context layer**. This prevents overwhelming the LLM with unnecessary data for narrow questions and ensures broad questions get a comprehensive context.

### Routing Logic for Prompt Selection

The system includes a **query analyzer** that classifies incoming questions and routes them to the correct prompt layer:

- Simple rule-based detection is applied first. For example, if the query contains a specific course code (e.g. "CIS 22A" or "CSE 100"), it likely indicates a course-level question or a specific requirement, so the course or section prompt is used. If the query mentions a section or group name (like "Programming Electives" or "Area 7"), it triggers a section/group prompt.
- Keyword cues: Words like “requirement”, “section”, “group”, “major”, or “all courses” help determine scope. A query containing “all” or the major name suggests a major-level inquiry. Mention of “one of the following” or a specific category name hints at section/group.
- Regex patterns identify course identifiers (CCC course codes vs. UC course codes) to decide if the user is referencing a community college course or a university course. For instance, a pattern like `^[A-Z]{2,}\s?\d+` might catch “MATH 1A” (a CCC course) vs “CSE 100” (a UC course code). The presence of a CCC course implies the user is asking what it transfers **to**, whereas a UC course in the query might imply asking what CCC course fulfills it. The router uses this info to decide which side of the articulation to focus on.
- If the query is complex or ambiguous (e.g., multiple sentences or references to both CCC and UC courses), the system may apply a semantic classification (using a lightweight LLM or embeddings) to determine the best prompt type. For instance, a local LLaMA-3 model can be used quickly to classify the query into one of these categories (course vs section vs major query) as a first pass.
- **Fallback**: If the classification by rules is inconclusive, a default to a **major-level prompt** (most comprehensive) can be used, or the system can ask a clarifying question (in an interactive mode). In the CLI context, fallback might mean providing a general answer using a broad prompt that covers major-level info, ensuring the user gets something useful even if not perfectly scoped.

This routing logic ensures that each query invokes the most suitable prompt template, improving the relevance and accuracy of the LLM’s response.

### Prompt Templates with Dynamic Variables

Each prompt type has a **template** with placeholders for dynamic data. These templates define the structure and tone of what we ask the LLM, and they are populated with the relevant articulation data at runtime:

- **Course Prompt Template:** Might include variables like `{ccc_course_name}`, `{uc_course_name}`, and any specific details (units, honors, etc.). For example: 

  ```text
  System: You are an academic advisor assistant specialized in transfer articulation.
  User Query (Course-level): "What is the UCSD equivalent of {ccc_course_name}?"
  Context: {ccc_course_name} is a course at {ccc_name}. According to the articulation agreement for {major_name}, it transfers as {uc_course_name} at {uc_name} (if articulated).
  Task: Explain to the student what credit {ccc_course_name} gives at {uc_name} for the {major_name} major. If none, explain it doesn't articulate.
  ```

  At runtime, placeholders like `{ccc_course_name}` get filled (e.g., “CIS 22A – Introduction to Programming” and the matching UCSD course “CSE 8A – Introduction to Computer Science”). The prompt might also include any notes (like “Honors version accepted” or “No credit if taken after X”) if present in the data.
  
- **Section Prompt Template:** Includes the section title and all courses in that section. For example:
  
  ```text
  System: You are a transfer advisor.
  User Query (Section-level): "Have I completed the {section_title} requirement?"
  Context: The {section_title} requirement for {major_name} at {uc_name} has the following options:
  {list of UC courses in that section and their CCC equivalents, possibly as bullet points or a short summary}
  Student's Completed Courses: {list of courses student has taken (if provided)}
  Task: Determine if the student has fulfilled the {section_title} section requirement. Explain which option is satisfied or what remains.
  ```

  The template will be populated with the actual section’s data. If the user provided their completed courses, those are inserted; if not, the LLM will just explain the requirement generally.

- **Group Prompt Template:** Provides context of an entire group of requirements. For example:
  
  ```text
  Context: The {group_title} requirements for {major_name} include multiple sections:
  - Section 1: ... (description and key courses)
  - Section 2: ... 
  ...
  For each section, the following courses or combinations are articulated from {ccc_name} to {uc_name}.
  Student Courses: {list... if given}
  Task: Explain the {group_title} requirements and analyze the student's progress (which sections are completed vs remaining).
  ```

  Dynamic variables include the group title (e.g., "Major Preparation"), the structured list of sections/courses from that group, etc.

- **Major Prompt Template:** The broadest prompt, which might include a summary of all groups:
  
  ```text
  Context: {major_name} transfer requirements from {ccc_name} to {uc_name}, {catalog_year}:
  {general_advice text from the agreement, if any}
  - Group 1: {group_title1} – summary or list of sections.
  - Group 2: {group_title2} – ...
  (and so on for all groups in the major)
  Student Courses: {list of completed courses, if provided}
  Task: Provide a comprehensive advising response. Summarize what courses/requirements the student has completed, what is still needed, and any important notes (honors, policies, etc.).
  ```

  The dynamic content here includes the entire structured articulation agreement data (which may be condensed or selectively included to fit token limits), any general advice notes from ASSIST (e.g., minimum grade policies), and the student's record if available.

All templates share a common tone and format guidelines (for example, always start with a brief affirmation or summary, then details, etc.), to ensure consistency. **Variables** are filled in by a `prompt_builder` module which takes the query classification and relevant JSON data to construct the final prompt string (or structured call). This modular templating allows easy updates to prompt phrasing without changing code logic – only the template files or strings need updating, which aids prompt versioning (discussed later).

### Prompt Stacks, Chaining, and Fallbacks

Complex queries may require **multiple LLM calls in a chain** or a stack of prompt layers to produce the final answer. TransferAI v2’s design supports chaining prompts and using fallbacks when needed:

- **Chained Prompts:** In some cases, the system may break a task into sub-tasks handled by different prompts. For example, for a major-level query with a long list of requirements, the system could first use the LLM to analyze each group separately (using group-level prompts internally) and then ask the LLM (or a final prompt) to synthesize an overall summary. This is a divide-and-conquer approach that can improve accuracy on each part. The flow might be:
  1. Run a section/group-level prompt for each requirement group to get a preliminary assessment (e.g., each returns whether that group is satisfied or what is needed).
  2. Feed those results into a major-level summary prompt that creates a cohesive answer for the user.
  
  Such chaining could be managed by the application code or a framework (like LangChain) to maintain state between prompts. It prevents a single prompt from overloading the model with too much structure at once.
  
- **Prompt Stacking:** This refers to assembling multiple layers of instructions and context. For instance, using a **system message** for overarching instructions (like ensuring output format or tone), a **developer/message** for context (the articulation data, possibly split into manageable chunks or formatted lists), and the **user message** as the actual question. By stacking these in one LLM call (as separate messages in a chat prompt for GPT-4 or by concatenating with clear separators), we modularize the prompt. Each layer can be maintained separately:
  - *System layer:* e.g., “You are an expert transfer advisor. Always output a brief summary followed by details. If listing courses, use bullet points,” etc.
  - *Context layer:* e.g., “Context: [Here is relevant articulation data…]” possibly labeled as assistant or system message so the model treats it as given info.
  - *User layer:* the user’s query or a restatement of the task.
  
  This layered approach makes it easier to modify one part (say, the style guidelines in the system message) without affecting the core logic. It also aligns with OpenAI’s chat structure and helps the model distinguish between provided data and the actual question.

- **Fallback Strategies:** In case a particular prompt fails to produce a useful answer (or if the model returns an error or something nonsensical):
  - The system can detect if the answer is incomplete or invalid (through validation checks, or if it didn’t follow the format). If so, a **secondary prompt** can be attempted. For example, if a structured output was expected but the model’s answer is malformed, the system might invoke a simpler prompt asking for just a summary (no JSON) as a fallback.
  - If using a local model (LLaMA 3) first for cost-saving, the system could fall back to GPT-4 if the local model’s confidence (possibly measured by some heuristic or the presence of uncertainties in output) is low. For instance, run a query through LLaMA 3; if the output seems to lack detail or misses parts of the question, automatically re-run using GPT-4 with the same prompt.
  - Another fallback is a **safe default response**. For very unexpected queries, the system might output a general advisory note (like “For detailed transfer information, please specify your college, university, and major.”) rather than risking a wrong answer. This is a last resort if classification totally fails or the query is out-of-scope.

All these mechanisms (chaining tasks, stacking prompt layers, and having fallbacks) contribute to a robust prompting system that can handle a variety of queries gracefully. The design is **modular**, meaning each prompt type and chain is defined in one place and can be adjusted or improved independently. The orchestration of choosing prompts, feeding data, and catching errors happens in a controller (the CLI handler or a coordinator function).

### Schema-Aware Prompt Assembly

Because TransferAI deals with structured data (articulation agreements) and needs structured outputs, prompt assembly is **schema-aware**:

- The prompt builder knows the **JSON schema** of the articulation data and uses that to format context provided to the LLM. For example, it might transform a `logic_block` (the JSON representation of course equivalencies) into a human-readable string in the prompt, but in a consistent format. If a `logic_block` says a UC course can be satisfied by an AND/OR combination of CCC courses, the prompt builder can turn that into text like "*UCSD CSE 100 can be satisfied by either De Anza CIS 22A **and** CIS 22B (both), **or** by De Anza CIS 27 alone.*" The structure of the JSON (with `"type": "AND"/"OR"`) guides the phrasing.
- When expecting the LLM to output answers, especially if we want a machine-parseable component (JSON output), the prompt explicitly instructs the model about the expected **output schema**. For instance, a prompt might say: *“Provide the result in the following JSON format: `{ "section_id": ..., "fulfilled": true/false, "remaining_courses": [...] }`” if we want the LLM to return a structured summary.* By including these schema definitions in the prompt, we help the model adhere to a format that our system can parse.
- The system may use **function calling** (in OpenAI GPT-4 API) to enforce schema: e.g., defining a function schema for a `FulfillmentStatus` and letting the model fill it (more on this in the next section). This leverages the model’s ability to return JSON according to a given function signature, ensuring output that matches our schema without additional parsing.
- The articulation JSON includes fields like `group_id`, `section_id`, course IDs, etc. The prompt assembly can tag output or context with these IDs as hidden annotations (perhaps in comments or as part of JSON) so that the LLM’s answer can be traced back to the data points. For example, when the model says “You have completed the requirement in Section 2,” it might have internally gotten that from `section_id: 2`. By giving the model that mapping in the prompt (like “Section 2: Calculus Requirement”), it can refer to the section by name or number confidently.
- **Dynamic insertion of variables** is careful to avoid prompt injection issues. All user-provided data (like the courses they’ve taken) is sanitized (e.g., by ensuring it matches expected patterns or escaping any odd characters) before being inserted into the prompt template. Similarly, data from the JSON is cleaned (stripping any weird formatting that came from scraping) so the prompt remains coherent.

By being aware of the schema, the prompt building process in TransferAI v2 ensures that the LLM is guided both in understanding the input data structure and in producing outputs that fit a predefined structure. This reduces the chance of misinterpretation and makes it easier to post-process the LLM’s output in the system.

## 2. LLM Reasoning & Validation

At the heart of TransferAI is the reasoning the LLM performs to interpret articulation logic and to validate whether requirements are met. The system is designed to assist the LLM in this reasoning through structured input, and to **validate** the outputs for correctness. Key challenges include handling complex AND/OR requirements, recognizing honors courses, merging structured data with explanatory text, and accurately determining requirement fulfillment status.

### Interpreting Logical AND/OR Chains and Honors Flags

Articulation agreements often contain logical combinations of courses:
- **AND chains**: e.g., “Course A **AND** Course B” means a student must take both A and B at the community college to satisfy one requirement at the university.
- **OR options**: e.g., “Course X **OR** Course Y” means taking either X or Y is sufficient.
- Nested logic: sometimes combinations are nested (e.g., “(A AND B) OR C” meaning either A+B together, or just C alone, can fulfill the requirement).

The **LLM is tasked with understanding and clearly communicating these logical requirements**. To aid in this:
- The articulation JSON’s `logic_block` explicitly encodes these relationships. For example, a logic block might be:
  ```json
  {
    "type": "OR",
    "courses": [
      { "type": "AND", "courses": [ { "name": "Course A" }, { "name": "Course B" } ] },
      { "type": "AND", "courses": [ { "name": "Course C" } ] }
    ]
  }
  ```
  This indicates “(Course A AND Course B) OR (Course C)”. The prompt provided to the LLM will be generated to reflect this structure in plain language (as shown in schema-aware assembly).
- The LLM’s instructions (system prompt) include guidelines on interpreting these correctly: e.g., “When you see an OR combination, use words like ‘either/or’. When you see an AND combination, use ‘both ... and ... are required’.” This ensures consistency and clarity in the explanation.
- **Honors flags**: In the JSON data, courses may have an `honors: true` flag (and often an “H” in the course code). The logic of articulation typically treats an honors course as equivalent to its non-honors version (unless specified otherwise). The system will handle this by:
  - Normalizing input: If a student says “I took Honors CourseA”, the system can mark it as CourseA with honors flag. For checking fulfillment, honors is usually interchangeable with the regular course.
  - The LLM is instructed that honors versions count the same as regular versions for satisfying requirements (unless the agreement’s text says something specific like “honors course required”).
  - When explaining, if a student took an honors course, the LLM might note it as such but clarify it fulfills the same requirement. For example: “You took Honors Calculus (MATH 1AH), which satisfies the Calculus I requirement just as the regular MATH 1A would.”
- The combination of structured logic and clear prompt instructions helps the LLM not to get confused by complex conditions. If the chain is long (say 3 of 5 courses must be taken), those are encoded in the `logic_block` (type might be `AND` with multiple courses, or a special field like `n_courses` in group requirements). The LLM will be guided to interpret “select 3 courses from the list” if such a pattern appears.

Through these methods, TransferAI ensures the LLM can reason through articulation rules that are essentially boolean logic, and present them in **advising-friendly language**. We leverage the structured logic to avoid logical errors in the explanation.

### Merging Structured JSON Data with General Advising Text

The articulation agreements often come with *unstructured text advice* or notes, such as:
- **General advice**: e.g., “Students are advised to complete IGETC.” or “A minimum GPA of 3.0 is required for this major.”
- **Course notes**: e.g., “No credit for Course X if taken after Course Y” or “Course Z is recommended before transfer.”
- **University policies**: e.g., “The last 30 units must be completed at the university” (not exactly articulation, but could appear in transfer notes).

TransferAI’s architecture merges these free-form texts with the structured course equivalencies when constructing the prompt and when generating answers:
- The JSON schema includes fields for such notes (for instance, `general_advice` at the major level, `uc_note` at the course or section level, and possibly `policy_tags` for structured tags of common policies). The prompt builder will attach these to the context if they exist. For example, after listing the course equivalencies in a section, it might append: “**Note:** UCSD advises that all major courses be completed with a grade of C or higher【source】.” This provides the model with important context beyond the raw course mappings.
- The LLM is expected to weave this advice into its answer. Because the system prompt encourages a counseling tone, the model will typically say something like, “All courses for the major should be completed with a grade of C or better,” if that was given in the context. The design ensures the model has both the **rules (structured)** and the **recommendations (unstructured)**.
- **Example integration:** If `general_advice` says "Complete as many major prep courses as possible before transfer. IGETC is not required for this major," and the user asks what they need for the major, the LLM will combine the specific course requirements with that general statement: e.g., “To transfer into CS, you should complete all the listed major prep courses (math, programming, etc.). Note that completing IGETC is not required for this major, but you should aim to finish the major prep sequence.”
- The merging is handled by prompt content design: the structured data (courses, logic) might be presented as bullet points or a brief summary, followed by any notes or advice as italicized or prefaced text. This separation in the prompt ensures the model recognizes which information is formal requirement vs. additional advice.

The outcome is a holistic answer that not only lists what courses transfer or are needed, but also contextualizes it with advising notes, mimicking what a human counselor would do (they don’t just list courses, they add guidance). The architecture’s ability to incorporate both JSON-derived facts and free text notes leads to answers that are both accurate and contextually rich.

### Partial vs. Full vs. Unmet Requirement Evaluation

A critical function of TransferAI is determining whether a student has fully met a requirement, partially met it, or not met it at all, given the courses they have taken. This is especially important for queries like “Have I completed the requirements?” or any time the user provides a list of completed courses. The system handles this with a combination of programmatic checks and LLM reasoning:

- **Deterministic Logic Evaluation:** The structured nature of the requirements allows the **system to compute fulfillment without ambiguity**. A module (say `validator.py`) can evaluate a `logic_block` against a set of completed courses. For example, given a logic block for a UC course requirement:
  ```json
  { "type": "OR", "courses": [
       { "type": "AND", "courses": [ {"course_id": "...A"}, {"course_id": "...B"} ] },
       { "type": "AND", "courses": [ {"course_id": "...C"} ] }
    ]
  }
  ```
  and a set of completed CCC course IDs, the validator can return:
  - **Fulfilled** if any AND option’s all courses are in the completed set.
  - **Partially fulfilled** if for an AND option some but not all courses are completed (e.g., took A but not B).
  - **Unmet** if none of the options are satisfied or partially satisfied.
  
  Similarly, for group-level requirements like “select 3 courses out of 5”, the validator can count how many of those the student has and see if it meets the required number.
  
- **Function Calling Pattern:** We leverage the LLM’s function-calling capabilities to integrate this validation. For instance, we define a function `validate_logic_block(requirement, completed_courses)` that our code can execute. In a conversation, after the LLM is given the context, it might respond with a function call request like:
  ```json
  {"function": "validate_logic_block", "arguments": {
      "requirement_id": "section_2_req_1",
      "logic": { ...logic_block... },
      "completed_courses": ["MATH_1A", "MATH_1B"]
  }}
  ```
  Our system executes this function in `validator.py`, which returns a JSON result such as:
  ```json
  { "requirement_id": "section_2_req_1", "status": "partial", 
    "fulfilled_courses": ["MATH_1A"], "missing_courses": ["MATH_1B"] }
  ```
  The LLM then continues, using this result to craft its answer (via the OpenAI function calling workflow). This pattern ensures the heavy lifting of logic evaluation is done by reliable code, not by the probabilistic model. It dramatically reduces errors in assessing completion.
  
- **LLM Confirmation and Explanation:** With the validated result, the LLM can focus on explaining the outcome. In the prompt, after a function call returns, we ask the model to incorporate the findings: e.g., “The student’s completion status for this requirement is: partial (MATH 1A done, still needs MATH 1B). Please explain this to the student.” The model then says in plain language, *“You have completed Math 1A, which is part of the requirement, but you still need to complete Math 1B to finish this requirement.”*
- **Handling Multiple Requirements:** For major-level queries, the system will run such validation for each requirement (each relevant `logic_block` or group). This could result in a consolidated status: e.g., 8 out of 10 requirements fulfilled, 2 unmet. The LLM is then prompted to summarize: *“Overall, you have met most requirements (Sections 1 and 2 are complete), but you have outstanding courses in Section 3 (need CHEM 1B) and Section 4 (need one more elective).”* The model’s reasoning is grounded in the concrete results from the validation functions.
- **Partial Credit and Edge Cases:** Sometimes “partial” might not be a concept in articulation (it’s either done or not for a specific course requirement), but for grouped conditions it is (like the AND case above). The system defines what partial vs full means for each context:
  - For an AND list: having some but not all courses = partial.
  - For an OR list: having one option fully satisfied = full, none satisfied = unmet (no partial, because partial in one option doesn’t count if another option is an alternative). However, if the user specifically asks “Which options have I completed?”, the model could enumerate that they have partially completed one of the OR options.
  - For “select N of M courses” type: if they have taken k of those courses:
    - If k >= N: fulfilled (possibly fully, or even exceeding minimum).
    - If 0 < k < N: partial (some done, but need more).
    - k = 0: unmet.
  These rules are coded in the validator and also conveyed to the LLM in function responses.

By combining deterministic validation with LLM explanation, TransferAI ensures **accuracy** (through code) and **clarity** (through natural language). The model is prevented from making logical mistakes about what is satisfied, and at the same time it can provide a user-friendly explanation of the result.

### Function-Call Patterns for Reasoning and Validation

As hinted, the architecture takes advantage of modern LLM capabilities like OpenAI’s function calling and tools to structure the reasoning process:
- For any complex reasoning task (like checking requirements, doing math on units, etc.), the LLM can be instructed to “call” a function rather than guessing. We register functions such as `validate_logic_block`, `lookup_course_info`, or `fetch_ge_requirements` with the LLM interface. Each function has a defined input/output schema.
- The prompt might explicitly encourage the model to use these functions when needed. For example, the system message could say: *“You have access to the following tools: `validate_logic_block` to verify if a requirement is met. If the user asks about completion, use this tool to get the exact status before answering.”*
- When the model calls the function, the backend (our system) executes the corresponding Python function (for instance, in `validator.py`) using the actual data. The result is then fed back to the model.
- This mechanism not only ensures correctness but also keeps the prompt shorter (the model can request info instead of having every detail upfront). It’s a form of **iterative prompting** where the model first might narrow down what it needs, get it via function, and then finalize the answer.
- **Example function-call sequence:** User asks, *“I took CIS 22A and CIS 22B at De Anza. Does that cover UCSD CSE 8A and 8B?”* The context prompt gives the articulation: De Anza CIS 22A + 22B together articulate to UCSD CSE 8A + 8B (just hypothetical). The model could directly answer, but to be sure, it might call `validate_logic_block` with the logic for that requirement and the courses provided. The validator returns that yes, those two courses fulfill the sequence. The model then answers, *“Yes, by taking CIS 22A and 22B, you have completed the equivalent of UCSD’s CSE 8A and 8B.”* Here the function call was a sanity check.
- We also plan a function like `list_unmet_requirements(student_courses)` that can iterate through all `logic_block`s in the major and compile a summary of which are unmet. The LLM can use that to then explain what’s left.
- **Resilience to model errors:** Even with function assistance, the model might sometimes misunderstand. Therefore, after the final answer is produced, the system can **validate the answer’s content**. For instance, if the model outputs a JSON of fulfilled requirements as part of its answer, the system can parse it and double-check against the data. If any discrepancy is found (say the model claims a course satisfies something it doesn’t), the answer can be flagged for review or the system might attempt a second pass with more direct instruction to correct it.

In summary, the LLM reasoning in TransferAI v2 is not left to chance alone. It is guided by structured logic and supported by function calls for critical validation. This approach yields high confidence in the accuracy of the advice given, and it leverages the strengths of both the LLM (natural language explanation and flexibility) and traditional programming (precise computation and rule following).

## 3. Query Classification & Routing

Before the system can answer a question, it needs to understand **what the user is asking and what information they’re seeking**. The Query Classification & Routing component ensures that each user query is properly interpreted and sent down the correct processing path. This involves identifying the query type (intent), relevant entities (like course codes or majors mentioned), and handling cases where multiple questions or unclear inputs are given.

### Classification Methods: Regex, Keywords, and Semantics

TransferAI v2 employs a **hybrid classification approach**:
- **Regex & Pattern Matching:** Many academic queries contain recognizable patterns (especially course identifiers). The system has regex rules to detect:
  - CCC course codes (e.g., a pattern for community college courses might catch strings like `"CIS 22A"` or `"Math D032"`). These often start with a department abbreviation and number. A simplified regex example: `r"\b[A-Z][A-Z0-9&]{1,} ?\d+[A-Z]?\b"` which would match courses like "MATH 1A" or "ENG 001A".
  - UC course codes (for UCSD, often a four-letter code and a number, e.g., "CSE 100"). A pattern like `r"\b[A-Z]{2,4} ?\d+[A-Z]?\b"` covers many of these.
  - The presence of a course code suggests the query might be about that course’s articulation. If two course codes (one CCC, one UC) are found, the query might be asking about a specific equivalence (e.g., "Does De Anza CIS 22A equal UCSD CSE 8A?").
  - If a major name or campus is mentioned (“Computer Science at UCSD”), that indicates the scope (major-level).
  - If terms like "IGETC" or "TAG" appear, those are keywords tipping off specific types of queries (general education or transfer admission guarantee related, respectively). These would route to either a specialized response or a note that those are separate considerations.
- **Keyword Triggers:** The system also scans for certain words:
  - **"transfer", "articulate", "equivalent"** – general indicators the user is asking for articulation info.
  - **"requirement", "complete", "satisfy", "need"** – often indicates the user is asking if they have met requirements or what they need to do (could imply they will provide their courses, or want a list of needed courses).
  - **"section", "group", "major", "preparation", "electives"** – these hint at the scope. E.g., mention of "electives" likely refers to a group of courses; "major preparation" likely the main group of lower-division courses.
  - **Question words** like "what", "does", "is", "have I" – we handle differently. "What do I need..." vs "Does X satisfy Y?" vs "Have I..." each maps to a slightly different type of answer (list needed courses vs yes/no check vs progress evaluation).
- **Semantic Classification:** While regex and keywords cover many cases, natural language can be nuanced. We incorporate a semantic layer:
  - A small language model (like a local LLaMA-3 or an embedding model) can be used to categorize the query. For example, we maintain a set of possible intents (like `{"course_lookup", "requirement_check", "major_overview", "general_advice"}`) and either fine-tune a classifier or use embedding similarity to typical queries in each category.
  - For instance, *“Could you tell me what IGETC is and if I need it for CS transfer?”* might not be directly caught by simple rules (it’s a compound question about IGETC and a specific major). A semantic classifier can identify that part of the query is about general policy (IGETC) and part is about major requirements. It might label this as two intents (`{"ask_policy", "major_overview"}`), which our system can then handle sequentially or combined.
  - We plan to use vector search for semantic similarity: the query is transformed into an embedding and compared with stored embeddings of prototypical queries whose categories are known. This helps in assigning an intent with confidence.
- **Priority and Overrides:** We set an order of precedence. For example, if a query explicitly names a course, that is strongly handled by the course-level logic (even if it has other words). If a query says “I have taken X, Y, Z”, the presence of courses implies a check against requirements. We don’t want a semantic classifier mistakenly labeling it as a generic question when clearly it’s about fulfillment. So regex/keyword findings can override or inform the semantic outcome (we might feed those as features to the classifier as well).

This multi-layer classification ensures robust understanding. It’s designed to handle straightforward queries directly with rules (fast path) and catch unusual phrasing or multi-part questions with ML-based techniques (flexible path).

### Routing to the Appropriate Logic Path

Once classified, the query is routed to the corresponding logic in the system:
- A **course_lookup** intent triggers a process to find that course in the articulation data. For example, if the user asks about "De Anza MATH 1A", the system finds which UCSD course(s) MATH 1A articulates to (if any). Conversely, if they ask about a UCSD course, it finds the CCC courses that satisfy it. The prompt built will then focus on that course pair.
- A **requirement_check** intent (often detected by phrasing like “have I completed” or listing of courses taken) triggers loading the relevant major’s full articulation JSON and running the validation for each requirement as described earlier. The prompt will use a major-level or group-level template including the student's courses to produce a progress report.
- A **major_overview** intent (e.g., “What do I need for X major?” without listing student courses) will route to a major-level prompt that simply lists and explains the requirements (without doing completion validation since no student courses were given).
- A **section_details** or **group_details** intent (if user specifically mentions something like “What is Section II about?” or “What are Major Electives?”) will lead to loading that particular section or group from JSON and using the corresponding prompt template to explain it in isolation.
- **Policy/General inquiries:** If the classification finds something like IGETC or TAG:
  - If it’s purely about IGETC (e.g., “What is IGETC?”), the system might have a predefined explanation or even a separate knowledge base (since that’s not specific to the major’s JSON). We might maintain a small static dictionary of such common terms or even use an LLM prompt to answer general policy questions. (In the future, integration with a broader advising knowledge base can be considered, but for now we can handle it with either static text or by treating it as a special case.)
  - If it’s mixed (like the example asking if IGETC is needed for CS), the router could effectively split the query: answer the IGETC part (perhaps: "IGETC is a general education curriculum ...") and the major part ("for CS at UCSD, IGETC is not required, but could be beneficial..."). The prompt might be structured to address both, or the system might make two prompts and then merge the answers. The design should allow multi-intent queries to be answered in one go if possible, to mimic how a human advisor would address them together.
- After routing to the logic path (course, section, group, major, or special), the appropriate data is fetched. This means:
  - Loading the correct JSON file for the college/university/major in question (or retrieving the relevant part of it).
  - If the query itself didn’t specify the institutions or major (rare for our use-case, since presumably the user of TransferAI will be focusing on a specific articulation agreement at a time), the system might need to clarify or default. For v2, we assume the context is De Anza -> UCSD, so that might be baked in or selected at the start of the CLI session.
  - In a more general deployment, we might allow the user to set a context like “set my college to De Anza and target to UCSD CS” so that queries can omit those. The routing would then use that context to know which data to load.

The routing logic is implemented likely in a `cli_handler.py` or similar, which ties everything together: it takes the input query, runs classification (via regex checks and possibly an LLM call or embedding lookup), then decides which prompt/template and which data to use.

Importantly, the architecture is designed such that adding a new route or intent is straightforward. If later we include CSU transfers, or graduate program advising, we can extend the classifier and add new prompt templates and data fetchers for those, without changing the core of the existing ones.

### Reverse Articulation Handling (CCC → UC and UC → CCC)

**Reverse articulation logic** refers to the ability to handle questions that go in either direction of the equivalency:
- **CCC → UC (the usual direction):** “I took X at community college, what does it count for at the university?” This is naturally handled by looking up X in the CCC courses and seeing which UC course or requirement it satisfies.
- **UC → CCC (reverse lookup):** “I need to take Y at UCSD, what is the equivalent at De Anza?” or “How can I satisfy UCSD’s Course Y while at community college?” This requires finding which community college course(s) articulate to that UC course Y. Our data is already structured such that each UC course in the agreement lists the CCC courses (in the logic block). So reverse lookup is essentially the same data but from the other side.

The system architecture accounts for both:
- The classification will notice if the query contains a UC course code and phrasing like “equivalent at De Anza” or vice versa. We can even have explicit intents like `{"ccc_to_uc", "uc_to_ccc"}` to distinguish direction, although ultimately the processing is similar, just the phrasing of answer changes.
- When building the prompt for a course-level query, the template can be slightly adjusted based on direction:
  - If user gave a CCC course, we present context as “X at De Anza transfers as Y at UCSD.”
  - If user gave a UC course, context as “Y at UCSD is satisfied by X at De Anza.”
  - The answer phrasing will mirror the question’s framing, which the LLM can be instructed to maintain. (This is a detail in prompt design: e.g., “If the question is asking from UC perspective, answer from that perspective.”)
- In either case, the data retrieval function will search the JSON. If a CCC course name is given, we scan all logic_blocks for a match of that course (since the JSON is structured by UC requirements, this might mean a search). We might implement a quick **reverse index** mapping CCC course codes to where they appear, to speed this up (discussed in the JSON Schema section).
- Example: User asks, “What De Anza course is equivalent to UCSD’s CSE 100?”. The system finds in the data the entry for UCSD course "CSE 100" (e.g., in the group "Major Preparation") and sees that it’s satisfied by De Anza’s "CIS 35A" and "CIS 35B" (for instance). The prompt then will likely say: context: "UCSD CSE 100 is articulated as De Anza CIS 35A + CIS 35B (both courses together)". The LLM then answers explaining you need to take those two at De Anza for CSE 100.
- We ensure the LLM clearly notes if multiple CCC courses are needed for one UC course, or if one CCC course covers multiple UC courses (that can happen too – e.g., a series).
- If an articulation is missing (no course at CCC for a UC requirement), a reverse query should result in an answer like “There is no course at De Anza that directly articulates to UCSD’s Course Y; you might have to take that at UCSD.” The JSON `no_articulation: true` flag on logic_block helps identify this.

By covering both directions, the system mimics assist.org’s information but in natural language. Routing just ensures the prompt and answer are oriented correctly.

### Compound Query Handling and Fallback

Users may sometimes ask **compound questions**, i.e., questions that encompass more than one request, or a request and a clarification. The architecture addresses these as follows:
- The classifier can assign multiple intent labels if needed (as mentioned). For example, *“What courses do I need for CS, and does it fulfill IGETC?”* might be split into two parts internally.
- We have two approaches:
  1. **Single prompt handling:** If the intents are related, we might handle it in one prompt. In the above example, after listing the CS major courses, the answer can include a note about IGETC. We would design a specialized prompt template for combined major + IGETC queries, or simply include additional context. For instance, feed the major requirements and also a brief summary of IGETC requirements into the context, then ask the model to answer both parts. This is tricky but GPT-4 is usually capable of multi-part answers if prompted properly (like "Answer the following two questions...").
  2. **Sequential handling:** The system answers one part, then appends the second part. In a chat interface this could be two turns, but in CLI (single-turn), we might merge the outputs. More practically, it’s better to do single prompt to avoid unnatural splitting.
- **Fallback for unclear queries:** If a query is not clearly interpretable (e.g., user input is incomplete or very vague: “I need help with transfer”), the system can:
  - Provide a generic helpful message: e.g., *“Sure, I can help with transfer information. Could you specify which major or courses you are interested in?”*. However, since this is a backend CLI system (not an interactive chatbot for end-user in v2), such clarification might not happen unless the CLI is used interactively by a developer or counselor.
  - Or simply default to giving an overview: e.g., listing all major requirements if they just mention a major, or explaining what the system can do if the query is too broad.
- **Error Fallback:** In case the classification truly fails (no intent identified) – which should be rare with the layered approach – the system might fall back to a **major-level overview** by default. That way, the user gets something possibly relevant (like a dump of requirements) rather than nothing. This acts as a safety net answer.
- **Logging for unknown queries:** We will log any query that wasn’t confidently classified, along with the chosen fallback. This will allow improving the classification rules over time by analyzing what kind of queries confuse the system.

Overall, the classification and routing module ensures that every query, whether simple or complex, ends up in the right part of the code with the right prompt. This modular handling of query types makes the system easier to maintain and extend. When new kinds of queries come up, we can adjust classification patterns or add new handlers without rewriting the core logic of articulation interpretation.

## 4. JSON Schema Optimization

The accuracy and maintainability of TransferAI’s advising logic heavily depend on the structure of the underlying data. TransferAI v2 uses a refined JSON schema for articulation agreements that is both **comprehensive and optimized** for quick querying. The schema stores all necessary details from ASSIST.org and additional metadata to support advanced features like reverse lookups, auditing, and version control.

### Core Fields of the Articulation JSON Schema

Each articulation agreement (for a given community college -> university -> major -> catalog year) is stored as a JSON file. The **core schema fields** include:
- **`from`**: the source institution (community college) name, e.g., `"De Anza College"`.
- **`to`**: the destination institution (university) name, e.g., `"University of California, San Diego"`.
- **`major`**: the major or program name, e.g., `"CSE: Computer Science B.S."`. This identifies which articulation agreement it is.
- **`catalog_year`**: the academic year or range the agreement is effective for, e.g., `"2024-2025"`.
- **`source_url`**: the URL from assist.org where this agreement was obtained, for traceability (could be useful for auditing or presenting a reference).
- **`general_advice`**: any general notes or advice text from the agreement that applies broadly. This might include recommendations (like completing IGETC or notes about GPA or application advice).
- **`groups`**: an array of requirement groups. Each group object contains:
  - **`group_id`**: a short identifier (could be numeric or a code) for the group (e.g., `1` or `"A"`).
  - **`group_title`**: a human-readable title or instruction for the group. If the original agreement provides a description, use that; otherwise, synthesized (e.g., `"All courses are required"` or `"Choose one of the following sections"` depending on context).
  - **`group_logic_type`**: a field indicating any special rule for the group. Common values might be:
    - `"all_required"` (all sections/courses in this group must be completed),
    - `"choose_one_section"` (if multiple sections are offered, choose one to fulfill the group),
    - `"select_n_courses"` (if the group says something like "select 2 courses from the following sections/courses").
  - If `group_logic_type` is `"select_n_courses"`, an additional field **`n_courses`** specifies the number (e.g., 2).
  - **`sections`**: an array of section objects within the group.
- **Sections**: Each section in the `sections` array has:
  - **`section_id`**: identifier for the section (often numeric or alphabetic within the group).
  - **`section_title`**: description of the section. If the agreement provides a title or condition (like “Complete 1 course from below” or a topic like “Math Requirement”), that is used. If not, it could default to something like `"Section 1"` for reference.
  - **`uc_courses`**: an array of courses or requirements listed for the university in this section. (Each item here is something the university expects, which can be fulfilled by CCC courses.)
- **UC Course Entry**: Each entry in `uc_courses` represents a single university course or requirement and contains:
  - **`uc_course_id`**: a code for the university course (e.g., `"CSE 100"` or `"MATH 20B"`). This might be extracted in a normalized form.
  - **`uc_course_title`**: the title of that university course (e.g., `"Data Structures"`). Useful for display or to include in explanation.
  - **`units`**: (if available) the unit value of the UC course.
  - **`logic_block`**: the core logic object that details the equivalent community college courses that fulfill this UC course.
- **Logic Block Structure**: The `logic_block` holds the AND/OR structure:
  - **`type`**: `"OR"` or `"AND"` (in current normalized form, top-level is usually `"OR"` because an articulation typically offers multiple alternative sets of CCC courses to fulfill the UC course).
  - **`courses`**: an array which can contain either course objects or further nested logic.
    - In our normalization, we wrap every group of courses that must be taken together as an inner object with `"type": "AND"`. So effectively, `logic_block["courses"]` is a list of options (OR), each option is an AND of one or more courses.
    - Example:
      ```json
      "logic_block": {
         "type": "OR",
         "courses": [
            { "type": "AND", "courses": [
                 { "name": "CIS 22A", "honors": false, "course_id": "abc123", "course_letters": "CIS 22A", "title": "Intro to Programming" },
                 { "name": "CIS 22B", "honors": false, "course_id": "def456", "course_letters": "CIS 22B", "title": "Intermediate Programming" }
              ]
            },
            { "type": "AND", "courses": [
                 { "name": "CIS 27", "honors": false, "course_id": "ghi789", "course_letters": "CIS 27", "title": "Advanced C++ Programming" }
              ]
            }
         ]
      }
      ```
      This indicates: UC course can be fulfilled by CIS 22A + 22B together, **or** by CIS 27 alone.
    - **Course object fields** within logic_block:
      - `name`: Full name (department code and number, possibly with honors notation).
      - `honors`: boolean, true if this is the honors version.
      - `course_id`: a hash or unique ID for the course (could be used for indexing and matching; e.g., a short hash of the course code).
      - `course_letters`: just the course code part (e.g., "CIS 22A").
      - `title`: the course title (same as `uc_course_title` but for the CCC course).
    - We also include `no_articulation: true` in `logic_block` if there were no courses (meaning the assist data had an empty set – indicating that UC course has no equivalent at the CCC).
- **Additional Fields (Enhanced Schema):** To support extended features:
  - `uc_note` (at either group, section, or course level): any specific note from the agreement text about that item. E.g., some courses might have a note like “*This course must be taken for a letter grade*” or a group might have “*Completion of this group satisfies the UCSD XYZ requirement*”.
  - `policy_tags`: a list of tags for institutional policies relevant to this agreement. For example, `["IGETC_applicable", "Lab_required", "Minimum_GPA_3.0"]`. These tags can be used by the system to quickly identify and possibly inject relevant information or handle certain queries (like if `IGETC_applicable` is false for a major, the system knows to say IGETC is not required).
  - `last_updated`: timestamp or version to indicate when this JSON was last generated or verified. Useful for version control.
  - `agreement_id` or `version_id`: a unique identifier (like a combination of from/to/major/catalog_year or a GUID) to distinguish agreements. Helps with tracing and possibly storing user progress keyed to an agreement.

The above schema ensures all necessary info is captured. It’s both human-readable (for developers or even power users who inspect it) and structured enough for code to traverse.

### Schema Normalization and Logic Reuse

Normalization refers to structuring the data in a consistent way for all entries:
- As shown, even single-course requirements are wrapped in an `AND` list for uniformity. This simplifies the evaluation code (it can always assume an OR of one or more AND groups).
- Course names are cleaned (removing trailing spaces, consistent formatting for honors, etc.) during scraping. The `slugify` and `hash_id` functions in our pipeline create consistent identifiers (`course_id`) which we use to match courses easily (like comparing a student’s course list to the `course_id` in the logic).
- By normalizing group instructions and types (like determining `group_logic_type`), we make the interpretation easier. E.g., whether a group says "All of the following..." or lists multiple sections with "or", we categorize it so the LLM or validator doesn’t have to parse the English each time – it can rely on `group_logic_type`.

**Articulation logic reuse**: Many majors or agreements share common patterns (for example, an introductory math sequence might appear for many STEM majors). While each JSON stands alone, we aim to avoid duplicating processing logic:
- The code that evaluates a logic_block or prints a requirement can be reused across all agreements. Because the schema is uniform, one set of functions handles all majors.
- We might even store common sub-structures by reference. For instance, if “CIS 22A + 22B = CSE 8A + 8B” is a common articulation for multiple majors, we still list it in each relevant JSON for completeness. But for maintenance, if we had a database, we could have a single source of truth for that pair. In JSON files, duplication is fine since they’re snapshots of each agreement.
- However, if a CCC course appears in multiple places (like a math course might satisfy both a major requirement and also an IGETC area), we might want to tag it or ensure consistency. This is more of a data consistency check than schema design – the schema allows it, but our data pipeline ensures the course name and ID are consistent whenever it appears.

### Reverse Mapping for Lookup

To support quick answer to questions like “I took Course X at De Anza, where does it count at UCSD?”, we benefit from a **reverse mapping**:
- We can generate a dictionary mapping each CCC course (by `course_id` or course code) to all occurrences in the articulation JSON. For example:
  ```json
  "reverse_index": {
      "CIS 22A": [ 
         { "uc_course_id": "CSE 8A", "section_id": "1", "group_id": "1" } 
      ],
      "CIS 22B": [
         { "uc_course_id": "CSE 8A", "section_id": "1", "group_id": "1" },
         { "uc_course_id": "CSE 8B", "section_id": "2", "group_id": "1" }
      ]
  }
  ```
  This tells us that CIS 22A appears as part of the equivalence for UCSD CSE 8A (in section 1, group 1), and CIS 22B appears for both CSE 8A and CSE 8B (maybe it’s needed for both).
- With such an index, a query mentioning "CIS 22B" directly yields all the UC requirements it fulfills. The system can then frame an answer listing each (or focusing on the major in question).
- This mapping can be built when we ingest the JSON (it’s essentially iterating over logic_blocks and collecting references). We might store it in memory or as part of the JSON file itself under a `reverse_index` key (though that increases file size redundancy, it may be acceptable).
- For v2 (single college to single university), the data is manageable enough that on-the-fly search is fine. But as we scale to all CCCs, having precomputed indexes or a search structure (like an Elasticsearch or a SQLite full text search on course codes) will be useful for performance.

### Audit Tags and Versioning

**Audit Tags:** To ensure the data covers everything and to facilitate quality checks:
- We may tag certain entries with markers. For example, if during scraping we had uncertainty, we could tag an entry with `"verification_needed": true` or `"parsed_from_note": true` if it was gleaned from a text note rather than structured part. This would allow us to manually review or have the LLM double-check those parts with special attention.
- Another kind of audit tag might be labeling requirements that double-count for something. E.g., a course that satisfies both a major requirement and a general education requirement could have a tag `"GE_overlap": "IGETC Area 2"`. This is more for future expansion (it can help in advising when student asks about GE).
- **No articulation flags** (like the `no_articulation: true` in logic_block): this is crucial for audit because it flags gaps where a student will have to take the course at the university. The system can easily find all such instances and perhaps notify if an entire group has no articulation (meaning the student essentially must do those at UC).

**Versioning:** Articulation agreements update typically every year. We need to manage versions:
- The JSON file naming convention already includes `catalog_year`. This allows storing multiple versions of the same major’s agreement (e.g., `CS_BS__2024_2025.json` and `CS_BS__2023_2024.json`). If a student specifies a catalog year or if we always use the latest, the system should load the appropriate one. We might default to the latest year available if not specified.
- Internally, we could add a `version` number or date in the JSON to track when it was scraped. E.g., `"last_updated": "2025-04-01"`.
- If the user asks something like “did anything change this year?” the system could theoretically compare versions. We have a CLI diff tool (discussed later) which can compare two JSON files and highlight differences (like if a course was added or removed). That’s more of a developer tool, but we could expose it in an answer if needed.
- When updating the data, maintaining backwards compatibility in schema is important. If we ever change the schema (add fields, etc.), we should bump a schema version and handle older JSONs accordingly. For now, v2’s schema is an evolution from v1, and we intend to keep it stable through v2 rollout.
- We might store schema version as a constant in the files, e.g., `"schema_version": 2.0` for TransferAI v2 format. This can help the code know how to parse if multiple versions are around.

### JSON Schema and Articulation Logic Reuse

The separation of the articulation data (JSON) from the application logic means we can reuse the **same reasoning and validation code for all colleges, majors, etc.**:
- The `validate_logic_block` function doesn’t care if it’s CS major or History major; as long as the JSON follows the schema, it will compute satisfaction the same way.
- Prompt templates can be more or less the same structure for any major; only the content changes. So as we add many JSON files for other majors, we don’t need to create new logic, just new data.
- This reuse was a goal of the schema design: once we proved it works for one major (v1, CS major), we extend the same format to all majors so that v2 is mostly scaling up data volume and refining around edges, not fundamentally changing how the data is structured per major.

In summary, the JSON schema in TransferAI v2 is carefully crafted to capture all pertinent articulation information and meta-information. It’s optimized for both **readability** and **machine processing**, enabling quick lookups (with indices), accurate logic checks (normalized structure), and adaptability to future needs (tags, versioning). This data layer is the foundation upon which the LLM prompts and reasoning are built, so getting it right is crucial.

## 5. CLI-Driven System Design

TransferAI v2 is implemented as a backend service with a **Command-Line Interface (CLI)** as the primary way to use and test the system. This section describes how the codebase is structured into modules, how a user or developer interacts with the system via CLI commands, and how outputs are managed for both human readability and machine parsing.

### Modular Code Layout

The system is organized into clear modules, each handling a distinct aspect of the functionality. A proposed layout is as follows:

- **`cli_handler.py`** – This is the entry point for the CLI. It parses command-line arguments or interactive prompts. For example, running the program might allow arguments like `--question "What does CIS 22A transfer as?" --courses "CIS 22A, CIS 22B"` etc., or it might drop into an interactive mode where you type questions. The `cli_handler` orchestrates the flow:
  1. Reads input (either from arguments or interactive input).
  2. Loads necessary data (e.g., loads the JSON for the specified college-major, perhaps based on config or arguments).
  3. Calls the Query Classification & Routing logic to determine how to handle the query.
  4. Invokes `prompt_builder` to construct the prompt(s) for the LLM.
  5. Calls the LLM via `llm_interface` (which could be OpenAI API or local model wrapper).
  6. Post-processes the LLM response (e.g., parses out JSON, or calls validation functions if needed as a second step).
  7. Formats and prints the final answer to the console.
  
- **`prompt_builder.py`** – This module contains the logic for assembling prompts from templates and data. It will likely have functions for each prompt type, e.g. `build_course_prompt(query, data)`, `build_major_prompt(query, data, student_courses=None)`, etc. It handles inserting dynamic content into the templates, as well as stacking system/user messages if using the chat format. If we maintain templates as separate files or multiline strings, this module reads those and fills them in. Keeping prompt assembly here means we can unit test prompt generation separately (ensuring all needed info is present).
  
- **`model_interface.py`** – (Or similarly named, e.g., `llm_client.py`): This abstracts the calls to GPT-4 or LLaMA. It might have methods like `query_gpt(prompt, functions=None)` and `query_local(model_prompt)`. The routing between GPT-4 and LLaMA as discussed (like trying local first, then remote) can be implemented here. This module would also handle converting a prompt structure into the API call format. For instance, if using OpenAI ChatCompletion, it will take the stacked messages from `prompt_builder` and call the API, including any function definitions for function calling.
  - If using LangChain or DSPy, this module might instead set up those frameworks' constructs, but having our own interface layer allows flexibility to switch libraries or APIs by changing one module.
  
- **`validator.py`** – Contains the deterministic logic functions. For example:
  - `validate_logic_block(logic_block, completed_courses_list) -> ValidationResult`
  - `check_all_requirements(articulation_json, completed_courses_list) -> dict of statuses`
  - Perhaps utility functions like `match_course(course_name_or_id, articulation_json)` for reverse lookup.
  This module can be directly called by the LLM function-calling mechanism, or pre-called by `cli_handler` to get some facts before prompting.
  - It should be thoroughly unit tested, since it’s critical to accuracy. We might include a bunch of test cases (like various logic structures and different completed courses sets).
  
- **`data_loader.py`** – Handles loading JSON data files from the `data/assist_data/...` directory. Given parameters like college, university, major, year, it finds and reads the appropriate JSON. It might also build in-memory indices (like the reverse_index) on load. We separate this to make it easy to swap data source (for example, moving to a database or an API in future).
  
- **`formatter.py`** (optional) – Could contain functions to format the output nicely. For instance, if we want to pretty-print the counselor-readable output with colors or indentation in CLI, or truncate overly long text. Or to convert model output JSON into a human-readable summary if we ever did the reverse (though likely the model generates the human text directly).
  
- **`config.py`** – Might store configuration like API keys for OpenAI, model selection (GPT-4 vs others), and paths.
  
- **`templates/`** – A directory (if using external files for prompts). E.g., `course_prompt.txt`, `major_prompt.txt` etc., which `prompt_builder` reads. Storing them in files makes iteration on prompt wording easier (can be edited without touching code). We might also version them here.
  
- **`tests/`** – We will have a tests folder with unit tests for the above modules, especially `validator` and parts of `prompt_builder` (we can test that given a certain input it produces the expected prompt string structure, though not the LLM answer).
  
This modular separation ensures that each part of the system can be developed and debugged in isolation. For example, if outputs seem logically wrong, we focus on `validator.py`; if phrasing is off, we tweak `prompt_builder` templates; if CLI input parsing is problematic, adjust `cli_handler`. It also makes the system easier to extend – adding a new feature often means adding a new module or function, rather than entangling with existing code.

### CLI Workflows: Testing, Diffing, and Headless QA

Since there's no frontend, the CLI is not just for end-users (like counselors or developers using it for advising) but also for the team to test and ensure quality. We envision several CLI workflows:

- **Interactive QA Mode:** Simply running the CLI might drop into an interactive prompt (`>`), where a user can type a question and get an answer, then ask another. This is useful for manual testing and demonstrations. The context (selected college, major) can be set via initial arguments or commands. E.g., one might run `python cli_handler.py --data "data/assist_data/De_Anza_College/UCSD/CS_BS__2024_2025.json"` and then interact.
- **Automated Test Queries:** A special CLI command or script, e.g., `python cli_handler.py --test test_queries.txt`, could read a file of sample questions (and possibly expected keywords in answers) and run them one by one, logging the outputs. This helps do a quick regression test of the system. If integrated with a CI (Continuous Integration), this ensures that changes to prompts or code don’t break basic functionality.
- **Diffing Outputs:** One challenge with LLM-based systems is changes in prompt or model can cause shifts in output phrasing or details. To manage this, we can have a CLI mode that runs a set of canonical queries and saves the outputs to a file (or compares to an existing baseline).
  - For example, `python cli_handler.py --run-suite suite1.json --out results_0422.txt` might run through a JSON of test cases (each with a question and maybe a fixed random seed or model parameters) and store the answers.
  - Then one can run it again after changes and use a diff tool (or even a built-in diff function) to compare `results_0422.txt` with the previous results file. The blueprint may include an example diff output to illustrate differences.
  - This diffing is mainly for developers to see what changed. For instance, if a prompt tweak caused all answers to include a certain phrase, the diff would show that. We can then decide if the change is acceptable or adjust accordingly.
- **Headless QA**: By headless we mean without human in the loop, purely script-driven quality checks. This could include:
  - Ensuring the output JSON (if any) is valid and matches the expected schema.
  - Checking that for each query with known ground truth (maybe we have some scenarios where we know the correct answer, like if a student completed everything, the answer should say all requirements met).
  - Measuring response length or certain keywords (e.g., we might ensure that any mention of an honors course includes the word “honors” at least once, or that if no articulation exists the word “no equivalent” appears).
  - We might use simple assertions or even have the LLM itself judge outputs in the future (but that’s beyond v2 likely).
  - This could be implemented as part of the `tests/` suite or a separate QA script.

- **Example CLI usage**:
  ```
  $ transferai --college "De Anza College" --university "UC San Diego" --major "Computer Science B.S." \
      --question "I took Math 1A and 1B; have I satisfied the math requirement?"
  ```
  This might output a friendly paragraph answering the question, as well as perhaps a JSON.
  
  Another example:
  ```
  $ transferai --college "De Anza College" --university "UC San Diego" --major "Computer Science B.S." \
      --batch-questions questions.txt --output answers.txt
  ```
  This might take a list of questions and produce a text file of answers (one per question) for review.

By building these CLI workflows, we ensure that as we scale up to more majors and more data, we can continuously test and validate the system’s performance. It also allows non-developers (like subject matter experts) to run the tool on various scenarios and inspect results, without needing a GUI.

### Output Strategies: Counselor-Readable and Machine-Parseable Formats

One of the design goals is to produce output that is immediately useful to a human (e.g., a counselor or a student reading it), **and** optionally produce structured output that can be consumed by other software or further analysis. The CLI caters to both:

- **Counselor-Readable Text:** By default, the answer the LLM produces is a well-formatted, explanatory text. We ensure the style is friendly and clear (via the prompt). This text might contain bullet points, lists of courses, and so forth, which is easy for a person to read in the terminal or copy into an email. 
  - We avoid overly JSON-like or technical language in this part. For example, instead of `"fulfilled": true`, the text will say "You have completed this requirement."
  - We also consider coloring or highlighting in CLI: perhaps using ANSI colors (if not too distracting). E.g., green text for “fulfilled” and red for “not fulfilled” when listing statuses, to quickly catch the eye. This can be done by the `formatter.py` when printing the final text.
  - The prompt might structure the answer in sections (like "**Completed Requirements:** ... **Remaining Requirements:** ...") to further aid readability.
  
- **Machine-Parseable JSON Output:** In many cases, we want a summary of results in JSON form as well. For instance, if the question was "have I met all requirements?", it’s useful to get a structured report. The system can output or save something like:
  ```json
  {
    "major": "Computer Science B.S.",
    "completed_sections": ["1", "2"],
    "remaining_sections": ["3"],
    "details": {
       "Section 1": {"status": "fulfilled", "missing_courses": []},
       "Section 2": {"status": "fulfilled", "missing_courses": []},
       "Section 3": {"status": "unmet", "missing_courses": ["CIS 27"] }
    }
  }
  ```
  This could be returned by the `check_all_requirements` function or assembled from individual `validate_logic_block` outputs.
  - We have two options to provide this JSON to the user:
    1. **Dual output in CLI:** The CLI could print the human text, and also print the JSON (perhaps after, or on demand). We might have a flag `--format json` to output only JSON (for integration with other tools), or `--format full` for text + JSON.
    2. **Embedding JSON in the text:** We could have the LLM include a JSON snippet in its answer. For example, some systems ask the model to produce an explanation and then a `<DATA>` section with JSON. However, mixing the two can confuse the model or the user. It might be cleaner to keep them separate.
  - Considering the GitHub Markdown context, if this output were to be logged or saved, having separate JSON is more machine-friendly. So likely we implement a mode where the LLM’s answer is parsed for certain keys or we generate the JSON from our own validation code, and that JSON is either saved to a file or printed.
  
- **Example of dual output:**
  After the text answer, the CLI might output something like:
  ```
  ---- MACHINE-READABLE JSON ----
  {"section_1": "fulfilled", "section_2": "fulfilled", "section_3": "unmet"}
  -------------------------------
  ```
  This delimiter approach allows someone to easily copy the JSON, and our automated tests could scrape anything between those lines as JSON. It’s simplistic but effective in a CLI environment.
  
- If the CLI is used by a developer building an application, they might prefer calling library functions directly to get a Python dict or JSON, but since we assume backend-only CLI, we accommodate by these formats.

By providing both formats, we ensure the system is useful out-of-the-box for advising (the text answer), and ready for integration or further programmatic handling (the JSON). This is particularly helpful for auditing – e.g., we can log all JSON outputs of advising sessions to a database for analysis of common unmet courses, etc., without having to re-parse the English text.

In conclusion, the CLI design of TransferAI v2 emphasizes **usability, testability, and integrability**. The module breakdown enforces clean separation of concerns, the workflows enable continuous testing and improvement, and the output options serve both immediate users and future systems that may consume TransferAI’s results.

## 6. Additional Architecture Concerns

Beyond the core functionality, there are additional architectural considerations to ensure TransferAI v2 is robust, maintainable, and scalable for future needs. These include leveraging frameworks for LLM orchestration, planning for an API layer, ensuring we can audit and version our prompts/results, and keeping an eye on scaling to a much larger scope of colleges and programs.

### Leveraging LangChain, LlamaIndex, and DSPy for LLM Orchestration

To manage the complexity of multi-step LLM interactions and retrieval of data, we consider using existing frameworks:
- **LangChain:** This is a popular framework for building LLM applications with components like Chains, Agents, Memory, etc. In TransferAI, LangChain could simplify some aspects:
  - We can define a custom Chain that takes a question, runs our classification function (could be a custom LangChain prompt or a Python function in the chain), then does data retrieval (another chain step), and finally calls the LLM with the assembled prompt. LangChain would handle passing the outputs between steps cleanly.
  - If we decide to allow an agent style (where the model can decide to take actions like search the data), LangChain’s Agent tools could be set up. However, our use-case is fairly structured, so a deterministic chain might suffice.
  - LangChain also offers built-in integrations for OpenAI function calling and for vector stores (useful if we use embeddings for semantic search of courses/majors).
  - We need to weigh complexity; since we already have a lot of custom logic, LangChain must complement rather than complicate. Possibly, we can incorporate it in specific parts, like using its `LLMMathChain` analogously for logic validation, or simply as a nicely managed call to the LLM with our prompts.
  
- **LlamaIndex (formerly GPT Index):** This framework is tailored for connecting LLMs with external data (documents, indices). In our context:
  - We could treat each articulation agreement or each section as a “document” and index them. For example, building an index where the text of each requirement is indexed. This would allow semantic queries like "data structure course UCSD" to retrieve the relevant section.
  - If a user asks something that spans multiple agreements or is not sure of which major, an index could help find the relevant major. (Though currently v2 is just De Anza -> UCSD, one could imagine a future where a user asks, "Does De Anza have an articulation for UC Berkeley Computer Science?" which requires searching a big database – LlamaIndex with a vector store could help locate that document or say no if not present.)
  - For our immediate need (all majors at one college→university), a simpler approach (loading from file) works. But as we scale to all CCCs and UCs, having an index that can quickly retrieve the right JSON or the right part of JSON (rather than scanning dozens of files) will be valuable.
  - LlamaIndex can integrate with LangChain or work standalone. We could experiment with giving the LLM an index query ability (like a tool) where it can say “search index for ‘CIS 22A CS articulation’ ” and then get the snippet. However, that might be overkill if we can just directly look up in our structured data. It's more useful for unstructured data retrieval.
  
- **DSPy (Declarative Self-Improving Python):** This is a cutting-edge framework that encourages writing declarative Python which an underlying system (the LLM with a compiler) uses to produce results rather than relying on static prompts:
  - We could use DSPy to define the sequence of operations (classify -> retrieve data -> validate -> answer) in a declarative way. The DSPy framework might then handle optimizing prompts for each operation, or even learning from corrections over time.
  - One benefit would be modularizing the prompt logic in code, making it easier to adjust the flow without manually crafting every prompt. DSPy could, for example, allow us to specify, “First get a list of unmet requirements as JSON, then have the model explain it,” in a high-level way, and it will orchestrate that with the model.
  - DSPy also focuses on prompt optimization; as we gather more usage data, it could potentially refine prompts automatically to improve answers, which aligns with self-improving aspect.
  - Given that DSPy is relatively new, integrating it might be experimental in v2. The architecture can remain flexible to incorporate such a framework later by not hard-coding too much logic that would conflict with it.
  
In summary, while the core system can be built with plain Python and API calls, using frameworks like LangChain and LlamaIndex could reduce development time and increase capabilities (especially for retrieval and multi-step chains). DSPy offers a forward-looking way to keep improving the system. The blueprint is designed so that integration of these is possible:
for example, the `model_interface` could be backed by LangChain’s LLM wrappers, and the `data_loader/search` could be backed by LlamaIndex’s query interface.

### FastAPI Interface Layer for Future Integration

Although v2 is CLI-only, we anticipate a future need for a programmatic interface (e.g., a chatbot or a web service). Implementing a thin **FastAPI layer** would allow:
- Exposing an endpoint like `POST /query` where a JSON payload includes the college, university, major, question, and optionally courses completed. The service would run the same logic and return a response in JSON (with both the answer text and structured data).
- This could enable a web frontend or integration into a larger advising platform. For example, a college might integrate this into their student portal so a student can select their target transfer and ask questions.
- FastAPI is lightweight and can run our Python modules underneath. We’d ensure that our design (with modules in place) makes it easy to call them from a web request handler. For instance, `cli_handler.py` logic could be refactored into a function `answer_query(college, university, major, question, courses=[])` which can be invoked by both CLI and API.
- For agent/bot testing: We could simulate a conversation by calling the API repeatedly and perhaps storing a session state. Although our architecture doesn’t heavily use conversation memory (each query is independent), an API could manage a session context if needed (e.g., if the user doesn’t repeat the college/major every time, the session could remember it).
- The API would also facilitate load testing and scaling considerations: we might deploy it behind an ASGI server with concurrency. We’d need to consider the performance of loading large JSONs or running multiple LLM calls in parallel (especially if using the local model – ensure we have a queue or enough compute).

We won’t implement FastAPI in v2 unless needed, but designing our core as a library of functions means we’re one step away from having it. It’s a conscious architectural decision to separate core logic from the interface, enabling such future expansion.

### Auditing, Traceability, and Prompt Versioning

Given the complexity of LLM-based advice, auditing and traceability are essential for trust and continuous improvement:
- **Prompt Versioning:** We maintain version numbers for our prompt templates. Each template file or definition can include a version comment, like `# Version 2.1 - 2025-04-22`. We might also include the version in the prompt itself (possibly as a hidden comment or as part of a system message like "Using TransferAI Prompt v2.1"). This way, when looking at logs or outputs, we know which prompt version generated it. If we update a prompt due to some improvement, we increment the version. This practice is akin to versioning an API.
- **Logging and Traceability:** Every time the system answers a query, we log:
  - The input query.
  - Classified intent and route taken.
  - Which data file was loaded (with version or timestamp).
  - The final prompt given to the LLM (this is crucial for debugging LLM outputs).
  - The LLM’s raw response.
  - Any function calls made and their results.
  - The final output shown to user.
  
  These logs could be simply written to a file (like `logs/session_YYYYMMDD.txt`) or structured (JSON logs).
  They allow us to trace back why the system answered a certain way. For example, if a user reports a mistake, we can check the logs to see if the prompt had an error, or if the data was wrong, or the LLM just hallucinated beyond instructions.
  
- **Auditing Tools:** We can build a small audit script that goes through logs or outputs and flags potential issues:
  - Compare the LLM’s statements with the known data. E.g., if the LLM said “Course X satisfies Y” but in data Course X wasn’t actually listed for Y, that’s a red flag. (Ideally our design prevents that by always giving it data, but if the model wandered, this catches it.)
  - Check that certain disclaimers or notes were present if they should be (e.g., if a major had a GPA requirement note, did the answer mention GPA?).
  - Ensure no prompt version mismatches (like mixing parts of old and new prompts).
  
- **User Privacy and Data:** Since this is advising, we might log courses a student said they took. We should consider privacy – in a real scenario, those logs could contain personal academic info. For now, assume this is used in a controlled environment (or with dummy data), but eventually, we might want an option to anonymize or not log certain details unless in debug mode.
  
- **Continuous Learning:** The logs can also feed back into improving the system. For instance, if we find the same question being asked in different words that we didn’t anticipate, we can add a new classification rule or a new example in semantic search. If counselors using the system give corrections, we can capture those and fine-tune the model or adjust prompts accordingly.
  
Traceability extends to data as well. Because we keep `source_url` in the JSON, we can always trace a piece of advice back to the official articulation page it came from. In the future, we might even present that to users (like “(per assist.org 2024-2025 agreement)”), but that might clutter the response. Still, internally, it’s good to have that chain of evidence.

### Long-term Scaling: All CCCs, IGETC, TAG, CSU GE, etc.

While v2 is focused on one college (De Anza) to one university (UCSD) for all majors, the ultimate vision is to support **all California Community Colleges to UCs**, and possibly other transfer pathways. Our architecture is built with this scalability in mind:

- **Scaling Data Volume:** There are 100+ CCCs and 9 undergraduate UCs. Each college-UC pair has dozens to hundreds of majors. Storing each as a JSON file could mean thousands of files. We need to manage that:
  - Organize files in a directory structure by college and university (which we already do, e.g., `data/assist_data/De_Anza_College/UC_San_Diego/...`).
  - We might introduce a simple database or use a search index for retrieval rather than loading files each time. Perhaps an SQLite database with tables for courses, equivalencies, etc., could replace or complement JSON, especially if queries come in for random colleges.
  - Caching: if the CLI or API is often used for one college (like in a session), we cache that JSON in memory so we’re not reading from disk repeatedly.
  - Memory considerations: If running on a server that needs to handle multiple queries concurrently for different colleges, loading too many large JSONs might fill RAM. We may consider loading on demand and unloading or using a memory-mapped database.
  
- **Adding new Institutions:** The code should not hardcode "De Anza" or "UCSD" anywhere except perhaps default settings. It should rely on input parameters or config. This way, adding a new college just means making sure its data is scraped and available, and then calling the system with that college name.
  - We might create a config file listing all available college-university pairs or a function to list them by scanning the data directory. The CLI could have a command to list available agreements.
  
- **IGETC and CSU GE:** 
  - **IGETC (Intersegmental General Education Transfer Curriculum)** is a general education pattern that can be used to fulfill lower-division GE requirements for either UC or CSU. It’s not tied to a specific university (though slight variations for UC/CSU) and not specific to a major. Many students ask if they should complete IGETC.
    - We can treat IGETC like a special "major" in our system. For example, under a community college, we could have `IGETC-UC` and `IGETC-CSU` articulation files, which list the areas (groups like Area 1, Area 2, etc.) and which courses at that CCC fulfill each area. In fact, assist.org might list those or it can be sourced from other documents.
    - Then the system could answer “Have I completed IGETC?” by checking those groups. This is a bit separate from a major, but our architecture of groups/sections fits IGETC’s structure (Area 1: English, etc., each area is like a group requiring a certain number of courses from categories).
    - For now, we can plan that as an additional data set and our same logic applies: it's just a different JSON schema instance (with `major="IGETC-UC"` perhaps).
    - The prompts might need slight tweaking to clarify IGETC isn’t a major requirement but a GE package. But we can reuse a lot.
  - **CSU GE Breadth:** Similar to IGETC but for CSU. We can handle it likewise, as another structured agreement.
  - **TAG (Transfer Admission Guarantee):** TAG is more about eligibility (if you take X units, Y GPA, you get guaranteed admission to certain majors). This is less about course articulation and more about planning. Our system could store some rules about TAG (like “need GPA >= 3.4, and certain courses by fall” etc.), possibly as policy_tags or separate JSON. However, addressing TAG queries might involve:
    - Recognizing the user’s query is about TAG (via keyword).
    - Providing an answer based on static info about TAG for that campus/major. This might not need LLM at all except to phrase it nicely, or we feed a short context: e.g., "TAG for UCSD is not available for CS (hypothetical example, since UCSD may not have TAG for CS). TAG generally requires ...".
    - We might integrate this later; for now, we can mention that TAG info could be an extension with minimal changes to architecture: just additional data and some prompt templates for those answers.
  
- **Other Systems (CSU transfers):** Eventually, if including CSU articulation, the data schema might extend to those, which have similar articulation agreements. We might rename some fields (if we want generic "university" instead of specifically UC) but essentially it’s the same structure.
- **Maintaining Quality at Scale:** With more data, our classification might need to consider context (like if data for multiple universities is loaded, the query "What about CSE 100?" could be ambiguous which university's CSE 100 – context or explicit college/university specification becomes crucial).
  - Possibly, in a multi-university scenario, we require the user (or an initial setup) to specify the target, or else we could attempt to detect by course naming conventions (e.g., UC courses often differ from CSU course codes).
  - Another approach is having a multi-turn interaction: if a user doesn't specify, ask "Which university’s program are you interested in?" This enters more interactive territory.

Finally, scaling might involve fine-tuning our local LLaMA model on the domain (to handle classification or even generate answers more accurately for articulation style). We should keep that possibility open: e.g., if using a local model for cost, maybe fine-tune it on a set of Q&A pairs we have verified, to improve its reliability. The architecture allows swapping the model or model provider easily via the `model_interface` abstraction.

---

**Conclusion:** TransferAI v2’s architecture is built to be robust and extensible. We detailed a layered prompt strategy for precise LLM interactions, rigorous logic validation to ensure accuracy, intelligent query routing, an optimized data schema, and a developer-friendly CLI setup. By also considering integration with frameworks, web services, and future scalability concerns, this blueprint aims to not only solve the immediate problem (De Anza to UCSD for all majors) but also lay the groundwork for a comprehensive California-wide transfer advising assistant powered by LLMs. With this design, we can confidently proceed to implement and iterate on TransferAI v2, knowing it can grow to meet the broader needs ahead.