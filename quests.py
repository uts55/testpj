class Quest:
    def __init__(self, id: str, title: str, description: str, stages: list[dict], optional_objectives: list[dict], rewards: dict):
        self.id = id
        self.title = title
        self.description = description
        self.stages = stages
        self.optional_objectives = optional_objectives
        self.rewards = rewards

# Sample Quest 1
q001 = Quest(
    id="q001",
    title="The Lost Sword",
    description="The Village Elder has lost his ancestral sword. He believes it was stolen by goblins in the nearby forest. Find it and return it to him.",
    stages=[
        {
            "stage_id": "q001_s1",
            "description": "Find the Elder's Sword.",
            "completion_condition": "has_item:elders_sword",
            "next_stage_id": "q001_s2",
            "status_description": "You found a sword that might be the Elder's. It feels ancient and important."
        },
        {
            "stage_id": "q001_s2",
            "description": "Return the sword to the Village Elder.",
            "completion_condition": "delivered_sword_to_elder",
            "next_stage_id": None,  # Or some indicator of quest completion
            "status_description": "You returned the sword to the Village Elder."
        }
    ],
    optional_objectives=[
        {
            "objective_id": "opt_defeat_goblin_chief",
            "description": "Defeat the Goblin Chief who guarded the sword.",
            "completion_condition": "defeated:goblin_chief_q001",
            "rewards": {'xp': 50, 'items': ['item_goblin_treasure_map'], 'currency': {'gold': 25}},
            "status_description": "You defeated the Goblin Chief, a fearsome foe!"
        }
    ],
    rewards={'xp': 100, 'items': ['item_goblin_chief_key'], 'currency': {'gold': 50}}
)

# Sample Quest 2
q002 = Quest(
    id="q002",
    title="The Alchemist's Request",
    description="The local alchemist needs a rare herb, Moonpetal, which only blooms at night in the Whispering Woods. She needs it to brew a potion for the sick.",
    stages=[
        {
            "stage_id": "q002_s1",
            "description": "Collect 3 Moonpetal herbs from the Whispering Woods.",
            "completion_condition": "has_items:moonpetal_herb:3",
            "next_stage_id": "q002_s2",
            "status_description": "You have collected enough Moonpetal herbs."
        },
        {
            "stage_id": "q002_s2",
            "description": "Deliver the Moonpetal herbs to the Alchemist.",
            "completion_condition": "delivered_moonpetal_to_alchemist",
            "next_stage_id": None, # Or some indicator of quest completion
            "status_description": "The Alchemist received the Moonpetal herbs."
        }
    ],
    optional_objectives=[], # No optional objectives for this quest
    rewards={'xp': 75, 'items': ['item_potion_healing_greater'], 'currency': {'silver': 150}}
)

# New Complex Quest 3
q003 = Quest(
    id="q003",
    title="The Shadow Over Riverwood",
    description="A dark presence looms over the village of Riverwood, corrupting the land and its creatures. Investigate the source and restore peace.",
    stages=[
        {
            "stage_id": "s1_investigate_corruption",
            "description": "Speak to the village elder of Riverwood about the strange occurrences and look for signs of corruption in the nearby woods.",
            "completion_condition": "dialogue_elder_riverwood_complete;found_corrupted_totem",
            "next_stage_id": "s2_find_hidden_shrine",
            "status_description": "The elder spoke of a growing shadow, and you found a strange, corrupted totem in the woods. The darkness seems to emanate from deeper within."
        },
        {
            "stage_id": "s2_find_hidden_shrine",
            "description": "Follow the trail of corruption to find the hidden shrine where the shadow entity is rumored to reside.",
            "completion_condition": "discovered_location:hidden_shadow_shrine",
            "next_stage_id": "s3_confront_entity",
            "status_description": "You've located the Hidden Shadow Shrine. The air here is thick with dark energy."
        },
        {
            "stage_id": "s3_confront_entity",
            "description": "Confront the entity within the shrine and banish it from Riverwood.",
            "completion_condition": "defeated:shadow_entity_riverwood",
            "next_stage_id": None, # final stage
            "status_description": "The Shadow Entity has been banished! Light returns to Riverwood."
        }
    ],
    optional_objectives=[
        {
            "objective_id": "opt_cleanse_altars",
            "description": "Find and cleanse the three minor corrupted altars scattered around Riverwood's outskirts.",
            "completion_condition": "cleansed_altars:3",
            "rewards": {'xp': 75, 'items': ['item_blessed_trinket'], 'currency': {'silver': 50}},
            "status_description": "You have cleansed all the minor corrupted altars, weakening the shadow's grip."
        },
        {
            "objective_id": "opt_rescue_spirit",
            "description": "Rescue the trapped nature spirit from the Shadow Entity's influence within the shrine before the final confrontation.",
            "completion_condition": "rescued:nature_spirit_riverwood",
            "rewards": {'xp': 100, 'items': ['item_spirit_boon_charm'], 'currency': {}},
            "status_description": "The nature spirit is free and offers its aid!"
        }
    ],
    rewards={'xp': 300, 'items': ["item_riverwood_defender_shield"], 'currency': {"gold": 150}}
)

ALL_QUESTS = {
    q001.id: q001,
    q002.id: q002,
    q003.id: q003
}

# Quest for Verdant Wardens
q_verdant_wardens_aid = Quest(
    id="q_verdant_wardens_aid",
    title="Whispers of Decay",
    description="Theron Ashwood of the Verdant Wardens has sensed a growing corruption in the Whisperwood. He seeks an outsider's help to investigate a defiled grove and recover a sacred seed before its power is twisted for dark purposes.",
    stages=[
        {
            "stage_id": "s1_speak_theron",
            "description": "Speak with Theron Ashwood at the Sunken Grove to learn more about the corruption.",
            "completion_condition": "dialogue_theron_vw_quest_start_complete",
            "next_stage_id": "s2_investigate_grove",
            "status_description": "Theron has asked you to investigate the Defiled Grove and retrieve a stolen sacred seed."
        },
        {
            "stage_id": "s2_investigate_grove",
            "description": "Travel to the Defiled Grove, overcome any corrupted guardians, and find the Stolen Sunseed.",
            "completion_condition": "has_item:stolen_sunseed;defeated:corrupted_grove_guardian",
            "next_stage_id": "s3_return_seed",
            "status_description": "You have recovered the Stolen Sunseed from the Defiled Grove."
        },
        {
            "stage_id": "s3_return_seed",
            "description": "Return the Stolen Sunseed to Theron Ashwood.",
            "completion_condition": "delivered_stolen_sunseed_to_theron",
            "next_stage_id": None,
            "status_description": "You returned the Stolen Sunseed to Theron. The Verdant Wardens are grateful."
        }
    ],
    optional_objectives=[],
    rewards={
        'xp': 150,
        'items': ['item_wardens_healing_draught'],
        'currency': {'silver': 100},
        'faction_rep_changes': [ # New reward type
            {"faction_id": "verdant_wardens", "amount": 25}
        ]
    }
)

ALL_QUESTS[q_verdant_wardens_aid.id] = q_verdant_wardens_aid
