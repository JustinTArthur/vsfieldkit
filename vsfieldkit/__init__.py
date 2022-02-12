from vsfieldkit.deinterlacing import scan_interlaced
from vsfieldkit.util import (assume_bff, assume_progressive, assume_tff,
                             double, group_by_combed, group_by_field_order)
from vsfieldkit.types import (ChromaSubsampleScanning,
                              InterlacedScanPostProcessor)

VERSION = 0, 1, 0

SCAN_BLENDED = ChromaSubsampleScanning.SCAN_BLENDED
SCAN_LATEST = ChromaSubsampleScanning.SCAN_LATEST
SCAN_UPSAMPLED = ChromaSubsampleScanning.SCAN_UPSAMPLED

BLEND_VERTICALLY = InterlacedScanPostProcessor.BLEND_VERTICALLY
