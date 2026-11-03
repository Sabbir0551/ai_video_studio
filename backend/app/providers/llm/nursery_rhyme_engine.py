"""
Nursery Rhyme & Kids Song Engine (Lalafun / CoComelon Formula).
- Synthesizes rhythmic cumulative nursery rhymes ("Rain Rain Go Away", "Old MacDonald", etc.).
- Assigns distinct 3D Pixar/Disney style animal characters to each verse/scene.
- Provides verse rhyming lyrics, visual prompt anchors, and dynamic scene progression.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from backend.app.providers.base import ScriptScene, ScriptResult


class NurseryRhymeEngine:
    """Specialized engine for producing top-tier 3D animated toddler nursery rhymes."""

    # Classic Lalafun "Rain Rain Go Away (Animal Version)" sequence
    RAIN_RAIN_VERSES = [
        {
            "animal": "puppy",
            "name_en": "Little puppy",
            "name_bn": "ছোট্ট কুকুর",
            "character_prompt": "cute 3D Pixar fluffy golden puppy dog, big shiny brown eyes, floppy ears, wearing a tiny yellow raincoat",
            "action_en": "sitting sadly on the wooden barn porch looking up at grey rain clouds, raindrops splashing nearby",
            "action_bn": "বারান্দায় বসে মন খারাপ করে বৃষ্টির দিকে তাকিয়ে আছে",
            "lyric_en": "Rain, rain, go away, come again another day! Little puppy wants to play, rain, rain, go away!",
            "lyric_bn": "বৃষ্টি, বৃষ্টি, চলে যাও, অন্য দিনে ফিরে এসো! ছোট্ট কুকুর খেলতে চায়, বৃষ্টি, বৃষ্টি, চলে যাও!",
            "camera": "slow_zoom_in"
        },
        {
            "animal": "kitten",
            "name_en": "Little kitty",
            "name_bn": "ছোট্ট বিড়াল",
            "character_prompt": "cute 3D Pixar fluffy white kitten cat, big round blue eyes, tiny pink nose, holding a little red umbrella",
            "action_en": "looking through a rain-streaked window pane with a soft paw against the glass, cozy barn interior",
            "action_bn": "জানালার কাচে থাবা রেখে বৃষ্টির ধারা দেখছে",
            "lyric_en": "Rain, rain, go away, come again another day! Little kitty wants to play, rain, rain, go away!",
            "lyric_bn": "বৃষ্টি, বৃষ্টি, চলে যাও, অন্য দিনে ফিরে এসো! ছোট্ট বিড়াল খেলতে চায়, বৃষ্টি, বৃষ্টি, চলে যাও!",
            "camera": "pan_right"
        },
        {
            "animal": "duckling",
            "name_en": "Little duckling",
            "name_bn": "ছোট্ট হাঁসের ছানা",
            "character_prompt": "cute 3D Pixar round yellow duckling, big sparkling eyes, tiny orange beak, wearing small red boots",
            "action_en": "standing by a pond with gentle water ripples, looking up at the sky, flapping tiny wings",
            "action_bn": "পুকুর পাড়ে দাঁড়িয়ে আকাশের দিকে পাখা নাড়ছে",
            "lyric_en": "Rain, rain, go away, come again another day! Little duckling wants to play, rain, rain, go away!",
            "lyric_bn": "বৃষ্টি, বৃষ্টি, চলে যাও, অন্য দিনে ফিরে এসো! ছোট্ট হাঁস খেলতে চায়, বৃষ্টি, বৃষ্টি, চলে যাও!",
            "camera": "bounce_playful"
        },
        {
            "animal": "lamb",
            "name_en": "Little lamb",
            "name_bn": "ছোট্ট ভেড়া",
            "character_prompt": "cute 3D Pixar fluffy white baby lamb, curly cloud-like wool, gentle dark eyes, pink inner ears",
            "action_en": "standing under a big green oak tree sheltered from the rain, waving hooves playfully",
            "action_bn": "বড় গাছের নিচে দাঁড়িয়ে বৃষ্টির ফোঁটা দেখছে",
            "lyric_en": "Rain, rain, go away, come again another day! Little lamb wants to play, rain, rain, go away!",
            "lyric_bn": "বৃষ্টি, বৃষ্টি, চলে যাও, অন্য দিনে ফিরে এসো! ছোট্ট ভেড়া খেলতে চায়, বৃষ্টি, বৃষ্টি, চলে যাও!",
            "camera": "slow_zoom_in"
        },
        {
            "animal": "pony",
            "name_en": "Little pony",
            "name_bn": "ছোট্ট ঘোড়া",
            "character_prompt": "cute 3D Pixar friendly brown baby horse pony foal, soft dark mane, big expressive cartoon eyes",
            "action_en": "peeking out from the red barn stable door, chewing sweet hay, looking at the rain puddles",
            "action_bn": "লাল আস্তাবলের দরজা দিয়ে মুখ বাড়িয়ে বৃষ্টির দিকে তাকিয়ে আছে",
            "lyric_en": "Rain, rain, go away, come again another day! Little pony wants to play, rain, rain, go away!",
            "lyric_bn": "বৃষ্টি, বৃষ্টি, চলে যাও, অন্য দিনে ফিরে এসো! ছোট্ট ঘোড়া খেলতে চায়, বৃষ্টি, বৃষ্টি, চলে যাও!",
            "camera": "pan_left"
        },
        {
            "animal": "friends",
            "name_en": "All animal friends",
            "name_bn": "সব বন্ধুরা",
            "character_prompt": "group of cute 3D Pixar animals: puppy dog, kitten cat, yellow duckling, and fluffy lamb gathered together",
            "action_en": "all animal friends holding paws and looking at the rain together, singing in cheerful harmony",
            "action_bn": "সব পশুপাখি বন্ধুরা একসাথে দাঁড়িয়ে বৃষ্টির দিকে গান গাইছে",
            "lyric_en": "Rain, rain, go away, come again another day! All our friends want to play, rain, rain, go away!",
            "lyric_bn": "বৃষ্টি, বৃষ্টি, চলে যাও, অন্য দিনে ফিরে এসো! সব বন্ধুরা খেলতে চায়, বৃষ্টি, বৃষ্টি, চলে যাও!",
            "camera": "slow_zoom_in"
        },
        {
            "animal": "rainbow",
            "name_en": "Rainbow Celebration",
            "name_bn": "রামধনু ও রোদের আনন্দ",
            "character_prompt": "glorious colorful rainbow over lush green meadow, golden warm sunshine, sparkling water puddles",
            "action_en": "puppy, kitten, duckling, and lamb dancing and jumping happily in the puddles under the bright rainbow",
            "action_bn": "আকাশে বিশাল রামধনু উঠেছে, মিষ্টি রোদ, সব বন্ধুরা মিলে আনন্দে নাচছে",
            "lyric_en": "Look, look! The rain has gone away! The bright warm sun is here today! Hip hip hooray, let's play!",
            "lyric_bn": "দেখো, বৃষ্টি থেমে গেছে! আকাশে মিষ্টি রোদ উঠেছে! চলো সবাই মিলে আনন্দে নাচি!",
            "camera": "bounce_playful"
        }
    ]

    @classmethod
    def is_nursery_rhyme(cls, prompt: str) -> bool:
        """Detect if prompt intends to create a nursery rhyme or toddler singing cartoon."""
        p = prompt.lower()
        keywords = [
            "rain rain go away", "lalafun", "animal version", "nursery rhyme", "cocomelon",
            "toddler song", "kids song", "rhymes", "singing animal", "বৃষ্টি বৃষ্টি চলে যাও",
            "ছোটদের গান", "নার্সারি রাইম", "ছড়া", "রাইম"
        ]
        return any(k in p for k in keywords)

    @classmethod
    def generate_rain_rain_rhyme(
        cls,
        language: str = "bn",
        target_duration: float = 60.0
    ) -> ScriptResult:
        """Generate high-production 3D animated Lalafun-style Rain Rain Go Away script."""
        is_bn = language.startswith("bn")
        scenes_data = cls.RAIN_RAIN_VERSES

        # Determine number of verses based on duration (minimum 4, up to all 7)
        if target_duration <= 45:
            selected_verses = [scenes_data[0], scenes_data[1], scenes_data[2], scenes_data[6]]
        elif target_duration <= 70:
            selected_verses = scenes_data[:6] + [scenes_data[6]]
        else:
            selected_verses = scenes_data

        dur_per_scene = max(5.0, target_duration / len(selected_verses))
        scenes: List[ScriptScene] = []

        for idx, v in enumerate(selected_verses):
            scene_num = idx + 1
            narration = v["lyric_bn"] if is_bn else v["lyric_en"]
            animal_tag = v["animal"]

            # Craft targeted prompt with Subject + 3D Animation Style + Environment
            visual_intent = (
                f"3D Pixar Disney CGI animation style, {v['character_prompt']}, "
                f"{v['action_en']}. Vibrant saturated colors, warm cinematic lighting, "
                f"expressive cute cartoon eyes, highly detailed 3D render."
            )

            transition = "dissolve" if idx > 0 else "fade_black"

            scenes.append(ScriptScene(
                scene_number=scene_num,
                narration=narration,
                estimated_duration=round(dur_per_scene, 1),
                visual_intent=visual_intent,
                visual_source_preference="ai_image",
                camera_motion=v["camera"],
                transition=transition,
                caption_emphasis=[v["name_bn"] if is_bn else v["name_en"], "Rain", "play"]
            ))

        title = "Rain Rain Go Away (Animal Version) - Lalafun 3D Animation" if not is_bn else "বৃষ্টি বৃষ্টি চলে যাও (পশুপাখিদের গান) - থ্রিডি অ্যানিমেশন"
        hook = scenes[0].narration
        body_summary = f"{len(scenes)} scenes of cute 3D animated animals singing the classic rhyme."
        cta = scenes[-1].narration

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
            provider_name="nursery-rhyme-engine",
            cost_usd=0.0
        )
