import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from google.genai import types

from cliston.core.garm.models import TacticalManual, ToolCallTrace
from cliston.core.garm.tactics_storage import TacticsStorage
from cliston.core.models import ToolCall


class TacticsManager:
    MIN_RELIABILITY = 0.5
    SUCCESS_RESULT = "success"
    QUERY_PLACEHOLDER = "[QUERY]"
    TICKER_PLACEHOLDER = "[TICKER]"
    TYPE_ACTION = "type"

    def __init__(self):
        self.tactics_storage = TacticsStorage()
        self.execution_trace: list[ToolCallTrace] = []

    @staticmethod
    def _normalize_manual_steps(manual_steps: str | list[str]) -> list[str]:
        # Convert to list of lines and filter empty
        lines = manual_steps if isinstance(manual_steps, list) else manual_steps.splitlines()
        cleaned = [str(step).strip() for step in lines if str(step).strip()]

        # Remove leading numbers (e.g. "1. ") and return non-empty steps
        normalized = [re.sub(r"^\d+\.\s*", "", step).strip() for step in cleaned]
        return [step for step in normalized if step]

    @staticmethod
    def inject_manuals_into_request(
        request: list[types.Part],
        existing_manuals: list[TacticalManual],
    ) -> list[types.Part]:
        if existing_manuals:
            logging.info(f"Injecting {len(existing_manuals)} TACTICAL_MANUALS into Garm's knowledge base.")

            request += [
                types.Part.from_text(
                    text=f"""
    TACTICAL_MANUAL:
    > objective: {i.objective}
    > steps: {json.dumps(TacticsManager._normalize_manual_steps(i.manual), ensure_ascii=True)}
    > reliability: {i.reliability}
    > last_updated: {i.last_updated}
    """,
                )
                for i in existing_manuals
                if i.reliability >= TacticsManager.MIN_RELIABILITY
            ]
        return request

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
            if m.reliability >= TacticsManager.MIN_RELIABILITY and m.manual.strip()
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
    def parse_manual_to_tool_calls(manual_steps: str | list[str], objective: str) -> list[ToolCall]:
        query_value = TacticsManager._extract_query_value(objective)
        manual_steps_text = "\n".join(TacticsManager._normalize_manual_steps(manual_steps))

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
        objective: str,
        report: dict,
        existing_manuals: list[TacticalManual],
        replay_manual: TacticalManual | None,
    ) -> None:
        manual_name = (
            report.get("manual", {}).get("name") or objective.strip().rstrip(".") or f"{domain} Browser Infiltration"
        )

        if not manual_name:
            logging.warning("No TACTICAL_MANUAL name found in Garm's output. Skipping manual processing.")
            return

        manual_steps = TacticsManager._build_verified_manual_steps(self.execution_trace)
        is_success = report.get("result", "").lower() == self.SUCCESS_RESULT and bool(manual_steps)
        normalized_name = TacticsManager._normalize_objective(manual_name)
        existing_manual = next(
            (m for m in existing_manuals if TacticsManager._normalize_objective(m.objective) == normalized_name),
            None,
        )

        # Update reliability for replayed manual if different from existing
        if replay_manual and (
            not existing_manual
            or TacticsManager._normalize_objective(replay_manual.objective)
            != TacticsManager._normalize_objective(existing_manual.objective)
        ):
            await self.tactics_storage.update_reliability(replay_manual, success=is_success)

        # Update reliability for existing manual
        if existing_manual:
            await self.tactics_storage.update_reliability(existing_manual, success=is_success)

        # Only archive if successful
        if not is_success:
            return

        manual = "\n".join(f"{idx}. {step}" for idx, step in enumerate(manual_steps, start=1))

        new_manual = TacticalManual(
            domain=domain,
            objective=manual_name,
            manual=manual,
            success_count=1,
            failure_count=0,
            last_updated=datetime.now(UTC),
        )

        await self.tactics_storage.archive_manual(new_manual)
