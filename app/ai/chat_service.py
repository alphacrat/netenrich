import os
import google.generativeai as genai
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any
import json
from datetime import datetime, timedelta


class LibraryChatAgent:
    def __init__(self):

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel("gemini-pro")

        # Database setup
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///library.db")
        self.engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(bind=self.engine)
        self.db = SessionLocal()

        # Database schema context for AI
        self.schema_context = """
        Database Schema:
        
        Table: books
        - id (INTEGER, PRIMARY KEY)
        - title (TEXT)
        - author (TEXT)
        - isbn (TEXT)
        - category (TEXT)
        - department (TEXT)
        - total_copies (INTEGER)
        - available_copies (INTEGER)
        - created_at (DATETIME)
        
        Table: students
        - id (INTEGER, PRIMARY KEY)
        - name (TEXT)
        - student_id (TEXT)
        - department (TEXT)
        - email (TEXT)
        - phone (TEXT)
        - created_at (DATETIME)
        
        Table: issues
        - id (INTEGER, PRIMARY KEY)
        - book_id (INTEGER, FOREIGN KEY to books.id)
        - student_id (INTEGER, FOREIGN KEY to students.id)
        - issue_date (DATETIME)
        - due_date (DATETIME)
        - return_date (DATETIME, nullable)
        - status (TEXT: issued/returned/overdue)
        
        Table: notifications
        - id (INTEGER, PRIMARY KEY)
        - student_id (INTEGER)
        - message (TEXT)
        - type (TEXT)
        - created_at (DATETIME)
        - is_read (BOOLEAN)
        """

    def analyze_query_and_generate_sql(self, user_query: str) -> str:
        """Convert natural language query to SQL using Gemini"""

        prompt = f"""
        You are a SQL expert for a library management system. 
        
        {self.schema_context}
        
        User Question: "{user_query}"
        
        Generate a SQL query to answer this question. Follow these rules:
        1. Return ONLY the SQL query, no explanations
        2. Use proper JOIN statements when needed
        3. For overdue books: due_date < current date AND return_date IS NULL
        4. For date ranges: use appropriate date functions
        5. Current date reference: use date('now') for SQLite
        6. For "last month": use date('now', '-1 month')
        7. For "this week": use date('now', '-7 days')
        
        Examples:
        - "How many books are overdue?" → SELECT COUNT(*) as overdue_count FROM issues WHERE due_date < date('now') AND return_date IS NULL
        - "Which department borrowed most books?" → SELECT s.department, COUNT(*) as borrow_count FROM issues i JOIN students s ON i.student_id = s.id GROUP BY s.department ORDER BY borrow_count DESC LIMIT 1
        
        SQL Query:
        """

        try:
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()

            # Clean up the response - remove any markdown formatting
            if sql_query.startswith("```sql"):
                sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
            elif sql_query.startswith("```"):
                sql_query = sql_query.replace("```", "").strip()

            return sql_query
        except Exception as e:
            print(f"Error generating SQL: {e}")
            return None

    def execute_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """Execute the SQL query and return results"""
        try:
            result = self.db.execute(text(sql_query))

            # Handle different types of queries
            if sql_query.strip().upper().startswith("SELECT"):
                rows = result.fetchall()
                columns = result.keys()

                # Convert to list of dictionaries
                data = []
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    data.append(row_dict)

                return {"success": True, "data": data, "row_count": len(data)}
            else:
                return {"success": True, "message": "Query executed successfully"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def format_response(self, user_query: str, sql_result: Dict[str, Any]) -> str:
        """Format the SQL result into a natural language response using Gemini"""

        if not sql_result["success"]:
            return f"I encountered an error: {sql_result.get('error', 'Unknown error')}"

        # Create prompt for natural language response
        prompt = f"""
        User asked: "{user_query}"
        
        Database query results: {json.dumps(sql_result['data'], indent=2)}
        
        Convert this data into a natural, conversational response. Be specific with numbers and details.
        If the result is empty, mention that no records were found.
        Keep the response concise but informative.
        
        Response:
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            # Fallback to simple formatting if AI fails
            if sql_result["data"]:
                return f"Found {sql_result['row_count']} results: {sql_result['data']}"
            else:
                return "No results found for your query."

    def chat(self, user_query: str) -> str:
        """Main chat function that processes user query end-to-end"""

        # Step 1: Convert natural language to SQL
        sql_query = self.analyze_query_and_generate_sql(user_query)

        if not sql_query:
            return (
                "I'm sorry, I couldn't understand your query. Please try rephrasing it."
            )

        print(f"Generated SQL: {sql_query}")  # For debugging

        # Step 2: Execute SQL query
        sql_result = self.execute_sql_query(sql_query)

        # Step 3: Format response naturally
        response = self.format_response(user_query, sql_result)

        return response

    def __del__(self):
        """Close database connection"""
        if hasattr(self, "db"):
            self.db.close()


# Example usage and testing
if __name__ == "__main__":
    agent = LibraryChatAgent()

    # Test queries
    test_queries = [
        "How many books are overdue?",
        "Which department borrowed the most books last month?",
        "How many new books were added this week?",
        "Show me all students from Computer Science department",
        "What books are available in the Fiction category?",
    ]

    for query in test_queries:
        print(f"\nQ: {query}")
        response = agent.chat(query)
        print(f"A: {response}")
        print("-" * 50)
