import os
import re
from typing import List, Optional, Tuple, Dict, Any
from backend.app.providers.base import LLMProvider, ScriptResult, ScriptScene


class SmartScriptEngine(LLMProvider):
    """
    Intelligent Script & Storyboard Engine.
    - Parses structured user prompts (Characters, Art Styles, Explicit Scenes, Dialogue, Timing).
    - Dynamically generates long-form multi-scene scripts (1 to 5+ minutes, 12+ scenes) based on target duration.
    - Locks character consistency anchors and visual style directives into every scene.
    """

    @property
    def name(self) -> str:
        return "smart-script-engine"

    def _extract_metadata_from_prompt(self, prompt: str) -> Tuple[str, str, Optional[float], List[str]]:
        """Extract Character definition, Style directive, Duration hint, and raw scene lines."""
        character_desc = ""
        style_directive = ""
        duration_hint = None
        scene_lines = []

        # 1. Detect Character definition
        char_match = re.search(
            r"(?:MAIN\s+CHARACTER|CHARACTER|HERO|AVATAR)\s*:\s*(.*?)(?=\n\s*(?:STYLE|STORY|SCENE|AUDIO|[A-Z\s]{3,}:|\d+[\.\:])|\Z)",
            prompt,
            re.IGNORECASE | re.DOTALL
        )
        if char_match:
            character_desc = char_match.group(1).strip()
            character_desc = re.sub(r'^[“"\'`]+|[”"\'`]+$', '', character_desc).strip()
            # If multiple lines, pick first 2 lines
            character_desc = " ".join(character_desc.splitlines()[:2]).strip()

        # 2. Detect Style directive
        style_match = re.search(
            r"(?:STYLE|VISUAL\s+STYLE|ART\s+STYLE|AESTHETIC)\s*:\s*(.*?)(?=\n\s*(?:MAIN\s+CHARACTER|CHARACTER|STORY|SCENE|AUDIO|[A-Z\s]{3,}:|\d+[\.\:])|\Z)",
            prompt,
            re.IGNORECASE | re.DOTALL
        )
        if style_match:
            style_directive = style_match.group(1).strip()
            style_directive = " ".join(style_directive.splitlines()[:2]).strip()

        # 3. Detect Duration hint (e.g. "2-minute", "120s", "60 seconds", "1 minute")
        dur_match = re.search(r"(\d+)\s*(?:-|\s)*(?:minute|min|মিনিট)", prompt, re.IGNORECASE)
        if dur_match:
            duration_hint = float(dur_match.group(1)) * 60.0
        else:
            sec_match = re.search(r"(\d+)\s*(?:-|\s)*(?:second|sec|সেকেন্ড)", prompt, re.IGNORECASE)
            if sec_match:
                duration_hint = float(sec_match.group(1))

        # 4. Extract Numbered Scenes (e.g. "1. Buli wakes up...", "Scene 1: ...", "১. ...")
        # Match lines like "1. ...", "12. ...", "Scene 1: ..."
        pattern = re.compile(r"^(?:(?:Scene|সিন)\s*)?(\d+|[০-৯]+)[\.\:\)]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
        matches = pattern.findall(prompt)
        if matches:
            for num, text in matches:
                scene_lines.append(text.strip())

        return character_desc, style_directive, duration_hint, scene_lines

    async def generate_script(
        self,
        topic_or_content: str,
        language: str = "bn",
        target_duration: float = 60.0,
        tone: str = "educational"
    ) -> ScriptResult:
        """Parse structured storyboard or dynamically synthesize long-form multi-scene script."""
        char_desc, style_dir, detected_duration, user_scenes = self._extract_metadata_from_prompt(topic_or_content)

        if detected_duration:
            target_duration = max(target_duration, detected_duration)

        # Default style if none provided
        if not style_dir:
            if "cartoon" in topic_or_content.lower() or "toddler" in topic_or_content.lower() or "pixar" in topic_or_content.lower():
                style_dir = "Pixar 3D animation style, bright primary colors, soft warm lighting, highly detailed 3D render"
            else:
                style_dir = "Cinematic 4K high quality, professional photography, natural lighting"

        # Default character anchor if none provided
        if not char_desc and ("buli" in topic_or_content.lower() or "duckling" in topic_or_content.lower()):
            char_desc = "Buli, cute round yellow duckling with shiny eyes, tiny orange beak and small red scarf"

        scenes: List[ScriptScene] = []

        # CASE A: User gave explicit numbered scenes (like in the toddler cartoon prompt)
        if len(user_scenes) >= 2:
            num_scenes = len(user_scenes)
            dur_per_scene = max(4.0, target_duration / num_scenes)

            for i, scene_text in enumerate(user_scenes):
                scene_num = i + 1

                # Extract dialogue if present in quotes
                dialogue_match = re.search(r'["“\']([^"”\']+)["”\']', scene_text)
                if dialogue_match:
                    # e.g., "Hello!" or "bye bye"
                    narration = scene_text
                else:
                    narration = scene_text

                # Build targeted visual intent with character anchor
                if char_desc:
                    visual_intent = f"{style_dir}. Character: {char_desc}. Scene {scene_num}: {scene_text}. 8k, detailed, clean composition."
                else:
                    visual_intent = f"{style_dir}. {scene_text}. 8k, detailed, clean composition."

                camera_motion = "slow_zoom_in" if i % 2 == 0 else "pan_right"
                transition = "dissolve" if i > 0 else "fade_black"

                scenes.append(ScriptScene(
                    scene_number=scene_num,
                    narration=narration,
                    estimated_duration=round(dur_per_scene, 1),
                    visual_intent=visual_intent,
                    visual_source_preference="ai_image",
                    camera_motion=camera_motion,
                    transition=transition,
                    caption_emphasis=[]
                ))

            title = f"Story: {user_scenes[0][:40]}..."
            hook = user_scenes[0]
            body_summary = f"{len(scenes)} scenes storyboard narrative"
            cta = user_scenes[-1]

        # CASE B: Freeform prompt -> dynamically synthesize scenes to reach target_duration
        else:
            # Determine number of scenes (each ~8-12 seconds)
            num_scenes = max(3, int(round(target_duration / 10.0)))
            dur_per_scene = target_duration / num_scenes

            is_bn = language.startswith("bn")
            clean_topic = topic_or_content.strip().split("\n")[0][:80]

            if is_bn:
                title = f"{clean_topic} সম্পর্কিত পূর্ণাঙ্গ তথ্যচিত্র"
                hook = f"আজকে আমরা জানবো {clean_topic} সম্পর্কে বিস্তারিত।"
                body_summary = f"{clean_topic} এর মূল ধারণা ও বিস্তার।"
                cta = "এমন আরও তথ্যবহুল ভিডিও দেখতে আমাদের চ্যানেলটি সাবস্ক্রাইব করুন!"

                # Create multi-scene progression
                stage_names = [
                    "ভূমিকা ও মূল পটভূমি",
                    "গুরুত্বপূর্ণ আবিষ্কার ও প্রযুক্তি",
                    "বাস্তব প্রয়োগ ও সুবিধা",
                    "ভবিষ্যতের সম্ভাবনা ও চ্যালেঞ্জ",
                    "বিশেষজ্ঞ মতামত ও মূল্যায়ন",
                    "চূড়ান্ত সিদ্ধান্ত ও বার্তা"
                ]

                for i in range(num_scenes):
                    stage_title = stage_names[i % len(stage_names)]
                    narration = f"{clean_topic} এর {stage_title} অত্যন্ত আকর্ষণীয় এবং তাৎপর্যপূর্ণ।"
                    if char_desc:
                        visual = f"{style_dir}. {char_desc} experiencing {stage_title} about {clean_topic}. High quality 4k render."
                    else:
                        visual = f"{style_dir}. Visualizing {stage_title} of {clean_topic}. Cinematic composition, 4k render."

                    scenes.append(ScriptScene(
                        scene_number=i + 1,
                        narration=narration,
                        estimated_duration=round(dur_per_scene, 1),
                        visual_intent=visual,
                        visual_source_preference="ai_image",
                        camera_motion="slow_zoom_in" if i % 2 == 0 else "pan_left",
                        transition="dissolve"
                    ))
            else:
                title = f"Deep Dive: {clean_topic}"
                hook = f"Welcome! Today we are exploring the fascinating world of {clean_topic}."
                body_summary = f"An in-depth multi-chapter breakdown of {clean_topic}."
                cta = "Thanks for watching! Subscribe for more deep dives."

                stage_names = [
                    "Introduction and Historical Context",
                    "Core Mechanisms and Technology",
                    "Real-World Applications and Case Studies",
                    "Key Breakthroughs and Milestones",
                    "Future Horizons and Emerging Trends",
                    "Final Summary and Core Takeaways"
                ]

                for i in range(num_scenes):
                    stage_title = stage_names[i % len(stage_names)]
                    narration = f"Looking at {stage_title}, we discover why {clean_topic} is truly remarkable."
                    if char_desc:
                        visual = f"{style_dir}. {char_desc} in {stage_title} of {clean_topic}. 3D render, vibrant lighting, 8k."
                    else:
                        visual = f"{style_dir}. Detailed scene showing {stage_title} of {clean_topic}. 8k photorealistic."

                    scenes.append(ScriptScene(
                        scene_number=i + 1,
                        narration=narration,
                        estimated_duration=round(dur_per_scene, 1),
                        visual_intent=visual,
                        visual_source_preference="ai_image",
                        camera_motion="slow_zoom_in" if i % 2 == 0 else "pan_left",
                        transition="dissolve"
                    ))

        total_words = sum(len(s.narration.split()) for s in scenes)

        return ScriptResult(
            title=title,
            hook=hook,
            body_summary=body_summary,
            call_to_action=cta,
            scenes=scenes,
            language=language,
            target_duration=target_duration,
            estimated_word_count=total_words,
            provider_name=self.name,
            cost_usd=0.0
        )
