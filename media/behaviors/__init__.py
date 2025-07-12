# inference_service/behaviors/__init__.py (Standalone with SQLite)

# Import necessary behavior classes
from behaviors.base_behavior import BaseBehavior
from behaviors.zhoujieruqin import ZhouJieRuQinBehavior
from behaviors.renshutongji import RenShuTongJiBehavior
from behaviors.insulator import InsulatorBehavior

# Map behavior codes (strings used in API requests) to their corresponding Behavior classes.
# Add new behaviors to this dictionary.
BEHAVIOR_MAP = {
    "ZHOUJIERUQIN": ZhouJieRuQinBehavior,
    "RENSHUTONGJI": RenShuTongJiBehavior,
    'INSULATOR': InsulatorBehavior,
    # Add other behaviors here:
    # "NEW_BEHAVIOR_CODE": NewBehaviorClass,
}

# Function to get a behavior handler instance
def get_behavior_handler(behavior_code: str, control_code: str) -> BaseBehavior | None:
    """
    Returns an instance of the behavior handler for the given behavior code.

    Args:
        behavior_code (str): The code identifying the behavior.
        control_code (str): The unique code for the control instance.

    Returns:
        BaseBehavior | None: An instance of the behavior handler, or None if the
                             behavior code is not found in the map.
    """
    BehaviorClass = BEHAVIOR_MAP.get(behavior_code)
    if BehaviorClass:
        return BehaviorClass(control_code)
    return None

