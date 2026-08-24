from typing import Dict, Any

enhanced_passages: Dict[str, Any] = {
    "village_square": {
        "tone": "warm adventure",
        "base_text": "You step into the village square, where chatter and market sounds mingle in the afternoon sun.",
        "events": [
            {
                "condition": lambda st: not st["flags"].get("has_map", False),
                "inject": "A merchant waves a rolled parchment toward you, eyes hopeful."
            },
            {
                "condition": lambda st: st["relationships"].get("elder", 0) >= 1,
                "inject": "The village elder spots you by the fountain and nods, as if expecting a word."
            },
            {
                "condition": lambda st: st["traits"].get("greedy", 0) >= 2,
                "inject": "A small pouch of coins lies forgotten atop a stall crate... or so it seems."
            },
            {
                "condition": lambda st: st["turn"] >= 3 and "red_stone" not in st["quests"],
                "inject": "Rumors drift by: something about a lost 'red stone' hidden beyond the woods."
            },
            {
                "condition": lambda st: st["turn"] >= 4 and not st["flags"].get("forest_hint_boost", False),
                "inject": "A guard mentions wolves at dusk and a red glow deeper in the woods.",
            },
        ],
        "choices": [
            {
                "text": "Approach the merchant about the parchment",
                "next": "ask_for_the_map_price",
                "requires": [{"not_flag": "has_map"}],
                "effects": [{"add_trait": {"greedy": 1}}]
            },
            {
                "text": "Greet the elder by the fountain",
                "next": "greet_the_elder",
                "effects": [{"add_rel": {"elder": 1}}]
            },
            {
                "text": "Pocket the unattended coin pouch (-1 honor, +3 gold)",
                "next": "village_square",
                "requires": [ {"gte_trait": {"greedy": 2}},{"not_flag": "stole_coin_pouch"}],
                "effects": [{"set_flag": {"stole_coin_pouch": True}},{"add_trait": {"honor": -1}},{"add_item": {"gold": 3}},{"msg": "You slip the pouch away—no one notices. This time."}]
            },
            {
                "text": "Set off toward the village outskirts",
                "next": "village_outskirts" 
            },
            {
                "text": "Check the notice board for odd jobs", "next": "notice_board",
                "effects": [{"add_trait": {"honor": 1}}]
            },
            {
                "text": "Visit the training yard",
                "next": "training_yard" 
            },
            {
                "text": "Eavesdrop on visiting traders",
                "next": "notice_board",
                "effects": [{"set_flag": {"heard_trader_rumors": True}}],
            },
            {
                "text": "Help a stall owner tidy up",
                "next": "village_square",
                "cooldown": 12,
                "effects": [
                    {"add_trait": {"honor": 1}},
                    {"add_item": {"gold": 1}},
                    {"msg": "You lend a hand and earn a small coin for your trouble."}
                ]
            },
            {
                "text": "Ask guards about safe routes",
                "next": "village_outskirts",
                "requires": [{"gte_trait": {"honor": 1}}]
            }
        ]
    },

    "greet_the_elder": {
        "tone": "reverent",
        "base_text": "The elder greets you with a worn smile and a measured gaze.",
        "events": [
            {
                "condition": lambda st: True,
                "inject": "He speaks of a red stone, lost long ago, and of the dangers that guard it."
            }
        ],
        "choices": [
            {
                "text": "Hear more about the red stone (start quest)",
                "next": "elder_reveals_treasure_hint",
                "effects": [{"quest_add": {"id": "red_stone", "stage": 0}}, {"set_flag": {"heard_red_stone": True}}]
            },
            {
                "text": "Thank him and return to the square",
                "next": "village_square"
            },
            {
                "text": "Speak further with the elder",
                "next": "greet_the_elder",
                "dynamic_msg": "elder_dialogue"
            }
        ]
    },

    "elder_reveals_treasure_hint": {
        "tone": "mystery",
        "base_text": "The elder leans closer, lowering his voice.",
        "events": [
            {
                "condition": lambda st: True,
                "inject": "He whispers of a forest road, wolves at dusk, and a cave that hums with a faint glow."
            }
        ],
        "choices": [
            {
                "text": "Venture into the dark forest",
                "next": "enter_the_dark_forest",
                "effects": [{"add_trait": {"brave": 1}}, {"quest_stage": {"id": "red_stone", "stage": 1}}]
            },
            { 
                "text": "Seek better equipment first (visit the forge)", "next": "visit_blacksmiths_forge"
            }
        ]
    },

    "ask_for_the_map_price": {
        "tone": "merchant",
        "base_text": "You inquire about the price of the ancient-looking parchment.",
        "events": [],
        "choices": [
            {
                "text": "Offer 5 gold for the map",
                "next": "village_square",
                "requires": [{"gte_item": {"gold": 5}}, {"not_flag": "has_map"}],
                "effects": [
                    {"add_item": {"gold": -5}},
                    {"set_flag": {"has_map": True}},
                    {"msg": "You count out five coins. The merchant nods and presses the parchment into your hands."}
                ]
            },
            {
                "text": "Propose a trade with a shiny stone",
                "next": "village_square",
                "requires": [{"has_item": "shiny_stone"}, {"not_flag": "has_map"}],
                "effects": [
                    {"set_item": {"shiny_stone": False}},
                    {"set_flag": {"has_map": True}},
                    {"msg": "The merchant eyes the stone, then smiles. \"Fair enough—it's yours.\""}
                ]
            },
            {
                "text": "Count your coins (you don’t have 5 gold)",
                "next": "ask_for_the_map_price",
                "requires": [{"not_flag": "has_map"}],
                "condition": lambda st: st["inventory"].get("gold", 0) < 5,
                "effects": [
                    {"msg": "The merchant shakes his head. \"Five gold, no less. Come back when your purse is heavier.\""}
                ]
            },
            {
                "text": "Ask the merchant for a hint",
                "next": "ask_for_the_map_price",
                "dynamic_msg": "merchant_dialogue"
            },
            { 
                "text": "Decline and return to the square",
                "next": "village_square" 
            }
        ]
    },

    "visit_blacksmiths_forge": {
        "tone": "craft",
        "base_text": "The forge roars with heat as the blacksmith hammers iron with practiced rhythm.",
        "events": [
            {"condition": lambda st: st["inventory"].get("gold", 0) >= 3,
             "inject": "He eyes your coin pouch and offers a sturdy dagger for 3 gold."}
        ],
        "choices": [
        {
            "text": "Buy the dagger (3 gold)",
            "next": "village_square",
            "requires": [{"gte_item": {"gold": 3}}],
            "effects": [{"add_item": {"gold": -3}}, {"set_item": {"dagger": True}}, {"add_trait": {"brave": 1}},
                        {"msg": "You pay the smith and feel the dagger’s weight settle at your belt."}]
        },
        {
            "text": "Check your purse (you can’t afford the dagger)",
            "next": "visit_blacksmiths_forge",
            "condition": lambda st: st["inventory"].get("gold", 0) < 3,
            "effects": [
                {"msg": "The smith shrugs: \"Three gold, no less. Help a farmer or take a job from the board.\""}
            ]
        },
        { 
            "text": "Return to the square",
              "next": "village_square" 
        },
        { 
            "text": "Ask about iron shipments (leads to outskirts)",
            "next": "village_outskirts", "effects": [{"add_trait": {"honor": 1}}] 
        }
    ]
    },

    "village_outskirts": {
        "tone": "caution",
        "base_text": "Fields give way to hedgerows and a dirt path that winds toward a shadowed treeline.",
        "events": [
            {
                "condition": lambda st: st["flags"].get("heard_red_stone", False),
                "inject": "The rumor of a red stone pulls at your thoughts as the forest looms ahead."
            }
        ],
        "choices": [
            { 
                "text": "Take the forest road",
                "next": "enter_the_dark_forest" 
            },
            { 
                "text": "Follow the road to another town",
                "next": "follow_the_road_to_another_town" 
            }
        ]
    },

    "enter_the_dark_forest": {
        "tone": "suspense",
        "base_text": "Dusk gathers under the canopy. Branches clutch at your sleeves as the path narrows.",
        "events": [
            {
                "condition": lambda st: st["traits"].get("brave", 0) >= 2,
                "inject": "Your steady footing parts the underbrush; distant growls fail to shake you."
            },
            {
                "condition": lambda st: st["quests"].get("red_stone", {}).get("stage", -1) >= 1,
                "inject": "A faint red hue flickers among the roots to your left."
            },
            {
                "condition": lambda st: st["flags"].get("marked_forest_path", False),
                "inject": "Your tree marks glint with sap; finding the ridge again will be easy."
            }
        ],
         "choices": [
            {
                "text": "Face the wolves",
                "next": "fight_wolves" 
            },
            {
                "text": "Sneak past the wolves (needs honor ≥ 1)",
                "next": "sneak_around_wolves",
                "requires": [{"gte_trait": {"honor": 1}}],
                "effects": [{"msg": "You steady yourself and slip quietly between the shadows."}]
            },
            {
                "text": "Try to sneak... but lose your nerve",
                "next": "enter_the_dark_forest",
                "condition": lambda st: st["traits"].get("honor", 0) < 1,
                "cooldown": 3,
                "effects": [
                    {"msg": "Your conscience wavers—you’re not confident enough to slip past unseen."}
                ]
            },
            {   "text": "Search for the cave",
                "next": "mysterious_cave",
                "requires": [{"has_flag": "heard_red_stone"}] 
            },
            {   
                "text": "Wander for a while (no clear clue to follow)",
                "next": "ridge_overlook",
                "requires": [{"not_flag": "heard_red_stone"}],
                "cooldown": 3,
                "effects": [{"msg": "Without a lead, every hollow looks the same. From the ridge, you might spot a glow."}] 
            },
            {   
                "text": "Make a small camp and observe (+1 brave)",
                "next": "forest_camp", "effects": [{"add_trait": {"brave": 1}}] 
            },
            {   
                "text": "Climb a ridge to scout a safer route", "next": "ridge_overlook" 
            },
            {   
                "text": "Scavenge for valuables in hollow logs (+1 gold, −1 honor)",
                "next": "village_outskirts",
                "cooldown": 10,
                "effects": [{"add_item": {"gold": 1}}, {"add_trait": {"honor": -1}}] 
            }
        ]
},

    "fight_wolves": {
        "tone": "action",
        "base_text": "Snarls split the dark as the pack fans out around you.",
        "events": [],
        "choices": [
            {
                "text": "Stand your ground (requires dagger)",
                "next": "mysterious_cave",
                "requires": [{"has_item": "dagger"}],
                "effects": [{"add_trait": {"brave": 1}}, {"add_item": {"pelt": 1}},
                            {"msg": "Steel flashes and the pack scatters. You strip a pelt before moving on."}]
            },
            {
                "text": "Check your gear (you lack a proper weapon)",
                "next": "enter_the_dark_forest",
                "condition": lambda st: not bool(st["inventory"].get("dagger", False)),
                "cooldown": 2,
                "effects": [
                    {"msg": "Facing a pack bare-handed is folly. Better equipment might change the odds."}
                ]
            },
            {   
                "text": "Retreat to the forest edge",
                "next": "enter_the_dark_forest",
                "cooldown": 2,
                "effects": [{"add_trait": {"brave": -1}}] 
                }
  ]
},

    "sneak_around_wolves": {
        "tone": "stealth",
        "base_text": "You breathe shallowly and lean into the hush, stepping between roots and shadow.",
        "events": [],
        "choices": [
            {
                "text": "Keep low and circle the den",
                "next": "mysterious_cave", "effects": [{"add_trait": {"brave": 1}}] 
            },
            { 
                "text": "Lose your nerve and go back",
                "next": "enter_the_dark_forest",
                "effects": [{"add_trait": {"brave": -1}}] 
            }
        ]
    },

    "mysterious_cave": {
        "tone": "mystery",
        "base_text": "The cave mouth exhales cold air; somewhere within, a pulse of crimson rises and fades.",
        "events": [
            {
                "condition": lambda st: st["flags"].get("chalk_trail", False),
                "inject": "White chalk dust smears the stone—your own marks. You won’t get lost this time."
            },
            {
                "condition": lambda st: st["flags"].get("heard_red_stone", False),
                "inject": "The elder's warning echoes in your memory as the glow deepens."
            },
            {
                "condition": lambda st: st["quests"].get("red_stone", {}).get("stage", -1) >= 1,
                "inject": "The glow throbs a shade brighter, and a draft draws you inward."
            },
            {
                "condition": lambda st: "red_stone" not in st.get("quests", {}),
                "inject": "A low thrum carries an old tale: a red stone lost somewhere in these tunnels.",
                "effects": [{"quest_add": {"id": "red_stone", "stage": 1}}]
            }
        ],
        "choices": [
            { 
                "text": "Enter the mine-like tunnels", "next": "enter_the_mine", 
                "effects": [{"quest_stage": {"id": "red_stone", "stage": 2}}] 
            },
            { 
                "text": "Return to the forest", 
                "next": "enter_the_dark_forest" 
            },
            { 
                "text": "Explore a narrow side chamber", 
                "next": "side_chamber" 
            }
        ]
    },

    "enter_the_mine": {
        "tone": "tension",
        "base_text": "Timbers groan. A fine dust catches the light in your lamp.",
        "events": [],
        "choices": [
            { 
                "text": "Search deeper for the gem", 
                "next": "search_deeper_for_gem" 
            },
            { 
                "text": "Leave the mine", 
                "next": "enter_the_dark_forest" 
            },
            { 
                "text": "Survey the beams and slip into a side passage", 
                "next": "side_chamber" 
            },
            { 
                "text": "Climb a vent shaft to the ridge", 
                "next": "ridge_overlook" 
            },
            { 
                "text": "Leave a chalk trail", 
                "next": "search_deeper_for_gem",
                "effects": [{"set_flag": {"chalk_trail": True}}] 
            }
        ]
    },

    "search_deeper_for_gem": {
        "tone": "tension",
        "base_text": "Passages twist until the air grows thin and the glow sharpens to a point.",
        "events": [],
        "choices": [
            { 
                "text": "Claim the red stone (quest item)", 
                "next": "treasure_found",
                "effects": [
                        {"set_item": {"red_stone": True}},
                        {"quest_add": {"id": "red_stone", "stage": 2}},   
                        {"quest_complete": "red_stone"},
                        {"msg": "The stone hums warm in your palm. You did it."}
                    ] 
            },
            { 
                "text": "A skittering sound—prepare to fight!", 
                "next": "fight_cave_spider" 
            }
        ]
    },

    "fight_cave_spider": {
        "tone": "action",
        "base_text": "A massive spider erupts from a crack in the rock, mandibles clicking.",
        "events": [],
        "choices": [
            { 
                "text": "Strike with the dagger",
                "next": "treasure_found", 
                "requires": [{"has_item": "dagger"}],
                "effects": [
                    {"add_item": {"silk": 1}},
                    {"add_trait": {"brave": 1}},
                    {"set_item": {"red_stone": True}},                 
                    {"quest_add": {"id": "red_stone", "stage": 2}},    
                    {"quest_complete": "red_stone"},                   
                    {"msg": "You dart in, cut deep, and the spider collapses. The cavern falls silent."}
                ]
            },
            { 
                "text": "Grab a rock—then think better of it",
                "next": "enter_the_mine",
                "effects": [{"add_trait": {"brave": -1}},
                            {"msg": "The spider rears and you scramble back. This is a bad fight without steel."}] 
            },
            { 
                "text": "Flee toward the entrance",
                "next": "enter_the_mine", 
                "effects": [{"add_trait": {"brave": -1}}] 
            }
        ]
},

    "treasure_found": {
        "tone": "triumph",
        "base_text": "Victory's scent mingles with dust and iron as you lift your prize.",
        "events": [],
        "choices": [
            {
                "text": "Return to the square and share the news",
                "next": "village_square",
                "effects": [{"add_rel": {"elder": 1}}, {"add_trait": {"honor": 1}}]
            },
            {
                "text": "Bring the red stone straight to the elder",
                "next": "greet_the_elder",
                "effects": [
                    {"add_rel": {"elder": 1}},
                    {"add_trait": {"honor": 1}},
                    {"msg": "You hurry back to the fountain, prize wrapped in cloth."}
                ]
            },
            {
                "text": "Celebrate briefly in the capital",
                "next": "explore_capital_streets",
                "effects": [
                    {"msg": "You take a breath and walk the lively streets before heading home with your tale."}
                ]
            }
    ]
    },

    "follow_the_road_to_another_town": {
        "tone": "travel",
        "base_text": "The road unfurls like ribbon across rolling fields toward a distant skyline.",
        "events": [],
        "choices": [
            { 
                "text": "Approach the capital city gates", 
                "next": "capital_city_gates" 
            },
            { 
                "text": "Turn back to the village", 
                "next": "village_square" 
            }
        ]
    },

    "capital_city_gates": {
        "tone": "awe",
        "base_text": "Stone towers cast long shadows. The city breathes with a thousand lives beyond the portcullis.",
        "events": [],
        "choices": [
            { 
                "text": "Wander into the capital streets", 
                "next": "explore_capital_streets" 
            },
            { 
                "text": "Return to the road", 
                "next": "follow_the_road_to_another_town" 
            }
        ]
    },

    "explore_capital_streets": {
        "tone": "lively",
        "base_text": "Vendors sing out their wares as acrobats tumble in a square painted with banners.",
        "events": [],
        "choices": [
            { 
                "text": "Head back to the gates", 
                "next": "capital_city_gates" 
            },
            {
                "text": "Ask a city patrol about the rumors",
                "next": "village_outskirts",
                "effects": [
                    {"msg": "A guard mentions wolf packs and strange lights—north of the village."}
                ]
            },
            {
                "text": "Pay 1 gold for a reliable rumor (gain cave lead)",
                "next": "village_outskirts",
                "requires": [{"gte_item": {"gold": 1}}],
                "condition": lambda st: not st["flags"].get("heard_red_stone", False),
                "effects": [
                    {"add_item": {"gold": -1}},
                    {"set_flag": {"heard_red_stone": True}},
                    {"msg": "The patrol sergeant sketches a rough path: 'Red light by a cave at dusk. Watch for wolves.'"}
                ]
            }
    ]
    },

    "notice_board": {
        "tone": "lively",
        "base_text": "Notes flutter on a wooden board: lost items, requests, and small rewards for quick hands.",
        "events": [],
        "choices": [
            {   "text": "Follow a trader’s tip toward the outskirts",
                "next": "village_outskirts",
                "requires": [{"has_flag": "heard_trader_rumors"}]
            },
            { 
                "text": "Accept a pest-clearing task (+2 gold on completion)", 
                "next": "village_outskirts",
                "effects": [{"quest_add": {"id": "pest_job", "stage": 0}}] 
            },
            { 
                "text": "Return to the square", 
                "next": "village_square" 
            }
        ]
    },

    "training_yard": {
        "tone": "action",
        "base_text": "You limber up with straw dummies and wooden posts, working on footwork and timing.",
        "events": [],
        "choices": [
            { 
                "text": "Practice footwork (+1 brave)", 
                "next": "village_square",
                "effects": [{"add_trait": {"brave": 1}}] },
            { 
                "text": "Back to the square", 
                "next": "village_square" 
            },
            { 
                "text": "Spar fairly with another villager (+1 honor)", 
                "next": "village_square", 
                "effects": [{"add_trait": {"honor": 1}}] 
            },
            { 
                "text": "Test your training in the woods", 
                "next": "village_outskirts" 
            }
        ]
    },

    "forest_camp": {
        "tone": "calm",
        "base_text": "A small fire crackles; the forest breathes around you as shadows drift and settle.",
        "events": [],
        "choices": [
        { 
            "text": "Press deeper once rested", 
            "next": "mysterious_cave" 
        },
        { 
            "text": "Return to the edge", 
            "next": "village_outskirts" 
        },
        {
            "text": "Gather herbs to sell (+1 gold)",
            "next": "village_outskirts",
            "requires": [{"not_flag": "herb_bundle"}],
            "effects": [
                {"add_item": {"gold": 1}},
                {"set_flag": {"herb_bundle": True}},
                {"msg": "You tie a small bundle of herbs. Someone in the village will want these."}
            ]
        }
    ]
    },

    "ridge_overlook": {
        "tone": "awe",
        "base_text": "From above, the paths thread like veins through the trees; the glow is easier to triangulate.",
        "events": [],
        "choices": [
            { 
                "text": "Descend toward the glow", 
                "next": "mysterious_cave" 
            },
            { 
                "text": "Skirt the wolves’ territory", 
                "next": "sneak_around_wolves" 
            },
            {
                "text": "Descend through a fissure into the mine",
                "next": "enter_the_mine",
                "requires": [{"gte_trait": {"brave": 2}}]
            },
            {
               "text": "Scrape rare lichen for barter",
                "next": "ridge_overlook",
                "requires": [{"not_flag": "scraped_lichen"}],
                "effects": [
                    {"set_flag": {"scraped_lichen": True}},
                    {"add_item": {"gold": 1}},
                    {"msg": "You gather a pinch of rare lichen—traders will pay for it."}
                ]
}
        ]
    },

    "side_chamber": {
        "tone": "mystery",
        "base_text": "A cramped fissure glitters faintly where mineral seams catch your light.",
        "events": [],
        "choices": [
            {
                "text": "Pocket a shiny stone",
                "next": "mysterious_cave",
                "requires": [{"not_flag": "took_shiny_stone"}],
                "effects": [
                    {"set_flag": {"took_shiny_stone": True}},
                    {"add_item": {"shiny_stone": 1}},
                    {"msg": "You pry a single glittering stone from the seam."}
                ]
            },
            {
                "text": "Return to the main passage",
                "next": "mysterious_cave"
            }
        ]
    }
}
