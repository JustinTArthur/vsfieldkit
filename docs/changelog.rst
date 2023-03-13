Changelog
=========
2.0.0
-----
New Features
^^^^^^^^^^^^
* Interlacing! Targeting deinterlacer testers and engineers in the broadcast
  space who've been instructed to avoid soft telecine. Two new functions:

  * :py:func:`vsfieldkit.telecine`
  * :py:func:`vsfieldkit.weave_fields`

* [Re]sampling kernels to supplement the out of the box vapoursynth.resize
  functions, but specialized for vsfieldkit tasks. They can be found in the
  :py:mod:`vsfieldkit.kernels` module. Includes an nnedi3 kernel-maker for use
  as a chroma upsampler.

* :py:func:`vsfieldkit.annotate_bobbed_fields` for retro-actively adding a
  property to bobbed frames noting the field (top or bottom) they came from.

* :py:func:`vsfieldkit.output_frame_inferred_y4m` for outputting yuv4mpeg2
  (y4m) data with metadata derived from the first frame's properties, allowing
  for interlaced output, SAR, and chroma siting as available.

Changed APIs
^^^^^^^^^^^^

* :py:func:`vsfieldkit.resample_as_progressive` ``kernel`` argument renamed
  to ``subsampling_kernel`` for clarity. ``upsampling_kernel`` argument added.
  It also now fakes luma-co-sited chroma during upsampling to avoid lossy
  chroma re-siting.
* :py:func:`vsfieldkit.resample_as_progressive` and
  :py:func:`vsfieldkit.upsample_as_progressive` now default to Spline 36 for
  any chroma subsampling or upsampling using the new 
  :py:func:`vsfieldkit.kernels.resample_chroma_with_spline36` .
* :py:func:`vsfieldkit.upsample_as_progressive` now has
  ``upsample_horizontally`` argument. Defaults to ``False``.
  :py:func:`vsfieldkit.resample_as_progressive` uses this as ``True``
  internally.

1.1.0
-----
* :py:func:`vsfieldkit.fill_analog_frame_ends` allows overriding the pre-fill
  mode and gives better error messaging when the fillborders plugin is missing
  the requested mode. The default mode is now ``"fillmargins"`` instead of
  ``"fixborders"`` in order to work with the release version of fillborders.
* :py:func:`vsfieldkit.fill_analog_frame_ends` works with progressive clips
  cropped by factors smaller than interlaced subsampling.
* :py:func:`vsfieldkit.fill_analog_frame_ends` more compatible with code
  autocompletion via removal of decorators.
* :py:func:`vsfieldkit.scan_interlaced` can brighten newly-scanned fields via
  new ``attack_factor`` argument.

1.0.2
-----
* :py:func:`vsfieldkit.fill_analog_frame_ends` will now look for EdgeFixer
  plugin first, followed by ContinuityFixer plugin as before. Having one of the
  two plugins is required.

1.0.1
-----
* Adds :py:func:`vsfieldkit.fill_analog_frame_ends` for cleaning the half-line
  black bars at the top and bottom of analog video.

Output Change:

* :py:func:`vsfieldkit.bob` now defaults to shifting according to the field's
  position. Feature added for completion, but it's also deprecated in favor of
  :py:func:`resize.Bob` in VapourSynth R58+.

Version 1.0.0 was yanked for an immediate bug fix.

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
