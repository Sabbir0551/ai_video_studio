from typing import List, Tuple, Dict, Any
from backend.app.models.analysis import EditDecision, EditOperationType, AnalysisReport, WordDetail
from backend.app.core.logging import logger


class CutValidator:
    """Rule-based validator ensuring cuts preserve natural speech, respect word boundaries, and maintain minimum clip continuity."""

    def __init__(
        self,
        min_keep_duration: float = 0.8,
        breath_padding: float = 0.12
    ):
        self.min_keep_duration = min_keep_duration
        self.breath_padding = breath_padding

    def validate_and_repair_cuts(
        self,
        report: AnalysisReport,
        aggressiveness: str = "balanced"
    ) -> List[EditDecision]:
        logger.info(f"Validating edit decisions [aggressiveness={aggressiveness}, total_candidates={len(report.suggested_edits)}]")

        # 1. Filter accepted cuts only
        cut_candidates = [
            e for e in report.suggested_edits
            if e.accepted and e.operation in (EditOperationType.CUT_SILENCE, EditOperationType.CUT_FILLER)
        ]

        if not cut_candidates:
            return []

        # Adjust thresholds by aggressiveness
        if aggressiveness == "gentle":
            # Only cut silences > 0.9s and keep more breath room
            padding = 0.18
            min_gap_to_cut = 0.9
        elif aggressiveness == "aggressive":
            # Tight cuts
            padding = 0.08
            min_gap_to_cut = 0.35
        else: # balanced
            padding = self.breath_padding
            min_gap_to_cut = 0.5

        # 2. Check and repair each cut against word boundaries
        repaired_cuts: List[Tuple[float, float, EditDecision]] = []
        for decision in cut_candidates:
            start = decision.start_time
            end = decision.end_time

            if decision.operation == EditOperationType.CUT_SILENCE:
                # Apply padding to avoid clipping consonants
                start = max(0.0, start + padding)
                end = max(start, end - padding)
                if (end - start) < min_gap_to_cut * 0.5:
                    continue  # Too small to bother cutting

            # Rule 1: No cutting mid-word (verify no word overlaps start or end)
            for w in report.words:
                if not w.is_filler:
                    # If cut starts inside a non-filler word, push cut start to word end
                    if w.start < start < w.end:
                        start = w.end + padding
                    # If cut ends inside a non-filler word, pull cut end to word start
                    if w.start < end < w.end:
                        end = w.start - padding

            if end > start + 0.15:
                repaired_cuts.append((start, end, decision))

        # 3. Sort cuts chronologically and merge overlapping cuts
        repaired_cuts.sort(key=lambda x: x[0])
        merged_cuts: List[Tuple[float, float, List[EditDecision]]] = []

        for start, end, decision in repaired_cuts:
            if not merged_cuts:
                merged_cuts.append((start, end, [decision]))
            else:
                last_s, last_e, decisions = merged_cuts[-1]
                if start <= last_e + 0.1: # Overlapping or virtually touching
                    merged_cuts[-1] = (last_s, max(last_e, end), decisions + [decision])
                else:
                    merged_cuts.append((start, end, [decision]))

        # 4. Rule 2: Minimum shot duration check
        # Check intervals BETWEEN cuts (the segments we KEEP)
        final_valid_cuts: List[EditDecision] = []
        last_cut_end = 0.0

        for idx, (c_start, c_end, orig_decisions) in enumerate(merged_cuts):
            keep_duration = c_start - last_cut_end
            if keep_duration < self.min_keep_duration and idx > 0:
                # Kept fragment is too small (e.g. 0.3s), merge into previous cut to avoid visual micro-stutter
                logger.info(f"Merging micro-fragment ({keep_duration:.2f}s) between cuts")
                if final_valid_cuts:
                    final_valid_cuts[-1].end_time = c_end
            else:
                primary_dec = orig_decisions[0]
                primary_dec.start_time = round(c_start, 3)
                primary_dec.end_time = round(c_end, 3)
                final_valid_cuts.append(primary_dec)
            last_cut_end = c_end

        logger.info(f"Validated {len(final_valid_cuts)} clean cut segments from {len(cut_candidates)} candidates")
        return final_valid_cuts


cut_validator = CutValidator()
