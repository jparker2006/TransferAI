from document_loader import load_documents
from query_parser import (
    extract_filters,
    extract_prefixes_from_docs,
    extract_reverse_matches,
    extract_group_matches,
    extract_section_matches
)
from logic_formatter import render_logic, render_group_summary, render_logic_str, explain_if_satisfied
from prompt_builder import build_prompt, PromptType
from llama_index.core import VectorStoreIndex, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class TransferAIEngine:
    def __init__(self):
        self.docs = []
        self.index = None
        self.query_engine = None
        self.uc_prefixes = []
        self.ccc_prefixes = []

    def configure(self):
        # 🔧 LLM Setup: TransferAI uses Ollama + LLaMA3 for safe, deterministic answers
        Settings.llm = Ollama(
            model="llama3",  # Swap with llama3:instruct or mistral if tone/guardrails needed
            temperature=0.1,  # Low temperature ensures logic fidelity (no speculation)
            request_timeout=90,  # Allows long prompts, especially for multi-section groups
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

    def validate_same_section(self, docs):
        if not docs:
            return []
        section = docs[0].metadata.get("section")
        return [d for d in docs if d.metadata.get("section") == section]

    def render_debug_meta(self, doc):
        return (
            f"📘 UC: {doc.metadata.get('uc_course', '')}\n"
            f"📗 CCC: {', '.join(doc.metadata.get('ccc_courses', [])) or 'None'}\n"
        )

    def handle_query(self, query: str):
        # # ✳️ Group inspection shortcut
        # if query.startswith("!group "):
        #     group_num = query.split("!group ")[-1].strip()
        #     matches = [d for d in self.docs if d.metadata.get("group") == group_num]
        #     print(f"\n🧪 Group {group_num} Test – {len(matches)} documents")
        #     if matches:
        #         for doc in matches[:1]:
        #             print("🔍 Group-level debug:")
        #             for k in ["group_logic_type", "n_courses", "section", "section_title"]:
        #                 print(f"  {k}: {doc.metadata.get(k)}")
        #             print("🧩 Course-level debug:")
        #             for k in ["logic_type", "course_count", "multi_course_option", "must_complete_at_uc", "options_summary"]:
        #                 print(f"  {k}: {doc.metadata.get(k)}")
        #         summary = render_group_summary(matches)
        #         print("\n📘 Group Summary:\n")
        #         print(summary)
        #     else:
        #         print("⚠️ No documents found for that group.")
        #     return

        # # ✳️ Section inspection shortcut
        # if query.startswith("!section "):
        #     sec_id = query.split("!section ")[-1].strip()
        #     matches = [d for d in self.docs if d.metadata.get("section") == sec_id]
        #     print(f"\n🧪 Section {sec_id} – {len(matches)} documents")
        #     for doc in matches:
        #         print(f"📘 {doc.metadata['uc_course']} – {doc.metadata['uc_title']}")
        #         print(f"  Logic: {doc.metadata.get('logic_type')}")
        #         print(f"  Summary: {doc.metadata.get('options_summary')}")
        #     return

        filters = extract_filters(query, self.uc_prefixes, self.ccc_prefixes)

        # Step 1: Group/section match
        group_docs = extract_section_matches(query, self.docs) or extract_group_matches(query, self.docs)
        if group_docs:
            # print("🧩 DEBUG: Group-level metadata check:")
            # for doc in group_docs[:1]:
            #     for k in ["group_logic_type", "n_courses", "section", "section_title"]:
            #         print(f"  {k}: {doc.metadata.get(k)}")
            #     for k in ["logic_type", "course_count", "multi_course_option", "must_complete_at_uc", "options_summary"]:
            #         print(f"  {k}: {doc.metadata.get(k)}")
            group_id = group_docs[0].metadata.get("group", "Unknown")
            group_title = group_docs[0].metadata.get("group_title", "")
            group_type = group_docs[0].metadata.get("group_logic_type", "")
            n_courses = group_docs[0].metadata.get("n_courses")

            if all(doc.metadata.get("group") == group_id for doc in group_docs):
                print(f"🔎 Found {len(group_docs)} matching documents in Group {group_id}.\n")
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

            for doc in group_docs:
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
                print(self.render_debug_meta(doc))
                print(f"🧠 AI: {response.strip()}\n")
            return

        # Step 2: Match by UC/CCC codes
        matched_docs = []
        for doc in self.docs:
            doc_uc = doc.metadata.get("uc_course", "").strip().upper()
            doc_ccc = [c.strip().upper() for c in doc.metadata.get("ccc_courses", [])]

            if filters.get("uc_course") and doc_uc not in map(str.upper, filters["uc_course"]):
                continue
            if filters.get("ccc_courses") and not all(cc in doc_ccc for cc in map(str.upper, filters["ccc_courses"])):
                continue

            matched_docs.append(doc)

        # Step 3: CCC reverse match fallback
        if not matched_docs and filters.get("ccc_courses"):
            matched_docs = extract_reverse_matches(query, self.docs)

        # Step 4: Section filter
        matched_docs = self.validate_same_section(matched_docs)[:3]

        # Step 5: Final rendering
        if matched_docs:
            # print("🧩 DEBUG: UC/CCC match metadata check:")
            # for doc in matched_docs[:1]:
            #     for k in ["logic_type", "course_count", "multi_course_option", "must_complete_at_uc", "options_summary"]:
            #         print(f"  {k}: {doc.metadata.get(k)}")

            print(f"🔍 Found {len(matched_docs)} matching document(s).\n")
            for doc in matched_docs:
                logic = render_logic(doc.metadata)
                rendered_logic = render_logic_str(doc.metadata)

                validation_msg = ""
                if filters.get("ccc_courses"):
                    selected = filters["ccc_courses"]
                    logic_block = doc.metadata.get("logic_block", {})
                    satisfied, validation_msg = explain_if_satisfied(selected, logic_block)
                    print("🧠 Validation:", validation_msg.strip(), "\n")

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

                if validation_msg:
                    prompt += f"\n\n🧠 Validation Check:\n{validation_msg.strip()}"

                response = Settings.llm.complete(prompt=prompt, max_tokens=512).text
                print(self.render_debug_meta(doc))
                print(f"🧠 AI: {response.strip()}\n")
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

    def run_cli_loop(self):
        print("\n🤖 TransferAI Chat (type 'exit' to quit)\n")
        print("🛠️ Debug Shortcuts: `!group N` or `!section A`\n")
        while True:
            try:
                query = input("You: ")
                if query.lower() in ["exit", "quit"]:
                    break
                print("AI is thinking...\n")
                self.handle_query(query)
            except Exception as e:
                print(f"[Error] {e}")


def main():
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    engine.run_cli_loop()


if __name__ == "__main__":
    main()
