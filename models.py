# models.py - Modele Pydantic V2
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from enum import Enum

class ItemType(str, Enum):
    weapon = "armă"
    consumable = "consumabil"
    quest = "obiect_important"
    currency = "monedă"
    misc = "diverse"

class InventoryItem(BaseModel):
    name: str
    type: ItemType
    value: int = 0
    quantity: int = 1
    description: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Numele obiectului nu poate fi gol")
        return v.strip()

class CharacterStats(BaseModel):
    health: int = Field(ge=0, le=100, default=100)
    max_health: int = Field(default=100)
    reputation: int = Field(ge=0, le=100, default=20)
    max_reputation: int = Field(default=100)
    gold: int = Field(ge=0, default=5)
    location: str = "Târgoviște"
    power_level: int = Field(ge=1, le=10, default=1)
    status_effects: List[str] = Field(default_factory=list)

class GameAction(BaseModel):
    action_text: str
    required_reputation: int = 0
    required_power_level: int = 1
    required_items: List[str] = Field(default_factory=list)

class NarrativeResponse(BaseModel):
    narrative: str = Field(..., min_length=10, max_length=500)
    health_change: Optional[int] = 0
    reputation_change: Optional[int] = 0
    gold_change: Optional[int] = 0
    items_gained: List[InventoryItem] = Field(default_factory=list)
    items_lost: List[str] = Field(default_factory=list)
    location_change: Optional[str] = None
    status_effects: List[str] = Field(default_factory=list)
    game_over: bool = False
    win_condition: bool = False
    suggestions: List[str] = Field(default_factory=list)
    
class GameState(BaseModel):
    character: CharacterStats
    inventory: List[InventoryItem]
    story: List[Dict[str, Any]]
    turn: int
    last_image_turn: int

    @field_validator('inventory')
    @classmethod
    def validate_inventory(cls, v):
        # Asigură că există cel puțin monedele
        if not any(item.name.endswith("galbeni") for item in v):
            v.append(InventoryItem(name="5 galbeni", type=ItemType.currency, value=5, quantity=1))
        return v