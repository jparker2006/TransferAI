import json
import os
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
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 25)
    print("🚀 Driver setup complete.")
    return driver, wait

def select_schools(driver, wait, cc_name, uni_name):
    driver.get("https://assist.org")
    print("🌐 Navigated to assist.org")

    # Select community college
    # print(f"🔎 Searching for CCC: {cc_name}")
    ccc_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Select an institution']")))
    ccc_input.click()
    ccc_input.send_keys(cc_name)
    ccc_input.send_keys(Keys.RETURN)
    print(f"✅ Selected CCC: {cc_name}")

    # Select university
    # print(f"🔎 Searching for UC: {uni_name}")
    uc_input = wait.until(EC.element_to_be_clickable((By.XPATH, "(//input[@placeholder='Select an institution'])[2]")))
    uc_input.click()
    uc_input.send_keys(uni_name)
    uc_input.send_keys(Keys.RETURN)
    print(f"✅ Selected UC: {uni_name}")

def select_major(driver, wait, major_filter):
    view_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'View Agreements') and not(@disabled)]"))
    )
    view_button.click()
    # print("🔎 Clicked 'View Agreements'")

    major_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Filter Major List']")))
    major_input.click()
    major_input.clear()
    # print(f"🔎 Filtering major list for: {major_filter}")
    major_input.send_keys(major_filter)

    cs_major = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//div[@id='autocomplete-options--destination']//a[.//div[contains(text(), '{major_filter}')]]")
        )
    )
    driver.execute_script("arguments[0].click();", cs_major)
    print(f"🎯 Clicked major: {major_filter}")


def scroll_all_emphases(driver, wait=None):
    if wait is None:
        wait = WebDriverWait(driver, 10)

    section_blocks = driver.find_elements(By.CLASS_NAME, "emphasis--section")
    print(f"🔎 Found {len(section_blocks)} emphasis--section blocks. Scrolling...")

    seen_ids = set()

    for idx, section in enumerate(section_blocks, 1):
        try:
            section_id = section.get_attribute("id") or f"idx_{idx}"
            if section_id in seen_ids:
                continue

            driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", section)
            wait.until(EC.visibility_of(section))
            seen_ids.add(section_id)

        except Exception as e:
            print(f"  ⚠️ Could not scroll to block {idx}: {e}")

    print(f"✅ Finished scrolling {len(seen_ids)} emphasis blocks")

def parse_general_advice(driver):
    try:
        advice = driver.find_element(By.CLASS_NAME, "generalInformation").text.strip()
        # print("📝 Found general advice text.")
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
        # print(f"         ⚠️ Failed to parse courseLine: {e}")
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
    def no_articulation_block():
        return {
            "type": "OR",
            "courses": [{
                "name": "No Course Articulated",
                "honors": False,
                "course_letters": "N/A",
                "title": "No Course Articulated",
                "course_id": hash_id("No Course Articulated")
            }],
            "no_articulation": True
        }

    try:
        content_div = ccc_block.find_element(By.CLASS_NAME, "view_sending__content")
    except:
        return no_articulation_block()

    children = content_div.find_elements(By.XPATH, "./*")

    non_empty_children = [
        child for child in children
        if child.get_attribute("class") and child.get_attribute("class").strip()
    ]

    has_course_line = any("courseLine" in (child.get_attribute("class") or "") for child in non_empty_children)
    has_bracket = any("bracketWrapper" in (child.get_attribute("class") or "") for child in non_empty_children)

    if not has_course_line and not has_bracket:
        return no_articulation_block()

    course_paths = []

    for child in non_empty_children:
        try:
            class_attr = (child.get_attribute("class") or "").lower()
            if "conjunction" in class_attr:
                continue

            elif "bracketwrapper" in class_attr:
                course_lines = child.find_elements(By.CLASS_NAME, "courseLine")
                and_group = []
                for cl in course_lines:
                    course = parse_single_course(cl)
                    if course:
                        and_group.append(normalize(course))
                if and_group:
                    course_paths.append({
                        "type": "AND",
                        "courses": and_group
                    })

            elif "courseline" in class_attr:
                course = parse_single_course(child)
                if course:
                    course_paths.append(normalize(course))

        except Exception as e:
            print(f"⚠️ Error parsing sending child: {e}")

    if not course_paths:
        return no_articulation_block()

    return {
        "type": "OR",
        "courses": course_paths
    }

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
    print(f"📦 Found {len(group_divs)} group containers on the page.")

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
        parsed_sections = []

        for sec_idx, section in enumerate(section_blocks, 1):
            section_label, section_header = "", ""

            # 🏷️ Try to extract section label (e.g., "A", "B")
            try:
                section_label = section.find_element(By.CLASS_NAME, "letterContent").text.strip()
            except:
                try:
                    label_elem = section.find_element(By.CLASS_NAME, "emphasis--label")
                    section_label = label_elem.text.strip()
                    if not section_label:
                        for span in label_elem.find_elements(By.TAG_NAME, "span"):
                            txt = span.text.strip()
                            if txt:
                                section_label = txt
                                break
                except:
                    section_label = f"NoLabel{sec_idx}"

            # 📘 Try to extract section instruction/header
            try:
                section_header = section.find_element(By.CLASS_NAME, "emphasis--header").text.strip()
            except:
                section_header = ""

            section_id = section_label if section_label else f"NoLabel{sec_idx}"
            full_instr = f"{section_label} - {section_header}" if section_label and section_header else section_label or section_header

            # 🔍 Determine section logic
            section_logic_type = "all_required"
            n_courses = None
            try:
                match = re.search(r"select\s+(\d+)\s+course", full_instr.lower())
                if match:
                    section_logic_type = "select_n_courses"
                    n_courses = int(match.group(1))
            except:
                pass

            # 📦 Build section data structure
            section_data = {
                "section_id": section_id,
                "section_title": full_instr,
                "section_logic_type": section_logic_type,
                "uc_courses": []
            }
            if n_courses:
                section_data["n_courses"] = n_courses

            row_sets = section.find_elements(By.CLASS_NAME, "articRow")
            for rowset in row_sets:
                try:
                    # 🔽 UC course block
                    uc_block = rowset.find_element(By.CLASS_NAME, "rowReceiving")
                    uc_code = uc_block.find_element(By.CLASS_NAME, "prefixCourseNumber").text.strip()
                    uc_title = uc_block.find_element(By.CLASS_NAME, "courseTitle").text.strip()

                    units = None
                    try:
                        units_text = uc_block.find_element(By.CLASS_NAME, "courseUnits").text.strip()
                        units = float(units_text.replace("units", "").strip())
                    except:
                        pass

                    # 🔁 CCC articulation logic
                    ccc_block = rowset.find_element(By.CLASS_NAME, "rowSending")
                    equivalent_sets = parse_equivalent_sets_from_sending_block(ccc_block)

                    if not equivalent_sets:
                        print(f"         ❌ EMPTY equivalent_sets for UC course: {uc_code}")

                    course_entry = {
                        "uc_course": f"{uc_code}: {uc_title}",
                        "units": units,
                        "equivalent_sets": equivalent_sets
                    }

                    section_data["uc_courses"].append(course_entry)
                except Exception as e:
                    print(f"         ⚠️ Failed to parse rowSet: {e}")

            parsed_sections.append(section_data)

            group_data["sections"].append(section_data)
        output["groups"].append(group_data)

    return output

def infer_group_logic_type(instruction: str, section_count: int) -> str:
    instruction = (instruction or "").lower()

    if "select" in instruction and "course" in instruction:
        return "select_n_courses"
    if "all required" in instruction or "required" in instruction:
        return "all_required"
    if section_count >= 2 and "or" in instruction:
        return "choose_one_section"

    # Safe fallback: one section = all required
    return "all_required"

def infer_required_course_count(instruction: str) -> int:
    match = re.search(r"select\s+(\d+)\s+courses?", instruction.lower())
    return int(match.group(1)) if match else 1

def hash_id(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]

def extract_course_letters_and_title(full_name: str):
    parts = full_name.strip().replace(":", "").split(" ", 2)
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}", parts[2] if len(parts) == 3 else ""
    return full_name.strip(), ""

def format_course_letters(course_name):
    return " ".join(course_name.replace(":", "").split()[:2])

def normalize(entry):
    if isinstance(entry, str):
        name = entry.strip()
        honors = False
    else:
        name = entry.get("name", "").strip()
        honors = entry.get("honors", False)

    letters = format_course_letters(name)
    title = name.replace(letters, "").strip(" -:")
    return {
        "name": name,
        "honors": honors,
        "course_id": hash_id(letters),
        "course_letters": letters,
        "title": title
    }


def restructure_for_rag(parsed_data):
    rag = {
        "major": parsed_data.get("major", ""),
        "from": parsed_data.get("from", ""),
        "to": parsed_data.get("to", ""),
        "source_url": parsed_data.get("source_url", ""),
        "catalog_year": parsed_data.get("catalog_year"),
        "general_advice": parsed_data.get("general_advice", ""),
        "groups": []
    }

    for group in parsed_data.get("groups", []):
        group_id = group.get("group_number", "")
        raw_group_instruction = group.get("instructions", "").strip()
        section_count = len(group.get("sections", []))
        group_logic_type = infer_group_logic_type(raw_group_instruction, section_count)

        group_instruction = raw_group_instruction or (
            "Complete one of the following sections" if group_logic_type == "choose_one_section" else
            f"Select {infer_required_course_count(raw_group_instruction)} course(s) from the following" if group_logic_type == "select_n_courses" else
            "All of the following UC courses are required" if group_logic_type == "all_required" else
            "See section-specific instructions"
        )

        section_list = []

        for section in group.get("sections", []):
            section_id = section.get("section_id", "")
            section_title = section.get("section_title", "").strip() or f"Section {section_id}"
            section_logic_type = section.get("section_logic_type", "all_required")
            n_courses = section.get("n_courses", None)

            uc_courses = []
            for course in section.get("uc_courses", []):
                uc_course_raw = course.get("uc_course", "")
                units = course.get("units", "")
                logic_block = course.get("equivalent_sets", {})
                uc_letters, uc_title = extract_course_letters_and_title(uc_course_raw)

                # Ensure proper structure
                if not isinstance(logic_block, dict) or "courses" not in logic_block:
                    logic_block = {
                        "type": "OR",
                        "courses": [{
                            "name": "No Course Articulated",
                            "honors": False,
                            "course_id": hash_id("No Course Articulated"),
                            "course_letters": "N/A",
                            "title": "No Course Articulated"
                        }],
                        "no_articulation": True
                    }
                else:
                    # Wrap every logic path in {type: AND, courses: [...]} even if it's a single course
                    new_courses = []
                    for entry in logic_block["courses"]:
                        if isinstance(entry, dict) and entry.get("type") == "AND":
                            # Already normalized
                            new_courses.append(entry)
                        elif isinstance(entry, list):
                            new_courses.append({
                                "type": "AND",
                                "courses": entry
                            })
                        else:
                            new_courses.append({
                                "type": "AND",
                                "courses": [entry]
                            })
                    logic_block["courses"] = new_courses

                uc_courses.append({
                    "uc_course_id": uc_letters,
                    "uc_course_title": uc_title,
                    "units": units,
                    "section_id": section_id,
                    "section_title": section_title,
                    "logic_block": logic_block
                })

            section_obj = {
                "section_id": section_id,
                "section_title": section_title,
                "section_logic_type": section_logic_type,
                "uc_courses": uc_courses
            }
            if section_logic_type == "select_n_courses" and n_courses:
                section_obj["n_courses"] = n_courses

            section_list.append(section_obj)


        group_obj = {
            "group_id": group_id,
            "group_title": group_instruction,
            "group_logic_type": group_logic_type,
            "sections": section_list
        }

        if group_logic_type == "select_n_courses":
            group_obj["n_courses"] = infer_required_course_count(group_instruction)

        rag["groups"].append(group_obj)

    return rag

# import re
def slugify(name: str) -> str:
    name = name.lower().replace('&', 'and')
    name = name.replace('.', '')  # Remove periods like in "B.S."
    name = re.sub(r'[^a-z0-9]+', '_', name)
    return re.sub(r'_+', '_', name).strip('_')



def scrape_articulation(driver, wait, cc_name, uni_name, major_filter):
    select_major(driver, wait, major_filter)


    # print("⏳ Waiting for articulation groups to load...")
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "groupContainer")))
    # print("✅ groupContainer(s) loaded.")

    source_url = driver.current_url
    print("Source URL: ", source_url)

    # print("🔎 Scrolling to ensure lazy-loaded content is visible...")
    scroll_all_emphases(driver)
    # time.sleep(2)  # Extra wait for dynamic content

    parsed_data = parse_course_sets(driver)
    parsed_data["major"] = major_filter  # Update major from parameter
    parsed_data["source_url"] = source_url
    rag_data = restructure_for_rag(parsed_data)


    # Saving the file
    ccc_slug = slugify(cc_name)
    uc_slug = slugify(uni_name)
    major_slug = slugify(major_filter)
    catalog_year = "2024_2025"

    output_dir = os.path.join("data", "assist_data", ccc_slug, uc_slug)
    os.makedirs(output_dir, exist_ok=True)

    # Final filename
    filename = f"{major_slug}__{catalog_year}.json"
    file_path = os.path.join(output_dir, filename)

    # Save
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(rag_data, f, indent=2, ensure_ascii=False)


    print("✅ RAG JSON written to " + file_path)




def scrape_majors_only(driver, wait, cc_name, uc_name):
    print(f"🎯 Scraping major list for {cc_name} → {uc_name}")
    select_schools(driver, wait, cc_name, uc_name)

    view_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'View Agreements') and not(@disabled)]"))
    )
    view_button.click()

    # Get source URL after transition
    wait.until(EC.presence_of_element_located((By.ID, "autocomplete-options--destination")))
    source_url = driver.current_url

    time.sleep(1)  # Allow full load of majors
    major_links = driver.find_elements(By.CSS_SELECTOR, "#autocomplete-options--destination a")

    majors = []
    for m in major_links:
        text = m.text.strip()
        if not text:
            continue
        if len(text) == 1 and text.isalpha():
            continue  # Skip headings like "A", "B", etc.
        if re.match(r"^[A-Z]\n", text):
            text = text[2:]
        if text == "All Majors":
            continue
        majors.append(text)

    print(f"✅ Found {len(majors)} cleaned majors.")

    result = {
        "from": cc_name,
        "to": uc_name,
        "source_url": source_url,
        "majors": majors
    }

    # Save to file
    os.makedirs("data/majors", exist_ok=True)
    ccc_slug = slugify(cc_name)
    uc_slug = slugify(uc_name)
    file_path = f"data/majors/{ccc_slug}__{uc_slug}__majors.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"📁 Saved major list to {file_path}")





def main():
    start = time.time()
    cc_name = "De Anza College"
    uc_name = "University of California, San Diego"

    majors = [
        "CSE: Computer Science B.S.",
        "Sociology/Economy and Society B.A.",
        "ECE: Electrical Engineering B.S.",
        "Accounting Minor: Rady School of Management",
        "Anthropology B.A. with Concentration in Archaeology",
        "Anthropology B.A. with Concentration in Biological Anthropology",
        "Anthropology B.A. with Concentration in Climate Change and Human Solutions",
        "Anthropology B.A. with Concentration in Sociocultural Anthropology",
        "Anthropology: Biological Anthropology B.S.",
        "Art: Art History/Criticism B.A. (Visual Arts)",
        "Art: Interdisciplinary Computing in the Arts Major (ICAM) B.A. (Visual Arts)",
        "Art: Media B.A. ( Visual Arts)",
        "Art: Speculative Design B.A. (Visual Arts)",
        "Art: Studio B.A. (Visual Arts)",
        "Astronomy and Astrophysics B.A.",
    ]

    driver, wait = setup_driver()

    for major in majors:
        try:
            print(f"\n🔁 Scraping {major}...")
            select_schools(driver, wait, cc_name, uc_name)  # Re-navigate per major
            scrape_articulation(driver, wait, cc_name, uc_name, major)
        except Exception as e:
            print(f"❌ Failed to scrape {major}: {e}")

    driver.quit()
    print("🔒 Driver closed.")
    end = time.time()
    print(f"⏱️ Elapsed time: {end - start:.2f} seconds")


if __name__ == "__main__":
    main()
