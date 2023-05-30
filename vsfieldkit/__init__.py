from vsfieldkit.deinterlacing import (bob, resample_as_progressive,
                                      upsample_as_progressive)
from vsfieldkit.interlacing import telecine, weave_fields
from vsfieldkit.output import output_frame_inferred_y4m
from vsfieldkit.repair import fill_analog_frame_ends
from vsfieldkit.sampling import resample_4fsc_as_bt601, resample_bt601_as_4fsc
from vsfieldkit.scanning import scan_interlaced
from vsfieldkit.types import (ChromaSubsampleScanning, Factor, FormatSpecifier,
                              InterlacedScanPostProcessor, PulldownPattern,
                              Resizer)
from vsfieldkit.util import (annotate_bobbed_fields, assume_bff,
                             assume_progressive, assume_tff, double,
                             group_by_combed, group_by_field_order)

VERSION = 2, 2, 0

SCAN_BLENDED = ChromaSubsampleScanning.SCAN_BLENDED
SCAN_LATEST = ChromaSubsampleScanning.SCAN_LATEST
SCAN_UPSAMPLED = ChromaSubsampleScanning.SCAN_UPSAMPLED

BLEND_VERTICALLY = InterlacedScanPostProcessor.BLEND_VERTICALLY

ADVANCED_PULLDOWN = PulldownPattern.ADVANCED_PULLDOWN
EURO_PULLDOWN = PulldownPattern.EURO_PULLDOWN
MATCHED_PULLDOWN = PulldownPattern.MATCHED_PULLDOWN
NTSC_FILM_PULLDOWN = PulldownPattern.NTSC_FILM_PULLDOWN
