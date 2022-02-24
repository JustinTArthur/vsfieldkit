scan_interlaced Deep Dive
=========================
:py:func:`~vsfieldkit.scan_interlaced` can be thought of as a converter between
storage/transport interlacing and display interlacing (a process sometimes
called scanning). The process is detailed below.

Interlacing for Storage/Transport
---------------------------------
When captured moments from a camera are stored, two moments' footage are laced
into eachother in a single frame or picture, so in European video systems, this
usually means 50 moments captured in a second are interlaced onto 25
frames\ [#other_territories]_\. These 25
frames could then be transported over HDTV broadcast or on a DVD and it's up to
the playback system how to present those 50 moments.


Interlacing for Display
-----------------------
Playback systems like your DVD player and television have a few choices when
they play back content that is stored or transported interlaced. Usually
the choices are:

Inverse Telecine or Field-matching
    Identify content originally captured as progressive frames at a slower pace
    than the rate of field moments, stretched out over interlaced fields to fit
    an interlaced medium. For example, playing back a DVD of a movie filmed at
    24 film-frames-per-second.

Deinterlacing
    Extract an interlaced field and construct a new frame for that moment
    using that field and optionally information from the fields stored for
    previous and next moments. These new frames can be displayed at the
    original field rate or the moments could be halved and the new frames would
    be displayed at the stored frame rate (half the field rate).

Interlacing-naive Progressive Scan
    Take the interlaced frame and send it to a progressive scan display as-is.
    If the original footage was captured at the interlaced frame rate, you'll
    lose the notion of the smooth motion of moving objects and the comb effect
    will be obvious to the viewer. If the playback mechanism doesn't even read
    interlaced color patterns from the picture, the combing effect will be
    thicker and colors could be displayed in the wrong rows.

    Content originally captured progressively and stored interlaced might
    appear uncombed to the viewer if the top and bottom fields of the same
    moment in time are stored in the same frame, occasionally repeated.

Interlaced Scan
    Extract an interlaced field and paint it onto the display with the same
    alternating lines it was stored with in that same position then extract
    the next interlaced field from the stored frame and paint it onto its
    corresponding lines at the relative moment in time it was captured at. The
    previously-painted lines might have begun to fade away during this new
    moment depending on the display technology.

If a video playback system is incapable of interlaced scan, it could instead be
fed progressive frames that represent the states of an interlaced scan display.
It is these kinds of frames that :py:func:`vsfieldkit.scan_interlaced` helps
produce.

.. note::
    To display interlaced footage scanned to progressive frames with
    :py:func:`vsfieldkit.scan_interlaced`\, the display device would need to
    support progressive scan at the original field rate (e.g. at 50 Hz or
    59.94-ish Hz) and you would need a means of transporting this footage, such
    as high speed HDMI or DisplayPort from a computer, or a USB drive plugged
    into an HDTV/UHD TV capable of aligning its refresh rate to the frame rate
    of content in its media player app.

Properties of Interlaced Scan Display
-------------------------------------
The viewer will perceive motion as smooth, but may either notice a comb
effect while two moments' fields remain painted in their respective lines
or may notice the fading of the previous moment's lines. If you grew up
with this form of display and rarely witnessed alternatives, it might
appear quite natural.

Why is interlaced tech still used in Modern Times?
--------------------------------------------------
It's the only way to transport high-frame-rate material to the home.
Modern digital theatre systems are now capable of receiving 48 progressive
fps content, but home entertainment systems don't have a standard way to take
in progressive 48 fps, 50 fps, or 60 fps material from the studio. If you wish
to convey smooth motion of events that were captured or rendered in high speed,
you can still do one of these at 50 or :math:`\frac{60000}{1001}` interlaced
fields per second:

* Put it on a DVD as 480i or 576i
* Put it on a Blu-ray as 480i, 576i, or 1080i
* Send a 1080i signal over HDTV broadcast tech.
* Send 1080i over proprietary digital cable or satellite channels.

When you do that, you're losing half of the vertical resolution you could be
using with the slower progressive formats and you have no idea how the end
viewer's home entertainment system will portray the footage you transport
as interlaced.

People making content are ready for high speed progressive options. Those
options just aren't there yet, so the above methods are still used to
transport high frame rate material, mostly for sports events, but occasionally
for concert footage and adult entertainment. Pushes by Peter Jackson and James
Cameron to open the doors for high speed progressive transport may also make
its way to the home for cinema, especially for 3D, where smooth motion helps
avoid nausea of the viewer.

Why Use :py:func:`~vsfieldkit.scan_interlaced` in Modern Times?
---------------------------------------------------------------
Bob deinterlacers like QTGMC and Yadif have features like motion interpolation
of neighbouring moments' fields to supplement image data presented in the
generated frames. This results in more detail per moment than ever before,
better capturing the original reality or intentions of the capture. So, you
may ask yourself why you would step backward in time and use
interlaced scan for display when QTGMC or Yadif paint a prettier picture with
no obvious comb effect.

Here are the biggest reasons you might want to:

Academia
    You might wish to demonstrate the evolution of video technology to a film
    class, but only have a progressive display system.
Lossless Display
    You may wish to ensure that every stored pixel has its time on display
    without any of the guessing, aligning, or blending a modern deinterlacer
    might perform. With :py:func:`vsfieldkit.scan_interlaced` this is achieved
    while maintaining smooth motion of natively deinterlaced footage.
Blend of Motion
    A bob deinterlacer can generate smooth motion from original interlaced
    fields if the final framerate isn't halved. However, you are often still
    placing an object in different places in different moments and if the
    object is filmed sharply with minimal shutter blur or is
    rendered/drawn/animated, the viewer could still have a jagged perception
    of the movement. Because interlaced scan results in remnants of the prior
    moment as the new moment is drawn, the net effect can be even smoother.
If it was the content producer's intended playback
    Rarely does a filmmaker think to themselves that interlacing is great and
    they want to work with it more; it's usually the opposite. However,
    should that moment arise, perhaps wanting to give a found-footage horror
    film the lo-fi reality feel that fits, you're covered.


Chances are, whatever modern equipment you'd normally play back interlaced
material on will deinterlace that content and play a progressive
representation. You could find the amount of moments presented are cut in half.

True interlaced scan could be done with an old CRT TV and means to transport
interlaced content to the TV or you could process interlaced content with
:py:func:`vsfieldkit.scan_interlaced` to prepare video that is displayed on
a progressive scan system in the same way it would in an interlaced scan
system.

.. rubric:: Footnotes

.. [#other_territories] :math:`\frac{60000}{1001}` or
    :math:`59.\overline{940059}` captured moments per second interlaced onto
    :math:`\frac{30000}{1001}` or :math:`29.\overline{970029}` frames
    per second in North America, some of South America, Liberia, Myanmar,
    South Korea, Taiwan, Philippines, Japan, and some Pacific Islands nations
    and territories.
