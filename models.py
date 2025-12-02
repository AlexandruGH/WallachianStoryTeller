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

class GameMode(str, Enum):
    FREE_WORLD = "Lume Liberă"
    CAMPAIGN = "Campanie: Pecetea Drăculeștilor"

class CharacterClassType(str, Enum):
    AVENTURIER = "Aventurier"
    STRAJER = "Străjer"
    NEGUSTOR = "Negustor"
    SPION = "Spion"
    CALATOR_RAZBOI = "Călător în Arta Războiului"
    CALUGAR = "Călugăr / Erudit"
    VANATOR = "Vânător / Războinic al Codrilor"
    LIBER = "Liber / Fără Facțiune"

class FactionType(str, Enum):
    DRACULESTI = "Drăculești"
    DANESTI = "Dănești"
    BOIERI_ARGESENI = "Boierii Argeșeni"
    SASI = "Sașii din Brașov/Sibiu"
    OTOMANI = "Otomanii Dunăreni"
    BOIERI_NOI = "Boierii Noi ai lui Vlad Țepeș"
    BOIERI_MOLDOVENI = "Mari Boieri Moldoveni"
    CRAIOVESTI = "Craiovești"
    SECUI = "Secuii"
    ROMANI_TRANSILVANENI = "Românii Transilvăneni"
    DOBROGENI = "Dobrogenii"
    MARGINIMEA = "Mărginimea Sibiului"
    MERCENARI = "Mercenarii Balcanici"
    NOBILI_TRANSILVANENI = "Nobilii transilvăneni"
    LIBER = "Liber / Fără Facțiune"

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
    character_class: Optional[CharacterClassType] = None
    faction: Optional[FactionType] = None
    
    # Attributes
    strength: int = 1      # Forță
    agility: int = 1       # Agilitate
    instinct: int = 1      # Instinct
    constitution: int = 1  # Constituție
    perception: int = 1    # Percepție
    intelligence: int = 1  # Inteligență
    charisma: int = 1      # Carismă
    culture: int = 1       # Cultură
    stealth: int = 1       # Furt/Stealth
    survival: int = 1      # Supraviețuire
    negotiation: int = 1   # Negociere
    archery: int = 1       # Tir cu arcul
    strategy: int = 1      # Strategie

    special_ability: Optional[str] = None
    passive_ability: Optional[str] = None
    game_mode: Optional[GameMode] = None
    current_episode: int = 0
    episode_progress: float = Field(ge=0.0, le=1.0, default=0.0) # 0.0 to 1.0 progress within current episode

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
    episode_progress: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Progresul curent în episod (0.0 - 1.0)")

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
