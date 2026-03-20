import re2 as re # The 'Safe-Engine' Swap
import logging

logger = logging.getLogger("BLACK-TAPE.SEARCH-ENGINE")

class SignalSearch:
    """
    Safe Search Engine for Project Blacktape.
    Guarantees linear-time execution to prevent ReDoS attacks.
    """
    def __init__(self, chat_data):
        self.chat_data = chat_data or {}

    def parse_query(self, query):
        filters = {"must_not": [], "must_have": [], "all_of": []}
        temp_query = query

        # 1. Exclusions: -[term]
        # RE2 handles these patterns safely and quickly.
        exclusions = re.findall(r'-\[([^\]]+)\]', temp_query)
        filters["must_not"] = [t.lower() for t in exclusions]
        temp_query = re.sub(r'-\[([^\]]+)\]', ' ', temp_query)

        # 2. Groups: (term1, term2)
        groups = re.findall(r'\(([^)]+)\)', temp_query)
        for content in groups:
            if ',' in content:
                filters["all_of"].append([t.strip().lower() for t in content.split(',') if t.strip()])
            else:
                filters["must_have"].append(content.lower())
        temp_query = re.sub(r'\(([^)]+)\)', ' ', temp_query)

        # 3. Exact: "word"
        quotes = re.findall(r'"([^"]+)"', temp_query)
        for term in quotes:
            # We use re.escape to ensure user symbols don't break the regex logic
            # RE2 guarantees this lookup won't backtrack.
            pattern = re.compile(rf'\b{re.escape(term.lower())}\b', re.IGNORECASE)
            filters["must_have"].append(pattern)
        temp_query = re.sub(r'"([^"]+)"', ' ', temp_query)

        # 4. Simple Terms
        for t in temp_query.split():
            if t.strip() and len(t) > 1:
                filters["must_have"].append(t.lower())

        return filters

    def match(self, text, filters):
        if not text: return False
        text = text.lower()

        # Immediate exit if an exclusion term is present
        if any(term in text for term in filters["must_not"]):
            return False

        # Check mandatory terms and patterns
        for f in filters["must_have"]:
            if hasattr(f, 'search'): # Check if it's a compiled RE2 pattern
                if not f.search(text): return False
            elif f not in text:
                return False

        # Check logical AND groups
        for group in filters["all_of"]:
            if not all(term in text for term in group):
                return False

        return True

    def execute(self, query):
        """
        Executes search across the vault.
        Note: chat_data is now passed from the DiskCache result.
        """
        if not query or len(query.strip()) < 2:
            return []

        filters = self.parse_query(query)
        results = []

        # Iterate through the pre-aligned chat structure
        for convo_id, messages in self.chat_data.items():
            for msg in messages:
                content = msg.get("Content", "")
                if self.match(content, filters):
                    results.append({
                        "convoId": convo_id,
                        "message": msg
                    })
        return results
