"""
Clear dry run messages file.
"""
from pathlib import Path


def clear_dry_run_messages():
    """Delete the dry run messages file."""
    dry_run_file = Path("storage/messages/dry_run_messages.json")
    
    if not dry_run_file.exists():
        print("✓ No dry run messages file to clear")
        return
    
    try:
        # Read count first
        import json
        with open(dry_run_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
            count = len(messages) if isinstance(messages, list) else 0
        
        # Delete file
        dry_run_file.unlink()
        print(f"✓ Cleared {count} dry run messages")
        print(f"  File deleted: {dry_run_file}")
        
    except Exception as e:
        print(f"❌ Error clearing messages: {e}")


if __name__ == "__main__":
    clear_dry_run_messages()
