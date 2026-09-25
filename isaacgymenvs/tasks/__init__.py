from .artgrasp import ArtGrasp
from .artmanip import ArtManip
from .wuji_demo_aligned import WujiDemoAligned
from .wuji_acquisition import WujiAcquisition
from .wuji_timed_acquisition import WujiTimedAcquisition
from .wuji_variable_timed_acquisition import WujiVariableTimedAcquisition
from .wuji_functional_hemisphere import WujiFunctionalHemisphere
from .wuji_bridge_hemisphere import WujiBridgeHemisphere
from .wuji_bridge3_hemisphere import WujiBridge3Hemisphere
from .wuji_bridge3_controller_state import WujiBridge3ControllerState

isaacgym_task_map = {
    "artgrasp": ArtGrasp,
    "artmanip": ArtManip,
    "wuji_demo_aligned": WujiDemoAligned,
    "wuji_acquisition": WujiAcquisition,
    "wuji_timed_acquisition": WujiTimedAcquisition,
    "wuji_variable_timed_acquisition": WujiVariableTimedAcquisition,
    "wuji_functional_hemisphere": WujiFunctionalHemisphere,
    "wuji_bridge_hemisphere": WujiBridgeHemisphere,
    "wuji_bridge3_hemisphere": WujiBridge3Hemisphere,
    "wuji_bridge3_controller_state": WujiBridge3ControllerState,
}
