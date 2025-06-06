import requests
import json
import time
from typing import List, Dict

class RateMyProfessorScraper:
    def __init__(self):
        self.base_url = "https://www.ratemyprofessors.com/graphql"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def search_schools(self, school_name: str) -> List[Dict]:
        """Search for schools by name"""
        query = """
        query NewSearchSchoolsQuery($query: SchoolSearchQuery!) {
          search: newSearch {
            schools(query: $query, first: 10) {
              edges {
                node {
                  id
                  name
                  city
                  state
                }
              }
            }
          }
        }
        """
        
        variables = {
            "query": {
                "text": school_name
            }
        }
        
        try:
            response = requests.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                schools = []
                
                if 'data' in data and data['data']['search']['schools']['edges']:
                    for edge in data['data']['search']['schools']['edges']:
                        school = edge['node']
                        schools.append({
                            'id': school['id'],
                            'name': school['name'],
                            'city': school['city'],
                            'state': school['state']
                        })
                
                return schools
            else:
                print(f"Failed to search schools: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error searching schools: {e}")
            return []

    def get_professors_batch(self, school_id: str, after_cursor: str = None, limit: int = 1000) -> Dict:
        """Get a batch of professors from a school"""
        query = """
        query TeacherSearchPaginationQuery($query: TeacherSearchQuery!, $count: Int!, $cursor: String) {
          search: newSearch {
            teachers(query: $query, first: $count, after: $cursor) {
              pageInfo {
                hasNextPage
                endCursor
              }
              edges {
                node {
                  id
                  firstName
                  lastName
                  department
                  avgRating
                  numRatings
                  wouldTakeAgainPercent
                  avgDifficulty
                  school {
                    name
                    id
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "query": {
                "schoolID": school_id,
                "fallback": True
            },
            "count": limit
        }
        
        if after_cursor:
            variables["cursor"] = after_cursor
        
        try:
            response = requests.post(
                self.base_url,
                json={"query": query, "variables": variables},
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if ('data' in data and 
                    data['data'] is not None and 
                    'search' in data['data'] and 
                    data['data']['search'] is not None and
                    'teachers' in data['data']['search'] and
                    data['data']['search']['teachers'] is not None):
                    
                    teachers_data = data['data']['search']['teachers']
                    professors = []
                    
                    if 'edges' in teachers_data and teachers_data['edges']:
                        for edge in teachers_data['edges']:
                            if edge and 'node' in edge and edge['node']:
                                prof = edge['node']
                                professors.append({
                                    'id': prof.get('id', ''),
                                    'name': f"{prof.get('firstName', '')} {prof.get('lastName', '')}".strip(),
                                    'first_name': prof.get('firstName', ''),
                                    'last_name': prof.get('lastName', ''),
                                    'department': prof.get('department', 'Unknown'),
                                    'rating': prof.get('avgRating'),
                                    'num_ratings': prof.get('numRatings'),
                                    'would_take_again': prof.get('wouldTakeAgainPercent'),
                                    'difficulty': prof.get('avgDifficulty'),
                                    'school_name': prof.get('school', {}).get('name', '') if prof.get('school') else '',
                                    'school_id': prof.get('school', {}).get('id', '') if prof.get('school') else ''
                                })
                    
                    # Get pagination info
                    page_info = teachers_data.get('pageInfo', {})
                    has_next_page = page_info.get('hasNextPage', False)
                    end_cursor = page_info.get('endCursor')
                    
                    return {
                        'professors': professors,
                        'has_next_page': has_next_page,
                        'end_cursor': end_cursor
                    }
                
            print(f"Failed to get professors batch: {response.status_code}")
            return {'professors': [], 'has_next_page': False, 'end_cursor': None}
                
        except Exception as e:
            print(f"Error getting professors batch: {e}")
            return {'professors': [], 'has_next_page': False, 'end_cursor': None}

    def get_all_professors(self, school_id: str, school_name: str) -> List[Dict]:
        """Get ALL professors from a school using pagination"""
        all_professors = []
        cursor = None
        batch_number = 1
        
        print(f"🎓 Starting to fetch all professors from {school_name}...")
        
        while True:
            print(f"   📚 Fetching batch {batch_number}...")
            
            # Get current batch
            batch_result = self.get_professors_batch(school_id, cursor, 1000)
            batch_professors = batch_result['professors']
            
            if batch_professors:
                all_professors.extend(batch_professors)
                print(f"   ✅ Batch {batch_number}: Found {len(batch_professors)} professors")
                print(f"   📊 Total so far: {len(all_professors)} professors")
            else:
                print(f"   ❌ Batch {batch_number}: No professors found")
                break
            
            # Check if there are more pages
            if not batch_result['has_next_page']:
                print(f"   🏁 Reached end of results")
                break
            
            # Prepare for next batch
            cursor = batch_result['end_cursor']
            batch_number += 1
            
            # Rate limiting - be nice to the API
            time.sleep(1)
        
        print(f"🎉 Completed! Total professors fetched: {len(all_professors)}")
        return all_professors

def create_rag_json(professors: List[Dict], school_info: Dict, output_file: str):
    """Create a JSON file formatted for RAG purposes"""
    
    # Prepare data for RAG
    rag_data = {
        "school_info": school_info,
        "total_professors": len(professors),
        "professors": []
    }
    
    for prof in professors:
        # Create a comprehensive text description for each professor
        description_parts = [
            f"Professor {prof['name']} teaches in the {prof['department']} department"
        ]
        
        if prof['rating']:
            description_parts.append(f"has an average rating of {prof['rating']}/5.0")
        
        if prof['difficulty']:
            description_parts.append(f"with a difficulty level of {prof['difficulty']}/5.0")
        
        if prof['num_ratings']:
            description_parts.append(f"based on {prof['num_ratings']} student reviews")
        
        if prof['would_take_again'] is not None and prof['would_take_again'] >= 0:
            description_parts.append(f"and {prof['would_take_again']:.1f}% of students would take their class again")
        
        description = " ".join(description_parts) + "."
        
        # Format for RAG
        prof_data = {
            "id": prof['id'],
            "name": prof['name'],
            "first_name": prof['first_name'],
            "last_name": prof['last_name'],
            "department": prof['department'],
            "description": description,
            "metrics": {
                "rating": prof['rating'],
                "difficulty": prof['difficulty'],
                "num_ratings": prof['num_ratings'],
                "would_take_again_percent": prof['would_take_again']
            },
            "school": {
                "name": prof['school_name'],
                "id": prof['school_id']
            }
        }
        
        rag_data["professors"].append(prof_data)
    
    # Save to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rag_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 RAG JSON file saved: {output_file}")
    print(f"📊 Contains {len(professors)} professors from {school_info['name']}")

def main():
    scraper = RateMyProfessorScraper()
    
    # Search for Santa Monica College
    print("🔍 Searching for Santa Monica College...")
    schools = scraper.search_schools("Santa Monica College")
    
    if not schools:
        print("❌ Santa Monica College not found")
        return
    
    # Find the exact match for Santa Monica College
    smc = None
    for school in schools:
        print(f"   Found: {school['name']} ({school['city']}, {school['state']})")
        if "Santa Monica" in school['name'] and school['city'].lower() == "santa monica":
            smc = school
            break
    
    if not smc:
        print("❌ Could not find exact match for Santa Monica College")
        return
    
    print(f"✅ Selected: {smc['name']} (ID: {smc['id']})")
    
    # Get all professors
    all_professors = scraper.get_all_professors(smc['id'], smc['name'])
    
    if not all_professors:
        print("❌ No professors found")
        return
    
    # Create RAG JSON file
    output_file = "data/santa_monica_college_professors_rag.json"
    create_rag_json(all_professors, smc, output_file)
    
    # Print some statistics
    print("\n📈 Statistics:")
    print(f"   Total professors: {len(all_professors)}")
    
    # Department breakdown
    departments = {}
    for prof in all_professors:
        dept = prof['department']
        departments[dept] = departments.get(dept, 0) + 1
    
    print(f"   Number of departments: {len(departments)}")
    print("   Top 10 departments:")
    for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"      {dept}: {count} professors")

if __name__ == "__main__":
    main() 