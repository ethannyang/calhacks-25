"""
Build Tracker - Tracks recommended item builds and monitors gold for next item
Uses live game data to recommend champion-specific builds based on matchup and team comp
"""

from typing import Optional, Dict, List
from loguru import logger


class ItemBuild:
    """Represents a recommended item build path"""
    def __init__(self, item_name: str, item_id: int, total_cost: int, components: List[Dict]):
        self.item_name = item_name
        self.item_id = item_id
        self.total_cost = total_cost
        self.components = components  # List of component items with costs

    def get_next_purchase(self, current_gold: int) -> Optional[Dict]:
        """Get the next item component the player should buy"""
        # Sort components by cost (buy cheaper components first usually)
        sorted_components = sorted(self.components, key=lambda x: x['cost'])

        for component in sorted_components:
            if current_gold >= component['cost']:
                return {
                    'name': component['name'],
                    'cost': component['cost'],
                    'can_afford': True
                }

        # If can't afford anything, return cheapest component
        if sorted_components:
            cheapest = sorted_components[0]
            return {
                'name': cheapest['name'],
                'cost': cheapest['cost'],
                'can_afford': False,
                'gold_needed': cheapest['cost'] - current_gold
            }

        return None


class BuildTracker:
    """Tracks champion-specific builds and monitors progress"""

    def __init__(self, item_data: Dict):
        """
        Initialize with Riot API item data
        item_data: Data from Data Dragon items.json
        """
        self.item_data = item_data
        self.items_by_id = {}
        self.items_by_name = {}

        # Parse item data
        if item_data and 'data' in item_data:
            for item_key, item_info in item_data['data'].items():
                item_id = int(item_info.get('id', 0))
                item_name = item_info.get('name', '')
                self.items_by_id[item_id] = item_info
                self.items_by_name[item_name.lower()] = item_info

        logger.info(f"BuildTracker initialized with {len(self.items_by_id)} items")

        # Champion-specific build paths (core first items)
        # Format: champion -> {role -> [item_builds]}
        self.champion_builds = self._initialize_champion_builds()

        # Current recommended build path for the player
        self.current_build: Optional[List[ItemBuild]] = None
        self.completed_items: List[int] = []

    def _initialize_champion_builds(self) -> Dict:
        """Initialize common champion build paths"""
        # Simplified build recommendations - in production, this would be from a database or API
        return {
            'garen': {
                'top': ['Stridebreaker', 'Plated Steelcaps', 'Black Cleaver', 'Dead Man\'s Plate'],
                'mid': ['Stridebreaker', 'Mercury\'s Treads', 'Black Cleaver', 'Force of Nature']
            },
            'darius': {
                'top': ['Stridebreaker', 'Plated Steelcaps', 'Dead Man\'s Plate', 'Sterak\'s Gage'],
            },
            'jinx': {
                'adc': ['Kraken Slayer', 'Berserker\'s Greaves', 'Runaan\'s Hurricane', 'Infinity Edge']
            },
            'lux': {
                'mid': ['Luden\'s Companion', 'Sorcerer\'s Shoes', 'Shadowflame', 'Rabadon\'s Deathcap'],
                'support': ['Imperial Mandate', 'Ionian Boots of Lucidity', 'Staff of Flowing Water']
            },
            'yasuo': {
                'mid': ['Immortal Shieldbow', 'Berserker\'s Greaves', 'Infinity Edge', 'Death\'s Dance'],
                'top': ['Immortal Shieldbow', 'Berserker\'s Greaves', 'Blade of the Ruined King']
            },
            'vi': {
                'jungle': ['Trinity Force', 'Plated Steelcaps', 'Black Cleaver', 'Dead Man\'s Plate']
            },
            'thresh': {
                'support': ['Zeke\'s Convergence', 'Mobility Boots', 'Knight\'s Vow', 'Redemption']
            }
        }

    def _get_item_info(self, item_name: str) -> Optional[Dict]:
        """Get item info from Data Dragon by name"""
        return self.items_by_name.get(item_name.lower())

    def _build_item_object(self, item_name: str) -> Optional[ItemBuild]:
        """Build an ItemBuild object from item name"""
        item_info = self._get_item_info(item_name)
        if not item_info:
            logger.warning(f"Item not found: {item_name}")
            return None

        item_id = int(item_info.get('id', 0))
        total_cost = item_info.get('gold', {}).get('total', 0)

        # Get component items
        components = []
        component_ids = item_info.get('from', [])
        for comp_id_str in component_ids:
            comp_id = int(comp_id_str)
            if comp_id in self.items_by_id:
                comp_info = self.items_by_id[comp_id]
                components.append({
                    'id': comp_id,
                    'name': comp_info.get('name', ''),
                    'cost': comp_info.get('gold', {}).get('total', 0)
                })

        return ItemBuild(item_name, item_id, total_cost, components)

    def set_build_path(self, champion: str, role: str, enemy_champion: Optional[str] = None,
                       enemy_team_comp: Optional[Dict] = None):
        """
        Set the recommended build path for a champion

        Args:
            champion: Player's champion name (lowercase)
            role: Player's role (top, mid, jungle, adc, support)
            enemy_champion: Lane opponent champion (for matchup-specific builds)
            enemy_team_comp: Enemy team composition analysis (for defensive items)
        """
        champion = champion.lower()

        # Get base build path for champion
        if champion not in self.champion_builds:
            logger.warning(f"No build path defined for {champion}")
            return

        role_builds = self.champion_builds[champion]
        if role not in role_builds:
            # Fallback to first available role
            role = list(role_builds.keys())[0]
            logger.info(f"Using fallback role {role} for {champion}")

        item_names = role_builds[role]

        # Build ItemBuild objects
        self.current_build = []
        for item_name in item_names:
            item_build = self._build_item_object(item_name)
            if item_build:
                self.current_build.append(item_build)

        logger.info(f"📋 Build path set for {champion} ({role}): {' → '.join(item_names)}")

        # TODO: Adjust build based on enemy_champion and enemy_team_comp
        # Example: If enemy has 3+ AP champions, prioritize magic resist
        # Example: If facing enemy_champion like Darius, rush anti-heal

    def get_next_item_recommendation(self, current_gold: int, completed_items: Optional[List[int]] = None) -> Optional[Dict]:
        """
        Get recommendation for next item to buy

        Returns:
            {
                'item_name': str,
                'item_cost': int,
                'next_component': str,
                'component_cost': int,
                'can_afford_component': bool,
                'gold_needed': int (if can't afford),
                'progress': str (e.g., "1/3 components")
            }
        """
        if not self.current_build:
            return None

        if completed_items:
            self.completed_items = completed_items

        # Find next uncompleted item in build path
        for item_build in self.current_build:
            if item_build.item_id not in self.completed_items:
                # This is the next item to work towards
                next_purchase = item_build.get_next_purchase(current_gold)

                if next_purchase:
                    components_count = len(item_build.components)
                    return {
                        'item_name': item_build.item_name,
                        'item_cost': item_build.total_cost,
                        'next_component': next_purchase['name'],
                        'component_cost': next_purchase['cost'],
                        'can_afford_component': next_purchase.get('can_afford', False),
                        'gold_needed': next_purchase.get('gold_needed', 0),
                        'progress': f"Building {item_build.item_name}",
                        'total_gold_needed': item_build.total_cost
                    }

        # All items completed
        return None

    def should_recall_for_item(self, current_gold: int, in_base: bool = False) -> Optional[Dict]:
        """
        Determine if player should recall to buy next item component

        Returns recommendation with HIGH priority if gold threshold met
        """
        if in_base:
            return None  # Already in base

        recommendation = self.get_next_item_recommendation(current_gold)
        if not recommendation:
            return None

        # Recall thresholds
        component_cost = recommendation['component_cost']
        can_afford = recommendation['can_afford_component']

        # HIGH priority recall: Can afford significant component
        if can_afford and component_cost >= 800:
            return {
                'priority': 'high',
                'reason': f"Can afford {recommendation['next_component']}",
                'message': f"RECALL: Buy {recommendation['next_component']} ({component_cost}g)",
                'gold': current_gold,
                'item_info': recommendation
            }

        # MEDIUM priority: Close to affording important component (within 150g)
        gold_needed = recommendation.get('gold_needed', 0)
        if 0 < gold_needed <= 150 and component_cost >= 800:
            return {
                'priority': 'medium',
                'reason': f"Almost have {recommendation['next_component']}",
                'message': f"Farm {gold_needed}g more for {recommendation['next_component']}",
                'gold': current_gold,
                'item_info': recommendation
            }

        return None

    def get_build_progress_summary(self, current_gold: int) -> str:
        """Get a summary of build progress for logging/display"""
        if not self.current_build:
            return "No build path set"

        completed = len(self.completed_items)
        total = len(self.current_build)
        next_rec = self.get_next_item_recommendation(current_gold)

        if next_rec:
            return f"Items: {completed}/{total} | Next: {next_rec['next_component']} ({next_rec['component_cost']}g)"
        else:
            return f"Build complete: {completed}/{total} items"
