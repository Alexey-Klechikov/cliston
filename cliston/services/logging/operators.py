from datetime import datetime
from pathlib import Path

from config import TaskExecutionConfig


def _get_or_create_log_file(task_id: str) -> Path:
    log_file = TaskExecutionConfig.TASK_LOG_DIR / f"{task_id}.txt"
    if not log_file.exists():
        log_file.touch()
    return log_file


def rename_log_file(task_id: str, state: str) -> Path:
    log_file = _get_or_create_log_file(task_id)
    completed_log_file = log_file.with_name(f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_{state}.txt")
    log_file.rename(completed_log_file)
    return completed_log_file


def log_task_input(user_message: str, task_id: str) -> None:
    log_file = _get_or_create_log_file(task_id)
    with open(log_file, "a") as f:
        f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
        f.write(f"TASK ID: {task_id}\n")
        f.write(f"USER MESSAGE: \n{user_message}\n\n")
        f.write("-" * 40 + "\n\n")


def log_task_output(role: str, output: str, task_id: str) -> None:
    log_file = _get_or_create_log_file(task_id)
    with open(log_file, "a") as f:
        f.write(f"TIMESTAMP: {datetime.now().isoformat()}\n")
        f.write(f"TASK ID: {task_id}\n")
        f.write(f"ROLE: {role}\n")
        f.write(f"OUTPUT: \n{output}\n\n")
        f.write("-" * 40 + "\n\n")
