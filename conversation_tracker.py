#!/usr/bin/env python3
"""
Daily Conversation Tracker
ஒரு நாளில் யாரோட எவ்வளோ நேரம், எப்படி பேசினோம் என்று track பண்ண
"""

import csv
import os
from datetime import datetime

CSV_FILE = "conversations_dataset.csv"
FIELDNAMES = [
    "date",
    "time",
    "person_name",
    "contact_type",       # Call / Chat / In-person
    "duration_minutes",
    "topic",
    "notes",
    "mood_after",         # 😊 Good / 😐 Neutral / 😔 Bad
]

# ── Colours ──────────────────────────────────────────────────────────────────
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def init_csv():
    """CSV file இல்லன்னா புதுசா create பண்ணும்."""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
        print(f"{GREEN}✅ புதுசா '{CSV_FILE}' create ஆச்சு!{RESET}\n")

def ask(prompt, options=None, required=True):
    """User input வாங்குற helper."""
    while True:
        if options:
            print(f"{CYAN}   Options: {' / '.join(f'[{i+1}] {o}' for i,o in enumerate(options))}{RESET}")
        value = input(f"  {BOLD}{prompt}{RESET} ").strip()

        if not value and not required:
            return ""
        if not value and required:
            print(f"{RED}  ⚠️  இது mandatory — please enter பண்ணுங்க.{RESET}")
            continue
        if options:
            if value.isdigit() and 1 <= int(value) <= len(options):
                return options[int(value) - 1]
            elif value in options:
                return value
            else:
                print(f"{RED}  ⚠️  Valid option select பண்ணுங்க (1-{len(options)}).{RESET}")
                continue
        return value

def add_entry():
    """புதுசா ஒரு conversation entry add பண்ண."""
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   ➕  புதுசா Conversation Add பண்ணுங்க")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    now = datetime.now()

    # Date — default today
    date_input = input(f"  {BOLD}Date (YYYY-MM-DD) [Enter = today {now.strftime('%Y-%m-%d')}]:{RESET} ").strip()
    date = date_input if date_input else now.strftime("%Y-%m-%d")

    # Time — default now
    time_input = input(f"  {BOLD}Time (HH:MM) [Enter = now {now.strftime('%H:%M')}]:{RESET} ").strip()
    time = time_input if time_input else now.strftime("%H:%M")

    person_name    = ask("யாரோட பேசினீங்க? (Person Name):")
    contact_type   = ask("எப்படி பேசினீங்க?", options=["Call", "Chat", "In-person"])

    while True:
        dur = input(f"  {BOLD}எவ்வளோ நேரம் பேசினீங்க? (minutes):{RESET} ").strip()
        if dur.isdigit() and int(dur) > 0:
            duration_minutes = int(dur)
            break
        print(f"{RED}  ⚠️  Valid number enter பண்ணுங்க.{RESET}")

    topic      = ask("என்ன topic பேசினீங்க? (சுருக்கமா):")
    notes      = ask("கூடுதல் notes (optional):", required=False) or "-"
    mood_after = ask("பேசிட்டு mood எப்படி இருந்துச்சு?", options=["Good", "Neutral", "Bad"])

    entry = {
        "date":             date,
        "time":             time,
        "person_name":      person_name,
        "contact_type":     contact_type,
        "duration_minutes": duration_minutes,
        "topic":            topic,
        "notes":            notes,
        "mood_after":       mood_after,
    }

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(entry)

    print(f"\n{GREEN}✅ Entry saved!{RESET}")
    print(f"   📅 {date} {time} | 👤 {person_name} | 📞 {contact_type} | ⏱ {duration_minutes} min | 😊 {mood_after}\n")

def view_today():
    """இன்னைக்கு பேசின conversations காட்டும்."""
    today = datetime.now().strftime("%Y-%m-%d")
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [r for r in reader if r["date"] == today]

    print(f"\n{BOLD}{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   📅  இன்னைக்கு ({today}) Conversations")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    if not rows:
        print(f"  {YELLOW}இன்னைக்கு எந்த entry-யும் இல்ல.{RESET}\n")
        return

    total_min = 0
    for i, r in enumerate(rows, 1):
        print(f"  {BOLD}[{i}]{RESET} {r['time']} | 👤 {r['person_name']} | "
              f"📞 {r['contact_type']} | ⏱ {r['duration_minutes']} min | "
              f"💬 {r['topic']} | 😊 {r['mood_after']}")
        if r['notes'] != "-":
            print(f"       📝 {r['notes']}")
        total_min += int(r['duration_minutes'])

    print(f"\n  {GREEN}மொத்தம்: {len(rows)} conversations | {total_min} minutes{RESET}\n")

def view_summary():
    """Per-person summary காட்டும்."""
    if not os.path.exists(CSV_FILE):
        print(f"\n{RED}  Dataset இல்ல இன்னும்.{RESET}\n")
        return

    from collections import defaultdict
    stats = defaultdict(lambda: {"count": 0, "total_min": 0, "types": set()})

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            p = r["person_name"]
            stats[p]["count"]     += 1
            stats[p]["total_min"] += int(r["duration_minutes"])
            stats[p]["types"].add(r["contact_type"])

    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"   📊  Person-wise Summary")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    sorted_stats = sorted(stats.items(), key=lambda x: x[1]["total_min"], reverse=True)
    for person, s in sorted_stats:
        types_str = ", ".join(sorted(s["types"]))
        print(f"  👤 {BOLD}{person}{RESET}")
        print(f"     Conversations: {s['count']} | Total: {s['total_min']} min | Via: {types_str}\n")

def export_info():
    abs_path = os.path.abspath(CSV_FILE)
    print(f"\n{GREEN}📁 Dataset location: {abs_path}{RESET}\n")

def main():
    init_csv()

    print(f"\n{BOLD}{GREEN}╔══════════════════════════════════════════╗")
    print(f"║   🗣️  Daily Conversation Tracker        ║")
    print(f"║   யாரோட எவ்வளோ நேரம் பேசினோம்?        ║")
    print(f"╚══════════════════════════════════════════╝{RESET}")

    while True:
        print(f"\n{BOLD}என்ன பண்ணணும்?{RESET}")
        print(f"  {CYAN}[1]{RESET} ➕  புதுசா conversation add பண்ண")
        print(f"  {CYAN}[2]{RESET} 📅  இன்னைக்கு conversations பார்க்க")
        print(f"  {CYAN}[3]{RESET} 📊  Person-wise summary பார்க்க")
        print(f"  {CYAN}[4]{RESET} 📁  CSV file location")
        print(f"  {CYAN}[5]{RESET} 🚪  Exit")

        choice = input(f"\n  {BOLD}உங்கள் choice (1-5):{RESET} ").strip()

        if choice == "1":
            add_entry()
            # Multiple entries add பண்ண option
            while True:
                more = input(f"  {CYAN}இன்னொரு conversation add பண்ணணுமா? (y/n):{RESET} ").strip().lower()
                if more == "y":
                    add_entry()
                else:
                    break

        elif choice == "2":
            view_today()

        elif choice == "3":
            view_summary()

        elif choice == "4":
            export_info()

        elif choice == "5":
            print(f"\n{GREEN}👋 Bye! Data save ஆயிடுச்சு — '{CSV_FILE}' check பண்ணுங்க.{RESET}\n")
            break

        else:
            print(f"{RED}  ⚠️  1 to 5 மட்டும் enter பண்ணுங்க.{RESET}")

if __name__ == "__main__":
    main()