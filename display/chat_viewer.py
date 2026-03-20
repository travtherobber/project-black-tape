# display/chat_viewer.py

from core.orchestrator import get_entries_by_type
from datetime import datetime

current_sort_dir = "asc"
selected_contact = None

def to_datetime(ts):
    """Convert microseconds / string timestamps to datetime"""
    if isinstance(ts, int):
        return datetime.utcfromtimestamp(ts / 1_000_000)
    try:
        return datetime.fromisoformat(ts.replace(" UTC",""))
    except:
        return datetime.utcnow()

def get_contacts():
    """Return list of contacts with chat counts and last message timestamp"""
    entries = get_entries_by_type("Chat")
    contacts = {}
    for e in entries:
        contact = e["data"].get("contact", "UNKNOWN")
        if contact not in contacts:
            contacts[contact] = {"count": 0, "last": e["timestamp"]}
        contacts[contact]["count"] += 1
        if to_datetime(e["timestamp"]) > to_datetime(contacts[contact]["last"]):
            contacts[contact]["last"] = e["timestamp"]
    # Sort by last timestamp descending
    sorted_contacts = sorted(contacts.items(), key=lambda x: to_datetime(x[1]["last"]), reverse=True)
    return [c[0] for c in sorted_contacts]

def render_thread(contact_name):
    """Render messages for a single contact"""
    entries = get_entries_by_type("Chat")
    messages = [e for e in entries if e["data"].get("contact") == contact_name]
    messages.sort(key=lambda m: to_datetime(m["timestamp"]), reverse=(current_sort_dir=="desc"))

    print(f"\n=== Chat with {contact_name} ===\n")
    for m in messages:
        direction = "YOU ->" if m["data"].get("is_sender") else "<- THEM"
        print(f"[{to_datetime(m['timestamp'])}] {direction} {m['content']}")
    print("\n" + "="*40 + "\n")

def start_chat_viewer():
    global selected_contact
    contacts = get_contacts()
    if not contacts:
        print("No chat data available.")
        return

    print("Contacts found:")
    for i, c in enumerate(contacts, 1):
        print(f"{i}. {c}")

    choice = input("Select contact by number: ")
    try:
        selected_contact = contacts[int(choice)-1]
        render_thread(selected_contact)
    except:
        print("Invalid selection.")
