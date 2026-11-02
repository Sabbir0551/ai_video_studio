from backend.app.providers.base import LLMProvider, ScriptResult, ScriptScene


class MockLLMProvider(LLMProvider):
    """Deterministic offline LLM provider returning structured storyboards."""

    @property
    def name(self) -> str:
        return "mock-llm"

    async def generate_script(
        self,
        topic_or_content: str,
        language: str = "bn",
        target_duration: float = 60.0,
        tone: str = "educational"
    ) -> ScriptResult:
        if language.startswith("bn"):
            return ScriptResult(
                title=f"{topic_or_content} সম্পর্কিত সংক্ষিপ্ত ভিডিও",
                hook="আপনি কি জানেন কৃত্রিম বুদ্ধিমত্তা কীভাবে আমাদের কাজ বদলে দিচ্ছে?",
                body_summary="ভিডিও তৈরির প্রতিটি ধাপে প্রযুক্তি এখন এনে দিচ্ছে অবিশ্বাস্য গতি।",
                call_to_action="নতুন প্রযুক্তির সাথে যুক্ত থাকতে সাবস্ক্রাইব করুন!",
                scenes=[
                    ScriptScene(
                        scene_number=1,
                        narration="স্বাগতম! কৃত্রিম বুদ্ধিমত্তা কীভাবে কাজ করে তা জেনে নেওয়া যাক।",
                        estimated_duration=3.5,
                        visual_intent="AI neural network conceptual graphic with luminous nodes",
                        visual_source_preference="user_or_stock",
                        camera_motion="slow_zoom_in",
                        transition="dissolve",
                        caption_emphasis=["স্বাগতম", "কৃত্রিম", "বুদ্ধিমত্তা"]
                    ),
                    ScriptScene(
                        scene_number=2,
                        narration="কম্পিউটার এখন মানুষের ভাষার জটিল অর্থ এবং ভাব নিমিষেই বুঝতে পারে।",
                        estimated_duration=4.2,
                        visual_intent="Data streams morphing into human speech waveforms",
                        visual_source_preference="user_or_stock",
                        camera_motion="pan_right",
                        transition="wipe_left",
                        caption_emphasis=["মানুষের", "ভাষা", "নিমিষেই"]
                    )
                ],
                language="bn",
                target_duration=target_duration,
                estimated_word_count=35,
                provider_name=self.name,
                cost_usd=0.0
            )
        else:
            return ScriptResult(
                title=f"Explainer: {topic_or_content}",
                hook="Did you know AI is revolutionizing video creation right now?",
                body_summary="From text to voice and intelligent editing, everything is automated.",
                call_to_action="Subscribe to stay ahead in technology!",
                scenes=[
                    ScriptScene(
                        scene_number=1,
                        narration="Welcome to the next generation of automated video creation.",
                        estimated_duration=3.0,
                        visual_intent="Futuristic modern workspace with holographic editing timeline",
                        visual_source_preference="user_or_stock",
                        camera_motion="slow_zoom_in",
                        transition="dissolve",
                        caption_emphasis=["Welcome", "generation", "creation"]
                    ),
                    ScriptScene(
                        scene_number=2,
                        narration="With intelligent speech synthesis and multi-modal scene analysis, editing takes seconds.",
                        estimated_duration=4.0,
                        visual_intent="High-tech audio waveforms and dynamic color grading suite",
                        visual_source_preference="user_or_stock",
                        camera_motion="pan_left",
                        transition="fade_black",
                        caption_emphasis=["intelligent", "multi-modal", "seconds"]
                    )
                ],
                language="en",
                target_duration=target_duration,
                estimated_word_count=40,
                provider_name=self.name,
                cost_usd=0.0
            )

