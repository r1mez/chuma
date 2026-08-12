"""Train the course-isolated student-knowledge DyGKT checkpoint.

Examples:
  python scripts/train_gnn.py
  python scripts/train_gnn.py --course-id 1 --course-id 2 --epochs 50
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ``python scripts/train_gnn.py`` puts ``scripts/`` rather than the AI-service
# root on sys.path.  Make the documented command work without requiring users
# to export PYTHONPATH manually.
AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from app.config import settings
from app.engines.gnn.trainer import train_from_repository


def main() -> None:
    parser = argparse.ArgumentParser(description="训练学生-知识点、课程隔离的原版结构 DyGKT 模型")
    parser.add_argument("--course-id", action="append", type=int, dest="course_ids", help="只训练指定学科；可重复传入")
    parser.add_argument("--output", default=settings.TGNN_MODEL_PATH, help="模型 checkpoint 文件路径")
    parser.add_argument("--epochs", type=int, default=settings.TGNN_TRAIN_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=settings.TGNN_TRAIN_BATCH_SIZE)
    parser.add_argument("--learning-rate", type=float, default=settings.TGNN_TRAIN_LEARNING_RATE)
    parser.add_argument("--history-size", type=int, default=settings.TGNN_HISTORY_SIZE)
    parser.add_argument("--min-samples", type=int, default=settings.TGNN_TRAIN_MIN_SAMPLES)
    args = parser.parse_args()

    result = train_from_repository(
        course_ids=args.course_ids,
        output_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        history_size=args.history_size,
        min_samples=args.min_samples,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
