from document_loader import load_documents
from query_parser import extract_filters, extract_prefixes_from_docs, extract_reverse_matches
from logic_formatter import render_logic
from prompt_builder import build_prompt
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
        Settings.llm = Ollama(
            model="llama3",
            temperature=0.2,
            request_timeout=60,
            system_prompt=(
                "You are TransferAI, a trusted UC transfer advisor.\n"
                "Only answer using the course articulation data provided in the prompt.\n"
                "Use course codes (like CSE 11, CIS 36B) and logic structure (e.g. CIS 35A OR (CIS 36A AND CIS 36B)).\n"
                "Be clear, concise, and never speculate.\n"
                "If there's no match, say: 'I don't have that information.'"
            )
        )
        Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

    def load(self):
        self.docs = load_documents()
        self.index = VectorStoreIndex.from_documents(self.docs)
        self.query_engine = self.index.as_query_engine(similarity_top_k=7)
        self.uc_prefixes = extract_prefixes_from_docs(self.docs, "uc_course")
        self.ccc_prefixes = extract_prefixes_from_docs(self.docs, "ccc_courses")

    # (within TransferAIEngine)
    def validate_same_section(self, docs):
        if not docs:
            return []
        section = docs[0].metadata.get("section")
        return [d for d in docs if d.metadata.get("section") == section]

    def handle_query(self, query: str):
        filters = extract_filters(query, self.uc_prefixes, self.ccc_prefixes)
        matched_docs = []

        for doc in self.docs:
            doc_uc = doc.metadata.get("uc_course")
            if not doc_uc:
                continue
            doc_ccc = doc.metadata.get("ccc_courses") or []
            if filters.get("uc_course") and doc_uc not in filters["uc_course"]:
                continue
            if filters.get("ccc_courses") and not all(cc in doc_ccc for cc in filters["ccc_courses"]):
                continue
            matched_docs.append(doc)

        # Fallback reverse match
        if not matched_docs and filters.get("ccc_courses"):
            matched_docs = extract_reverse_matches(query, self.docs)

        # ✨ Enforce same section
        matched_docs = self.validate_same_section(matched_docs)

        # Limit for safety
        matched_docs = matched_docs[:3]

        if matched_docs:
            print(f"\U0001F50E Found {len(matched_docs)} matching document(s).\n")
            for doc in matched_docs:
                logic = render_logic(doc.metadata)
                uc_course = doc.metadata.get("uc_course", "Unknown")
                prompt = build_prompt(logic, query.strip(), uc_course)
                response = Settings.llm.complete(prompt=prompt, max_tokens=512).text
                print(f"\U0001F4D8 UC: {uc_course}")
                print(f"\U0001F4D7 CCC: {', '.join(doc.metadata.get('ccc_courses', [])) or 'None'}")
                print(f"\U0001F9E0 AI: {response}\n")
        else:
            print("⚠️ No exact UC/CCC code match — using semantic fallback.\n")
            response = self.query_engine.query(query)
            print("\U0001F9E0 AI:", response, "\n")
            for node in response.source_nodes:
                print(f"\U0001F50D Source: {node.metadata.get('uc_course', 'N/A')} | CCC: {', '.join(node.metadata.get('ccc_courses', [])) or 'None'}")
                print(f"   {node.text[:150]}...\n")


    def run_cli_loop(self):
        print("\n🤖 TransferAI Chat (type 'exit' to quit)\n")
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
