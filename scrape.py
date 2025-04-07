import json
import time
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
        instr = group.find_element(By.CSS_SELECTOR, ".instructionsPreview awc-instruction-section").get_attribute("textContent").strip()
        if instr:
            return instr
    except Exception as e:
        print(f"⚠️ Could not extract from awc-instruction-section: {e}")
    try:
        instr = group.find_element(By.CSS_SELECTOR, ".instructionsPreview awc-instruction-list").get_attribute("textContent").strip()
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

def parse_course_sets(driver):
    output = {
        "major": "",  # Set dynamically later
        "from": "De Anza College",
        "to": "University of California, San Diego",
        "general_advice": parse_general_advice(driver),
        "groups": []
    }

    group_divs = driver.find_elements(By.CLASS_NAME, "groupContainer")
    print(f"\n📦 Found {len(group_divs)} group containers on the page.")

    for group_idx, group in enumerate(group_divs, 1):
        group_number = ""
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
            # Debugging Step 1: Clearly check and log section label/header
            section_label, section_header = "", ""

            try:
                section_label = section.find_element(By.CLASS_NAME, "emphasis--label").text.strip()
                print(f"    🔖 Section {sec_idx}: Found label '{section_label}'")
            except Exception as e:
                print(f"    ⚠️ Section {sec_idx}: Label not found ({e})")

            try:
                section_header = section.find_element(By.CLASS_NAME, "emphasis--header").text.strip()
                print(f"    📑 Section {sec_idx}: Found header '{section_header}'")
            except Exception as e:
                print(f"    ⚠️ Section {sec_idx}: Header not found ({e})")

            # Use fallback if necessary
            section_id = section_label if section_label else f"NoLabel{sec_idx}"
            full_instr = f"{section_label} - {section_header}" if section_label and section_header else section_label or section_header

            section_data = {
                "section": section_id,
                "instructions": full_instr,
                "courses": []
            }

            print(f"    📝 Parsing section '{section_id}' with instructions '{full_instr}'")

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
                        or_groups = [ccc_block]

                    equivalent_sets = []
                    for or_group in or_groups:
                        and_courses = []
                        course_lines = or_group.find_elements(By.CLASS_NAME, "courseLine")
                        for cl in course_lines:
                            prefix = cl.find_element(By.CLASS_NAME, "prefixCourseNumber").text.strip()
                            title = cl.find_element(By.CLASS_NAME, "courseTitle").text.strip()
                            course_name = f"{prefix} {title}"
                            and_courses.append({
                                "name": course_name,
                                "honors": "HONORS" in course_name.upper()
                            })
                        if and_courses:
                            equivalent_sets.append(and_courses)
                    if not equivalent_sets:
                        equivalent_sets = [[{"name": "No Course Articulated", "honors": False}]]

                    course_entry = {
                        "uc_course": f"{uc_code}: {uc_title}",
                        "units": units,
                        "equivalent_sets": equivalent_sets
                    }

                    section_data["courses"].append(course_entry)
                    print(f"         ✅ Parsed UC course: {course_entry['uc_course']} with {len(equivalent_sets)} eq sets.")
                except Exception as e:
                    print(f"         ⚠️ Failed to parse rowSet: {e}")

            group_data["sections"].append(section_data)
        output["groups"].append(group_data)

    return output

def restructure_for_rag(parsed_data):
    """
    Flatten the nested structure into a list of document entries for RAG.
    Each document includes a unique id, title, combined content text, and metadata.
    The section field is included.
    """
    rag = {
        "major": parsed_data.get("major", ""),
        "from": parsed_data.get("from", ""),
        "to": parsed_data.get("to", ""),
        "general_advice": parsed_data.get("general_advice", ""),
        "documents": []
    }
    for group in parsed_data.get("groups", []):
        group_num = group.get("group_number", "")
        group_instructions = group.get("instructions", "")
        for section in group.get("sections", []):
            section_label = section.get("section", "")
            section_instructions = section.get("instructions", "")
            for course in section.get("courses", []):
                uc_course = course.get("uc_course", "")
                units = course.get("units", "")
                eq_sets = course.get("equivalent_sets", [])
                option_texts = []
                for option in eq_sets:
                    # Join courses in each equivalent set with " AND "
                    courses_text = " AND ".join([c.get("name", "") for c in option])
                    option_texts.append(courses_text)
                # Join multiple equivalent sets with " OR "
                eq_text = " OR ".join(option_texts)
                uc_code = uc_course.split(":")[0].strip() if ":" in uc_course else uc_course.strip()
                # Create a document id using group, section, and course code
                doc_id = f"group{group_num}_{section_label if section_label else 'NA'}_{uc_code.replace(' ', '')}"
                title = f"{uc_course} Articulation Requirement"
                content_lines = []
                if group_instructions:
                    content_lines.append(f"Group {group_num} Instruction: {group_instructions}")
                else:
                    content_lines.append(f"Group {group_num}")
                if section_instructions:
                    content_lines.append(f"Section Instruction ({section_label}): {section_instructions}")
                if units:
                    content_lines.append(f"UC Course: {uc_course} ({units} units)")
                else:
                    content_lines.append(f"UC Course: {uc_course}")
                content_lines.append("Equivalent Options:")
                content_lines.append(eq_text)
                content = "\n".join(content_lines)
                metadata = {
                    "group": group_num,
                    "section": section_label,
                    "uc_course": uc_code,
                    "units": units,
                    "institution_from": parsed_data.get("from", ""),
                    "institution_to": parsed_data.get("to", "")
                }
                rag["documents"].append({
                    "doc_id": doc_id,
                    "title": title,
                    "content": content,
                    "metadata": metadata
                })
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
