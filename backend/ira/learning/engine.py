from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from ..experience.models import Experience, ExecutionPreference
from ..experience.store import ExperienceStore
from ..pipeline_log import pipeline_log


class LearningEngine:
    """Analyzes execution experiences to dynamically recommend optimal parameter paths."""

    def __init__(self, store: ExperienceStore, knowledge_service: Any | None = None) -> None:
        self.store = store
        self.knowledge_service = knowledge_service

    def learn(self, experience: Experience) -> None:
        """Analyzes an experience record, calculates confidence adjustments, and saves preferences."""
        tool = experience.tool
        original_params = experience.parameters
        param_hash = self.compute_hash(original_params)

        # Get all experiences for this tool to compute success/failure rate
        # We filter in memory to find ones matching param_hash
        all_exp = self.store.history(limit=1000)
        matching_exps = [
            e for e in all_exp
            if e.tool == tool and self.compute_hash(e.parameters) == param_hash
        ]

        successes = sum(1 for e in matching_exps if e.success)
        total = len(matching_exps)
        failures = total - successes

        # Confidence Formula: confidence = 1.0 - 0.75 ** (successes - failures)
        net = successes - failures
        if net <= 0:
            confidence = 0.0
        else:
            confidence = 1.0 - (0.75 ** net)
        confidence = max(0.0, min(1.0, confidence))

        success_rate = successes / total if total > 0 else 0.0

        # Determine the preferred parameters
        if experience.success:
            preferred = experience.metadata.get("recovered_parameters", original_params)
        else:
            # On failure, look up if we have an existing preference. If so, preserve its preferred_parameters
            # but update confidence and success rate. If not, default to original params.
            existing = self.store.preferred_parameters(tool, param_hash)
            preferred = existing.preferred_parameters if existing else original_params

        pref = ExecutionPreference(
            tool=tool,
            parameter_hash=param_hash,
            preferred_parameters=preferred,
            confidence=confidence,
            success_rate=success_rate,
            last_used=datetime.now(timezone.utc),
        )

        self.store.save_preference(pref)
        pipeline_log(
            "Learning",
            f"Preference updated for {tool} (hash: {param_hash[:8]}). "
            f"Successes: {successes}, Failures: {failures}, Confidence: {confidence:.2f}"
        )

        # Feed into Knowledge Graph
        if self.knowledge_service and hasattr(self.knowledge_service, "remember_experience"):
            try:
                self.knowledge_service.remember_experience(experience)
            except Exception as e:
                pipeline_log("Learning", f"Failed to sync with KnowledgeService: {e}")

    def recommend(self, tool: str, original_parameters: dict[str, Any]) -> ExecutionPreference | None:
        """Looks up a recommendation for the tool and parameter configuration if confidence is high enough."""
        param_hash = self.compute_hash(original_parameters)
        pref = self.store.preferred_parameters(tool, param_hash)
        
        # Only recommend if we actually have a preferred alternative and confidence is > 0.0
        if pref and pref.confidence > 0.0:
            # If the preferred params are identical to the original params, no recommendation is needed
            if self.compute_hash(pref.preferred_parameters) == param_hash:
                return None
            
            pipeline_log(
                "Learning",
                f"Recommending preferred path for {tool}: {pref.preferred_parameters} "
                f"(confidence: {pref.confidence:.2f})"
            )
            return pref
            
        return None

    @staticmethod
    def compute_hash(parameters: dict[str, Any]) -> str:
        """Generates a deterministic SHA-256 fingerprint for a parameters dictionary."""
        return hashlib.sha256(
            json.dumps(parameters, sort_keys=True).encode()
        ).hexdigest()
