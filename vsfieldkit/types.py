from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Union


class ChromaSubsampleScanning(Enum):
    SCAN_BLENDED = 'SCAN_BLENDED'
    """Internally, original field chroma is upsampled to have single line
    color. The final image is then resampled to the original subsampling
    format, causing each line's color to be blended with its neighbours.
    Currently the blending is performed *after* post-processing to allow
    post-processors access to the upsampled chroma data.
    """

    SCAN_LATEST = 'SCAN_LATEST'
    """The field that is new in a frame supplies the color for all lines of
    that frame."""

    SCAN_UPSAMPLED = 'SCAN_UPSAMPLED'
    """Returns a clip upsampled to have single line color. For example, if
    YUV420P8 clip was scanned, the resulting clip would be in YUV422P8
    ensure the original colors from each line's source are maintained."""


class InterlacedScanPostProcessor(Enum):
    BLEND_VERTICALLY = 'BLEND_VERTICALLY'
    """Blends the entire contents vertically to remove comb lines. You
    effectively lose close to half of the vertical detail as a side effect."""


Factor = Union[int, float, Decimal, Fraction]
