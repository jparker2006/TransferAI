import json
import os
from llama_index.core import Document


def format_equivalency(metadata):
    if metadata.get("no_articulation"):
        return "No articulated course satisfies this UC course."

    logic = metadata.get("logic_structure", [])
    if not logic:
        return "No articulation logic provided."

    group_type = metadata.get("group_logic_type", "").lower()
    n_required = metadata.get("n_courses")
    formatted_groups = []

    for group in logic:
        codes = [c.get("course_letters", "UNKNOWN").strip() for c in group]
        joined = " AND ".join(codes)
        formatted_groups.append(f"({joined})" if len(codes) > 1 else joined)

    if group_type == "choose_one_section":
        return "Complete one of the following:\n- " + "\n- ".join(formatted_groups)
    elif group_type == "all_required":
        return "All of the following are required:\n" + " AND ".join(formatted_groups)
    elif group_type == "select_n_courses":
        return f"Select {n_required} of the following options:\n- " + "\n- ".join(formatted_groups)
    else:
        return "Equivalent De Anza options:\n- " + "\n- ".join(formatted_groups)


class DocumentAdapter:
    def __init__(self, raw):
        self.raw = raw

    def get_text(self):
        raise NotImplementedError

    def get_metadata(self):
        raise NotImplementedError


class ArticulationAdapter(DocumentAdapter):
    def get_text(self):
        m = self.raw.get("metadata", {})
        return (
            f"Title: {self.raw['title']}\n"
            f"UC Course: {m.get('uc_course', 'Unknown')}\n"
            f"CCC Courses: {', '.join(m.get('ccc_courses', [])) or 'None'}\n"
            f"Group Logic Type: {m.get('group_logic_type', 'N/A')}\n"
            f"Equivalency: {format_equivalency(m)}\n\n"
            f"{self.raw['content']}"
        )

    def get_metadata(self):
        m = self.raw.get("metadata", {})
        return {
            "uc_course": m.get("uc_course", "").strip(),
            "ccc_courses": list(map(str.strip, m.get("ccc_courses", []))) if isinstance(m.get("ccc_courses"), list) else [],
            "group": m.get("group"),
            "section": m.get("section"),
            "group_logic_type": m.get("group_logic_type"),
            "n_courses": m.get("n_courses"),
            "logic_structure": m.get("logic_structure"),
            "no_articulation": m.get("no_articulation", False),
            "doc_type": self.raw.get("metadata", {}).get("doc_type", "articulation")
        }


class OverviewAdapter(DocumentAdapter):
    def get_text(self):
        return f"Overview:\n{self.raw.get('content', '')}"

    def get_metadata(self):
        return {
            "doc_type": "overview",
            "title": self.raw.get("title", "Untitled"),
            "source": self.raw.get("metadata", {}).get("institution_from", "")
        }

# Registry for future expansion
def get_adapter(doc):
    doc_type = doc.get("metadata", {}).get("doc_type", "articulation")
    if doc_type == "articulation":
        return ArticulationAdapter(doc)
    elif doc_type == "overview":
        return OverviewAdapter(doc)
    raise ValueError(f"Unsupported document type: {doc_type}")



def load_documents(path=None):
    if path is None:
        current_dir = os.path.dirname(__file__)
        path = os.path.join(current_dir, "data/rag_data.json")
    with open(path, "r") as f:
        raw_json = json.load(f)

    docs = []
    for raw_doc in raw_json.get("documents", []):
        adapter = get_adapter(raw_doc)
        docs.append(Document(
            text=adapter.get_text(),
            metadata=adapter.get_metadata()
        ))

    return docs
