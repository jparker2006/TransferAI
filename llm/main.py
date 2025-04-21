from document_loader import load_documents
from query_parser import (
    extract_filters,
    extract_prefixes_from_docs,
    extract_reverse_matches,
    extract_group_matches,
    extract_section_matches,
    normalize_course_code,
    find_uc_courses_satisfied_by
)
from logic_formatter import (
    render_logic, 
    render_group_summary, 
    render_logic_str, 
    explain_if_satisfied, 
    find_uc_courses_satisfied_by,
    validate_combo_against_group,
    include_binary_explanation,
    validate_uc_courses_against_group_sections,
    is_honors_pair_equivalent
)
from prompt_builder import build_prompt, PromptType
from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import json, re


class TransferAIEngine:
    def __init__(self):
        self.docs = []
        self.index = None
        self.query_engine = None
        self.uc_prefixes = []
        self.ccc_prefixes = []

        # 🔧 New: full course catalogs (used for smarter query parsing)
        self.uc_course_catalog = set()
        self.ccc_course_catalog = set()


    def configure(self):
        # 🔧 LLM Setup: TransferAI uses Ollama + LLaMA3 for safe, deterministic answers
        Settings.llm = Ollama(
            model="llama3",  # Swap with llama3:instruct or mistral if tone/guardrails needed
            temperature=0.1,  # Low temperature ensures logic fidelity (no speculation)
            request_timeout=120,  # Allows long prompts, especially for multi-section groups
            system_prompt = (
                "You are TransferAI, a professional UC transfer counselor trained to interpret official ASSIST.org course articulation data.\n"
                "You provide reliable, logic-accurate academic advising to California community college students transferring to the University of California (UC) system.\n"
                "Your answers must be based *only* on the articulation logic provided. Do not speculate, infer, or suggest alternative paths. Never reference courses not explicitly included in the articulation data.\n"
                "\n"
                "You must follow articulation logic exactly as written, including:\n"
                "- OR: multiple standalone CCC options (only one is required)\n"
                "- AND: CCC courses that must all be completed together\n"
                "- Nested combinations: e.g., AND blocks inside OR paths\n"
                "- Group-level logic: choose_one_section (complete exactly one full section), all_required (complete all UC courses listed), select_n_courses (complete a specific number)\n"
                "- No articulation: if a UC course has no CCC equivalent, state clearly: 'This course must be completed at the UC.'\n"
                "\n"
                "Never collapse or combine articulation paths. Do not merge multiple CCC options into one. Show every valid option independently and clearly.\n"
                "\n"
                "Use correct UC and CCC course codes and full course titles (e.g., 'CSE 11 – Introduction to Programming and Computational Problem Solving', 'CIS 36B – Intermediate Problem Solving in Java').\n"
                "\n"
                "Your tone must be confident, professional, and counselor-grade — never casual, speculative, emotional, or vague. Avoid chatbot-style phrasing.\n"
                "\n"
                "Format every response in a clean, logically structured way:\n"
                "- Use 'Option A', 'Option B', etc., to label articulation paths\n"
                "- Use bullet points for clarity\n"
                "- Use phrases like '(complete all)' for multi-course AND requirements\n"
                "- For group questions, explain how the student satisfies the group (e.g., 'Complete all UC courses in one section', or 'Choose 2 out of the following')\n"
                "\n"
                "Your answer must be short, deterministic, and grounded entirely in the official logic — and nothing else."
            )
        )

        # 🧠 Embedding Model: Optimized for semantic queries against articulation logic blocks
        Settings.embed_model = HuggingFaceEmbedding(
            model_name="all-mpnet-base-v2"
        )

    def load(self):
        self.docs = [doc for doc in load_documents() if doc.text.strip()]
        self.index = VectorStoreIndex.from_documents(self.docs)
        self.query_engine = self.index.as_query_engine(similarity_top_k=10)

        self.uc_prefixes = extract_prefixes_from_docs(self.docs, "uc_course")
        self.ccc_prefixes = extract_prefixes_from_docs(self.docs, "ccc_courses")

        self.build_course_catalogs()

    def validate_same_section(self, docs):
        if not docs:
            return []
        section = docs[0].metadata.get("section")
        return [d for d in docs if d.metadata.get("section") == section]

    def build_course_catalogs(self):
        self.uc_course_catalog = set()
        self.ccc_course_catalog = set()

        for doc in self.docs:
            for ccc in doc.metadata.get("ccc_courses", []):
                if ccc:
                    self.ccc_course_catalog.add(normalize_course_code(ccc))

        for doc in self.docs:
            uc = doc.metadata.get("uc_course")
            if uc:
                self.uc_course_catalog.add(normalize_course_code(uc))




    def render_debug_meta(self, doc):
        return (
            f"📘 UC: {doc.metadata.get('uc_course', '')}\n"
            f"📗 CCC: {', '.join(doc.metadata.get('ccc_courses', [])) or 'None'}\n"
        )

    def handle_query(self, query: str):
        filters = extract_filters(
            query,
            uc_course_catalog=self.uc_course_catalog,
            ccc_course_catalog=self.ccc_course_catalog
        )

        print("🎯 [DEBUG] Extracted filters:", filters)
        if len(filters.get("uc_course", [])) > 1 and "group" in query.lower():
            # Try group-level match for multi-UC combo (like CSE 8A + 8B)
            group_docs = extract_section_matches(query, self.docs) or extract_group_matches(query, self.docs)

            # 🔁 Fallback: All UC courses belong to same group, even if "Group" wasn't mentioned
            if not group_docs:
                uc_filtered_docs = [
                    doc for doc in self.docs
                    if doc.metadata.get("uc_course", "").strip().upper() in filters["uc_course"]
                ]
                if len(uc_filtered_docs) == len(filters["uc_course"]):
                    group_ids = {doc.metadata.get("group") for doc in uc_filtered_docs}
                    if len(group_ids) == 1:
                        group_docs = uc_filtered_docs
                        print(f"🔁 [Fallback] All UC courses share Group {list(group_ids)[0]}")

            if group_docs and all(
                doc.metadata.get("group") == group_docs[0].metadata.get("group")
                for doc in group_docs
            ):
                group_id = group_docs[0].metadata.get("group", "Unknown")
                group_title = group_docs[0].metadata.get("group_title", "")
                group_type = group_docs[0].metadata.get("group_logic_type", "")
                n_courses = group_docs[0].metadata.get("n_courses")

                from collections import defaultdict
                sections_by_id = defaultdict(list)
                for doc in group_docs:
                    sid = doc.metadata.get("section", "default")
                    sections_by_id[sid].append(doc)

                group_dict = {
                    "logic_type": group_type,
                    "n_courses": n_courses,
                    "sections": [
                        {
                            "section_id": section_id,
                            "uc_courses": [
                                {
                                    "name": doc.metadata.get("uc_course"),
                                    "logic_blocks": doc.metadata.get("logic_block", [])
                                }
                                for doc in docs_in_section
                            ]
                        }
                        for section_id, docs_in_section in sections_by_id.items()
                    ]
                }

                # Run validator for multi-UC queries
                validation = validate_uc_courses_against_group_sections(filters["uc_course"], group_dict)

                if validation["is_fully_satisfied"]:
                    return (
                        f"✅ Yes! Your UC course combination ({', '.join(filters['uc_course'])}) satisfies Group {group_id} Section {validation['satisfied_section_id']}."
                    )
                else:
                    missing = validation.get("missing_uc_courses", [])
                    return (
                        f"❌ No, your courses do not fully satisfy any single section of Group {group_id}.\n"
                        f"You're missing: {', '.join(missing)}."
                    )

            # Default fallback if not part of same group
            return self.handle_multi_uc_query(query, filters["uc_course"])


        # Step 1: Group/section match
        group_docs = extract_section_matches(query, self.docs) or extract_group_matches(query, self.docs)
        if group_docs:
            group_id = group_docs[0].metadata.get("group", "Unknown")
            group_title = group_docs[0].metadata.get("group_title", "")
            group_type = group_docs[0].metadata.get("group_logic_type", "")
            n_courses = group_docs[0].metadata.get("n_courses")

            if all(doc.metadata.get("group") == group_id for doc in group_docs):
                print(f"🔎 Found {len(group_docs)} matching documents in Group {group_id}.\n")

                # ✅ [R13] Combo CCC → Group logic validation
                if filters.get("ccc_courses"):
                    from collections import defaultdict

                    # Step: Group group_docs by section
                    sections_by_id = defaultdict(list)
                    for doc in group_docs:
                        sid = doc.metadata.get("section", "default")
                        sections_by_id[sid].append(doc)

                    # Build full group_dict with section_id info
                    group_dict = {
                        "logic_type": group_type,
                        "n_courses": n_courses,
                        "sections": [
                            {
                                "section_id": section_id,
                                "uc_courses": [
                                    {
                                        "name": doc.metadata.get("uc_course"),
                                        "logic_blocks": doc.metadata.get("logic_block", [])
                                    }
                                    for doc in docs_in_section
                                ]
                            }
                            for section_id, docs_in_section in sections_by_id.items()
                        ]
                    }

                    for doc in group_docs:
                        logic_block = doc.metadata.get("logic_block", [])

                        # If it's a string, parse it
                        if isinstance(logic_block, str):
                            try:
                                logic_block = json.loads(logic_block)
                            except json.JSONDecodeError:
                                print(f"❌ Could not parse logic_block for {doc.metadata.get('uc_course')}")
                                logic_block = []

                        # ✅ If it's a dict (single block), wrap in a list
                        elif isinstance(logic_block, dict):
                            logic_block = [logic_block]

                        # ✅ If it's already a list, do nothing
                        elif not isinstance(logic_block, list):
                            print(f"⚠️ Unexpected logic_block type: {type(logic_block)}")
                            logic_block = []

                        group_dict["sections"][0]["uc_courses"].append({
                            "name": doc.metadata.get("uc_course"),
                            "logic_blocks": logic_block
                        })

                    # ✅ Run validation
                    validation = validate_combo_against_group(filters["ccc_courses"], group_dict)

                    if validation["is_fully_satisfied"]:
                        return (
                            f"✅ Yes! Your courses ({', '.join(filters['ccc_courses'])}) fully satisfy Group {group_id}.\n\n"
                            f"Matched UC courses: {', '.join(validation['satisfied_uc_courses'])}."
                        )
                    elif validation["partially_satisfied"]:
                        missing = (
                            validation["required_count"] - validation["satisfied_count"]
                            if validation["required_count"] is not None
                            else "some required courses"
                        )
                        return (
                            f"⚠️ Your courses partially satisfy Group {group_id}.\n"
                            f"You’ve matched: {', '.join(validation['satisfied_uc_courses'])}, "
                            + (
                                f"but you still need {missing} more UC course(s)."
                                if isinstance(missing, int)
                                else "but they span across multiple sections. To satisfy Group 1, all UC courses must come from the same section."
                            )
                        )

                    else:
                        return (
                            f"❌ Your courses do not satisfy Group {group_id}.\n"
                            f"No UC course articulation paths were matched."
                        )

                rendered_logic = render_group_summary(group_docs)
                prompt = build_prompt(
                    logic="",
                    user_question=query.strip(),
                    prompt_type=PromptType.GROUP_LOGIC,
                    group_id=group_id,
                    group_title=group_title,
                    group_logic_type=group_type,
                    n_courses=n_courses,
                    rendered_logic=rendered_logic
                )
                response = Settings.llm.complete(prompt=prompt, max_tokens=700).text
                print(f"📘 Group: {group_id}")
                print(f"🧠 AI: {response.strip()}\n")
                return

        # Step 2: Match by UC/CCC codes
        matched_docs = []
        uc_filter = [uc.upper() for uc in filters.get("uc_course", [])]

        for doc in self.docs:
            doc_uc = doc.metadata.get("uc_course", "").strip().upper()
            doc_ccc = [c.strip().upper() for c in doc.metadata.get("ccc_courses", [])]

            if uc_filter and doc_uc not in uc_filter:
                continue
            if filters.get("ccc_courses") and not all(cc in doc_ccc for cc in map(str.upper, filters["ccc_courses"])):
                continue

            matched_docs.append(doc)

        # 🔐 R4: Force-match UC course if normal matching fails
        if not matched_docs and uc_filter:
            force_matched_docs = [
                doc for doc in self.docs
                if doc.metadata.get("uc_course", "").strip().upper() in uc_filter
            ]
            if force_matched_docs:
                print(f"🎯 [R4] UC force-match found: {', '.join(uc_filter)}")
                matched_docs = force_matched_docs

        matched_docs = [
            doc for doc in matched_docs
            if doc.metadata.get("uc_course") and doc.metadata.get("logic_block")
        ]

        # Step 3: CCC reverse match fallback
        if not matched_docs and filters.get("ccc_courses"):
            matched_docs = extract_reverse_matches(query, self.docs)

        # Step 3.5: R11 — Reverse-match CCC course → UC course(s)
        if not matched_docs and filters.get("ccc_courses") and not filters.get("uc_course"):
            print("🎯 [R11] Attempting reverse match from CCC → UC...")
            for ccc in filters["ccc_courses"]:
                reverse_docs = find_uc_courses_satisfied_by(ccc, self.docs)
                if reverse_docs:
                    print(f"🎯 [R11] {ccc} satisfies → {[doc.metadata.get('uc_course') for doc in reverse_docs]}")
                    matched_docs.extend(reverse_docs)

            # ✅ Stop here and render the R11 results only
            if matched_docs:
                matched_docs = self.validate_same_section(matched_docs)[:3]
                print(f"🔍 Found {len(matched_docs)} matching document(s).\n")

                for doc in matched_docs:
                    logic = render_logic(doc.metadata)
                    rendered_logic = render_logic_str(doc.metadata)

                    prompt = build_prompt(
                        logic=logic,
                        user_question=query.strip(),
                        prompt_type=PromptType.COURSE_EQUIVALENCY,
                        uc_course=doc.metadata.get("uc_course", ""),
                        uc_course_title=doc.metadata.get("uc_title", ""),
                        group_id=doc.metadata.get("group", ""),
                        group_title=doc.metadata.get("group_title", ""),
                        group_logic_type=doc.metadata.get("group_logic_type", ""),
                        section_title=doc.metadata.get("section_title", ""),
                        n_courses=doc.metadata.get("n_courses"),
                        rendered_logic=rendered_logic
                    )

                    response = Settings.llm.complete(prompt=prompt, max_tokens=512).text
                    print(f"🧠 AI: {self.strip_ai_meta(response.strip())}\n")

                return  # ✅ Prevent further fallback



        # Step 4: Section filter
        matched_docs = self.validate_same_section(matched_docs)[:3]

        # Step 5: Final rendering
        if matched_docs:
            print(f"🔍 Found {len(matched_docs)} matching document(s).\n")

            # R4 safeguard — enforce UC course filter if present
            if filters.get("uc_course"):
                matched_docs = [
                    doc for doc in matched_docs
                    if doc.metadata.get("uc_course", "").strip().upper() in map(str.upper, filters["uc_course"])
                ]
            elif len(matched_docs) > 1:
                query_uc_matches = {
                    normalize_course_code(token)
                    for token in re.findall(r"[A-Z]{2,5}\s?\d+[A-Z]{0,2}", query.upper())
                }
                matched_docs = [
                    doc for doc in matched_docs
                    if normalize_course_code(doc.metadata.get("uc_course", "")) in query_uc_matches
                ] or [matched_docs[0]]

            responses_by_uc = {}

            for doc in matched_docs:
                logic = render_logic(doc.metadata)
                rendered_logic = render_logic_str(doc.metadata)

                question_override = query.strip()
                if not filters.get("uc_course"):
                    question_override = f"Which courses satisfy {doc.metadata.get('uc_course', 'this course')}?"

                if filters.get("ccc_courses"):
                    selected = filters["ccc_courses"]
                    logic_block = doc.metadata.get("logic_block", {})

                    if len(selected) == 2:
                        # print(f"🪵 Logic block contents: {json.dumps(logic_block, indent=2)}")
                        if is_honors_pair_equivalent(logic_block, selected[0], selected[1]):
                            print("✅ [Honors Shortcut] Detected honors/non-honors pair for same UC course.")
                            return "❌ No, these courses are equivalent for UC transfer credit."

                    satisfied, validation_msg = explain_if_satisfied(selected, logic_block)
                    if not satisfied:
                        return validation_msg

                prompt = build_prompt(
                    logic=logic,
                    user_question=question_override,
                    prompt_type=PromptType.COURSE_EQUIVALENCY,
                    uc_course=doc.metadata.get("uc_course", ""),
                    uc_course_title=doc.metadata.get("uc_title", ""),
                    group_id=doc.metadata.get("group", ""),
                    group_title=doc.metadata.get("group_title", ""),
                    group_logic_type=doc.metadata.get("group_logic_type", ""),
                    section_title=doc.metadata.get("section_title", ""),
                    n_courses=doc.metadata.get("n_courses"),
                    rendered_logic=rendered_logic
                )

                response = Settings.llm.complete(prompt=prompt, max_tokens=512).text.strip()
                uc_name = doc.metadata.get("uc_course", "Unknown UC Course")
                responses_by_uc[uc_name] = response

            # 🎯 Print all per-UC course responses cleanly
            for uc, text in responses_by_uc.items():
                print(f"📘 {uc}:\n{text}\n")

        else:
            print("⚠️ No UC/CCC match — using fallback vector search.\n")
            response = self.query_engine.query(query)
            if hasattr(response, "source_nodes"):
                print("🧠 AI:", response.response.strip(), "\n")
                for node in response.source_nodes:
                    print(f"🔍 Source: {node.metadata.get('uc_course', 'N/A')} | CCC: {', '.join(node.metadata.get('ccc_courses', [])) or 'None'}")
                    print(f"   {node.text[:150]}...\n")
            else:
                print("🧠 AI:", response.strip(), "\n")

    def format_multi_uc_response(self, courses, answers):
        return "\n\n".join([
            f"**{course}**:\n{answer.strip()}" for course, answer in zip(courses, answers)
        ])
    
    @staticmethod
    def strip_ai_meta(response: str) -> str:
        # Remove AI-style headers, meta explanations, and filler phrases
        patterns = [
            r"(?i)^here'?s my response.*?\n",                  # "Here's my response"
            r"(?i)^I'?m TransferAI.*?\n",                      # "I'm TransferAI"
            r"(?i)^📨 \*\*Student Question:\*\*.*?\n",         # Student Question section
            r"(?i)^🎓 \*\*UC Course:\*\*.*?\n",                # UC Course header
            r"(?i)^✅ \*\*How to Respond:\*\*.*?\n",           # Instructional headers
            r"(?i)^That'?s it!.*?\n",                          # Casual wrap-up
            r"(?i)I'?ll make sure to.*?(?:\n|$)",              # Self-referential filler
            r"(?i)I'?m committed to.*?(?:\n|$)",               # More filler
        ]

        cleaned = response
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned, flags=re.MULTILINE)

        return cleaned.strip()



    def handle_multi_uc_query(self, query: str, uc_courses: list):
        results = []

        for uc in uc_courses:
            print(f"📤 Evaluating course: {uc}")
            doc = next(
                (d for d in self.docs if normalize_course_code(d.metadata.get("uc_course", "")) == uc),
                None
            )

            if not doc:
                results.append(f"No articulation found for {uc}.")
                continue

            rendered_logic = render_logic_str(doc.metadata)
            logic = render_logic(doc.metadata)

            prompt = build_prompt(
                logic=logic,
                user_question=query.strip(),
                prompt_type=PromptType.COURSE_EQUIVALENCY,
                uc_course=doc.metadata.get("uc_course", ""),
                uc_course_title=doc.metadata.get("uc_title", ""),
                group_id=doc.metadata.get("group", ""),
                group_title=doc.metadata.get("group_title", ""),
                group_logic_type=doc.metadata.get("group_logic_type", ""),
                section_title=doc.metadata.get("section_title", ""),
                n_courses=doc.metadata.get("n_courses"),
                rendered_logic=rendered_logic
            )

            response = Settings.llm.complete(prompt=prompt, max_tokens=512).text
            results.append(self.strip_ai_meta(response.strip()))

        return self.format_multi_uc_response(uc_courses, results)



    def run_cli_loop(self):
        print("\n🤖 TransferAI Chat (type 'exit' to quit)\n")
        print("🛠️ Debug Shortcuts: `!group N` or `!section A`\n")
        while True:
            try:
                query = input("You: ")
                if query.lower() in ["exit", "quit"]:
                    break
                print("AI is thinking...\n")
                response = self.handle_query(query)
                if response:
                    print(response.strip())
            except Exception as e:
                print(f"[Error] {e}")

def main():
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    engine.run_cli_loop()


if __name__ == "__main__":
    main()