"""Deterministic local-fixture browser runtime."""

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import json

from kernel.personal_ai.adapters.adapter_registry import admit_adapter_capability
from kernel.personal_ai.adapters.browser_adapter_contract import (
    BrowserFixtureActions,
    BrowserFixtureRuntimePaths,
    build_browser_fixture_capability_request,
)
from kernel.personal_ai.hash_utils import sha256_file, sha256_text
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BrowserFixtureResult",
    "run_browser_fixture",
    "run_browser_fixture_from_actions_file",
]


@dataclass(frozen=True)
class BrowserFixtureResult:
    fixture_path: Path
    output_dir: Path
    action_log_path: Path
    evidence_manifest_path: Path
    action_count: int
    required_human_approval: bool


def run_browser_fixture_from_actions_file(
    fixture_path: Path,
    actions_path: Path,
    output_dir: Path,
) -> BrowserFixtureResult:
    action_file = Path(actions_path)
    if not action_file.exists() or not action_file.is_file():
        raise ValueError("actions_path is missing")
    try:
        actions = json.loads(action_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("actions_path is malformed") from error
    policy = {}
    if isinstance(actions, dict) and isinstance(actions.get("actions"), list):
        policy = actions.get("policy", {})
        actions = actions["actions"]
    if policy is None:
        policy = {}
    if not isinstance(policy, dict):
        raise ValueError("browser fixture policy is malformed")
    return run_browser_fixture(
        fixture_path,
        output_dir,
        actions,
        allowed_domains=tuple(policy.get("allowed_domains", ())),
        allow_form_submit=policy.get("allow_form_submit") is True,
        timeout_seconds=int(policy.get("timeout_seconds", 5)),
    )


def run_browser_fixture(
    fixture_path: Path,
    output_dir: Path,
    actions: list[dict[str, object]],
    *,
    allowed_domains: tuple[str, ...] = (),
    allow_form_submit: bool = False,
    timeout_seconds: int = 5,
) -> BrowserFixtureResult:
    if str(fixture_path).startswith(("http://", "https://")):
        raise ValueError("external URLs are not allowed")
    fixture_file = Path(fixture_path)
    output_path = Path(output_dir)
    _validate_fixture_path(fixture_file)
    _validate_output_dir(fixture_file, output_path)
    if not isinstance(actions, list):
        raise ValueError("browser fixture actions must be a list")
    _validate_runtime_policy(allowed_domains, allow_form_submit, timeout_seconds)

    paths = BrowserFixtureRuntimePaths()
    action_log_path = output_path / paths.action_log_file
    evidence_manifest_path = output_path / paths.evidence_manifest_file
    _require_no_overwrite(action_log_path)
    _require_no_overwrite(evidence_manifest_path)

    decision = admit_adapter_capability(build_browser_fixture_capability_request())
    if not decision.is_runtime_safe_for_current_branch():
        raise ValueError("browser fixture adapter is not admitted")

    html = fixture_file.read_text(encoding="utf-8")
    parser = _FixtureParser()
    parser.feed(html)
    _validate_fixture_navigation_policy(parser, allowed_domains)
    before_snapshot = _snapshot(parser, html, filled_fields={})
    filled_fields = {}
    action_records = []
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError("browser fixture action is malformed")
        action_records.append(
            _apply_action(
                index,
                action,
                parser,
                filled_fields,
                allow_form_submit=allow_form_submit,
            )
        )
    after_snapshot = _snapshot(parser, html, filled_fields=filled_fields)

    action_log = {
        "log_type": "personal_ai_execution_os_v2_browser_action_log",
        "authority": "non_authority",
        "execution_capability": "deterministic_local_fixture_only",
        "fixture_path": fixture_file.as_posix(),
        "fixture_sha256": sha256_file(fixture_file),
        "external_network_used": False,
        "credential_storage_used": False,
        "payment_action_performed": False,
        "account_creation_performed": False,
        "real_browser_runtime_used": False,
        "playwright_runtime_used": False,
        "selenium_runtime_used": False,
        "external_navigation_denied_by_default": True,
        "domain_allowlist": list(allowed_domains),
        "timeout_seconds": timeout_seconds,
        "destructive_action_performed": False,
        "allowed_actions": list(BrowserFixtureActions.allowed()),
        "actions": action_records,
        "required_human_approval": True,
    }
    evidence_manifest = {
        "manifest_type": "personal_ai_execution_os_v2_browser_evidence_manifest",
        "authority": "non_authority",
        "execution_capability": "deterministic_local_fixture_only",
        "fixture_path": fixture_file.as_posix(),
        "fixture_sha256": sha256_file(fixture_file),
        "action_log_path": action_log_path.as_posix(),
        "before_dom_snapshot": before_snapshot,
        "after_dom_snapshot": after_snapshot,
        "external_urls_rejected": True,
        "domain_allowlist": list(allowed_domains),
        "external_navigation_denied_by_default": True,
        "form_submission_requires_fixture_policy": True,
        "form_submission_approval_gate_satisfied": allow_form_submit,
        "credential_storage_used": False,
        "payment_action_performed": False,
        "account_creation_performed": False,
        "real_screenshot_captured": False,
        "screenshot_evidence": {
            "mode": "dom_metadata_only_fixture",
            "real_screenshot_captured": False,
            "before_dom_sha256": before_snapshot["dom_sha256"],
            "after_dom_sha256": after_snapshot["dom_sha256"],
        },
        "timeout_quarantine_policy": {
            "timeout_seconds": timeout_seconds,
            "failure_quarantine_required": True,
            "external_runtime_timeout_not_applicable": True,
        },
        "raw_filled_values_stored": False,
        "required_human_approval": True,
    }
    write_json_atomically(action_log_path, action_log)
    write_json_atomically(evidence_manifest_path, evidence_manifest)
    return BrowserFixtureResult(
        fixture_path=fixture_file,
        output_dir=output_path,
        action_log_path=action_log_path,
        evidence_manifest_path=evidence_manifest_path,
        action_count=len(action_records),
        required_human_approval=True,
    )


class _FixtureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.links = []
        self.inputs = {}
        self.buttons = {}
        self.form_count = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = {key: value or "" for key, value in attrs}
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self.links.append(
                {
                    "href": attrs_dict.get("href", ""),
                    "text": "",
                }
            )
        if tag == "input":
            name = attrs_dict.get("name", attrs_dict.get("id", ""))
            if name:
                self.inputs[name] = attrs_dict
        if tag == "button":
            button_id = attrs_dict.get("id", attrs_dict.get("name", ""))
            if button_id:
                self.buttons[button_id] = attrs_dict
        if tag == "form":
            self.form_count += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        if self.links and self.links[-1]["text"] == "":
            text = data.strip()
            if text:
                self.links[-1]["text"] = text


def _validate_fixture_path(fixture_file):
    fixture_text = str(fixture_file)
    if fixture_text.startswith(("http://", "https://")):
        raise ValueError("external URLs are not allowed")
    if not fixture_file.exists():
        raise ValueError("fixture_path is missing")
    if not fixture_file.is_file():
        raise ValueError("fixture_path is not a file")
    if fixture_file.suffix.lower() not in (".html", ".htm"):
        raise ValueError("fixture_path must be an html file")


def _validate_output_dir(fixture_file, output_path):
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    if _path_is_inside(output_path, fixture_file.parent):
        raise ValueError("output_dir must be outside fixture directory")


def _validate_runtime_policy(allowed_domains, allow_form_submit, timeout_seconds):
    if not isinstance(allowed_domains, tuple):
        raise ValueError("allowed_domains must be a tuple")
    for domain in allowed_domains:
        if not isinstance(domain, str) or not domain:
            raise ValueError("allowed domain is malformed")
        if "/" in domain or ":" in domain:
            raise ValueError("allowed domain must be a hostname")
    if allow_form_submit not in (True, False):
        raise ValueError("allow_form_submit must be a boolean")
    if type(timeout_seconds) is not int or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if timeout_seconds > 30:
        raise ValueError("timeout_seconds exceeds browser fixture policy")


def _validate_fixture_navigation_policy(parser, allowed_domains):
    for link in parser.links:
        href = link["href"]
        if _is_external_url(href) and _url_host(href) not in allowed_domains:
            raise ValueError("external fixture link is not in domain allowlist")


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = Path(candidate_path).resolve(strict=True)
    resolved_root = Path(root_path).resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True


def _require_no_overwrite(path):
    if Path(path).exists():
        raise ValueError("browser fixture output already exists")


def _apply_action(index, action, parser, filled_fields, *, allow_form_submit):
    action_name = action.get("action")
    if action_name not in BrowserFixtureActions.allowed():
        raise ValueError("browser fixture action is not allowed")
    if _action_contains_external_url(action):
        raise ValueError("external URLs are not allowed")
    if _action_contains_forbidden_sensitive_intent(action):
        raise ValueError("sensitive browser action is not allowed")
    if action_name == BrowserFixtureActions.OPEN_LOCAL_FIXTURE:
        return _action_record(index, action_name, {"opened": True})
    if action_name == BrowserFixtureActions.INSPECT_TITLE:
        return _action_record(index, action_name, {"title": parser.title})
    if action_name == BrowserFixtureActions.INSPECT_LINKS:
        return _action_record(
            index,
            action_name,
            {
                "link_count": len(parser.links),
                "links": [
                    {
                        "href": link["href"],
                        "text_length": len(link["text"]),
                    }
                    for link in parser.links
                ],
            },
        )
    if action_name == BrowserFixtureActions.FILL_ALLOWED_FIELD:
        return _fill_allowed_field(index, action, parser, filled_fields)
    if action_name == BrowserFixtureActions.CLICK_ALLOWED_BUTTON:
        return _click_allowed_button(
            index,
            action,
            parser,
            allow_form_submit=allow_form_submit,
        )
    raise ValueError("browser fixture action is not allowed")


def _action_contains_external_url(action):
    for value in action.values():
        if isinstance(value, str) and _is_external_url(value):
            return True
    return False


def _action_contains_forbidden_sensitive_intent(action):
    sensitive_terms = (
        "account",
        "api_key",
        "checkout",
        "credential",
        "password",
        "payment",
        "purchase",
        "register",
        "secret",
        "sign_up",
        "signup",
        "token",
    )
    for key, value in action.items():
        text = (str(key) + " " + str(value)).lower()
        if any(term in text for term in sensitive_terms):
            return True
    return False


def _fill_allowed_field(index, action, parser, filled_fields):
    field_name = str(action.get("field_name", ""))
    value = str(action.get("value", ""))
    field = parser.inputs.get(field_name)
    if field is None:
        raise ValueError("allowed field is missing")
    if field.get("data-seos-allowed-field") != "true":
        raise ValueError("field is not allowed by fixture policy")
    field_type = field.get("type", "text").lower()
    if field_type == "password" or _field_name_is_sensitive(field_name):
        raise ValueError("credential fields are not allowed")
    filled_fields[field_name] = {
        "value_length": len(value),
        "value_sha256": sha256_text(value),
    }
    return _action_record(
        index,
        BrowserFixtureActions.FILL_ALLOWED_FIELD,
        {
            "field_name": field_name,
            "value_length": len(value),
            "value_sha256": sha256_text(value),
            "raw_value_stored": False,
        },
    )


def _click_allowed_button(index, action, parser, *, allow_form_submit):
    button_id = str(action.get("button_id", ""))
    button = parser.buttons.get(button_id)
    if button is None:
        raise ValueError("allowed button is missing")
    if button.get("data-seos-allowed-button") != "true":
        raise ValueError("button is not allowed by fixture policy")
    if _button_is_forbidden_sensitive_action(button_id, button):
        raise ValueError("sensitive browser action is not allowed")
    button_type = button.get("type", "button").lower()
    if (
        button_type == "submit"
        and button.get("data-seos-allow-submit") != "true"
    ):
        raise ValueError("form submission is not allowed by fixture policy")
    if button_type == "submit" and allow_form_submit is not True:
        raise ValueError("form submission requires explicit approval gate")
    return _action_record(
        index,
        BrowserFixtureActions.CLICK_ALLOWED_BUTTON,
        {
            "button_id": button_id,
            "submit_action": button_type == "submit",
            "form_submit_approval_gate": allow_form_submit,
        },
    )


def _field_name_is_sensitive(field_name):
    lowered = field_name.lower()
    return any(
        token in lowered
        for token in (
            "api_key",
            "card",
            "credential",
            "cvv",
            "password",
            "secret",
            "ssn",
            "token",
        )
    )


def _button_is_forbidden_sensitive_action(button_id, button):
    action_text = " ".join(
        str(value)
        for value in (
            button_id,
            button.get("name", ""),
            button.get("value", ""),
            button.get("data-seos-action", ""),
        )
    ).lower()
    return any(
        token in action_text
        for token in (
            "account",
            "checkout",
            "payment",
            "purchase",
            "register",
            "sign_up",
            "signup",
        )
    )


def _is_external_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _url_host(value):
    if not _is_external_url(value):
        return ""
    without_scheme = value.split("://", 1)[1]
    host_port = without_scheme.split("/", 1)[0]
    return host_port.split(":", 1)[0].lower()


def _action_record(index, action_name, result):
    return {
        "index": index,
        "action": action_name,
        "status": "completed",
        "result": result,
    }


def _snapshot(parser, html, filled_fields):
    return {
        "title": parser.title,
        "dom_sha256": sha256_text(html),
        "link_count": len(parser.links),
        "allowed_field_count": sum(
            1
            for field in parser.inputs.values()
            if field.get("data-seos-allowed-field") == "true"
        ),
        "allowed_button_count": sum(
            1
            for button in parser.buttons.values()
            if button.get("data-seos-allowed-button") == "true"
        ),
        "form_count": parser.form_count,
        "filled_fields": {
            field_name: filled_fields[field_name]
            for field_name in sorted(filled_fields)
        },
        "screenshot_equivalent": "dom_metadata_only",
    }
