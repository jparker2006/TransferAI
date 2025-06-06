import requests
import json
import re
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
            schools(query: $query, first: 40) {
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

    def get_professors_by_school_id(self, school_id: str, limit: int = 100) -> List[Dict]:
        """Get professors from a school by school ID"""
        # Start with the requested limit, but be prepared to reduce it
        current_limit = min(limit, 1000)  # Cap at 1000 initially
        
        query = """
        query TeacherSearchPaginationQuery($query: TeacherSearchQuery!, $count: Int!) {
          search: newSearch {
            teachers(query: $query, first: $count) {
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
        
        # Try different limits if the initial one fails
        limits_to_try = [current_limit, 500, 200, 100, 50, 20]
        
        for attempt_limit in limits_to_try:
            if attempt_limit > limit:
                continue
                
            variables = {
                "query": {
                    "schoolID": school_id,
                    "fallback": True
                },
                "count": attempt_limit
            }
            
            try:
                response = requests.post(
                    self.base_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check if we have the expected data structure
                    if ('data' in data and 
                        data['data'] is not None and 
                        'search' in data['data'] and 
                        data['data']['search'] is not None and
                        'teachers' in data['data']['search'] and
                        data['data']['search']['teachers'] is not None and
                        'edges' in data['data']['search']['teachers']):
                        
                        professors = []
                        edges = data['data']['search']['teachers']['edges']
                        
                        if edges:
                            for edge in edges:
                                if edge and 'node' in edge and edge['node']:
                                    prof = edge['node']
                                    professors.append({
                                        'id': prof.get('id', ''),
                                        'name': f"{prof.get('firstName', '')} {prof.get('lastName', '')}".strip(),
                                        'department': prof.get('department', 'Unknown'),
                                        'rating': prof.get('avgRating'),
                                        'num_ratings': prof.get('numRatings'),
                                        'would_take_again': prof.get('wouldTakeAgainPercent'),
                                        'difficulty': prof.get('avgDifficulty'),
                                        'school_name': prof.get('school', {}).get('name', '') if prof.get('school') else '',
                                        'school_id': prof.get('school', {}).get('id', '') if prof.get('school') else ''
                                    })
                        
                        if professors:
                            print(f"   ✅ Successfully fetched {len(professors)} professors (limit: {attempt_limit})")
                            return professors
                        elif attempt_limit == limits_to_try[-1]:
                            # If this was our last attempt and we still got no professors
                            print(f"   ⚠️  No professors found even with limit {attempt_limit}")
                            return []
                    else:
                        # Data structure is not as expected
                        if attempt_limit == limits_to_try[-1]:
                            print(f"   ❌ Unexpected response structure even with limit {attempt_limit}")
                            print(f"   Response data keys: {list(data.keys()) if data else 'None'}")
                            return []
                        else:
                            print(f"   ⚠️  Limit {attempt_limit} too high, trying smaller limit...")
                            continue
                else:
                    if attempt_limit == limits_to_try[-1]:
                        print(f"   ❌ Failed to get professors: {response.status_code}")
                        return []
                    else:
                        print(f"   ⚠️  HTTP {response.status_code} with limit {attempt_limit}, trying smaller limit...")
                        continue
                        
            except Exception as e:
                if attempt_limit == limits_to_try[-1]:
                    print(f"   ❌ Error getting professors: {e}")
                    return []
                else:
                    print(f"   ⚠️  Error with limit {attempt_limit}: {e}, trying smaller limit...")
                    continue
        
        return []

def test_scraper():
    print("🚀 Testing custom Rate My Professor scraper...")
    
    scraper = RateMyProfessorScraper()
    
    # Test 1: Search for schools
    print("\n🔍 Searching for schools...")
    test_schools = ["USC", "Harvard", "Stanford", "MIT"]
    
    found_school = None
    for school_name in test_schools:
        print(f"   Searching for: {school_name}")
        schools = scraper.search_schools(school_name)
        
        if schools:
            print(f"   ✅ Found {len(schools)} school(s):")
            for school in schools[:3]:  # Show first 3
                print(f"      - {school['name']} ({school['city']}, {school['state']}) [ID: {school['id']}]")
                if found_school is None:
                    found_school = school
        else:
            print(f"   ❌ No schools found for: {school_name}")
    
    # Test 2: Get professors from found school
    if found_school:
        print(f"\n🎓 Getting professors from {found_school['name']}...")
        professors = scraper.get_professors_by_school_id(found_school['id'], limit=3000)
        
        if professors:
            print(f"✅ Found {len(professors)} professors:")
            print("=" * 80)
            
            for i, prof in enumerate(professors[:3000], 1):
                print(f"{i}. {prof['name']}")
                print(f"   Department: {prof['department']}")
                print(f"   Rating: {prof['rating']}/5.0" if prof['rating'] else "   Rating: N/A")
                print(f"   Difficulty: {prof['difficulty']}/5.0" if prof['difficulty'] else "   Difficulty: N/A")
                print(f"   Total Ratings: {prof['num_ratings']}" if prof['num_ratings'] else "   Total Ratings: N/A")
                if prof['would_take_again'] is not None:
                    print(f"   Would Take Again: {prof['would_take_again']:.1f}%")
                else:
                    print("   Would Take Again: N/A")
                print()
                
            print(f"Total professors fetched: {len(professors)}")
        else:
            print("❌ No professors found")
    else:
        print("❌ No school found to test with")

if __name__ == "__main__":
    test_scraper()
