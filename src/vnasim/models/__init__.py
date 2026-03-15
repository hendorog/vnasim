"""VNA instrument models."""

from vnasim.models.sna5000 import SNA5000Model
from vnasim.models.keysight_ena import E5071BModel
from vnasim.models.keysight_e5080 import E5080Model
from vnasim.models.copper_mountain import CopperMountainModel
from vnasim.models.rs_znb import RSZNBModel
from vnasim.models.anritsu_shockline import AnritsuShockLineModel

MODEL_REGISTRY: dict[str, type] = {
    "sna5000": SNA5000Model,
    "e5071b": E5071BModel,
    "e5080": E5080Model,
    "copper_mountain": CopperMountainModel,
    "rs_znb": RSZNBModel,
    "anritsu_shockline": AnritsuShockLineModel,
}
