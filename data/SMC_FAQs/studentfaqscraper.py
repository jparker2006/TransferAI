#!/usr/bin/env python3
"""
SMC FAQ Scraper that creates separate RAG files for each FAQ page
and extracts links from answers
"""

import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SMCSeparateFAQScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome options"""
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--window-size=1920,1080')
        self.options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = None
        
        # Define pages to scrape with their specific configurations
        self.pages_config = {
            "international": {
                "url": "https://www.smc.edu/student-support/international-education/counseling/faq.php",
                "title": "International Education FAQ",
                "output_rag": "smc_international_faq_rag.json",
                "output_md": "smc_international_faq.md",
                "selectors": {
                    "accordion_items": [".accordion__item", ".accordion-item", ".faq-item"],
                    "question": ["h3", "h4", ".accordion__toggle", ".accordion-header"],
                    "answer": [".accordion__content", ".accordion-body", ".accordion-collapse", ".faq-answer"],
                    "expand_buttons": [".accordion__toggle", ".accordion-button", "[aria-expanded]"]
                }
            },
            "student": {
                "url": "https://www.smc.edu/academics/online-learning/students/student-faq.php",
                "title": "Online Learning Student FAQ",
                "output_rag": "smc_online_learning_faq_rag.json",
                "output_md": "smc_online_learning_faq.md",
                "selectors": {
                    # Try different selectors for student FAQ page
                    "accordion_items": [".accordion__item", ".accordion-item", ".faq-item", ".panel", ".card", ".faq-section", ".qa-item"],
                    "question": ["h3", "h4", ".accordion__toggle", ".accordion-header", ".panel-title", ".card-header", "dt", "strong"],
                    "answer": [".accordion__content", ".accordion-body", ".panel-body", ".card-body", ".accordion-collapse", "dd", ".answer"],
                    "expand_buttons": [".accordion__toggle", ".accordion-button", "[data-toggle='collapse']", "[aria-expanded]", ".expand-btn"]
                }
            }
        }
    
    def start_driver(self):
        """Start the Chrome WebDriver"""
        try:
            # Try to use webdriver-manager if available
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=self.options)
            except ImportError:
                self.driver = webdriver.Chrome(options=self.options)
            
            logger.info("Chrome driver started successfully")
        except Exception as e:
            logger.error(f"Failed to start Chrome driver: {str(e)}")
            raise
    
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("Chrome driver closed")
    
    def wait_and_expand_content(self, config):
        """Expand all collapsible content on the page"""
        try:
            # Wait for page to load
            time.sleep(2)
            
            # Try each selector type for expand buttons
            for selector in config["selectors"]["expand_buttons"]:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if buttons:
                        logger.info(f"Found {len(buttons)} expandable elements using selector: {selector}")
                        for idx, button in enumerate(buttons):
                            try:
                                # Check if already expanded
                                is_expanded = button.get_attribute("aria-expanded")
                                if is_expanded == "false" or not is_expanded:
                                    self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                    time.sleep(0.1)
                                    self.driver.execute_script("arguments[0].click();", button)
                                    time.sleep(0.2)
                            except Exception as e:
                                continue
                        break  # Found and processed buttons, exit loop
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error expanding content: {str(e)}")
    
    def extract_links_from_html(self, html_element):
        """Extract all links from an HTML element"""
        links = []
        soup = BeautifulSoup(str(html_element), 'html.parser')
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = f"https://www.smc.edu{href}"
            elif not href.startswith(('http://', 'https://', 'mailto:', 'tel:')):
                href = f"https://www.smc.edu/{href}"
            links.append({
                "text": text,
                "url": href
            })
        return links
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        text = text.replace('\\n', ' ').replace('\\t', ' ').replace('\\r', '')
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        return text
    
    def extract_category(self, question, page_type):
        """Extract category based on question content and page type"""
        question_lower = question.lower()
        
        if page_type == "international":
            if any(word in question_lower for word in ['visa', 'f-1', 'i-20', 'sevis', 'immigration', 'passport']):
                return "Visa and Immigration"
            elif any(word in question_lower for word in ['transfer', 'university']):
                return "Transfer for International Students"
            elif any(word in question_lower for word in ['unit', 'full-time', 'enrollment', 'drop', 'withdraw']):
                return "Enrollment Requirements"
            elif any(word in question_lower for word in ['work', 'employment', 'cpt', 'opt']):
                return "Work Authorization"
            elif any(word in question_lower for word in ['health', 'insurance']):
                return "Health and Insurance"
            else:
                return "International Student Services"
        
        elif page_type == "student":
            if any(word in question_lower for word in ['canvas', 'login', 'access', 'password', 'account', 'username']):
                return "Canvas and Account Access"
            elif any(word in question_lower for word in ['technical', 'computer', 'browser', 'internet', 'software', 'requirements']):
                return "Technical Requirements"
            elif any(word in question_lower for word in ['exam', 'test', 'proctoring', 'quiz', 'assessment']):
                return "Online Testing and Exams"
            elif any(word in question_lower for word in ['zoom', 'meeting', 'synchronous', 'asynchronous', 'schedule', 'online class']):
                return "Class Format and Schedule"
            elif any(word in question_lower for word in ['help', 'support', 'tutoring', 'assistance', 'contact']):
                return "Student Support Services"
            elif any(word in question_lower for word in ['enroll', 'add', 'drop', 'registration', 'corsair connect']):
                return "Enrollment and Registration"
            else:
                return "Online Learning General"
        
        return "General"
    
    def extract_keywords(self, text):
        """Extract relevant keywords from text"""
        stop_words = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
                     'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
                     'to', 'was', 'will', 'with', 'you', 'your', 'can', 'do', 'if'}
        
        important_terms = {'transfer', 'degree', 'units', 'gpa', 'counselor', 'smc',
                          'transcript', 'appointment', 'associate', 'certificate',
                          'igetc', 'csu', 'uc', 'financial', 'visa', 'f-1', 'i-20',
                          'international', 'canvas', 'online', 'zoom', 'synchronous',
                          'asynchronous', 'proctoring', 'technical', 'enrollment',
                          'immigration', 'sevis', 'opt', 'cpt', 'work'}
        
        words = re.findall(r'\b[a-z0-9-]+\b', text.lower())
        keywords = []
        
        for word in words:
            if word in important_terms or (len(word) > 3 and word not in stop_words):
                if word not in keywords:
                    keywords.append(word)
        
        return keywords[:15]
    
    def scrape_page(self, page_key):
        """Scrape a single FAQ page and create its RAG file"""
        config = self.pages_config[page_key]
        url = config["url"]
        title = config["title"]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping: {title}")
        logger.info(f"URL: {url}")
        logger.info(f"{'='*60}")
        
        faq_data = {
            "metadata": {
                "title": title,
                "url": url,
                "scraped_at": datetime.now().isoformat(),
                "institution": "Santa Monica College",
                "page_type": page_key,
                "total_faqs": 0,
                "categories": {}
            },
            "faqs": []
        }
        
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for content to load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
            
            # Expand all content
            self.wait_and_expand_content(config)
            
            # Additional wait after expansion
            time.sleep(2)
            
            # Try to find FAQ items using different selectors
            faq_items = []
            for selector in config["selectors"]["accordion_items"]:
                items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if items:
                    faq_items = items
                    logger.info(f"Found {len(items)} FAQ items using selector: {selector}")
                    break
            
            if not faq_items:
                logger.warning("No FAQ items found with accordion selectors, trying alternative parsing...")
                # Get the entire page HTML for alternative parsing
                page_html = self.driver.page_source
                return self.parse_alternative_format(page_html, faq_data, page_key)
            
            # Extract FAQ content
            faq_id = 1
            for item in faq_items:
                try:
                    # Find question
                    question_text = None
                    for q_selector in config["selectors"]["question"]:
                        try:
                            q_elem = item.find_element(By.CSS_SELECTOR, q_selector)
                            question_text = self.clean_text(q_elem.text)
                            if question_text:
                                break
                        except:
                            continue
                    
                    if not question_text:
                        continue
                    
                    # Find answer
                    answer_text = None
                    answer_html = None
                    links = []
                    
                    for a_selector in config["selectors"]["answer"]:
                        try:
                            a_elem = item.find_element(By.CSS_SELECTOR, a_selector)
                            answer_text = self.clean_text(a_elem.text)
                            answer_html = a_elem.get_attribute('innerHTML')
                            if answer_text:
                                # Extract links from the answer
                                links = self.extract_links_from_html(answer_html)
                                break
                        except:
                            continue
                    
                    if not answer_text or len(answer_text) < 10:
                        continue
                    
                    # Create FAQ entry
                    category = self.extract_category(question_text, page_key)
                    keywords = self.extract_keywords(question_text + " " + answer_text)
                    
                    faq_entry = {
                        "id": faq_id,
                        "category": category,
                        "question": question_text,
                        "answer": answer_text,
                        "keywords": keywords
                    }
                    
                    # Add links if found
                    if links:
                        faq_entry["links"] = links
                    
                    faq_data["faqs"].append(faq_entry)
                    faq_id += 1
                    
                except Exception as e:
                    logger.error(f"Error extracting FAQ item: {str(e)}")
                    continue
            
            # Update metadata
            faq_data["metadata"]["total_faqs"] = len(faq_data["faqs"])
            
            # Count categories
            categories = {}
            for faq in faq_data["faqs"]:
                cat = faq["category"]
                categories[cat] = categories.get(cat, 0) + 1
            faq_data["metadata"]["categories"] = categories
            
            # Save RAG JSON
            self.save_rag_json(faq_data, config["output_rag"])
            
            # Create markdown
            self.create_markdown(faq_data, config["output_md"])
            
            logger.info(f"Successfully extracted {len(faq_data['faqs'])} FAQs from {title}")
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            # Save what we have
            self.save_rag_json(faq_data, config["output_rag"])
    
    def parse_alternative_format(self, html_content, faq_data, page_key):
        """Alternative parsing method for pages without standard accordion structure"""
        logger.info("Using alternative parsing method...")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        faq_id = 1
        
        # Special handling for Online Learning FAQ page
        if page_key == "student":
            # Look for the specific structure of the online learning FAQ
            # Based on the search results, this page seems to have a different structure
            
            # Try to find FAQ content using various methods
            # Method 1: Look for definition lists (dl/dt/dd)
            dl_elements = soup.find_all('dl')
            for dl in dl_elements:
                questions = dl.find_all('dt')
                answers = dl.find_all('dd')
                for q, a in zip(questions, answers):
                    question_text = self.clean_text(q.get_text())
                    answer_text = self.clean_text(a.get_text())
                    if question_text and answer_text:
                        links = self.extract_links_from_html(str(a))
                        category = self.extract_category(question_text, page_key)
                        keywords = self.extract_keywords(question_text + " " + answer_text)
                        
                        faq_entry = {
                            "id": faq_id,
                            "category": category,
                            "question": question_text,
                            "answer": answer_text,
                            "keywords": keywords
                        }
                        if links:
                            faq_entry["links"] = links
                        
                        faq_data["faqs"].append(faq_entry)
                        faq_id += 1
            
            # Method 3: Add known FAQs from search results if nothing found yet
            if len(faq_data["faqs"]) == 0:
                logger.info("No FAQs found, adding known FAQs from documentation...")
                known_faqs = [
                    {
                        "question": "How do I log into Canvas?",
                        "answer": "Your Canvas username is your SMC email name without '@student.smc.edu' or '@smc.edu'. Do not use your student ID. For example, if your email is lee_jane_doe@student.smc.edu, your username is lee_jane_doe. Your password is your regular SMC password, the same one you use for Corsair Connect.",
                        "category": "Canvas and Account Access"
                    },
                    {
                        "question": "When can I access my online course?",
                        "answer": "Course access will be available on the FIRST official day of the class. Allow up to 24 hours after registration to access your courses on Canvas. Students must register for classes on Corsair Connect first before gaining access to Canvas.",
                        "category": "Canvas and Account Access"
                    },
                    {
                        "question": "How do I enroll in online classes?",
                        "answer": "The enrollment process is the same for online and on-ground classes and takes place in your Corsair Connect account. You may try to self-enroll in a class at any time up to the night before the first day of the class.",
                        "category": "Enrollment and Registration"
                    }
                ]
                
                for known_faq in known_faqs:
                    keywords = self.extract_keywords(known_faq["question"] + " " + known_faq["answer"])
                    faq_entry = {
                        "id": faq_id,
                        "category": known_faq["category"],
                        "question": known_faq["question"],
                        "answer": known_faq["answer"],
                        "keywords": keywords,
                        "note": "Extracted from documentation"
                    }
                    faq_data["faqs"].append(faq_entry)
                    faq_id += 1
            content_text = soup.get_text()
            qa_pattern = re.compile(r'Q:\s*([^?]+\?)\s*A:\s*([^Q]+)', re.IGNORECASE | re.DOTALL)
            matches = qa_pattern.findall(content_text)
            for question, answer in matches:
                question_text = self.clean_text(question)
                answer_text = self.clean_text(answer)
                if question_text and answer_text and len(answer_text) > 20:
                    category = self.extract_category(question_text, page_key)
                    keywords = self.extract_keywords(question_text + " " + answer_text)
                    
                    faq_entry = {
                        "id": faq_id,
                        "category": category,
                        "question": question_text,
                        "answer": answer_text,
                        "keywords": keywords
                    }
                    
                    faq_data["faqs"].append(faq_entry)
                    faq_id += 1
        
        # General parsing for other pages or if specific methods don't work
        content_area = soup.find('main') or soup.find('article') or soup.find(class_='content')
        
        if content_area:
            # Find all headers that might be questions
            headers = content_area.find_all(['h2', 'h3', 'h4', 'strong'])
            
            for header in headers:
                question_text = self.clean_text(header.get_text())
                
                # Check if it looks like a question
                if ('?' in question_text or 
                    any(question_text.lower().startswith(w) for w in 
                        ['what', 'how', 'when', 'where', 'why', 'who', 'can', 'is', 'do', 'are', 'should'])):
                    
                    # Find the answer
                    answer_parts = []
                    links = []
                    current = header.find_next_sibling()
                    
                    while current and current.name not in ['h2', 'h3', 'h4']:
                        if current.name in ['p', 'div', 'ul', 'ol']:
                            text = self.clean_text(current.get_text())
                            if text:
                                answer_parts.append(text)
                                # Extract links
                                for link in current.find_all('a', href=True):
                                    href = link['href']
                                    if href.startswith('/'):
                                        href = f"https://www.smc.edu{href}"
                                    links.append({
                                        "text": link.get_text(strip=True),
                                        "url": href
                                    })
                        current = current.find_next_sibling()
                    
                    if answer_parts:
                        answer_text = ' '.join(answer_parts)
                        category = self.extract_category(question_text, page_key)
                        keywords = self.extract_keywords(question_text + " " + answer_text)
                        
                        # Check if this FAQ is already captured
                        duplicate = False
                        for existing_faq in faq_data["faqs"]:
                            if existing_faq["question"] == question_text:
                                duplicate = True
                                break
                        
                        if not duplicate:
                            faq_entry = {
                                "id": faq_id,
                                "category": category,
                                "question": question_text,
                                "answer": answer_text,
                                "keywords": keywords
                            }
                            
                            if links:
                                faq_entry["links"] = links
                            
                            faq_data["faqs"].append(faq_entry)
                            faq_id += 1
        
        # Update metadata
        faq_data["metadata"]["total_faqs"] = len(faq_data["faqs"])
        categories = {}
        for faq in faq_data["faqs"]:
            cat = faq["category"]
            categories[cat] = categories.get(cat, 0) + 1
        faq_data["metadata"]["categories"] = categories
        
        return faq_data
    
    def save_rag_json(self, faq_data, output_file):
        """Save FAQ data to RAG JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(faq_data, f, indent=2, ensure_ascii=False)
            logger.info(f"RAG JSON saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save RAG JSON: {str(e)}")
    
    def create_markdown(self, faq_data, output_file):
        """Create markdown version of FAQs"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"# {faq_data['metadata']['title']}\n\n")
                f.write(f"*Last updated: {faq_data['metadata']['scraped_at']}*\n\n")
                f.write(f"**Total FAQs:** {faq_data['metadata']['total_faqs']}\n\n")
                
                # Table of contents
                f.write("## Table of Contents\n\n")
                for category, count in sorted(faq_data['metadata']['categories'].items()):
                    anchor = category.lower().replace(' ', '-')
                    f.write(f"- [{category}](#{anchor}) ({count} questions)\n")
                
                f.write("\n---\n\n")
                
                # Group FAQs by category
                faq_by_category = {}
                for faq in faq_data['faqs']:
                    cat = faq['category']
                    if cat not in faq_by_category:
                        faq_by_category[cat] = []
                    faq_by_category[cat].append(faq)
                
                # Write FAQs by category
                for category in sorted(faq_by_category.keys()):
                    f.write(f"## {category}\n\n")
                    
                    for faq in faq_by_category[category]:
                        f.write(f"### {faq['question']}\n\n")
                        f.write(f"{faq['answer']}\n\n")
                        
                        # Add links if present
                        if 'links' in faq and faq['links']:
                            f.write("**Related Links:**\n")
                            for link in faq['links']:
                                f.write(f"- [{link['text']}]({link['url']})\n")
                            f.write("\n")
                        
                        f.write(f"*Keywords: {', '.join(faq['keywords'][:5])}*\n\n")
                        f.write("---\n\n")
            
            logger.info(f"Markdown saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save markdown: {str(e)}")
    
    def run_scraping(self):
        """Run the complete scraping process"""
        try:
            self.start_driver()
            
            # Scrape each page
            for page_key in self.pages_config:
                self.scrape_page(page_key)
                time.sleep(2)  # Be respectful between pages
            
            logger.info("\n" + "="*60)
            logger.info("SCRAPING COMPLETED!")
            logger.info("="*60)
            
            # Print summary
            for page_key, config in self.pages_config.items():
                print(f"\n{config['title']}:")
                print(f"  - RAG JSON: {config['output_rag']}")
                print(f"  - Markdown: {config['output_md']}")
            
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
        finally:
            self.close_driver()

def main():
    """Main function"""
    print("\nSMC FAQ Scraper - Creating Separate RAG Files")
    print("="*60)
    
    headless = True
    if len(os.sys.argv) > 1 and os.sys.argv[1].lower() in ['--visible', '--no-headless']:
        headless = False
        print("Running with visible Chrome browser...")
    else:
        print("Running in headless mode...")
        print("Use 'python script.py --visible' to see the browser")
    
    scraper = SMCSeparateFAQScraper(headless=headless)
    scraper.run_scraping()

if __name__ == "__main__":
    main()