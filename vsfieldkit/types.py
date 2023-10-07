from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Callable, Union

from vapoursynth import PresetVideoFormat, VideoFormat, VideoNode

Factor = Union[int, float, Decimal, Fraction]

FormatSpecifier = Union[PresetVideoFormat, VideoFormat, VideoNode, int]

Resizer = Callable[..., VideoNode]
"""A function following the same signature as VapourSynth's built in
resize/resample kernels."""


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


class PulldownPattern(Enum):
    """Commonly found pulldown pattern."""

    ADVANCED_PULLDOWN = '2:3:3:2'
    """For 24000/1001p to 60000/1001i where no field-matching is needed
    in IVTC because the only "dirty" frames can be decimated."""

    EURO_PULLDOWN = '2:2:2:2:2:2:2:2:2:2:2:3'
    """For 24p to 50i with no speed-up or speed-down required."""

    MATCHED_PULLDOWN = '2'
    """Each progressive frame is laid out on an interlaced frame."""

    NTSC_FILM_PULLDOWN = '2:3:2:3'
    """For 24000/1001p to 60000/1001i with the least amount of judder.
    """
