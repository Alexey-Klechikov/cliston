import re
from datetime import UTC, datetime
from typing import Any

from cliston.core.garm.models import Report, ReportResult, TacticalManual, ToolCallTrace
from cliston.core.garm.tactics_storage import TacticsStorage
from cliston.core.models import ToolCall


class TacticsManager:
    MIN_RELIABILITY = 0.5
    QUERY_PLACEHOLDER = "[QUERY]"
    TICKER_PLACEHOLDER = "[TICKER]"
    TYPE_ACTION = "type"

    def __init__(self):
        self.tactics_storage = TacticsStorage()
        self.execution_trace: list[ToolCallTrace] = []

    @staticmethod
    def _normalize_manual_steps(manual_steps: list[str]) -> list[str]:
        cleaned = [str(step).strip() for step in manual_steps if str(step).strip()]

        # Remove leading numbers (e.g. "1. ") and return non-empty steps
        normalized = [re.sub(r"^\d+\.\s*", "", step).strip() for step in cleaned]
        return [step for step in normalized if step]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}

    @staticmethod
    def select_best_manual(existing_manuals: list[TacticalManual], objective: str) -> TacticalManual | None:
        objective_tokens = TacticsManager._tokenize(objective)

        # Filter valid manuals and score them
        valid_manuals = [
            (m, len(objective_tokens & TacticsManager._tokenize(m.objective)) + m.reliability)
            for m in existing_manuals
            if m.reliability >= TacticsManager.MIN_RELIABILITY and m.steps
        ]

        return max(valid_manuals, key=lambda x: x[1])[0] if valid_manuals else None

    @staticmethod
    def _extract_query_value(objective: str) -> str:
        quoted = re.search(r"['\"]([^'\"]+)['\"]", objective)
        if quoted:
            return quoted.group(1).strip()

        ticker_like = re.search(r"\b[A-Z]{2,8}\d{0,3}\b", objective)
        if ticker_like:
            return ticker_like.group(0).strip()

        return " ".join(objective.split())[:64]

    @staticmethod
    def _parse_browser_navigate(call_blob: str) -> ToolCall | None:
        """Parse browser_navigate call."""
        match = re.search(r"url\s*=\s*'([^']*)'", call_blob)
        url = match.group(1) if match else None
        return ToolCall(name="browser_navigate", arguments={"url": url}) if url else None

    @staticmethod
    def _parse_browser_interact(call_blob: str, query_value: str) -> ToolCall | None:
        """Parse browser_interact call."""
        arguments: dict[str, str] = {}
        for match in re.finditer(r"(action|selector|value)\s*=\s*'((?:\\'|[^'])*)'", call_blob):
            key = match.group(1)
            value = match.group(2).replace("\\'", "'").strip()
            if key == "value" and value in {TacticsManager.QUERY_PLACEHOLDER, TacticsManager.TICKER_PLACEHOLDER}:
                value = query_value
            arguments[key] = value

        # Require action and selector
        if not arguments.get("action") or not arguments.get("selector"):
            return None

        return ToolCall(name="browser_interact", arguments=arguments)

    @staticmethod
    def parse_manual_to_tool_calls(manual: TacticalManual, objective: str | None = None) -> list[ToolCall]:
        query_value = TacticsManager._extract_query_value(objective or manual.objective)
        manual_steps_text = "\n".join(TacticsManager._normalize_manual_steps(manual.steps))

        parsed_calls: list[ToolCall] = []
        call_blobs = re.findall(r"browser_(?:navigate|inspect|interact)\([^\n]*\)", manual_steps_text)

        for call_blob in call_blobs:
            if call_blob.startswith("browser_inspect"):
                parsed_calls.append(ToolCall(name="browser_inspect", arguments={}))
            elif call_blob.startswith("browser_navigate"):
                parsed = TacticsManager._parse_browser_navigate(call_blob)
                if parsed:
                    parsed_calls.append(parsed)
            elif call_blob.startswith("browser_interact"):
                parsed = TacticsManager._parse_browser_interact(call_blob, query_value)
                if parsed:
                    parsed_calls.append(parsed)

        return parsed_calls

    @staticmethod
    def _safe_str(value: Any) -> str:
        """Safely escape string for manual serialization."""
        return str(value).replace("\\", "\\\\").replace("'", "\\'").strip()

    @staticmethod
    def _parse_tool_call_as_string(tool_call: ToolCall) -> str | None:
        def _format_navigate() -> str:
            url = TacticsManager._safe_str(tool_call.arguments.get("url", ""))
            return f"browser_navigate(url='{url}')"

        def _format_interact() -> str:
            action = TacticsManager._safe_str(tool_call.arguments.get("action", ""))
            selector = TacticsManager._safe_str(tool_call.arguments.get("selector", ""))

            if action == TacticsManager.TYPE_ACTION:
                return "browser_interact(action='type', selector='{selector}', value='{value}')".format(
                    selector=selector,
                    value=TacticsManager.QUERY_PLACEHOLDER,
                )

            value = tool_call.arguments.get("value")
            if value:
                return "browser_interact(action='{action}', selector='{selector}', value='{value}')".format(
                    action=action,
                    selector=selector,
                    value=TacticsManager._safe_str(value),
                )
            return f"browser_interact(action='{action}', selector='{selector}')"

        def _format_inspect() -> str:
            return "browser_inspect()"
            # Dispatch table

        formatters = {
            "browser_navigate": _format_navigate,
            "browser_interact": _format_interact,
            "browser_inspect": _format_inspect,
        }

        formatter = formatters.get(tool_call.name)
        return formatter() if formatter else None

    @staticmethod
    def _build_verified_manual_steps(execution_trace: list[ToolCallTrace]) -> list[str]:
        successful_steps: list[str] = []

        for step in execution_trace:
            if not step.success:
                continue

            manual_step = TacticsManager._parse_tool_call_as_string(step.tool_call)
            if not manual_step:
                continue

            if successful_steps and successful_steps[-1] == manual_step:
                continue

            successful_steps.append(manual_step)

        return successful_steps

    @staticmethod
    def _normalize_objective(objective: str) -> str:
        """Normalize objective for comparison."""
        return objective.strip().lower()

    async def create_or_update_tactical_manual(
        self,
        domain: str,
        report: Report | None,
        existing_manuals: list[TacticalManual],
    ) -> None:
        if not (report and report.manual):
            return

        manual_steps = TacticsManager._build_verified_manual_steps(self.execution_trace)
        normalized_name = TacticsManager._normalize_objective(report.manual.name)
        existing_manual = next(
            (m for m in existing_manuals if TacticsManager._normalize_objective(m.objective) == normalized_name),
            None,
        )

        # Update reliability for existing manual
        if existing_manual:
            await self.tactics_storage.update_reliability(
                existing_manual,
                success=report.result == ReportResult.SUCCESS,
            )
            return

        # Only archive if successful
        if report.result == ReportResult.FAILURE or not manual_steps:
            return

        new_manual = TacticalManual(
            domain=domain,
            objective=report.manual.name,
            steps=manual_steps,
            success_count=1,
            failure_count=0,
            last_updated=datetime.now(UTC),
        )

        await self.tactics_storage.archive_manual(new_manual)
