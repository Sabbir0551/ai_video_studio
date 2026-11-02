import re
from typing import List, Dict, Any, Tuple
from backend.app.models.timeline import WordTimestamp
from backend.app.models.analysis import WordDetail, EditDecision, EditOperationType


class SpeechAnalyzer:
    """Analyzes transcribed speech: identifies filler words, false starts, awkward pauses, and pacing."""

    BN_FILLERS = {"মানে", "ইয়ে", "আসলে", "হুম", "মানেকি", "আরকি"}
    EN_FILLERS = {"um", "uh", "like", "basically", "actually", "literally", "sorta"}

    def __init__(self, min_silence_gap: float = 0.5):
        self.min_silence_gap = min_silence_gap

    def analyze_words(
        self,
        words: List[WordTimestamp],
        language: str = "bn"
    ) -> Tuple[List[WordDetail], List[EditDecision], float]:
        is_bn = language.startswith("bn")
        target_fillers = self.BN_FILLERS if is_bn else self.EN_FILLERS

        detailed_words: List[WordDetail] = []
        suggested_edits: List[EditDecision] = []

        total_words = len(words)
        total_duration = words[-1].end - words[0].start if total_words > 0 else 1.0
        wpm = (total_words / (total_duration / 60.0)) if total_duration > 0 else 0.0

        for idx, w in enumerate(words):
            # Strip punctuation while preserving Bengali Unicode characters (including vowel marks)
            clean_word = re.sub(r"[^\w\s\u0980-\u09FF]", "", w.word.strip().lower())
            is_filler = clean_word in target_fillers
            
            detailed_words.append(WordDetail(
                word=w.word,
                start=w.start,
                end=w.end,
                confidence=1.0,
                is_filler=is_filler
            ))

            # 1. Edit decision for filler words
            if is_filler:
                suggested_edits.append(EditDecision(
                    id=f"edit_filler_{idx+1}",
                    operation=EditOperationType.CUT_FILLER,
                    start_time=w.start,
                    end_time=w.end,
                    reason=f"Remove filler word '{w.word}' to increase conversational punch",
                    confidence=0.92,
                    accepted=True,
                    extra_params={"word": w.word}
                ))

            # 2. Check for unnatural pauses before next word
            if idx < len(words) - 1:
                gap = words[idx+1].start - w.end
                if gap >= self.min_silence_gap:
                    # Keep a natural breath room (e.g. 0.15s) and cut the rest
                    cut_start = round(w.end + 0.15, 3)
                    cut_end = round(words[idx+1].start - 0.10, 3)
                    if cut_end > cut_start + 0.2:
                        suggested_edits.append(EditDecision(
                            id=f"edit_silence_gap_{idx+1}",
                            operation=EditOperationType.CUT_SILENCE,
                            start_time=cut_start,
                            end_time=cut_end,
                            reason=f"Cut dead silence ({gap:.2f}s gap between words)",
                            confidence=0.95,
                            accepted=True,
                            extra_params={"gap_duration": round(gap, 2)}
                        ))

            # 3. Check for repeated words / stutter (e.g. "আমি আমি", "to to")
            if idx < len(words) - 1:
                next_clean = re.sub(r"[^\w\s\u0980-\u09FF]", "", words[idx+1].word.strip().lower())
                if clean_word and clean_word == next_clean:
                    suggested_edits.append(EditDecision(
                        id=f"edit_stutter_{idx+1}",
                        operation=EditOperationType.CUT_FILLER,
                        start_time=w.start,
                        end_time=w.end,
                        reason=f"Remove stuttered duplicate word '{w.word}'",
                        confidence=0.88,
                        accepted=True,
                        extra_params={"stutter_word": w.word}
                    ))

        return detailed_words, suggested_edits, round(wpm, 1)


speech_analyzer = SpeechAnalyzer()
