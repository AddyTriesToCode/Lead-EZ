"""
View dry run messages saved during pipeline runs.
"""
import json
from pathlib import Path


def view_dry_run_messages():
    """Display all messages saved in dry run mode."""
    dry_run_file = Path("storage/messages/dry_run_messages.json")
    
    if not dry_run_file.exists():
        print("❌ No dry run messages found")
        print(f"   File: {dry_run_file}")
        return
    
    try:
        with open(dry_run_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
        
        if not isinstance(messages, list):
            print("❌ Invalid format in dry run messages file")
            return
        
        if len(messages) == 0:
            print("📭 No messages in dry run file (file is empty)")
            return
        
        print(f"📬 Found {len(messages)} dry run messages")
        print("=" * 80)
        
        for i, msg in enumerate(messages, 1):
            print(f"\n{i}. Message ID: {msg.get('message_id', 'N/A')}")
            print(f"   Channel: {msg.get('channel', 'N/A').upper()} | Variant: {msg.get('variant', 'N/A')}")
            print(f"   Lead: {msg.get('lead', {}).get('name', 'N/A')}")
            print(f"   Company: {msg.get('lead', {}).get('company', 'N/A')}")
            print(f"   Email: {msg.get('lead', {}).get('email', 'N/A')}")
            print(f"   Saved at: {msg.get('saved_at', msg.get('timestamp', 'N/A'))}")
            print(f"   Content preview: {msg.get('content', '')[:100]}...")
            
        print("\n" + "=" * 80)
        print(f"Total: {len(messages)} messages")
        print(f"File: {dry_run_file}")
        
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {dry_run_file}")
    except Exception as e:
        print(f"❌ Error reading file: {e}")


if __name__ == "__main__":
    view_dry_run_messages()
