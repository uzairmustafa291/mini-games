import json
import math
import os
import tempfile
from datetime import datetime
from pathlib import Path


SCORES_FILE = Path(__file__).with_name("puzzle_scores.json")


def load_scores():
    try:
        with SCORES_FILE.open("r", encoding="utf-8") as score_file:
            scores = json.load(score_file)
    except FileNotFoundError:
        return []

    if not isinstance(scores, list):
        raise ValueError("The score file must contain a list of scores.")

    for score in scores:
        if (
            not isinstance(score, dict)
            or not isinstance(score.get("roll_number"), str)
            or not isinstance(score.get("name"), str)
            or not isinstance(score.get("seconds"), (int, float))
            or isinstance(score.get("seconds"), bool)
            or not math.isfinite(score["seconds"])
            or score["seconds"] < 0
            or not isinstance(score.get("won"), bool)
        ):
            raise ValueError("The score file contains an invalid score entry.")

    return scores


def has_played(scores, roll_number):
    normalized_roll_number = roll_number.strip().casefold()
    return any(
        score["roll_number"].strip().casefold() == normalized_roll_number
        for score in scores
    )


def record_score(scores, roll_number, name, seconds, won):
    if has_played(scores, roll_number):
        raise ValueError("This roll number has already played.")

    updated_scores = [
        *scores,
        {
            "roll_number": roll_number,
            "name": name,
            "seconds": round(seconds, 2),
            "won": won,
            "played_at": datetime.now().isoformat(timespec="seconds"),
        },
    ]

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=SCORES_FILE.parent,
            prefix=f"{SCORES_FILE.name}.",
            suffix=".tmp",
            delete=False,
        ) as score_file:
            temporary_path = Path(score_file.name)
            json.dump(updated_scores, score_file, indent=2)
            score_file.write("\n")
            score_file.flush()
            os.fsync(score_file.fileno())
        os.replace(temporary_path, SCORES_FILE)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return updated_scores
