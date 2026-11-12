"""Generate candidate reference-board images for one style pack (not approved).

The board is a human-reviewed asset: this script only produces candidates and a
manifest marked PENDING_REVIEW. Images stay local (ignored by Git).

    .venv\\Scripts\\python.exe scripts\\gen_reference_board.py --style oriental.ink_wash --limit 12
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from drama_studio.config import find_project_root
from drama_studio.paths import style_boards_root
from drama_studio.domain.style import compile_image_prompt, get_pack, packs_root

SUBJECTS = [
    "distant mountain ranges above a wide river",
    "a lone traditional Chinese fishing boat with a woven awning on a misty river",
    "a misty valley with layered peaks",
    "an old pine growing from a cliff rock",
    "a tall waterfall between cliffs with wide empty sky above",
    "a full moon over still water and reeds",
    "a wooden pavilion in light rain",
    "an empty riverbank with reeds and stones",
    "lotus leaves floating on a quiet pond",
    "bamboo grove in thin mist",
    "snow-covered peaks under pale sky",
    "bare winter branches at a quiet pond with wide open water beside them",
]


SUBJECTS_BY_STYLE = {
    "oriental.modern_chinese": [
        "a plain white plaster wall with a narrow vertical slit window and one bamboo shadow",
        "a frameless floor-to-ceiling glass wall opening onto a misty garden",
        "a still water courtyard with a single circular opening, the only circle in the frame",
        "a long covered corridor with a thin dark roof and open sides framing water",
        "a scholar rock set in moss and pebbles beside shallow water",
        "a low stone bridge over still water with a long horizontal window in the far wall",
        "a white wall with a long horizontal window and a thin roof edge",
        "slender bamboo against a white wall with soft leaf shadows",
        "a waterside terrace opening to a wide river and distant hills through frameless glass",
        "a tea room with a dark timber table, one celadon cup and a horizontal window onto water",
        "snow on dark roof tiles and white walls with a vertical slit window",
        "a white wall with a thin vertical slat screen, no square grid",
    ],
    "artistic.japanese_soft": [
        "raindrops on a chain-link fence at blue hour",
        "a puddle reflecting a bicycle wheel and a slice of sky",
        "a clear umbrella covered in raindrops against a dusk sky",
        "an empty station bench under a small canopy at noon",
        "a rural T-junction with a convex traffic mirror and power lines",
        "a lowered railway crossing barrier in wind, no train",
        "a vending machine glowing at blue hour on a quiet street",
        "a rice field under a clear noon sky with thin cirrus",
        "a riverside levee with layered altocumulus and a distant town",
        "a seaside road under broken wind-torn clouds",
        "a hilltop view of a town at blue hour with first lights",
        "a summer field with a single wind-bent tree and clear sky",
    ],
    "artistic.surrealism": [
        "a lone wooden door standing in an empty desert",
        "a stone pocket watch sagging over a bare branch",
        "a green apple with a clean cut revealing clockwork gears inside",
        "an umbrella and a sewing machine on a long table in a plain room",
        "a giant smooth stone sphere resting on a beach at low tide",
        "a staircase climbing into still water",
        "a lead-grey cloud resting heavily on a plain",
        "a mirror lake reflecting a sky that does not match the one above",
        "a floating island with one house and a long shadow",
        "a glass plant growing from a stone floor",
        "a street whose asphalt rolls up like a carpet at the far end",
        "a long arcade with stretched shadows and an empty chair",
    ],
    "artistic.impasto_oil": [
        "three ripe pears on a linen cloth",
        "a single sunlit lemon on a dark table",
        "a field of wheat under a heavy sky",
        "a coastal cliff with breaking waves",
        "a bouquet of wildflowers in a ceramic jug",
        "a sliced loaf of bread on a wooden board",
        "a mountain lake at dusk",
        "an old wooden door in a stone wall",
        "a bowl of red fruit on a blue cloth",
        "a bare winter tree against a low sun",
        "a fishing boat pulled onto shingle",
        "a copper kettle on a windowsill",
    ],
    "artistic.impressionism": [
        "a riverbank with poplars in afternoon light",
        "a field of poppies under a summer sky",
        "a garden path with dappled shadows",
        "a rowing boat on a still pond",
        "an empty cafe terrace in late sun",
        "a haystack in evening light",
        "a stone bridge over a river with reflections",
        "a seaside cliff in morning haze",
        "a lily pond with floating leaves",
        "a village street in autumn light",
        "a laundry line in a green garden",
        "a snow-covered path at dusk",
    ],
    "artistic.ukiyo_e": [
        "a rocky inlet with small waves at dawn",
        "a rural road through rice fields with a low ridge on the horizon",
        "a wooden bridge in heavy rain",
        "a waterfall between steep cliffs",
        "a full moon over a pine ridge",
        "a flock of cranes above reeds",
        "a snow-covered temple gate",
        "a riverside teahouse with paper lanterns at dusk",
        "a plum branch against a pale sky",
        "a rocky shore with wind-bent pines",
        "a castle on a hill above mist",
        "a fishing village of thatched huts at dawn",
    ],
    "retro.collage": [
        "a torn vintage train photograph over plain torn paper",
        "a paper-cut mountain range above a halftone sky",
        "a torn travel poster of a seaside resort",
        "a paper bird flying over a printed city map",
        "layered paper flowers with magazine clippings",
        "a paper cassette tape on sheet music",
        "a torn botanical print with a paper leaf",
        "a paper boat on a printed wave",
        "a cut-out window framing a printed landscape",
        "a stack of old landscape postcards with torn edges",
        "a blank paper clock face with no numerals",
        "a paper camera with a plain lens on a halftone background",
    ],
    "retro.pop_art": [
        "a single red apple with a thick black outline",
        "a plain red soda can on a flat yellow field",
        "a telephone receiver floating on blue",
        "a banana on a flat blue background",
        "a pair of sunglasses on yellow",
        "a flower with halftone petals",
        "a cassette tape on a flat red field",
        "a diner coffee cup on blue",
        "a lightning bolt on yellow",
        "a heart with halftone dots",
        "a sneaker on a flat graphic background",
        "a stack of pancakes on a plate",
    ],
    "retro.synthwave": [
        "a first-person cockpit view of a neon grid road at night",
        "a chrome sports car rushing past at ground level with red light trails",
        "a wireframe moon over a dark grid valley",
        "a magenta thunderstorm over a neon highway",
        "a retro computer terminal in a dark room, no grid",
        "a chrome sphere on a grid floor with an off-center horizon",
        "a neon motel at the edge of the frame with half the sky empty",
        "a VHS tape on a table with CRT scan lines, no sunset",
        "a laser sky over a dark ocean with no sun disk",
        "a low-angle city skyline under neon haze, no grid",
        "a chrome ring half out of frame on a grid plane",
        "a wireframe mountain range under a storm sky, no sunset",
    ],
    "retro.y2k": [
        "a chrome bubble chair in a white void",
        "a translucent inflatable chair",
        "a bondi-blue translucent disc floating over a pastel gradient",
        "a transparent flip phone with a small antenna on a pearl surface",
        "a holographic CD reflecting pastel light",
        "a lime-green translucent sneaker on a clean pedestal",
        "a translucent laptop on a white background",
        "a chrome heart pendant floating",
        "a clear plastic bubble holding liquid",
        "a mirrored sphere on a pastel floor",
        "an electric-purple inflatable sofa in an empty studio",
        "a transparent hair clip with holographic film",
    ],
    "realism.documentary": [
        "a weathered fishing trawler on a mudflat at low tide, dawn mist",
        "a rusted tin roof with rain streaks in a mountain village",
        "a distant figure with an umbrella on a wet street at dusk",
        "a cracked concrete wall with peeling paint and moss",
        "a storm front over a wheat field",
        "a dark tungsten-lit kitchen with steam",
        "a muddy stone path after rain",
        "a corroded metal bridge over a brown river",
        "a dusty market stall at noon with no people",
        "a foggy pine forest with wet bark",
        "a dry riverbed with cracked mud",
        "fishing nets and buoys on a wet dock",
    ],
    "realism.new_topographics": [
        "an empty gas station under flat overcast light",
        "a parking lot with a single light pole",
        "a roadside motel with a blank sign",
        "a suburban intersection with power lines",
        "a concrete drainage channel in dry grass",
        "a self-storage building under a white sky",
        "a strip mall facade with empty parking",
        "a highway overpass over dry scrub",
        "a laundromat window at dusk with no people",
        "a warehouse loading dock",
        "a row of identical houses under flat light",
        "a dead-end road with a chain-link fence",
    ],
    "animation.pixar": [
        "a stylized 3D toy robot sitting on a wooden shelf",
        "a cozy 3D workshop with warm lamps and floating dust",
        "a stylized 3D teapot with exaggerated curves on a windowsill",
        "a small 3D camper van in a stylized forest",
        "a 3D stack of books with a glowing lamp",
        "a stylized 3D cafe interior with rounded furniture",
        "a 3D red bicycle leaning on a sunny wall",
        "a stylized 3D garden with oversized flowers",
        "a 3D radio and a cup on a bedside table",
        "a stylized 3D lighthouse on a rounded cliff",
        "a 3D toy train on a curved track",
        "a stylized 3D kitchen with copper pots",
    ],
    "advertising.swiss_minimal": [
        "a white ceramic cup on a matte grey grid backdrop",
        "a wireless earbud case on a plain warm-grey field",
        "a glass bottle on a concrete pedestal",
        "a closed notebook on a pale grid",
        "a minimal desk lamp on a neutral field",
        "a white sneaker on a low plinth",
        "a steel watch on a matte block",
        "a small speaker on a pale background",
        "a moulded chair on a concrete floor",
        "a perfume bottle on a white plinth",
        "a thin laptop half open on a grey field",
        "a camera lens standing on a matte surface",
    ],
    "advertising.product_macro": [
        "a watch movement in macro",
        "a single earbud in macro",
        "a perfume cap with water droplets",
        "a lipstick bullet in macro",
        "a glass of iced drink with condensation",
        "a camera lens edge in macro",
        "a cream jar with a swirl",
        "a brushed metal bottle in macro",
        "a sneaker sole in macro",
        "a piece of dark chocolate in macro",
        "coffee beans in macro",
        "a phone edge in macro",
    ],
    "advertising.acid_pop": [
        "a sneaker silhouette on acid yellow",
        "a soda can on hot pink",
        "headphones on cyan",
        "a skateboard on a checkerboard",
        "an energy drink can on acid green",
        "sunglasses on hot pink",
        "a boombox silhouette on cyan",
        "a roller skate on yellow",
        "wrapped candy on pink",
        "a phone case on a checkerboard",
        "a cap silhouette on cyan",
        "a cassette on acid yellow",
    ],
    "advertising.lifestyle_film": [
        "hands tying a shoe by a sunny window",
        "hands holding a coffee cup at a warm kitchen table",
        "a bicycle in a golden-hour kitchen",
        "a picnic blanket in late sun",
        "a dog asleep on a linen sofa",
        "laundry moving in afternoon sun",
        "hands turning a book page by a window",
        "hands chopping vegetables in warm light",
        "a view from the back seat through the windshield at sunset",
        "beach towels on a balcony rail",
        "balcony plants in warm light",
        "a breakfast table with morning sun",
    ],
    "advertising.clay_3d": [
        "a clay smartphone on a small pedestal",
        "a clay coffee cup with a saucer",
        "a clay shopping bag",
        "a clay car",
        "a clay potted plant",
        "a clay wallet",
        "a clay headphone set",
        "a clay gift box",
        "a clay laptop",
        "a clay camera",
        "a clay burger",
        "a clay house",
    ],
    "advertising.oriental_minimal": [
        "a tea canister on a vast rice-paper field",
        "a porcelain cup with steam",
        "an incense holder with a thin smoke line",
        "a ceramic vase on plaster",
        "a rice-paper lamp",
        "a bamboo tray with one cup",
        "an ink stone and a brush",
        "a linen pouch on stone",
        "a wooden comb on paper",
        "a teapot on a low stone slab",
        "a folded fan on paper",
        "a stone bowl with water",
    ],
    "animation.xuanji_3d": [
        "a young swordsman in a dark embroidered robe standing on a cliff edge at dusk, seen from behind in three-quarter view",
        "a close-up portrait of a young man with wind-blown strand hair and a gold-thread embroidered collar, backlit by warm sun",
        "an armoured general in red and black lamellar kneeling among spears on a battlefield at sunset, low angle past the foreground soldiers",
        "two figures facing each other in a dark bamboo forest with cold teal mist and one warm lantern",
        "a veiled woman in layered indigo silk seated on a stone bench in a moonlit courtyard",
        "a long ruined temple corridor lined with weathered stone guardian statues, a tiny distant figure under dust-filled shafts of light",
        "a close desk still life of a jade seal, an ink stone, a brush and a half-open blank scroll in warm lamplight, a blurred figure far behind",
        "a vast cloud sea with floating stone peaks and one small pavilion, a lone tiny figure on the nearest cliff edge seen from far away",
        "a close view of armoured gauntlets and a sword hilt resting on rain-wet mossy stone, a blurred figure behind",
        "a crowd of soldiers with raised spears and tall banners before a mountain pass at dawn",
        "an old master in white robes standing in falling snow before a temple gate",
        "a girl in magenta silk running through a night market of paper lanterns, sleeves blurred by motion",
    ],
}

NOTES_BY_STYLE = {
    "oriental.modern_chinese": {
        1: "openings are a narrow vertical slit and a horizontal band only",
        2: "frameless glass only, rectangular edge, no round opening",
        3: "exactly one circular opening in the far wall, no ring on the water and no second circle",
        4: "open corridor sides only, rectangular openings",
        5: "moss and pebbles around the rock, shallow water, rectangular openings",
        6: "horizontal band window only, rectangular",
        7: "long horizontal window only, rectangular",
        8: "no opening at all, only bamboo and leaf shadows",
        9: "frameless glass only, rectangular edge",
        10: "horizontal window onto water, rectangular",
        11: "vertical slit window only",
        12: "thin vertical slats only, rectangular",
    },
    "artistic.japanese_soft": {
        1: "macro detail, blue hour, no large cloud, fence wire straight and continuous, no text",
        2: "macro puddle reflection, thin cirrus, no text or signage",
        3: "macro umbrella, golden hour, small cumulus, no characters or signage",
        4: "medium shot, noon light, small cumulus, empty bench, no characters and no station signage",
        5: "medium shot, noon light, clear sky, poles straight and evenly spaced, no text on the mirror",
        6: "medium shot, golden hour, broken clouds, no train and no characters, barrier straight",
        7: "medium shot, blue hour, clear sky, vending machine without readable labels or logos",
        8: "wide shot, noon light, thin cirrus only, no towering cumulus tower",
        9: "wide shot, golden hour, layered altocumulus, no centered cloud tower",
        10: "wide shot, golden hour, broken clouds, no sun disk on the horizon",
        11: "wide shot, blue hour only, clear sky, no sun disk",
        12: "wide shot, noon light, clear sky, one tree, no large cumulus",
    },
    "artistic.surrealism": {
        1: "only the door is impossible; no floating objects and no figures",
        2: "the watch is carved from stone yet sags like cloth; no floating objects",
        3: "only the cut apple reveals clockwork; everything else ordinary",
        4: "only these two ordinary objects share the table; nothing else impossible",
        5: "the sphere rests on the sand; no floating objects",
        6: "only the upper steps disappear beneath the still water; no extra objects",
        7: "the cloud is heavy like lead and touches the ground; no floating",
        8: "only the reflection is wrong; the sky above stays calm",
        9: "only the island floats; the water below is still",
        10: "the plant itself is made of clear glass, no vase",
        11: "only the street surface rolls up; buildings stay straight and undistorted",
        12: "long arcade, shadows stretch farther than the light allows, no people",
    },
    "artistic.impasto_oil": {
        1: "exactly three ripe pears, one in front and two behind, curved knife strokes follow each pear",
        4: "one breaking wave, no boats and no people",
        5: "broad knife masses for jug and flowers, no thin fussy stems",
        8: "rough thick plaster wall against a smoother thinner wooden door, wood tones only, no coloured patches",
        11: "one boat only, no figures",
        12: "curved knife strokes follow the kettle's round body, no square tiles",
    },
    "artistic.impressionism": {
        1: "a clear sunlit focal tree with decisive strokes, foreground loosely brushed",
        4: "one empty rowing boat, no figures",
        5: "empty tables and chairs, no people",
        6: "the haystack is the decisive focal mass, water loosely brushed",
        11: "no people, only cloth moving in the wind",
        12: "a clear focal path with decisive strokes, background loose",
    },
    "artistic.ukiyo_e": {
        1: "small waves only, no giant claw wave, no distant cone mountain",
        2: "a low rounded ridge only, no iconic conical mountain",
        3: "two ordinary travellers with umbrellas, faces not detailed, no landmark",
        5: "the moon is a flat pale disc with no craters and no photographic texture",
        7: "gate only, no people and no cartouche",
        8: "wooden teahouse with paper lanterns, no bridge and no modern structures",
        12: "flat-bottomed wasen boats with a sculling oar, no cabins and no engines, no people",
    },
    "retro.collage": {
        1: "no map, no readable letters or numbers, only torn paper and print grain",
        4: "map shows abstract street lines only, no readable letters",
        5: "no faces and no people, botanical clippings only, background scraps carry no readable letters",
        6: "cassette flattened into print with scratches and halftone, not glossy 3D",
        9: "landscape postcards only, no readable handwriting or stamps",
        10: "landscape postcards only, no portraits and no faces",
        11: "the clock face is clearly visible with hour marks only, no numerals and no text",
        12: "camera is a flat print fragment with scratches and halftone, lens ring has no text or numbers, not glossy product photography",
    },
    "retro.pop_art": {
        2: "a small starburst graphic and a blank label band, no readable letters",
        7: "no text on the cassette, one halftone dot scale",
        8: "a blank sleeve band and a small starburst, no logo and no readable text",
        11: "plain sneaker with no logos, no brand marks and no text",
    },
    "retro.synthwave": {
        1: "dashboard dials and steering wheel, no readable text on any screen",
        5: "blank screen with no text",
        7: "blank sign, no readable letters",
        8: "no label text on the tape",
        10: "no readable signs, silhouette skyline only",
    },
    "retro.y2k": {
        3: "no logo and no readable text, one four-point star accent",
        4: "a transparent flip phone, not a modern flat smartphone, no logo or text",
        6: "no logo and no brand marks",
        11: "no logo and no readable text",
    },
    "realism.documentary": {
        3: "the figure is small and distant, face not visible, no readable text",
        9: "empty stall, no people and no readable text",
        12: "wet ropes and buoys, no text",
    },
    "realism.new_topographics": {
        3: "blank sign with no readable letters",
        9: "no people and no readable signs",
        11: "identical houses, no readable numbers",
        12: "no signage and no people",
    },
    "animation.pixar": {
        1: "toy robot without text or logos, no human characters",
        4: "no logos or text on the van",
        11: "plain toy train, no logos or text",
    },
    "advertising.swiss_minimal": {
        1: "no readable text, blank copy zone on the right",
        3: "blank glass bottle with no label and no letters or numbers",
        6: "no brand marks or text",
        8: "plain speaker with no brand text or logo",
        10: "blank perfume bottle with no label text or letters",
        12: "plain lens with no markings, numbers or brand text",
    },
    "advertising.product_macro": {
        1: "no brand text on the dial",
        2: "no logo or text",
        6: "no lens branding text",
    },
    "advertising.acid_pop": {
        1: "plain sneaker with no logo, no swoosh and no brand text",
        2: "no label text",
        5: "blank can label with no letters, no face and no people",
        7: "no text on the boombox",
        9: "plain candy wrapper with no letters or logo",
        10: "plain phone case with abstract shapes only, no figure and no people",
    },
    "advertising.lifestyle_film": {
        1: "faces out of frame, no readable text",
        5: "no text or logo on the sofa",
        6: "book cover is blank with no letters",
        9: "front seats and dashboard ahead, steering wheel on the left, windshield centred, blank steering wheel emblem with no brand logo, no people",
    },
    "advertising.clay_3d": {
        1: "no screen text or logo",
        9: "no logo or text on the laptop",
    },
    "advertising.oriental_minimal": {
        1: "no label text, no ornament",
        7: "no writing on the paper",
        9: "wooden comb with no engraved characters or text",
    },
    "animation.xuanji_3d": {
        1: "one figure only, no crowd, no readable text on the robe",
        2: "the face is clearly formed with two eyes and a natural mouth, no second face, no text",
        3: "many soldiers in the foreground but only the kneeling general in focus, banners blank",
        4: "exactly two figures at opposite edges of the frame, no third person, no text",
        5: "one figure only, no attendants, no plaques with characters",
        6: "the carved statues and corridor fill the frame, the figure is small and distant with no face visible, no inscriptions",
        7: "the desk objects are the sharp subject, the figure is soft and small with no face and no hands, the scroll is blank",
        8: "the landscape fills the frame, the figure is very small with no face visible, no birds, the pavilion is the only architecture",
        9: "the metal and wet stone are the sharp subject, the figure is out of focus with no hands, no engraved characters",
        10: "the crowd stays at a distance with faces unresolved, banners blank",
        11: "one figure only, snow falling, no attendants, the temple plaque is blank",
        12: "one runner only, lanterns carry no characters, no crowd faces",
    },
}

DEFAULT_NOTE = "reference board sample, no characters, clean edges with no ornamental frame"
DEFAULT_NOTE_BY_STYLE = {
    "oriental.modern_chinese": (
        "reference board sample, matte surfaces, no people, no ornamental frame, "
        "no repeated circular openings, at least forty percent empty space"
    ),
    "artistic.ukiyo_e": (
        "reference board sample, no text and no cartouche, flat woodblock colour and washi grain"
    ),
    "artistic.impressionism": (
        "reference board sample, no characters, no text, broken brushwork and soft edges"
    ),
    "artistic.impasto_oil": (
        "reference board sample, no characters, no text, thick paint relief and canvas weave"
    ),
    "artistic.surrealism": (
        "reference board sample, no characters, no creatures, no text, "
        "one impossible element only, calm precise painting, long shadows"
    ),
    "artistic.japanese_soft": (
        "reference board sample, no characters, no text or signage, clean painted edges, "
        "one clear focal point at one shot scale"
    ),
    "retro.collage": (
        "reference board sample, no characters, no readable text, torn paper edges and print grain"
    ),
    "retro.pop_art": (
        "reference board sample, no characters, no text, flat ink and halftone dots"
    ),
    "retro.synthwave": (
        "reference board sample, no characters, no text or signage, neon glow and grid perspective"
    ),
    "retro.y2k": (
        "reference board sample, no characters, no text, chrome and translucent plastic"
    ),
    "realism.documentary": (
        "raw documentary photograph, natural light, no text, no staged composition"
    ),
    "realism.new_topographics": (
        "deadpan documentary photograph, flat light, no readable text, no people"
    ),
    "animation.pixar": (
        "stylized 3D render, no characters, no text, no logos, cinematic soft light"
    ),
    "advertising.swiss_minimal": (
        "clean advertising still, no readable text, generous copy space, matte paper"
    ),
    "advertising.product_macro": (
        "product macro photograph, no text, controlled highlights, contact shadow"
    ),
    "advertising.acid_pop": (
        "acid pop advertising, no readable text, flat colour, blank copy zone"
    ),
    "advertising.lifestyle_film": (
        "cinematic lifestyle photograph, faces out of frame, no readable text, film grain"
    ),
    "advertising.clay_3d": (
        "stylized 3D clay advertising, no text or logo, soft shadow, blank copy zone"
    ),
    "advertising.oriental_minimal": (
        "oriental minimal advertising, no text, no ornament, vast negative space"
    ),
    "animation.xuanji_3d": (
        "reference board sample, cinematic Chinese 3D animated series frame, "
        "original character designs, no text, no watermark, no logos"
    ),
}


def _note(style: str, index: int) -> str:
    default = DEFAULT_NOTE_BY_STYLE.get(style, DEFAULT_NOTE)
    extra = NOTES_BY_STYLE.get(style, {}).get(index)
    return f"{default}, {extra}" if extra else default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--seed-base", type=int, default=5100)
    args = parser.parse_args()

    root = find_project_root()
    pack = get_pack(root, args.style)
    directory = style_boards_root() / pack.identity.group / pack.identity.id.split(".")[1]
    candidates = directory / "candidates"
    params_dir = candidates / "params"
    params_dir.mkdir(parents=True, exist_ok=True)

    subjects = SUBJECTS_BY_STYLE.get(args.style, SUBJECTS)
    jobs = []
    camera = "static" if "static" in pack.camera.allowed_moves else pack.camera.allowed_moves[0]
    for index, subject in enumerate(subjects[: args.limit], start=1):
        prompt = compile_image_prompt(
            pack, subject=subject, layers={}, camera_move=camera,
            extra_note=_note(args.style, index),
        )
        params = {
            "positive_prompt": prompt,
            "seed": args.seed_base + index,
            "width": 576,
            "height": 1024,
            "steps": 16,
            "cfg": 1.0,
            "filename_prefix": f"refboard/{pack.identity.group}_{pack.identity.id.split('.')[1]}/{index:02d}",
        }
        path = params_dir / f"{index:02d}.json"
        path.write_text(json.dumps(params, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        jobs.append({
            "id": f"{index:02d}",
            "workflow": "workflows/flux3_t2i_api.json",
            "params": str(path).replace("\\", "/"),
            "out": str(candidates / f"{index:02d}").replace("\\", "/"),
        })

    (candidates / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    (directory / "manifest.json").write_text(json.dumps({
        "style": pack.identity.id,
        "status": "PENDING_REVIEW",
        "subjects": subjects[: args.limit],
        "note": "Candidates only. Approve/reject each sample by hand; images are local and not in Git.",
        "license": "generated locally with FLUX.3; reference images are not redistributed",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"jobs": str(candidates / "jobs.json"), "count": len(jobs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
