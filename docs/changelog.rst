Changelog
=========
Next Version
------------
* :py:func:`vsfieldkit.bob` is deprecated in VapourSynth R58+ in favor of
  core.std.Bob.

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
