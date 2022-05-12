Changelog
=========
1.0.1
------------
* Fixes :py:func:`vsfieldkit.fill_analog_frame_ends` blank widths of ``0`` to
  support leaving an edge unrepaired.

1.0.0
------------
* Adds :py:func:`vsfieldkit.fill_analog_frame_ends` for cleaning the half-line
  black bars at the top and bottom of analog video.

Output Change:

* :py:func:`vsfieldkit.bob` now defaults to shifting according to the field's
  position. Feature added for completion, but it's also deprecated
  in favor of :py:func:`resize.Bob` in VapourSynth R58+.

0.3.0
-----
* New functions for re-interpreting progressive frames with interlaced sub-sampled chroma:

  * :py:func:`vsfieldkit.resample_as_progressive`
  * :py:func:`vsfieldkit.upsample_as_progressive`

* Adds phosphor decay simulation for :py:func:`vsfieldkit.scan_interlaced`


0.2.0
-----
Adds :py:func:`vsfieldkit.bob` deinterlacer.

0.1.0
-----
First release. :py:func:`vsfieldkit.scan_interlaced` and some nifty utilities.
