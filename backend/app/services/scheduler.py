import asyncio
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from app.services.podcast import generate_podcast_show
from app.config import settings

SCHEDULES_FILE = Path("./podcast_schedules.json")
LEGACY_SCHEDULE_FILE = Path("./podcast_schedule.json")

DEFAULT_PROGRAMS = [
    {
        "id": "prog_matinale_07",
        "name": "Matinale Quotidienne 07:00",
        "enabled": True,
        "frequency": "daily",
        "time": "07:00",
        "topics_count": 5,
        "max_days": 7,
        "only_verified": True,
        "tone": "journal_matinal",
        "voice": "Marie - Neutral",
        "theme": "",
        "last_run": None
    }
]

def calculate_next_run(prog: dict) -> str:
    if not prog.get("enabled"):
        return "Désactivé"

    time_str = prog.get("time", "07:00")
    freq = prog.get("frequency", "daily")

    try:
        target_hour, target_minute = map(int, time_str.split(":"))
    except Exception:
        target_hour, target_minute = 7, 0

    now = datetime.now()

    for day_offset in range(8):
        candidate = now + timedelta(days=day_offset)
        candidate_target = candidate.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if candidate_target <= now:
            continue

        weekday = candidate.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
        matches_freq = False
        if freq == "daily":
            matches_freq = True
        elif freq == "weekdays" and weekday < 5:
            matches_freq = True
        elif freq == "weekly_monday" and weekday == 0:
            matches_freq = True
        elif freq == "weekly_friday" and weekday == 4:
            matches_freq = True

        if matches_freq:
            diff_sec = int((candidate_target - now).total_seconds())
            hours = diff_sec // 3600
            mins = (diff_sec % 3600) // 60

            if day_offset == 0:
                day_name = "Aujourd'hui"
            elif day_offset == 1:
                day_name = "Demain"
            else:
                days_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
                day_name = days_fr[weekday]

            time_formatted = candidate_target.strftime("%H:%M")
            countdown = f"dans {hours}h {mins}min" if hours > 0 else f"dans {mins}min"
            return f"{day_name} à {time_formatted} ({countdown})"

    return "Prochainement"

def load_schedules() -> list[dict]:
    if not SCHEDULES_FILE.exists():
        if LEGACY_SCHEDULE_FILE.exists():
            try:
                with open(LEGACY_SCHEDULE_FILE, "r", encoding="utf-8") as f:
                    legacy = json.load(f)
                    legacy["id"] = "prog_matinale_legacy"
                    legacy["name"] = "Programme Principal"
                    save_schedules([legacy])
                    return [legacy]
            except Exception:
                pass
        save_schedules(DEFAULT_PROGRAMS)
        return DEFAULT_PROGRAMS

    try:
        with open(SCHEDULES_FILE, "r", encoding="utf-8") as f:
            programs = json.load(f)
            if isinstance(programs, list):
                for p in programs:
                    p["next_run_display"] = calculate_next_run(p)
                return programs
            return DEFAULT_PROGRAMS
    except Exception:
        return DEFAULT_PROGRAMS

def save_schedules(programs: list[dict]):
    with open(SCHEDULES_FILE, "w", encoding="utf-8") as f:
        json.dump(programs, f, indent=2, ensure_ascii=False)

def add_schedule_program(data: dict) -> dict:
    programs = load_schedules()
    prog_id = f"prog_{secrets.token_hex(4)}"
    new_prog = {
        "id": prog_id,
        "name": data.get("name") or "Nouveau Programme Radio",
        "enabled": bool(data.get("enabled", True)),
        "frequency": data.get("frequency", "daily"),
        "time": data.get("time", "07:00"),
        "topics_count": int(data.get("topics_count", 5)),
        "max_days": int(data.get("max_days", 7)),
        "only_verified": bool(data.get("only_verified", True)),
        "tone": data.get("tone", "journal_matinal"),
        "voice": data.get("voice", "Marie - Neutral"),
        "theme": data.get("theme", ""),
        "last_run": None
    }
    programs.append(new_prog)
    save_schedules(programs)
    new_prog["next_run_display"] = calculate_next_run(new_prog)
    return new_prog

def update_schedule_program(prog_id: str, data: dict) -> dict:
    programs = load_schedules()
    updated_prog = None
    for p in programs:
        if p["id"] == prog_id:
            p["name"] = data.get("name", p.get("name"))
            p["enabled"] = bool(data.get("enabled", p.get("enabled")))
            p["frequency"] = data.get("frequency", p.get("frequency"))
            p["time"] = data.get("time", p.get("time"))
            p["topics_count"] = int(data.get("topics_count", p.get("topics_count")))
            p["max_days"] = int(data.get("max_days", p.get("max_days")))
            p["only_verified"] = bool(data.get("only_verified", p.get("only_verified")))
            p["tone"] = data.get("tone", p.get("tone"))
            p["voice"] = data.get("voice", p.get("voice"))
            p["theme"] = data.get("theme", p.get("theme"))
            updated_prog = p
            break

    if updated_prog:
        save_schedules(programs)
        updated_prog["next_run_display"] = calculate_next_run(updated_prog)
        return updated_prog
    raise ValueError("Programme introuvable.")

def toggle_schedule_program(prog_id: str, enabled: bool = None) -> dict:
    programs = load_schedules()
    target_prog = None
    for p in programs:
        if p["id"] == prog_id:
            p["enabled"] = not p["enabled"] if enabled is None else enabled
            target_prog = p
            break

    if target_prog:
        save_schedules(programs)
        target_prog["next_run_display"] = calculate_next_run(target_prog)
        return target_prog
    raise ValueError("Programme introuvable.")

def delete_schedule_program(prog_id: str):
    programs = load_schedules()
    filtered = [p for p in programs if p["id"] != prog_id]
    save_schedules(filtered)
    return {"status": "success", "id": prog_id}

def should_run_today(frequency: str, now: datetime) -> bool:
    weekday = now.weekday()  # 0 = Monday, 4 = Friday, 5 = Sat, 6 = Sun
    if frequency == "daily":
        return True
    elif frequency == "weekly_monday":
        return weekday == 0
    elif frequency == "weekly_friday":
        return weekday == 4
    elif frequency == "weekdays":
        return weekday < 5
    return True

async def start_podcast_scheduler_loop():
    """
    Background loop that checks every 30 seconds all enabled podcast programs
    and triggers automated show generation when target time is reached.
    """
    print("[Podcast Scheduler] Boucle d'arrière-plan multi-programmes démarrée.")
    while True:
        try:
            programs = load_schedules()
            now = datetime.now()
            current_time_str = now.strftime("%H:%M")
            current_date_str = now.strftime("%Y-%m-%d")

            for prog in programs:
                if not prog.get("enabled"):
                    continue

                freq = prog.get("frequency", "daily")
                target_time = prog.get("time", "07:00")
                last_run = prog.get("last_run")

                if should_run_today(freq, now) and current_time_str == target_time and last_run != current_date_str:
                    from app.api.routes_feeds import get_vps_api_key
                    key = get_vps_api_key()

                    if key:
                        print(f"[Podcast Scheduler] Déclenchement du programme '{prog.get('name')}' ({freq}, {target_time})...")
                        await generate_podcast_show(
                            topics_count=prog.get("topics_count", 5),
                            max_days=prog.get("max_days", 7),
                            only_verified=prog.get("only_verified", True),
                            tone=prog.get("tone", "journal_matinal"),
                            voice_key=prog.get("voice", "Marie - Neutral"),
                            theme=prog.get("theme", ""),
                            api_key=key
                        )
                        prog["last_run"] = current_date_str
                        save_schedules(programs)
                        print(f"[Podcast Scheduler] Émission '{prog.get('name')}' générée avec succès !")
                    else:
                        print(f"[Podcast Scheduler Note] Clé API Mistral non disponible pour le programme '{prog.get('name')}'.")

        except Exception as e:
            print(f"[Podcast Scheduler Loop Error]: {e}")

        await asyncio.sleep(30)
