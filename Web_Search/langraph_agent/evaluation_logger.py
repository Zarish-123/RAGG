
import json
from datetime import datetime, timezone
from pathlib import Path


# Store results in this file
EVALUATION_FILE = Path(__file__).parent / "evaluations.jsonl"


def save_evaluation(
    question: str,
    answer: str,
    evaluation: dict
) -> None:

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "answer": answer,
        "metrics": evaluation
    }

    # Append one JSON record per line
    with open(
        EVALUATION_FILE,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            json.dumps(record, ensure_ascii=False) + "\n"
        )

    print(f"\nEvaluation saved to: {EVALUATION_FILE}")
