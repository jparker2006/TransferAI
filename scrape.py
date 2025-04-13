import json
import time
import re
import hashlib
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def setup_driver():
    options = Options()
    # Uncomment the next line to run headless if desired
    # options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 25)
    print("🚀 Driver setup complete.")
    return driver, wait

def select_schools(driver, wait, cc_name, uni_name):
    driver.get("https://assist.org")
    print("🌐 Navigated to assist.org")

    # Select community college
    print(f"🔎 Searching for CCC: {cc_name}")
    ccc_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Select an institution']")))
    ccc_input.click()
    ccc_input.send_keys(cc_name)
    time.sleep(1)
    ccc_input.send_keys(Keys.RETURN)
    print(f"✅ Selected CCC: {cc_name}")

    # Select university
    print(f"🔎 Searching for UC: {uni_name}")
    uc_input = wait.until(EC.element_to_be_clickable((By.XPATH, "(//input[@placeholder='Select an institution'])[2]")))
    uc_input.click()
    uc_input.send_keys(uni_name)
    time.sleep(1)
    uc_input.send_keys(Keys.RETURN)
    print(f"✅ Selected UC: {uni_name}")

def select_major(driver, wait, major_filter):
    view_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'View Agreements') and not(@disabled)]"))
    )
    view_button.click()
    print("🔎 Clicked 'View Agreements'")

    major_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Filter Major List']")))
    major_input.click()
    major_input.clear()
    print(f"🔎 Filtering major list for: {major_filter}")
    major_input.send_keys(major_filter)
    time.sleep(1.5)

    cs_major = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//div[@id='autocomplete-options--destination']//a[.//div[contains(text(), '{major_filter}')]]")
        )
    )
    driver.execute_script("arguments[0].click();", cs_major)
    print(f"🎯 Clicked major: {major_filter}")

def scroll_all_emphases(driver):
    section_blocks = driver.find_elements(By.CLASS_NAME, "emphasis--section")
    print(f"🔎 Found {len(section_blocks)} emphasis--section blocks. Scrolling...")
    for idx, section in enumerate(section_blocks, 1):
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", section)
            time.sleep(1.5)
            print(f"  ↳ Scrolled to emphasis block {idx}")
        except Exception as e:
            print(f"  ⚠️ Could not scroll to block {idx}: {e}")
        # Save the last section block's HTML for inspection
    if section_blocks:
        with open("debug_section_block.html", "w", encoding="utf-8") as f:
            f.write(section_blocks[-1].get_attribute("outerHTML"))
    print("✅ Finished scrolling emphasis blocks")

def parse_general_advice(driver):
    try:
        advice = driver.find_element(By.CLASS_NAME, "generalInformation").text.strip()
        print("📝 Found general advice text.")
        return advice
    except Exception as e:
        print(f"⚠️ General advice not found: {e}")
        return ""

def get_group_instructions(group):
    # Try multiple selectors until non-empty instruction text is found.
    try:
        instr = group.find_element(By.CSS_SELECTOR, "awc-instruction-section").get_attribute("textContent").strip()
        if instr:
            return instr
    except Exception as e:
        print(f"⚠️ Could not extract from awc-instruction-section: {e}")
    try:
        instr = group.find_element(By.CSS_SELECTOR, "awc-instruction-list").get_attribute("textContent").strip()
        if instr:
            return instr
    except Exception:
        pass
    try:
        instr = group.find_element(By.CLASS_NAME, "instructionsHeader").text.strip()
        if instr:
            return instr
    except Exception:
        pass
    try:
        instr = group.find_element(By.CLASS_NAME, "instructionsPreview").text.strip()
        if instr:
            return instr
    except Exception:
        pass
    try:
        instr = group.find_element(By.CLASS_NAME, "sectionAdvisements").get_attribute("textContent").strip()
        if instr:
            return instr
    except Exception:
        pass
    return ""

def parse_single_course(cl):
    try:
        prefix = cl.find_element(By.CLASS_NAME, "prefixCourseNumber").text.strip()
        title = cl.find_element(By.CLASS_NAME, "courseTitle").text.strip()
        return {
            "name": f"{prefix} {title}",
            "honors": "HONORS" in title.upper()
        }
    except Exception as e:
        print(f"         ⚠️ Failed to parse courseLine: {e}")
        return None

def parse_and_group(and_block):
    and_group = []
    course_lines = and_block.find_elements(By.CLASS_NAME, "courseLine")
    for cl in course_lines:
        course = parse_single_course(cl)
        if course:
            and_group.append(course)
    return and_group

def parse_equivalent_sets_from_sending_block(ccc_block):
    try:
        content_div = ccc_block.find_element(By.CLASS_NAME, "view_sending__content")
    except:
        print("         ❌ No .view_sending__content found — defaulting to no articulation.")
        return [[{"name": "No Course Articulated", "honors": False}]]

    children = content_div.find_elements(By.XPATH, "./*")
    print("         🧩 Children classes in sending block:")
    for child in children:
        print("            -", child.get_attribute("class"))

    non_empty_children = [child for child in children if child.get_attribute("class") and child.get_attribute("class").strip()]
    has_course_line = any("courseLine" in (child.get_attribute("class") or "") for child in non_empty_children)
    has_bracket = any("bracketWrapper" in (child.get_attribute("class") or "") for child in non_empty_children)

    if not has_course_line and not has_bracket:
        print("         ❌ No relevant courseLines or bracketWrappers — No Articulation.")
        return [[{"name": "No Course Articulated", "honors": False}]]

    equivalent_sets = []

    for child in non_empty_children:
        try:
            class_attr = child.get_attribute("class") or ""
            if "conjunction" in class_attr:
                continue
            elif "bracketWrapper" in class_attr:
                course_lines = child.find_elements(By.CLASS_NAME, "courseLine")
                and_group = []
                for cl in course_lines:
                    course = parse_single_course(cl)
                    if course:
                        and_group.append(course)
                if and_group:
                    equivalent_sets.append(and_group)
                    print(f"         ✅ Compound AND group: {' AND '.join(c['name'] for c in and_group)}")
            elif "courseLine" in class_attr:
                course = parse_single_course(child)
                if course:
                    equivalent_sets.append([course])
                    print(f"         ✅ Single-course OR: {course['name']}")
            else:
                print(f"         ⚠️ Unrecognized block class: {class_attr}")
        except Exception as e:
            print(f"         ⚠️ Error parsing sending child: {e}")

    return equivalent_sets

def parse_course_sets(driver):
    output = {
        "major": "",
        "from": "De Anza College",
        "to": "University of California, San Diego",
        "catalog_year": "2024–2025",
        "general_advice": parse_general_advice(driver),
        "groups": []
    }

    group_divs = driver.find_elements(By.CLASS_NAME, "groupContainer")
    print(f"\n📦 Found {len(group_divs)} group containers on the page.")

    for group_idx, group in enumerate(group_divs, 1):
        try:
            group_number = group.find_element(By.CLASS_NAME, "groupNumber").text.strip()
        except:
            group_number = str(group_idx)
        group_instructions = get_group_instructions(group)

        group_data = {
            "group_number": group_number,
            "instructions": group_instructions,
            "sections": []
        }

        section_blocks = group.find_elements(By.CLASS_NAME, "emphasis--section")
        print(f"🗂  Group {group_number} instructions: '{group_instructions}'")
        print(f"   ↳ Found {len(section_blocks)} sections in Group {group_number}.")

        for sec_idx, section in enumerate(section_blocks, 1):
            section_label, section_header = "", ""
            try:
                section_label = section.find_element(By.CLASS_NAME, "letterContent").text.strip()
            except:
                try:
                    label_elem = section.find_element(By.CLASS_NAME, "emphasis--label")
                    section_label = label_elem.text.strip()
                    if not section_label:
                        nested_spans = label_elem.find_elements(By.TAG_NAME, "span")
                        for span in nested_spans:
                            txt = span.text.strip()
                            if txt:
                                section_label = txt
                                break
                except:
                    section_label = f"NoLabel{sec_idx}"

            try:
                section_header = section.find_element(By.CLASS_NAME, "emphasis--header").text.strip()
            except:
                section_header = ""

            section_id = section_label if section_label else f"NoLabel{sec_idx}"
            full_instr = f"{section_label} - {section_header}" if section_label and section_header else section_label or section_header

            section_data = {
                "section": section_id,
                "instructions": full_instr,
                "courses": []
            }

            row_sets = section.find_elements(By.CLASS_NAME, "articRow")
            print(f"      ↳ Section '{section_id}': found {len(row_sets)} articRow mappings.")

            for rowset in row_sets:
                try:
                    uc_block = rowset.find_element(By.CLASS_NAME, "rowReceiving")
                    uc_code = uc_block.find_element(By.CLASS_NAME, "prefixCourseNumber").text.strip()
                    uc_title = uc_block.find_element(By.CLASS_NAME, "courseTitle").text.strip()
                    units = None
                    try:
                        units_text = uc_block.find_element(By.CLASS_NAME, "courseUnits").text.strip()
                        units = float(units_text.replace("units", "").strip())
                    except:
                        pass

                    ccc_block = rowset.find_element(By.CLASS_NAME, "rowSending")
                    or_groups = ccc_block.find_elements(By.CLASS_NAME, "orGroup")

                    if not or_groups:
                        print("         ⚠️ No .orGroup found — falling back to .rowSending > .courseLine or brackets")

                    equivalent_sets = parse_equivalent_sets_from_sending_block(ccc_block)

                    if equivalent_sets == []:
                        print(f"         ❌ EMPTY equivalent_sets for UC course: {uc_code}")

                    course_entry = {
                        "uc_course": f"{uc_code}: {uc_title}",
                        "units": units,
                        "equivalent_sets": equivalent_sets
                    }

                    section_data["courses"].append(course_entry)
                    print(f"         ✅ Parsed UC course: {course_entry['uc_course']} with {len(equivalent_sets)} eq set(s).")
                except Exception as e:
                    print(f"         ⚠️ Failed to parse rowSet: {e}")

            group_data["sections"].append(section_data)
        output["groups"].append(group_data)

    return output

def infer_group_logic_type(instruction: str) -> str:
    """Infer logical type of course group requirement based on instruction text."""
    instruction = instruction.lower()

    if "complete" in instruction and "or" in instruction:
        return "choose_one_section"  # e.g. Group 1: A or B

    if "select" in instruction and "course" in instruction:
        return "select_n_courses"  # e.g. Group 3: Select 2 courses

    return "all_required"  # Default fallback

def infer_required_course_count(instruction: str) -> int:
    match = re.search(r"select\s+(\d+)\s+courses?", instruction.lower())
    return int(match.group(1)) if match else 1

def extract_course_letters_and_title(full_name: str):
    parts = full_name.strip().split(" ", 2)
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}", parts[2] if len(parts) == 3 else ""
    return full_name.strip(), ""

def format_course_letters(course_name):
    """Extract course letters from full course name (e.g. CIS 36B from CIS 36B Java)."""
    return " ".join(course_name.split()[:2])

def hash_id(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]

def restructure_for_rag(parsed_data):
    rag = {
        "major": parsed_data.get("major", ""),
        "from": parsed_data.get("from", ""),
        "to": parsed_data.get("to", ""),
        "catalog_year": parsed_data.get("catalog_year"),
        "general_advice": parsed_data.get("general_advice", ""),
        "documents": []
    }

    # Add the overview document
    rag["documents"].append({
        "doc_id": "major_overview",
        "title": f"{rag['major']} Transfer Overview ({rag['catalog_year']})",
        "content": rag["general_advice"],
        "metadata": {
            "doc_type": "overview",
            "institution_from": rag["from"],
            "institution_to": rag["to"],
            "major": rag["major"],
            "catalog_year": rag["catalog_year"]
        }
    })

    for group in parsed_data.get("groups", []):
        group_num = group.get("group_number", "")
        raw_group_instruction = group.get("instructions", "").strip()
        group_logic_type = infer_group_logic_type(raw_group_instruction)

        # Smart fallback for missing group instructions
        if raw_group_instruction:
            group_instruction = raw_group_instruction
        else:
            if group_logic_type == "choose_one_section":
                group_instruction = "Complete one of the following options"
            elif group_logic_type == "select_n_courses":
                n = infer_required_course_count(raw_group_instruction)
                group_instruction = f"Select {n} course(s) from the options below"
            elif group_logic_type == "all_required":
                group_instruction = "All of the following are required"
            else:
                group_instruction = "See section-specific instructions"

        for section in group.get("sections", []):
            section_label = section.get("section", "")
            section_instruction = section.get("instructions", "").strip()
            section_courses = []

            for course in section.get("courses", []):
                uc_course_raw = course.get("uc_course", "")
                units = course.get("units", "")
                eq_sets = course.get("equivalent_sets", [])
                uc_course = uc_course_raw.strip().replace(":", "")
                uc_letters = format_course_letters(uc_course)
                uc_title = uc_course.replace(uc_letters, "").strip(" -:")
                section_courses.append(uc_letters)
                course_id = hash_id(uc_letters)

                is_no_articulation = (
                    len(eq_sets) == 1 and
                    len(eq_sets[0]) == 1 and
                    eq_sets[0][0].get("name", "").lower().strip() == "no course articulated"
                )

                logic_structure = []
                ccc_courses = set()

                if is_no_articulation:
                    logic_structure = [[{
                        "name": "No Course Articulated",
                        "honors": False,
                        "course_id": hash_id("No Course Articulated"),
                        "course_letters": "N/A",
                        "title": "No Course Articulated"
                    }]]
                    no_articulation = True
                else:
                    no_articulation = False
                    for eq_group in eq_sets:
                        option = []
                        for entry in eq_group:
                            name = entry.get("name", "").strip()
                            honors = entry.get("honors", False)
                            letters = format_course_letters(name)
                            title = name.replace(letters, "").strip(" -:")
                            ccc_courses.add(letters)
                            option.append({
                                "name": name,
                                "honors": honors,
                                "course_id": hash_id(letters),
                                "course_letters": letters,
                                "title": title
                            })
                        logic_structure.append(option)

                metadata = {
                    "group": group_num,
                    "section": section_label,
                    "section_courses": section_courses,
                    "section_title": section_instruction or section_label,
                    "uc_course": uc_letters,
                    "uc_course_id": course_id,
                    "uc_title": uc_title,
                    "units": units,
                    "institution_from": rag["from"],
                    "institution_to": rag["to"],
                    "catalog_year": rag["catalog_year"],
                    "logic_structure": logic_structure,
                    "ccc_courses": sorted(ccc_courses),
                    "no_articulation": no_articulation,
                    "group_logic": group_instruction,
                    "group_logic_type": group_logic_type
                }

                if group_logic_type == "select_n_courses":
                    metadata["n_courses"] = infer_required_course_count(group_instruction)

                doc = {
                    "doc_id": f"group{group_num}_{section_label}_{uc_letters.replace(' ', '')}",
                    "title": f"{uc_course} Articulation Requirement",
                    "content": f"Group {group_num} Instruction: {group_instruction}\n"
                               f"Section Instruction ({section_label}): {section_instruction}\n"
                               f"UC Course: {uc_course} ({units} units)\n"
                               f"Equivalent Options:\n{logic_structure}",
                    "metadata": metadata
                }

                rag["documents"].append(doc)

    return rag

def main():
    # Accept dynamic parameters from command line arguments if provided.
    cc_name = "De Anza College"
    uni_name = "University of California, San Diego"
    major_filter = "CSE: Computer Science B.S."
    if len(sys.argv) >= 4:
        cc_name = sys.argv[1]
        uni_name = sys.argv[2]
        major_filter = sys.argv[3]

    driver, wait = setup_driver()
    select_schools(driver, wait, cc_name, uni_name)
    select_major(driver, wait, major_filter)

    print("⏳ Waiting for articulation groups to load...")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "groupContainer")))
    print("✅ groupContainer(s) loaded.")

    print("🔎 Scrolling to ensure lazy-loaded content is visible...")
    scroll_all_emphases(driver)
    time.sleep(2)  # Extra wait for dynamic content

    # Dump full page source for debugging if needed.
    with open("debug_full_page_after_scroll.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("📝 Dumped full page to debug_full_page_after_scroll.html")

    parsed_data = parse_course_sets(driver)
    parsed_data["major"] = major_filter  # Update major from parameter
    rag_data = restructure_for_rag(parsed_data)

    with open("rag_data.json", "w", encoding="utf-8") as f:
        json.dump(rag_data, f, indent=2, ensure_ascii=False)
    print("✅ RAG JSON written to rag_data.json")
    driver.quit()
    print("🔒 Driver closed.")

if __name__ == "__main__":
    main()
