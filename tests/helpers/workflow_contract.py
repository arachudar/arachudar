"""
tests/helpers/workflow_contract.py
Contract reference adapter for GitHub Actions news_pipeline.yml (Feature 12)
and Dry-Run Verification integration (Feature 13).
"""

from typing import List, Dict, Any, Optional


class WorkflowContract:
    """
    Contract reference adapter for GitHub Actions news_pipeline.yml (F12)
    and Dry-Run Verification integration (F13).
    Conforms to PROJECT.md § CI/CD Automation and R4/R5.
    """
    REQUIRED_SECRETS = frozenset({
        "NVIDIA_API_KEY",
        "BLOGGER_BLOG_ID",
        "BLOGGER_CLIENT_ID",
        "BLOGGER_CLIENT_SECRET",
        "BLOGGER_REFRESH_TOKEN",
    })

    CRON_SCHEDULE = "0 */4 * * *"

    DISPATCH_INPUTS = {
        "dry_run": {"default": "false", "type": "boolean"},
        "limit": {"default": "5", "type": "number"},
        "category": {"default": "all", "type": "string"},
    }

    @classmethod
    def get_authoritative_spec(cls) -> Dict[str, Any]:
        return {
            "name": "Arachudar Tamil News Automation Pipeline",
            "cron_schedule": cls.CRON_SCHEDULE,
            "cron_interval_hours": 4,
            "dispatch_inputs": cls.DISPATCH_INPUTS,
            "required_secrets": list(cls.REQUIRED_SECRETS),
            "runner_command": "python -m src.pipeline",
        }

    @classmethod
    def validate_cron_schedule(cls, cron_expr: str, min_interval_hours: int = 1) -> bool:
        """
        Validates 5-part cron syntax and enforces safe interval >= min_interval_hours.
        """
        if not cron_expr or not isinstance(cron_expr, str):
            return False
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        minute, hour, dom, month, dow = parts
        if minute != "0" and not minute.isdigit():
            return False
        if hour.startswith("*/"):
            try:
                step = int(hour[2:])
                if step < min_interval_hours or step > 24:
                    return False
            except ValueError:
                return False
        elif hour.isdigit():
            h_val = int(hour)
            if h_val < 0 or h_val > 23:
                return False
        elif hour == "*":
            if min_interval_hours > 1:
                return False
        return True

    @classmethod
    def build_dispatch_command(
        cls,
        dry_run: bool = False,
        limit: int = 5,
        category: str = "all"
    ) -> List[str]:
        """Translates workflow_dispatch inputs into pipeline CLI arguments."""
        cmd = ["python", "-m", "src.pipeline", f"--limit={limit}"]
        if category and category != "all":
            cmd.append(f"--category={category}")
        if dry_run:
            cmd.append("--dry-run")
        return cmd

    @classmethod
    def simulate_workflow_execution(cls, dry_run: bool = True) -> Dict[str, Any]:
        """
        Simulates workflow execution. In dry-run mode, guarantees 0 live posts.
        """
        if dry_run:
            return {
                "status": "PASS",
                "dry_run_mode": True,
                "live_posts": 0,
                "html_updated_ephemeral": True,
                "canonical_template_mutated": False,
            }
        return {
            "status": "PASS",
            "dry_run_mode": False,
            "live_posts": 1,
            "html_updated_ephemeral": True,
            "canonical_template_mutated": False,
        }

    @classmethod
    def validate_workflow_spec(cls, workflow_text: str) -> Dict[str, Any]:
        """Validates real YAML workflow text against contract."""
        schedule_valid = ("0 */4 * * *" in workflow_text) or ("schedule:" in workflow_text and "cron:" in workflow_text)
        has_dispatch = "workflow_dispatch:" in workflow_text
        has_dry_run = "dry_run:" in workflow_text
        secrets_found = [sec for sec in cls.REQUIRED_SECRETS if sec in workflow_text]
        return {
            "schedule_valid": schedule_valid,
            "has_workflow_dispatch": has_dispatch,
            "has_dry_run_input": has_dry_run,
            "secrets_found": secrets_found,
            "has_all_secrets": len(secrets_found) == len(cls.REQUIRED_SECRETS),
        }
