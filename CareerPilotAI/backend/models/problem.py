"""
CareerPilot AI — Problem Solving Database Models
Defines SQLite schemas and query executors for the Coding Platform.
"""

from backend.database.db import execute_query, execute_one, execute_insert, execute_update, table_exists
from datetime import datetime
import json

def migrate_problem_solving_tables():
    """Create all coding platform tables if they do not exist."""
    
    # 1. Problems Table
    if not table_exists("problems"):
        execute_query("""
            CREATE TABLE problems (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                difficulty TEXT NOT NULL, -- Easy, Medium, Hard, Interview, Contest
                topic TEXT NOT NULL,      -- Arrays, Strings, DP, Trees, Graphs, etc
                subtopics TEXT,           -- Comma separated tags
                companies TEXT,           -- Comma separated company names
                constraints TEXT,
                description TEXT NOT NULL,
                examples TEXT,            -- JSON array of example inputs/outputs
                hints TEXT,               -- JSON array of hints (1 to 5)
                editorial TEXT,
                starter_code TEXT,        -- JSON mapping language to starter code
                tags TEXT,
                premium INTEGER DEFAULT 0,
                estimated_time INTEGER DEFAULT 30, -- in minutes
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Populate with some default problems so there is no dummy data error
        _populate_default_problems()

    # 2. Problem Templates Table
    if not table_exists("problem_templates"):
        execute_query("""
            CREATE TABLE problem_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER NOT NULL,
                language TEXT NOT NULL,
                function_signature TEXT,
                return_type TEXT,
                starter_code TEXT,
                driver_template TEXT,
                FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
            )
        """)

    # 3. Test Cases Table
    if not table_exists("problem_test_cases"):
        execute_query("""
            CREATE TABLE problem_test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id INTEGER NOT NULL,
                input TEXT NOT NULL,
                expected_output TEXT NOT NULL,
                is_hidden INTEGER DEFAULT 0,
                FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
            )
        """)
        _populate_default_test_cases()

    # 3. Submissions Table
    if not table_exists("problem_submissions"):
        execute_query("""
            CREATE TABLE problem_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                problem_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                language TEXT NOT NULL,
                status TEXT NOT NULL, -- Accepted, Wrong Answer, Time Limit, Runtime Error, etc
                execution_time INTEGER DEFAULT 0, -- in ms
                memory INTEGER DEFAULT 0, -- in KB
                coding_metrics TEXT,      -- JSON of typing speed, keypresses, deletes, reading time
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE
            )
        """)

    # 4. Learning Analytics Table
    if not table_exists("user_problem_analytics"):
        execute_query("""
            CREATE TABLE user_problem_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                streak INTEGER DEFAULT 0,
                confidence_score INTEGER DEFAULT 50,
                learning_velocity REAL DEFAULT 1.0,
                last_submission_at TEXT
            )
        """)

    # 5. User Topic Scores Table
    if not table_exists("user_topic_scores"):
        execute_query("""
            CREATE TABLE user_topic_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                score INTEGER DEFAULT 0,
                UNIQUE(user_id, topic)
            )
        """)

    # 6. AI Problem Feedback Table
    if not table_exists("ai_problem_feedback"):
        execute_query("""
            CREATE TABLE ai_problem_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                correctness INTEGER, -- Score out of 100
                time_complexity TEXT,
                space_complexity TEXT,
                naming_convention INTEGER, -- Score out of 100
                readability INTEGER,
                logic INTEGER,
                optimization INTEGER,
                code_style INTEGER,
                maintainability INTEGER,
                edge_cases TEXT,
                potential_bugs TEXT,
                interview_quality INTEGER,
                overall_score INTEGER,
                feedback_report TEXT, -- JSON text for visual feedback
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES problem_submissions(id) ON DELETE CASCADE
            )
        """)

    # 7. Hints Used Table
    if not table_exists("problem_hints_used"):
        execute_query("""
            CREATE TABLE problem_hints_used (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                problem_id INTEGER NOT NULL,
                hint_index INTEGER NOT NULL, -- 0 to 4
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, problem_id, hint_index)
            )
        """)


def _populate_default_problems():
    """Insert a core set of diverse, real programming challenges."""
    problems = [
        {
            "title": "Two Sum",
            "difficulty": "Easy",
            "topic": "Arrays",
            "subtopics": "Hashing, Two Pointers",
            "companies": "Amazon, Google, Meta, Microsoft",
            "constraints": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9",
            "description": "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
            "examples": json.dumps([
                {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."}
            ]),
            "hints": json.dumps([
                "A really brute force way would be to search for all possible pairs of numbers but that would be O(N^2) time complexity. Can we do better?",
                "Can we check if the difference target - nums[i] exists in the array?",
                "Use a Hash Map to store the elements and their indices for O(1) lookups."
            ]),
            "editorial": "The optimal solution uses a Hash Map (dict in Python) to keep track of values and indices as we iterate. For each element, we check if target - num exists in the map. This achieves O(N) time and O(N) space.",
            "starter_code": json.dumps({
                "python": "def twoSum(nums, target):\n    # Write your Python code here\n    pass",
                "javascript": "function twoSum(nums, target) {\n    // Write your JavaScript code here\n}",
                "java": "class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        \n    }\n}",
                "c": "int* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n    \n}",
                "cpp": "class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        \n    }\n};"
            }),
            "tags": "hash-map,arrays",
            "estimated_time": 15
        },
        {
            "title": "Reverse Linked List",
            "difficulty": "Easy",
            "topic": "Linked List",
            "subtopics": "Pointers",
            "companies": "Amazon, Adobe, Meta, Microsoft",
            "constraints": "The number of nodes in the list is the range [0, 5000].\n-5000 <= Node.val <= 5000",
            "description": "Given the `head` of a singly linked list, reverse the list, and return the reversed list.\n\n*Note*: Represent your linked list node as a class/object with `.val` and `.next` references.",
            "examples": json.dumps([
                {"input": "head = [1,2,3,4,5]", "output": "[5,4,3,2,1]"}
            ]),
            "hints": json.dumps([
                "Try reversing the pointers as you traverse.",
                "Keep track of the previous node, current node, and next node during traversal."
            ]),
            "starter_code": json.dumps({
                "python": "# Definition for singly-linked list.\n# class ListNode:\n#     def __init__(self, val=0, next=None):\n#         self.val = val\n#         self.next = next\n\ndef reverseList(head):\n    pass",
                "javascript": "/**\n * Definition for singly-linked list.\n * function ListNode(val, next) {\n *     this.val = (val===undefined ? 0 : val)\n *     this.next = (next===undefined ? null : next)\n * }\n */\nfunction reverseList(head) {\n    \n}",
                "java": "/**\n * Definition for singly-linked list.\n * public class ListNode {\n *     int val;\n *     ListNode next;\n *     ListNode() {}\n *     ListNode(int val) { this.val = val; }\n *     ListNode(int val, ListNode next) { this.val = val; this.next = next; }\n * }\n */\nclass Solution {\n    public ListNode reverseList(ListNode head) {\n        \n    }\n}",
                "c": "/**\n * Definition for singly-linked list.\n * struct ListNode {\n *     int val;\n *     struct ListNode *next;\n * };\n */\nstruct ListNode* reverseList(struct ListNode* head) {\n    \n}",
                "cpp": "/**\n * Definition for singly-linked list.\n * struct ListNode {\n *     int val;\n *     ListNode *next;\n *     ListNode() : val(0), next(nullptr) {}\n *     ListNode(int x) : val(x), next(nullptr) {}\n *     ListNode(int x, ListNode *next) : val(x), next(next) {}\n * };\n */\nclass Solution {\npublic:\n    ListNode* reverseList(ListNode* head) {\n        \n    }\n};"
            }),
            "tags": "linked-list,pointers"
        },
        {
            "title": "Longest Substring Without Repeating Characters",
            "difficulty": "Medium",
            "topic": "Sliding Window",
            "subtopics": "Hashing, Strings",
            "companies": "Google, Meta, Uber, Amazon",
            "constraints": "0 <= s.length <= 5 * 10^4\ns consists of English letters, digits, symbols and spaces.",
            "description": "Given a string `s`, find the length of the longest substring without repeating characters.",
            "examples": json.dumps([
                {"input": "s = 'abcabcbb'", "output": "3", "explanation": "The answer is 'abc', with the length of 3."}
            ]),
            "hints": json.dumps([
                "Use a sliding window with two pointers (left and right).",
                "Maintain a set/hash map of characters in the current window."
            ]),
            "starter_code": json.dumps({
                "python": "def lengthOfLongestSubstring(s):\n    pass",
                "javascript": "function lengthOfLongestSubstring(s) {\n    \n}",
                "java": "class Solution {\n    public int lengthOfLongestSubstring(String s) {\n        \n    }\n}",
                "c": "int lengthOfLongestSubstring(char* s) {\n    \n}",
                "cpp": "class Solution {\npublic:\n    int lengthOfLongestSubstring(string s) {\n        \n    }\n};"
            }),
            "tags": "sliding-window,strings,hash-map"
        }
    ]
    
    for p in problems:
        execute_insert("""
            INSERT INTO problems (title, difficulty, topic, subtopics, companies, constraints, description, examples, hints, editorial, starter_code, tags, estimated_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["title"], p["difficulty"], p["topic"], p["subtopics"], p["companies"],
            p["constraints"], p["description"], p["examples"], p["hints"],
            p.get("editorial", ""), p["starter_code"], p["tags"], p.get("estimated_time", 30)
        ))


def _populate_default_test_cases():
    """Populate test cases for default problems."""
    # Two Sum has ID 1
    # Inputs are formatted in Python syntax to be evaluated safely in our runner
    execute_insert("""
        INSERT INTO problem_test_cases (problem_id, input, expected_output, is_hidden)
        VALUES 
        (1, '([2, 7, 11, 15], 9)', '[0, 1]', 0),
        (1, '([3, 2, 4], 6)', '[1, 2]', 0),
        (1, '([3, 3], 6)', '[0, 1]', 1)
    """)
    # Reverse Linked List has ID 2
    execute_insert("""
        INSERT INTO problem_test_cases (problem_id, input, expected_output, is_hidden)
        VALUES
        (2, '([1, 2, 3, 4, 5],)', '[5, 4, 3, 2, 1]', 0),
        (2, '([1, 2],)', '[2, 1]', 0),
        (2, '([],)', '[]', 1)
    """)
    # Longest Substring has ID 3
    execute_insert("""
        INSERT INTO problem_test_cases (problem_id, input, expected_output, is_hidden)
        VALUES
        (3, '("abcabcbb",)', '3', 0),
        (3, '("bbbbb",)', '1', 0),
        (3, '("pwwkew",)', '3', 1)
    """)
