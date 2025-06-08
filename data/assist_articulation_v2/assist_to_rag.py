#!/usr/bin/env python3
"""
assist_to_rag.py - A module to convert raw ASSIST JSON files into a structured format
for Retrieval-Augmented Generation (RAG).

This module implements the logic reverse-engineered from the assist.org front-end
to transform the complex, nested JSON data into a clean, human-readable, and
context-rich format suitable for AI applications.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass, field, fields
import re
from urllib.parse import quote


# ======================================================================================
# 1. DATA MODELING & ENUMS (Replicating the JS Enums and Data Structures)
# ======================================================================================

# Sorting helper function, equivalent to `C(e)` and `V(e)` in JS
def _sort_by(key: Callable[[Any], Any]):
    return lambda arr: sorted(arr, key=key)

def _sort_by_position(items: List[Any]) -> List[Any]:
    return sorted(items, key=lambda x: x.position)

class TemplateAssetType(str, Enum):
    GENERAL_TITLE = "GeneralTitle"
    GENERAL_TEXT = "GeneralText"
    REQUIREMENT_TITLE = "RequirementTitle"
    REQUIREMENT_GROUP = "RequirementGroup"

class TemplateCellType(str, Enum):
    COURSE = "Course"
    SERIES = "Series"
    REQUIREMENT = "Requirement"
    GENERAL_EDUCATION = "GeneralEducation"
    CSUGE = "CSUGE"
    CSUAI = "CSUAI"
    IGETC = "IGETC"
    CALGETC = "CALGETC"

class SendingArticulationItemType(str, Enum):
    COURSE_GROUP = "CourseGroup"
    ADVISEMENT = "Advisement"

class SendingCourseGroupItemType(str, Enum):
    COURSE = "Course"
    ADVISEMENT = "Advisement"

class AdvisementType(str, Enum):
    N_FOLLOWING = "NFollowing"
    N_IN_N_DIFFERENT_AREAS = "NInNDifferentAreas"
    N_IN_ANY_N_AREAS = "NInAnyNAreas"
    ADDITIONAL_N_TO_REACH = "AdditionalNToReach"
    N_FROM_UNITS = "NFromUnits"
    N_TO_N_FOLLOWING = "NToNFollowing"
    
class AdvisementAmountQuantifier(str, Enum):
    NONE = "None"
    UP_TO = "UpTo"
    AT_LEAST = "AtLeast"

# Dataclasses to represent the normalized data model
def _from_dict(cls, data):
    if data is None:
        return None
    
    # Get the names of the fields for the dataclass
    field_names = {f.name for f in fields(cls)}
    
    # Filter the input data to only include keys that are fields in the dataclass
    filtered_data = {k: v for k, v in data.items() if k in field_names}
    
    return cls(**filtered_data)


@dataclass
class Course:
    prefix: str
    courseNumber: str
    courseTitle: str
    minUnits: float
    maxUnits: float
    visibleCrossListedCourses: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class Series:
    conjunction: str
    name: str
    courses: List[Course]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        if 'courses' in data and data['courses']:
            instance.courses = [_from_dict(Course, course_data) for course_data in data['courses']]
        return instance

@dataclass
class SendingCourseGroupItem:
    type: SendingCourseGroupItemType
    position: int
    course: Optional[Course] = None
    advisement: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data['course'] = _from_dict(Course, data)
        return _from_dict(cls, data)

@dataclass
class SendingArticulationItem:
    type: SendingArticulationItemType
    position: int
    courseConjunction: Optional[str] = None
    items: List[SendingCourseGroupItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        if 'items' in data and data['items']:
            instance.items = _sort_by_position([SendingCourseGroupItem.from_dict(i) for i in data['items']])
        return instance

@dataclass
class SendingArticulation:
    items: List[SendingArticulationItem] = field(default_factory=list)
    noArticulationReason: Optional[str] = None
    courseGroupConjunctions: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        if 'items' in data and data['items']:
            instance.items = _sort_by_position([SendingArticulationItem.from_dict(i) for i in data['items']])
        return instance

@dataclass
class Articulation:
    templateCellId: str
    articulation: SendingArticulation

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        # The articulation data is nested under an 'articulation' key, which then has a 'sendingArticulation' key
        if 'articulation' in data and data['articulation'] and 'sendingArticulation' in data['articulation']:
            instance.articulation = SendingArticulation.from_dict(data['articulation']['sendingArticulation'])
        else:
            instance.articulation = SendingArticulation()
        return instance

@dataclass
class Cell:
    id: str
    type: TemplateCellType
    position: int
    course: Optional[Course] = None
    series: Optional[Series] = None
    seriesAttributes: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        course_data = data.get('course')
        if course_data:
            # The cross-listed courses are siblings of the course object in the cell
            course_data['visibleCrossListedCourses'] = data.get('visibleCrossListedCourses', [])
        
        series_data = data.get('series')
        
        data['course'] = _from_dict(Course, course_data)
        data['series'] = Series.from_dict(series_data) if series_data else None
        return _from_dict(cls, data)

@dataclass
class Row:
    cells: List[Cell]
    position: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        instance.cells = [Cell.from_dict(c) for c in data.get('cells', [])]
        return instance

@dataclass
class Advisement:
    type: AdvisementType
    amount: float
    selectionType: str
    position: int
    amountUnitType: Optional[str] = None
    fromAmount: Optional[float] = None
    toAmount: Optional[float] = None
    unitType: Optional[str] = None
    amountQuantifier: Optional[str] = 'None'


    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return _from_dict(cls, data)


@dataclass
class Section:
    rows: List[Row]
    position: int
    advisements: List[Advisement] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        instance.rows = _sort_by_position([Row.from_dict(r) for r in data.get('rows', [])])
        instance.advisements = _sort_by_position([Advisement.from_dict(a) for a in data.get('advisements', [])])
        return instance

@dataclass
class TemplateAsset:
    type: TemplateAssetType
    position: int
    content: Optional[str] = None
    sections: List[Section] = field(default_factory=list)
    instruction: Optional[Dict[str, Any]] = None
    advisements: List[Advisement] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        instance = _from_dict(cls, data)
        if 'sections' in data and data['sections']:
            instance.sections = _sort_by_position([Section.from_dict(s) for s in data['sections']])
        if 'advisements' in data and data['advisements']:
            instance.advisements = _sort_by_position([Advisement.from_dict(a) for a in data.get('advisements', [])])
        return instance

@dataclass
class NormalizedAgreement:
    name: str
    sending_institution_name: str
    receiving_institution_name: str
    template_assets: List[TemplateAsset] = field(default_factory=list)
    articulations: Dict[str, Articulation] = field(default_factory=dict)

# ======================================================================================
# 2. TRANSFORMATION & NORMALIZATION (Equivalent of Ce.toModel)
# ======================================================================================

def _transform_raw_json(raw_data: Dict[str, Any]) -> NormalizedAgreement:
    """
    Transforms the raw ASSIST JSON into a normalized, sorted, and typed data model.
    This is the Python equivalent of the `Ce.toModel` logic from assist_main.js.
    """
    result = raw_data.get("result", {})
    if not result:
        raise ValueError("JSON does not contain a 'result' key.")

    # Parse all the stringified JSON fields
    try:
        receiving_institution = json.loads(result['receivingInstitution'])
        sending_institution = json.loads(result['sendingInstitution'])
        template_assets_raw = json.loads(result.get('templateAssets', '[]'))
        articulations_raw = json.loads(result.get('articulations', '[]'))
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse stringified JSON field: {e}")

    # Create a quick-lookup map for articulations by templateCellId
    articulation_map = {
        art_data['templateCellId']: Articulation.from_dict(art_data)
        for art_data in articulations_raw if 'templateCellId' in art_data
    }
    
    # The 'name' for an institution is an array, get the most recent one
    def get_institution_name(inst_data):
        names = inst_data.get('names', [])
        return names[0]['name'] if names else "Unknown Institution"

    return NormalizedAgreement(
        name=result.get("name"),
        sending_institution_name=get_institution_name(sending_institution),
        receiving_institution_name=get_institution_name(receiving_institution),
        template_assets=_sort_by_position([TemplateAsset.from_dict(asset) for asset in template_assets_raw]),
        articulations=articulation_map
    )

# ======================================================================================
# 3. TEXT GENERATION (Equivalent of Angular Pipes and Rendering Logic)
# ======================================================================================

def _format_course(course: Course, include_units=True) -> str:
    """Formats a course object into a string like 'CSE 8A: Intro to Programming (4.00 units)'"""
    title = course.courseTitle.strip()
    prefix = course.prefix.strip()
    number = course.courseNumber.strip()
    
    text = f"{prefix} {number}: {title}"
    if include_units:
        # Check if this is a variable unit course (minUnits != maxUnits)
        if course.minUnits != course.maxUnits:
            unit_str = f"({course.minUnits:.2f} - {course.maxUnits:.2f} units)"
        else:
            units = course.maxUnits
            unit_str = f"({units:.2f} units)"
        text = f"{text} {unit_str}"
    
    if course.visibleCrossListedCourses:
        cross_listed_texts = []
        for cl_course_data in course.visibleCrossListedCourses:
            # Handle both nested and direct course data structures
            if 'course' in cl_course_data:
                # Nested structure: course data is under a 'course' key (e.g., CSE case)
                cl_course = cl_course_data['course']
                if cl_course.get('prefix') and cl_course.get('courseNumber'):
                    cross_listed_texts.append(f"{cl_course['prefix'].strip()} {cl_course['courseNumber'].strip()}")
            elif cl_course_data.get('prefix') and cl_course_data.get('courseNumber'):
                # Direct structure: course data is directly in the array (e.g., Political Science case)
                cross_listed_texts.append(f"{cl_course_data['prefix'].strip()} {cl_course_data['courseNumber'].strip()}")
        if cross_listed_texts:
            text += f" (Same as {', '.join(cross_listed_texts)})"
            
    return text

def _format_series(series: Series, include_units=True) -> str:
    """Formats a series object into a string like 'HILD 2A AND HILD 2B AND HILD 2C'"""
    if not series.courses:
        return series.name if series.name else "Empty Series"
    
    course_texts = [_format_course(course, include_units=include_units) for course in series.courses]
    conjunction = f" {series.conjunction.upper()} "
    return conjunction.join(course_texts)

def _format_advisement_string(advisement: Advisement) -> str:
    """
    Converts an advisement object into a human-readable string.
    Equivalent of the `calculateAdvisementString` pipe.
    """
    def format_amount(amount, unit_type):
        unit_type_str = unit_type.lower() if unit_type != "Course" else "course"
        plural = "s" if amount > 1 and unit_type != "None" else ""
        return f"{int(amount) if amount.is_integer() else amount} {unit_type_str}{plural}"

    adv_type = advisement.type
    if adv_type == AdvisementType.N_FOLLOWING:
        return f"{advisement.selectionType} {format_amount(advisement.amount, advisement.amountUnitType)} from the following"
    if adv_type == AdvisementType.N_TO_N_FOLLOWING:
        from_str = format_amount(advisement.fromAmount, advisement.unitType).split(' ')[0]
        to_str = format_amount(advisement.toAmount, advisement.unitType)
        return f"{advisement.selectionType} {from_str} - {to_str} from the following"
    
    # Fallback for unhandled advisement types
    return "Special articulation agreement. Please check the ASSIST website for details."

def _generate_text_for_sending_articulation(articulation: SendingArticulation) -> str:
    """
    Generates the text for the 'sending' side of the agreement, handling AND/OR logic.
    """
    # If a specific reason is provided (e.g., "Must be taken at university"), use it.
    # This is the most authoritative piece of information when no courses are listed.
    if articulation.noArticulationReason and articulation.noArticulationReason.strip() and articulation.noArticulationReason != "Not Articulated":
        return articulation.noArticulationReason

    if articulation.noArticulationReason == "Not Articulated":
        return "Not Articulated"

    if not articulation.items:
        return "No Course Articulated"

    group_texts = []
    for item in articulation.items:
        if item.type == SendingArticulationItemType.COURSE_GROUP:
            course_texts = []
            for course_item in item.items:
                if course_item.type == SendingCourseGroupItemType.COURSE and course_item.course:
                    course_texts.append(_format_course(course_item.course, include_units=True))
            
            conjunction = f" {item.courseConjunction.upper()} "
            group_text = conjunction.join(course_texts)
            # Only wrap in parentheses if there is more than one course in the sub-group (e.g., for an AND condition)
            if len(course_texts) > 1:
                group_text = f"({group_text})"
            group_texts.append(group_text)

    # Determine the top-level conjunction. Default to OR, but use courseGroupConjunctions if available.
    top_level_conjunction = "OR"
    if articulation.courseGroupConjunctions and articulation.courseGroupConjunctions[0].get("groupConjunction"):
        top_level_conjunction = articulation.courseGroupConjunctions[0].get("groupConjunction")

    return f" {top_level_conjunction.upper()} ".join(group_texts)


# ======================================================================================
# 4. ORCHESTRATION & RAG OUTPUT ASSEMBLY
# ======================================================================================

def _clean_html(raw_html: str) -> str:
    """Removes HTML tags and cleans up whitespace."""
    if not raw_html:
        return ""
    clean_text = re.sub('<.*?>', '', raw_html) # Remove HTML tags
    clean_text = clean_text.replace('&nbsp;', ' ') # Replace non-breaking spaces
    return ' '.join(clean_text.split()) # Normalize whitespace

def process_assist_json_file(file_path: Union[str, Path], manual_source_url: Optional[str] = None, major_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Main orchestration function. Loads a raw ASSIST JSON, transforms it, and generates
    a structured RAG output.

    Args:
        file_path: Path to the input ASSIST JSON file.
        manual_source_url: A URL to use if one cannot be generated.
        major_key: The major key from the batch config, used for URL generation.

    Returns:
        A dictionary containing the structured RAG data.
    """
    file_path = Path(file_path)
    with open(file_path, 'r') as f:
        raw_data = json.load(f)

    # 1. Transform raw data into normalized model
    agreement = _transform_raw_json(raw_data)

    # 2. Assemble RAG documents into a hierarchical structure
    general_information = []
    requirement_groups = []
    current_requirement_area = ""
    group_id = 0

    # Process all template assets in their sorted order
    for asset in agreement.template_assets:
        if asset.type == TemplateAssetType.REQUIREMENT_TITLE:
            current_requirement_area = _clean_html(asset.content)
            continue
        
        if asset.type == TemplateAssetType.GENERAL_TEXT:
            general_information.append({
                "text": _clean_html(asset.content)
            })
            continue
        
        if asset.type == TemplateAssetType.REQUIREMENT_GROUP:
            group_id += 1
            
            # --- Start Instruction Logic ---
            group_instruction_text = ""
            if asset.instruction:
                instruction_type = asset.instruction.get('type')
                conjunction = asset.instruction.get('conjunction')
                selection_type = asset.instruction.get('selectionType', 'Complete').capitalize()
                amount = asset.instruction.get('amount')
                amount_unit_type = asset.instruction.get('amountUnitType', 'Course')

                # Handles "Complete X course from A, B, or C" type instructions
                if instruction_type == 'NFromConjunction':
                    if amount and amount > 0:
                        unit_text = amount_unit_type.lower() if amount_unit_type != "Course" else "course"
                        plural = "s" if amount > 1 and amount_unit_type == "Course" else ""
                        amount_str = int(amount) if amount.is_integer() else amount
                        
                        # Generate section labels (A, B, C, etc.)
                        section_labels = [chr(ord('A') + i) for i, _ in enumerate(asset.sections)]
                        
                        joined_labels = ""
                        # Handles "Or" conjunction for the labels
                        if conjunction == 'Or':
                            if len(section_labels) > 2:
                                joined_labels = ", ".join(section_labels[:-1]) + ", or " + section_labels[-1]
                            elif len(section_labels) == 2:
                                joined_labels = " or ".join(section_labels)
                            elif section_labels:
                                joined_labels = section_labels[0]
                        # Handles "And" conjunction for the labels
                        elif conjunction == 'And':
                            if len(section_labels) > 2:
                                joined_labels = ", ".join(section_labels[:-1]) + ", and " + section_labels[-1]
                            elif len(section_labels) == 2:
                                joined_labels = " and ".join(section_labels)
                            elif section_labels:
                                joined_labels = section_labels[0]
                        else: # Fallback for single section or unknown conjunction
                           if section_labels:
                                joined_labels = section_labels[0]

                        if joined_labels:
                            group_instruction_text = f"{selection_type} {amount_str} {unit_text}{plural} from {joined_labels}"

                # Handles "Select A, B, or C" type instructions (for instructions without a specific amount)
                elif instruction_type == 'Conjunction':
                    section_labels = [chr(ord('A') + i) for i, _ in enumerate(asset.sections)]
                    joined_labels = ""

                    if conjunction == 'Or':
                        if len(section_labels) > 2:
                            joined_labels = ", ".join(section_labels[:-1]) + ", or " + section_labels[-1]
                        elif len(section_labels) == 2:
                            joined_labels = " or ".join(section_labels)
                        elif section_labels:
                            joined_labels = section_labels[0]
                    elif conjunction == 'And':
                        if len(section_labels) > 2:
                            joined_labels = ", ".join(section_labels[:-1]) + ", and " + section_labels[-1]
                        elif len(section_labels) == 2:
                            joined_labels = " and ".join(section_labels)
                        elif section_labels:
                            joined_labels = section_labels[0]
                    
                    if joined_labels:
                        group_instruction_text = f"{selection_type} {joined_labels}"

                # Handles "Complete the following" type instructions
                elif instruction_type == 'Following':
                    group_instruction_text = f"{selection_type} the following"
                
                # Handles "Complete X courses from the following" type instructions
                elif instruction_type == 'NFromArea':
                    if amount and amount > 0:
                        unit_text = amount_unit_type.lower() if amount_unit_type != "Course" else "course"
                        plural = "s" if amount > 1 and amount_unit_type == "Course" else ""
                        amount_str = int(amount) if amount.is_integer() else amount
                        group_instruction_text = f"{selection_type} {amount_str} {unit_text}{plural} from the following"
            # --- End Instruction Logic ---

            # --- Start Group Attributes Logic ---
            group_notes = ""
            if asset.attributes:
                attribute_texts = [_clean_html(attr.get('content', '')) for attr in asset.attributes]
                group_notes = ". ".join(filter(None, attribute_texts))
            # --- End Group Attributes Logic ---

            # Group-level advisements can add to the instruction
            if asset.advisements:
                group_advisement_text = " AND ".join([_format_advisement_string(adv) for adv in asset.advisements])
                if group_instruction_text:
                    group_instruction_text += f". {group_advisement_text}"
                else:
                    group_instruction_text = group_advisement_text

            current_group = {
                "group_id": group_id,
                "requirement_area": current_requirement_area,
                "group_instruction": group_instruction_text.strip(),
                "sections": []
            }
            
            # Only add group_notes if there are attributes
            if group_notes.strip():
                current_group["group_notes"] = group_notes.strip()

            for section_index, section in enumerate(asset.sections):
                section_label = chr(ord('A') + section_index)
                section_rule_text = ""
                if section.advisements:
                    section_rule_text = " AND ".join([_format_advisement_string(adv) for adv in section.advisements])

                if section.attributes:
                    attribute_texts = [_clean_html(attr.get('content', '')) for attr in section.attributes]
                    section_attribute_text = ". ".join(filter(None, attribute_texts))
                    if section_rule_text:
                        section_rule_text += f". {section_attribute_text}"
                    else:
                        section_rule_text = section_attribute_text

                current_section = {
                    "section_label": section_label,
                    "section_rule": section_rule_text.strip(),
                    "requirements": []
                }

                for row in section.rows:
                    for cell in row.cells:
                        if cell.type == TemplateCellType.COURSE and cell.course:
                            receiving_course_text = _format_course(cell.course)
                            
                            articulation = agreement.articulations.get(cell.id)
                            sending_course_text = "No Course Articulated"
                            if articulation:
                                sending_course_text = _generate_text_for_sending_articulation(articulation.articulation)

                            current_section["requirements"].append({
                                "receiving_course_text": receiving_course_text,
                                "sending_course_text": sending_course_text,
                            })
                        elif cell.type == TemplateCellType.SERIES and cell.series:
                            receiving_series_text = _format_series(cell.series)

                            if cell.seriesAttributes:
                                attribute_texts = [_clean_html(attr.get('content', '')) for attr in cell.seriesAttributes]
                                prefix = " ".join(filter(None, attribute_texts))
                                if prefix:
                                    receiving_series_text = f"{prefix}\\n{receiving_series_text}"
                            
                            articulation = agreement.articulations.get(cell.id)
                            sending_course_text = "No Course Articulated"
                            if articulation:
                                sending_course_text = _generate_text_for_sending_articulation(articulation.articulation)

                            current_section["requirements"].append({
                                "receiving_course_text": receiving_series_text,
                                "sending_course_text": sending_course_text,
                            })
                
                if current_section["requirements"]:
                    current_group["sections"].append(current_section)
            
            if current_group["sections"]:
                requirement_groups.append(current_group)

    # 3. Generate source URL if not provided
    source_url = manual_source_url
    if not source_url and major_key:
        raw_result = raw_data.get("result", {})
        year_id = json.loads(raw_result.get('academicYear', '{}')).get('id')
        sending_id = json.loads(raw_result.get('sendingInstitution', '{}')).get('id')
        receiving_id = json.loads(raw_result.get('receivingInstitution', '{}')).get('id')
        if all([year_id, sending_id, receiving_id, major_key]):
            # This is the full key that ASSIST uses for deep linking.
            full_view_by_key = f"{year_id}/{sending_id}/to/{receiving_id}/Major/{major_key}"
            encoded_view_by_key = quote(full_view_by_key)
            source_url = (f"https://assist.org/transfer/results?year={year_id}&institution={sending_id}"
                          f"&agreement={receiving_id}&agreementType=to&viewAgreementsOptions=true"
                          f"&view=agreement&viewBy=major&viewSendingAgreements=false"
                          f"&viewByKey={encoded_view_by_key}")


    # Final RAG output structure
    return {
        "source_url": source_url,
        "agreement_title": agreement.name,
        "academic_year": "2024-2025",
        "sending_institution": agreement.sending_institution_name,
        "receiving_institution": agreement.receiving_institution_name,
        "general_information": general_information,
        "requirement_groups": requirement_groups,
    }

def save_rag_json(rag_data: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """Saves the RAG data to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(rag_data, f, indent=2) 