from enum import Enum


class ChromaSubsampleScanning(Enum):
    SCAN_BLENDED = 'SCAN_BLENDED'
    """Internally, original field chroma is upsampled to have single line
    color. The final image is then resampled to the original subsampling
    format, causing each line's color to be blended with its neighbours."""

    SCAN_LATEST = 'SCAN_LATEST'
    """The field that is new in a frame supplies the color for all lines of
    that frame."""

    SCAN_UPSAMPLED = 'SCAN_UPSAMPLED'
    """Returns a clip upsampled to have single line color. For example, if
    YUV420P8 clip was scanned, the resulting clip would be in YUV422P8
    ensure the original colors from each line's source are maintained."""


class InterlacedScanPostProcessor(Enum):
    BLEND_VERTICALLY = 'BLEND_VERTICALLY'
