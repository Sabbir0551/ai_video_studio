import os
import re
from typing import List, Optional, Tuple, Dict, Any
from backend.app.providers.base import LLMProvider, ScriptResult, ScriptScene
from backend.app.providers.llm.nursery_rhyme_engine import NurseryRhymeEngine


class SmartScriptEngine(LLMProvider):
    """
    Intelligent Script & Storyboard Engine.
    - Parses structured user prompts (Characters, Art Styles, Explicit Scenes, Dialogue, Timing).
    - Detects Kids Nursery Rhymes (Lalafun / CoComelon formula) and synthesizes melodic verse rhymes.
    - Extracts per-scene character focus so multi-animal stories feature distinct animals in each scene.
    - Dynamically generates multi-scene scripts based on target duration.
    """

    @property
    def name(self) -> str:
        return "smart-script-engine"

    def _extract_metadata_from_prompt(self, prompt: str) -> Tuple[str, str, Optional[float], List[str], str]:
        """Extract Character definition, Style directive, Duration hint, raw scene lines, and Animal Friends."""
        character_desc = ""
        style_directive = ""
        duration_hint = None
        scene_lines = []
        animal_friends = ""

        # 1. Detect Character definition
        char_match = re.search(
            r"(?:MAIN\s+CHARACTER|CHARACTER|HERO|AVATAR)\s*:\s*(.*?)(?=\n\s*(?:STYLE|SETTING|ANIMAL\s+FRIENDS|STORY|SCENE|AUDIO|[A-Z\s]{3,}:|\d+[\.\:])|\Z)",
            prompt,
            re.IGNORECASE | re.DOTALL
        )
        if char_match:
            character_desc = char_match.group(1).strip()
            character_desc = re.sub(r'^[“"\'`]+|[”"\'`]+$', '', character_desc).strip()
            character_desc = " ".join(character_desc.splitlines()[:2]).strip()

        # 2. Detect Animal Friends / Secondary characters
        animals_match = re.search(
            r"(?:ANIMAL\s+FRIENDS|FRIENDS|ANIMALS)\s*:\s*(.*?)(?=\n\s*(?:STYLE|SETTING|MAIN\s+CHARACTER|STORY|SCENE|AUDIO|[A-Z\s]{3,}:|\d+[\.\:])|\Z)",
            prompt,
            re.IGNORECASE | re.DOTALL
        )
        if animals_match:
            animal_friends = animals_match.group(1).strip()
            animal_friends = " ".join(animal_friends.splitlines()[:2]).strip()

        # 3. Detect Style directive
        style_match = re.search(
            r"(?:STYLE|VISUAL\s+STYLE|ART\s+STYLE|AESTHETIC)\s*:\s*(.*?)(?=\n\s*(?:SETTING|MAIN\s+CHARACTER|ANIMAL\s+FRIENDS|STORY|SCENE|AUDIO|[A-Z\s]{3,}:|\d+[\.\:])|\Z)",
            prompt,
            re.IGNORECASE | re.DOTALL
        )
        if style_match:
            style_directive = style_match.group(1).strip()
            style_directive = " ".join(style_directive.splitlines()[:2]).strip()

        # 4. Detect Duration hint (e.g. "2-minute", "120s", "60 seconds", "1 minute")
        dur_match = re.search(r"(\d+)\s*(?:-|\s)*(?:minute|min|মিনিট)", prompt, re.IGNORECASE)
        if dur_match:
            duration_hint = float(dur_match.group(1)) * 60.0
        else:
            sec_match = re.search(r"(\d+)\s*(?:-|\s)*(?:second|sec|সেকেন্ড)", prompt, re.IGNORECASE)
            if sec_match:
                duration_hint = float(sec_match.group(1))

        # 5. Extract Numbered Scenes (e.g. "1. Buli wakes up...", "Scene 1: ...", "১. ...")
        pattern = re.compile(r"^(?:(?:Scene|সিন)\s*)?(\d+|[০-৯]+)[\.\:\)]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
        matches = pattern.findall(prompt)
        if matches:
            for num, text in matches:
                scene_lines.append(text.strip())

        return character_desc, style_directive, duration_hint, scene_lines, animal_friends

    def _detect_scene_focus(self, scene_text: str, default_char: str, animal_friends: str = "") -> str:
        """Isolate the specific character or animal hero for the current scene."""
        s_lower = scene_text.lower()
        if any(w in s_lower for w in ["puppy", "dog", "কুকুর"]):
            return "cute 3D Pixar puppy dog with floppy ears, shiny eyes, cheerful tail"
        elif any(w in s_lower for w in ["kitten", "cat", "kitty", "বিড়াল", "বিড়াল"]):
            return "cute 3D Pixar fluffy kitten cat with whiskers, round blue eyes, tiny pink nose"
        elif any(w in s_lower for w in ["duckling", "duck", "buli", "হাঁস"]):
            return "cute 3D Pixar round yellow duckling with shiny eyes and tiny orange beak"
        elif any(w in s_lower for w in ["lamb", "sheep", "ভেড়া", "ভেড়া"]):
            return "cute 3D Pixar fluffy white baby lamb with curly soft wool and pink ears"
        elif any(w in s_lower for w in ["foal", "horse", "pony", "ঘোড়া", "ঘোড়া"]):
            return "cute 3D Pixar brown baby horse foal with soft mane and expressive eyes"
        elif any(w in s_lower for w in ["cow", "গরু"]):
            return "cute 3D Pixar gentle spotted cow with big warm eyes"
        elif any(w in s_lower for w in ["rainbow", "রামধনু", "রংধনু"]):
            return "vibrant colorful rainbow over green meadow with puppy, kitten, duckling, and lamb dancing"
        elif any(w in s_lower for w in ["rain", "বৃষ্টি"]):
            return f"cute 3D {default_char or 'cartoon animal'} looking at falling raindrops with umbrella"

        if default_char:
            return f"3D {default_char}"
        return "cute 3D Pixar cartoon character"

    async def generate_script(
        self,
        topic_or_content: str,
        language: str = "bn",
        target_duration: float = 60.0,
        tone: str = "educational"
    ) -> ScriptResult:
        """Parse structured storyboard or dynamically synthesize long-form multi-scene script."""
        # 1. Check if user prompt is a nursery rhyme request (Lalafun / CoComelon formula)
        if NurseryRhymeEngine.is_nursery_rhyme(topic_or_content):
            # If user didn't provide full custom numbered scenes, synthesize true nursery rhyme
            _, _, detected_dur, user_scenes, _ = self._extract_metadata_from_prompt(topic_or_content)
            if len(user_scenes) < 3:
                return NurseryRhymeEngine.generate_rain_rain_rhyme(
                    language=language,
                    target_duration=detected_dur or target_duration
                )

        char_desc, style_dir, detected_duration, user_scenes, animal_friends = self._extract_metadata_from_prompt(topic_or_content)

        if detected_duration:
            target_duration = max(target_duration, detected_duration)

        # Default style if none provided
        if not style_dir:
            if any(w in topic_or_content.lower() for w in ["cartoon", "toddler", "pixar", "kids", "rhyme", "lalafun"]):
                style_dir = "3D Pixar Disney CGI animation style, vibrant primary colors, soft warm lighting, highly detailed 3D render"
            else:
                style_dir = "Cinematic 4K high quality, professional photography, natural lighting"

        # Default character anchor if none provided
        if not char_desc and any(w in topic_or_content.lower() for w in ["buli", "duckling"]):
            char_desc = "Buli, cute round yellow duckling with shiny eyes, tiny orange beak and small red scarf"

        scenes: List[ScriptScene] = []

        # CASE A: User gave explicit numbered scenes
        if len(user_scenes) >= 2:
            num_scenes = len(user_scenes)
            dur_per_scene = max(4.0, target_duration / num_scenes)

            for i, scene_text in enumerate(user_scenes):
                scene_num = i + 1

                # Extract dialogue or narration
                dialogue_match = re.search(r'["“\']([^"”\']+)["”\']', scene_text)
                narration = scene_text

                # Detect scene-specific hero character (puppy vs kitten vs duckling vs lamb vs horse)
                scene_char_focus = self._detect_scene_focus(scene_text, char_desc, animal_friends)

                # Prioritize Subject + Action + 3D Pixar Animation in the first 120 characters
                visual_intent = (
                    f"3D Pixar CGI animation style, {scene_char_focus}. "
                    f"Scene: {scene_text}. "
                    f"Vibrant colors, soft warm lighting, highly detailed 3D render."
                )

                camera_motion = "slow_zoom_in" if i % 2 == 0 else "pan_right"
                if "rain" in scene_text.lower() or "sad" in scene_text.lower():
                    camera_motion = "slow_zoom_in"
                elif "dance" in scene_text.lower() or "jump" in scene_text.lower() or "splash" in scene_text.lower():
                    camera_motion = "bounce_playful"

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
            is_cartoon = any(w in topic_or_content.lower() for w in ["cartoon", "toddler", "kids", "baby", "rhyme", "farm", "animal"])
            num_scenes = max(4, int(round(target_duration / 10.0)))
            dur_per_scene = target_duration / num_scenes

            is_bn = language.startswith("bn")
            clean_topic = topic_or_content.strip().split("\n")[0][:80]

            if is_cartoon:
                title = f"{clean_topic} - 3D অ্যানিমেশন গল্প" if is_bn else f"{clean_topic} - 3D Cartoon Story"
                hook = "আজকে সুন্দর এক আনন্দের দিন!" if is_bn else "Today is a beautiful and fun day!"
                body_summary = f"A fun 3D animated journey with animal friends about {clean_topic}."
                cta = "এমন আরও মজার কার্টুন দেখতে সাবস্ক্রাইব করুন!" if is_bn else "Subscribe for more fun 3D cartoon stories!"

                cartoon_stages_bn = [
                    ("সকালের রোদ ও নতুন দিন", "ছোট্ট কুকুরছানা সকালে ঘুম থেকে উঠে বন্ধুদের ডাকছে।", "cute 3D Pixar puppy dog running on morning green farm meadow"),
                    ("পুকুরপাড়ে হাঁসের খেলা", "ছোট্ট হলুদ হাঁস পানিতে নেমে খুশিতে পাখা ঝাপটাচ্ছে।", "cute 3D Pixar yellow duckling splashing happily in blue farm pond"),
                    ("আস্তাবলে মিষ্টি ছানা", "ছোট্ট সাদা ভেড়া আর ঘোড়ার ছানা ঘাস খাচ্ছে ও আনন্দ করছে।", "cute 3D Pixar fluffy white lamb and brown foal horse chewing sweet hay"),
                    ("আকাশে মেঘ ও বৃষ্টির গান", "আকাশে মেঘ জমতেই সবাই একসাথে লাল আস্তাবলে আশ্রয় নিলো।", "cute 3D Pixar puppy, kitten and duckling looking out from red barn"),
                    ("রামধনু ও রোদের আনন্দ", "বৃষ্টি শেষে আকাশে বিশাল রামধনু, সবাই খুশিতে নাচছে।", "glorious colorful rainbow over green hills with all cute 3D animals dancing")
                ]
                cartoon_stages_en = [
                    ("Morning Sunshine", "The cute puppy wakes up and happily greets the farm friends.", "cute 3D Pixar puppy dog running on morning green farm meadow"),
                    ("Duckling at the Pond", "The little yellow duckling swims and splashes with tiny water droplets.", "cute 3D Pixar yellow duckling splashing happily in blue farm pond"),
                    ("Playtime at the Barn", "The fluffy white lamb and baby foal chew fresh hay together.", "cute 3D Pixar fluffy white lamb and brown foal horse chewing sweet hay"),
                    ("Rainy Clouds and Song", "Rain begins to fall softly as all the animals gather inside the cozy barn.", "cute 3D Pixar puppy, kitten and duckling looking out from red barn"),
                    ("Rainbow Celebration", "The rain clears, a bright rainbow appears, and everyone dances in puddles.", "glorious colorful rainbow over green hills with all cute 3D animals dancing")
                ]

                stages = cartoon_stages_bn if is_bn else cartoon_stages_en

                for i in range(num_scenes):
                    stage_title, stage_narr, stage_vis = stages[i % len(stages)]
                    visual = f"3D Pixar CGI animation style, {stage_vis}. Vibrant primary colors, warm lighting, highly detailed 3D render."
                    scenes.append(ScriptScene(
                        scene_number=i + 1,
                        narration=stage_narr,
                        estimated_duration=round(dur_per_scene, 1),
                        visual_intent=visual,
                        visual_source_preference="ai_image",
                        camera_motion="bounce_playful" if i % 2 == 0 else "slow_zoom_in",
                        transition="dissolve"
                    ))
            elif is_bn:
                title = f"{clean_topic} সম্পর্কিত পূর্ণাঙ্গ তথ্যচিত্র"
                hook = f"আজকে আমরা জানবো {clean_topic} সম্পর্কে বিস্তারিত।"
                body_summary = f"{clean_topic} এর মূল ধারণা ও বিস্তার।"
                cta = "এমন আরও তথ্যবহুল ভিডিও দেখতে আমাদের চ্যানেলটি সাবস্ক্রাইব করুন!"

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

