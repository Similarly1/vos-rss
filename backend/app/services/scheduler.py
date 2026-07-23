import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from app.services.podcast import generate_podcast_show
from app.config import settings

SCHEDULE_FILE = Path("./podcast_schedule.json")

DEFAULT_SCHEDULE = {
    "enabled": False,
    "frequency": "daily",  # 'daily' | 'weekly_monday' | 'weekly_friday' | 'weekdays'
    "time": "07:00",
    "topics_count": 5,
    "max_days": 7,
    "only_verified": True,
    "tone": "journal_matinal",
    "voice": "Marie - Dynamic",
    "theme": "",
    "last_run": None
}

def load_schedule_config() -> dict:
    if not SCHEDULE_FILE.exists():
        return DEFAULT_SCHEDULE
    try:
        with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**DEFAULT_SCHEDULE, **data}
    except Exception:
        return DEFAULT_SCHEDULE

def save_schedule_config(config: dict):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

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
    Background loop that checks every 30 seconds if it's time to automatically generate the scheduled podcast.
    """
    print("[Podcast Scheduler] Boucle d'arrière-plan démarrée.")
    while True:
        try:
            config = load_schedule_config()
            if config.get("enabled"):
                freq = config.get("frequency", "daily")
                target_time = config.get("time", "07:00")
                now = datetime.now()
                current_time_str = now.strftime("%H:%M")
                current_date_str = now.strftime("%Y-%m-%d")

                last_run = config.get("last_run")

                if should_run_today(freq, now) and current_time_str == target_time and last_run != current_date_str:
                    key = settings.mistral_api_key
                    if key:
                        print(f"[Podcast Scheduler] Déclenchement de l'émission programmée ({freq}, {target_time})...")
                        await generate_podcast_show(
                            topics_count=config.get("topics_count", 5),
                            max_days=config.get("max_days", 7),
                            only_verified=config.get("only_verified", True),
                            tone=config.get("tone", "journal_matinal"),
                            voice_key=config.get("voice", "Marie - Dynamic"),
                            theme=config.get("theme", ""),
                            api_key=key
                        )
                        config["last_run"] = current_date_str
                        save_schedule_config(config)
                        print("[Podcast Scheduler] Émission matinale générée et ajoutée au flux AntennaPod !")
                    else:
                        print("[Podcast Scheduler] Clé API Mistral non disponible dans settings pour le cron.")

        except Exception as e:
            print(f"[Podcast Scheduler Error]: {e}")

        await asyncio.sleep(30)
