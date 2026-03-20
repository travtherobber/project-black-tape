from collections import defaultdict

class ChatOrganizer:
    def organize(self, chat_list):
        """
        Returns nested structure for robust dashboard rendering:
        {
            "Conversation": {
                "Sender": [ {"timestamp": "...", "text": "..."} ]
            }
        }
        Sorts messages reliably, even with missing timestamps.
        """
        organized = defaultdict(lambda: defaultdict(list))

        for msg in chat_list:
            conv = msg.get("conversation", "Unknown")
            sender = msg.get("sender", "Unknown")
            timestamp = msg.get("timestamp", "0000-00-00 00:00:00")
            text = msg.get("text", "")

            # Sanitize text
            if not isinstance(text, str):
                text = str(text)

            organized[conv][sender].append({
                "timestamp": timestamp,
                "text": text
            })

        # Sort each sender's messages by timestamp safely
        for conv in organized:
            for sender in organized[conv]:
                try:
                    organized[conv][sender].sort(key=lambda x: x["timestamp"])
                except Exception:
                    # fallback: leave unsorted if timestamps invalid
                    pass

        return organized
