from typing import Optional, Dict, List

class Faction:
    def __init__(self,
                 id: str,
                 name: str,
                 description: str,
                 goals: str,
                 relationships: Dict[str, str],
                 members: Optional[List[str]] = None):
        self.id: str = id
        self.name: str = name
        self.description: str = description
        self.goals: str = goals
        self.relationships: Dict[str, str] = relationships
        self.members: List[str] = members if members is not None else []
