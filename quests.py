class Quest:
    def __init__(self, id: str, title: str, description: str, objectives: list[str], rewards: dict, status_descriptions: dict[str, str]):
        self.id = id
        self.title = title
        self.description = description
        self.objectives = objectives
        self.rewards = rewards
        self.status_descriptions = status_descriptions

# Sample Quest 1
q001 = Quest(
    id="q001",
    title="The Lost Sword",
    description="The Village Elder has lost his ancestral sword. He believes it was stolen by goblins in the nearby forest. Find it and return it to him.",
    objectives=["Find the Elder's Sword.", "Return the sword to the Village Elder."],
    rewards={'xp': 100, 'items': ['item_goblin_chief_key'], 'currency': {'gold': 50}},
    status_descriptions={
        'accepted': 'You agreed to help the Elder find his sword.',
        'objective_1_done': "You found a sword that might be the Elder's.",
        'completed': 'You returned the sword and the Elder rewarded you.'
    }
)

# Sample Quest 2
q002 = Quest(
    id="q002",
    title="The Alchemist's Request",
    description="The local alchemist needs a rare herb, Moonpetal, which only blooms at night in the Whispering Woods. She needs it to brew a potion for the sick.",
    objectives=["Collect 3 Moonpetal herbs from the Whispering Woods.", "Deliver the Moonpetal herbs to the Alchemist."],
    rewards={'xp': 75, 'items': ['item_potion_healing_greater'], 'currency': {'silver': 150}},
    status_descriptions={
        'accepted': 'You promised the Alchemist to gather Moonpetal herbs.',
        'objective_1_done': 'You have collected enough Moonpetal herbs.',
        'completed': 'The Alchemist thanked you for the herbs and gave you a reward.'
    }
)

ALL_QUESTS = {
    q001.id: q001,
    q002.id: q002
}
