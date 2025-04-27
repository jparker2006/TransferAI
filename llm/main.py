"""
Main Engine Module for TransferAI

This module provides the core TransferAIEngine class that coordinates the entire system.
It handles:

1. Configuration of LLM and embedding models
2. Loading and indexing of articulation data
3. Processing user queries and routing to appropriate handlers
4. Generating responses based on retrieved articulation information
5. Handling various query types including course equivalency, validation, and group requirements

The TransferAIEngine integrates all components (document loader, query parser, logic formatter,
and prompt builder) to provide a seamless interface for answering articulation questions.
"""

from llm.document_loader import load_documents
from llm.query_parser import (
    extract_filters,
    extract_prefixes_from_docs,
    extract_reverse_matches,
    extract_group_matches,
    extract_section_matches,
    normalize_course_code,
    find_uc_courses_satisfied_by
)
from articulation import (
    render_logic_str, 
    render_logic_v2,
    render_group_summary, 
    explain_if_satisfied, 
    validate_combo_against_group,
    include_binary_explanation,
    validate_uc_courses_against_group_sections,
    is_honors_pair_equivalent,
    render_binary_response,
    is_articulation_satisfied,
    render_combo_validation,
    explain_honors_equivalence,
    is_honors_required
)
from articulation.analyzers import (
    find_uc_courses_satisfied_by,
    get_uc_courses_satisfied_by_ccc,
    count_uc_matches
)
from llm.prompt_builder import build_prompt, PromptType
from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
import json, re
from typing import List, Any, Optional


class TransferAIEngine:
    """
    Core engine that coordinates the TransferAI articulation system.
    
    This class integrates all components of the TransferAI system including document loading,
    query parsing, and response generation. It manages both vector search and rule-based matching
    for articulation queries, handling various query types like course equivalency, group requirements,
    and validation of course combinations.
    
    Attributes:
        docs: List of loaded articulation documents.
        index: Vector store index for semantic search.
        query_engine: LlamaIndex query engine for fallback searches.
        uc_prefixes: List of UC department prefixes (e.g., "CSE", "MATH").
        ccc_prefixes: List of CCC department prefixes.
        uc_course_catalog: Set of known UC courses.
        ccc_course_catalog: Set of known CCC courses.
    """
    def __init__(self):
        """
        Initialize the TransferAI engine with empty state.
        
        The engine starts with empty collections that will be populated during the
        configure and load steps.
        """
        self.docs = []
        self.index = None
        self.query_engine = None
        self.uc_prefixes = []
        self.ccc_prefixes = []

        # 🔧 New: full course catalogs (used for smarter query parsing)
        self.uc_course_catalog = set()
        self.ccc_course_catalog = set()


    def configure(self) -> None:
        """
        Configure LLM and embedding models for the TransferAI system.
        
        Sets up:
        1. A small, efficient LLM model with a specialized system prompt for articulation queries
        2. An embedding model optimized for semantic search in articulation documents
        """
        # 🔧 LLM Setup: TransferAI uses Ollama + smaller model for more accurate responses
        Settings.llm = Ollama(
            model="deepseek-r1:1.5b",  # Small 1.1GB model that's already available
            temperature=0,  # Zero temperature for deterministic responses with no speculation
            request_timeout=120,  # Reduced timeout for faster responses
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
                "For yes/no questions, always start with a clear 'Yes' or 'No' based on the articulation data, not your own reasoning.\n"
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

    def load(self) -> None:
        """
        Load and index articulation documents for querying.
        
        This method:
        1. Loads articulation documents from the data source
        2. Creates a vector index for semantic search
        3. Extracts course prefixes and builds course catalogs for lookup
        """
        self.docs = [doc for doc in load_documents() if doc.text.strip()]
        self.index = VectorStoreIndex.from_documents(self.docs)
        self.query_engine = self.index.as_query_engine(similarity_top_k=10)

        self.uc_prefixes = extract_prefixes_from_docs(self.docs, "uc_course")
        self.ccc_prefixes = extract_prefixes_from_docs(self.docs, "ccc_courses")

        self.build_course_catalogs()

    def validate_same_section(self, docs: List[Any]) -> List[Any]:
        """
        Filter documents to keep only those in the same section as the first document.
        
        This is used for ensuring consistency when responding to section-specific queries,
        as articulation rules can vary between sections.
        
        Args:
            docs: List of articulation documents to filter.
            
        Returns:
            A filtered list of documents all belonging to the same section.
        """
        if not docs:
            return []
        section = docs[0].metadata.get("section")
        return [d for d in docs if d.metadata.get("section") == section]

    def build_course_catalogs(self) -> None:
        """
        Build comprehensive catalogs of all UC and CCC courses in the data.
        
        These catalogs are used for improving query parsing and course code recognition,
        allowing the system to identify course mentions in user queries.
        """
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

    def render_debug_meta(self, doc: Any) -> str:
        """
        Generate a debug string for document metadata.
        
        Args:
            doc: The document to extract metadata from.
            
        Returns:
            A formatted string with UC course and CCC course information.
        """
        return (
            f"📘 UC: {doc.metadata.get('uc_course', '')}\n"
            f"📗 CCC: {', '.join(doc.metadata.get('ccc_courses', [])) or 'None'}\n"
        )

    def handle_query(self, query: str) -> Optional[str]:
        """
        Process a user query and generate an articulation response.
        
        This core method handles the full query processing pipeline:
        1. Extract UC/CCC course references and filters from the query
        2. Match to appropriate documents based on query type (group, course, validation)
        3. Apply specialized logic for different query cases
        4. Generate a formatted response with articulation information
        
        Args:
            query: The user's natural language query about course articulation.
            
        Returns:
            A formatted response string with articulation information, or None if
            a direct response is not needed (e.g., for group queries handled by the LLM).
            
        Note:
            This method contains multiple specialized handlers for different query patterns
            and fallback mechanisms to ensure reliable responses.
        """
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
                    explanation = f"Your UC course combination ({', '.join(filters['uc_course'])}) satisfies Group {group_id} Section {validation['satisfied_section_id']}."
                    return render_binary_response(True, explanation)
                else:
                    missing = validation.get("missing_uc_courses", [])
                    explanation = f"Your courses do not fully satisfy any single section of Group {group_id}.\nYou're missing: {', '.join(missing)}."
                    return render_binary_response(False, explanation)

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
                        explanation = f"Your courses ({', '.join(filters['ccc_courses'])}) fully satisfy Group {group_id}.\n\nMatched UC courses: {', '.join(validation['satisfied_uc_courses'])}."
                        return render_binary_response(True, explanation)
                    elif validation["partially_satisfied"]:
                        missing = (
                            validation["required_count"] - validation["satisfied_count"]
                            if validation["required_count"] is not None
                            else "some required courses"
                        )
                        explanation = (
                            f"Your courses partially satisfy Group {group_id}.\n"
                            f"You've matched: {', '.join(validation['satisfied_uc_courses'])}, "
                            + (
                                f"but you still need {missing} more UC course(s)."
                                if isinstance(missing, int)
                                else "but they span across multiple sections. To satisfy Group 1, all UC courses must come from the same section."
                            )
                        )
                        return render_binary_response(False, explanation)
                    else:
                        explanation = f"Your courses do not satisfy Group {group_id}.\nNo UC course articulation paths were matched."
                        return render_binary_response(False, explanation)

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
                    logic = render_logic_str(doc.metadata)
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

            # ✅ R31 — Single CCC → exactly 1 UC course match
            if filters.get("ccc_courses") and len(filters["ccc_courses"]) == 1:
                ccc = filters["ccc_courses"][0]
                match_count, direct_matches, contribution_matches = count_uc_matches(ccc, self.docs)
                
                if match_count == 0 and not contribution_matches:
                    return f"❌ No, {ccc} does not satisfy any UC course requirements."
                elif match_count == 1:
                    message = f"❌ No, {ccc} alone only satisfies {direct_matches[0]}."
                    if contribution_matches:
                        message += f"\n\nHowever, {ccc} can contribute to satisfying {', '.join(contribution_matches)} when combined with additional courses."
                    return message
                elif match_count > 1:
                    message = f"✅ Yes, {ccc} can satisfy multiple UC courses: {', '.join(direct_matches)}."
                    if contribution_matches:
                        message += f"\n\nAdditionally, it can contribute to satisfying {', '.join(contribution_matches)} when combined with other courses."
                    return message

            # ✅ R4 safeguard — enforce UC course filter if present
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
                logic = render_logic_str(doc.metadata)
                rendered_logic = render_logic_str(doc.metadata)

                question_override = query.strip()
                if not filters.get("uc_course"):
                    question_override = f"Which courses satisfy {doc.metadata.get('uc_course', 'this course')}?"

                # ✅ CCC-based validation (ex: user asks "does XYZ course satisfy…")
                if filters.get("ccc_courses"):
                    selected = filters["ccc_courses"]
                    logic_block = doc.metadata.get("logic_block", {})

                    # ✅ Test 20 — Honors/non-honors equivalence
                    if len(selected) == 2 and is_honors_pair_equivalent(logic_block, selected[0], selected[1]):
                        print("✅ [Honors Shortcut] Detected honors/non-honors pair for same UC course.")
                        return f"✅ Yes, {explain_honors_equivalence(selected[0], selected[1])}"

                    # Use structured validation instead of direct explain_if_satisfied
                    validation = is_articulation_satisfied(logic_block, selected)
                    if not validation["is_satisfied"]:
                        explanation = validation["explanation"]
                        return render_binary_response(False, explanation, doc.metadata.get("uc_course", ""))
                    else:
                        # For satisfied cases, continue with normal prompt generation
                        print(f"✅ [Validation] {selected} satisfies {doc.metadata.get('uc_course', '')}") 

                # 🧠 Prompt still runs for all non-short-circuited logic
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

            # 🎯 Print all UC-course-specific responses
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

        # Check for specific question patterns
        if "require honors" in query.lower() and filters.get("uc_course"):
            for uc_course in filters["uc_course"]:
                doc = next((d for d in self.docs if normalize_course_code(d.metadata.get("uc_course", "")) == normalize_course_code(uc_course)), None)
                if doc:
                    logic_block = doc.metadata.get("logic_block", {})
                    honors_required = is_honors_required(logic_block)
                    if honors_required:
                        return f"# ✅ Yes, {uc_course} requires honors courses.\n\nBased on the official articulation data, only honors courses will satisfy {uc_course}. Non-honors options are not available."
                    else:
                        return f"# ❌ No, {uc_course} does not require honors courses.\n\nBased on the official articulation data, you can satisfy {uc_course} with either honors or non-honors courses."
                        
            # Default response if no specific UC course found
            return "Cannot determine honors requirements without a valid UC course."
            
        # Check for articulation availability questions
        if any(term in query.lower() for term in ["articulated", "equivalent", "satisfy", "transfer to"]) and filters.get("uc_course"):
            for uc_course in filters["uc_course"]:
                doc = next((d for d in self.docs if normalize_course_code(d.metadata.get("uc_course", "")) == normalize_course_code(uc_course)), None)
                if doc:
                    logic_block = doc.metadata.get("logic_block", {})
                    if isinstance(logic_block, dict) and logic_block.get("no_articulation", False):
                        return f"# ❌ No, {uc_course} has no articulation at De Anza.\n\nThis course must be completed at UCSD. There are no De Anza courses that satisfy this requirement."
                    else:
                        # This has articulation options, let the normal flow handle it
                        pass
                        
            # Default case will continue to normal flow

    def handle_multi_uc_query(self, query: str, uc_courses: list) -> str:
        """
        Handle queries involving multiple UC courses.
        
        Processes each UC course separately and combines the results into a
        single comprehensive response.
        
        Args:
            query: The original user query.
            uc_courses: List of UC course codes mentioned in the query.
            
        Returns:
            A formatted response string containing articulation information
            for each UC course.
        """
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
            logic = render_logic_str(doc.metadata)

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

    def format_multi_uc_response(self, courses: List[str], answers: List[str]) -> str:
        """
        Format multiple UC course responses into a single coherent response.
        
        Args:
            courses: List of UC course codes.
            answers: List of corresponding response texts.
            
        Returns:
            A formatted string with each course and its answer clearly separated.
        """
        return "\n\n".join([
            f"**{course}**:\n{answer.strip()}" for course, answer in zip(courses, answers)
        ])
    
    @staticmethod
    def strip_ai_meta(response: str) -> str:
        """
        Remove AI-style headers and meta explanations from responses.
        
        This cleans up LLM-generated responses by removing various boilerplate phrases,
        headers, and self-references to produce more professional, concise answers.
        
        Args:
            response: The raw response from the LLM.
            
        Returns:
            A cleaned string with boilerplate and meta-text removed.
        """
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

    def run_cli_loop(self) -> None:
        """
        Run an interactive command-line interface for the TransferAI system.
        
        Processes user queries continually until the user exits, handling exceptions
        gracefully and providing debug shortcuts.
        """
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
    """
    Entry point for the TransferAI system.
    
    Initializes the TransferAIEngine, configures models, loads articulation data,
    and starts the interactive CLI loop.
    """
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    engine.run_cli_loop()


if __name__ == "__main__":
    main()