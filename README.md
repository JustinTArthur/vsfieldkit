# vsfieldkit
Collection of functions for working with interlaced content in VapourSynth.

## Dependencies
Just VapourSynth. 

## Usage
### `assume_bff(clip: vs.VideoNode) -> vs.VideoNode`

### `assume_tff(clip: vs.VideoNode) -> vs.VideoNode`

### `double(clip: vs.VideoNode) -> vs.VideoNode`
Returns a clip where each original frame is repeated once and plays at
twice the speed so the played image matches the original in time.

Not specific to interlacing or deinterlacing, but useful for doubling
original interlaced pictures so they can be compared against doubled frame
output from a bob or phosphor deinterlacer.

Example:
```python
original = vsfieldkit.double(interlaced_clip)
deinterlaced = havsfunc.QTGMC(interlaced_clip, TFF=True)

analysis = vs.core.std.StackHorizontal((
    original,
    deinterlaced
))
analysis.set_output()
```

### `group_by_combed(clip: vs.VideoNode) -> Iterator[tuple[Optional[bool], vs.VideoNode]]`
Assuming the passed-in clip was processed by a filter that performs
comb detection, this splits the clip into segments based on whether they
are combed or not. The values it generates are `True`, `False`, or `None` if it
was marked combed, not combed, or not marked as well as the segment of the
clip.

Example:
```python
detelecined = tivtc.TFM(interlaced_clip, PP=1)

progressive_clips = []
for is_combed, segment in vsfieldkit.group_by_combed(detelecined):
    if is_combed:
        progressive_clips.append(havsfunc.QTGMC(segment, TFF=False))
    else:
        progressive_clips.append(tivtc.TDecimate(segment))

vs.core.std.Splice(progressive_clips).set_output()
```

### `group_by_field_order(clip: vs.VideoNode) -> Iterator[tuple[Optional[vs.FieldBased], vs.VideoNode]]`
Splits a clip up into segments as field order changes. The values it generates
are:
* Field order expressed as a `vapoursynth.FieldBased`
enumeration or `None` if field order is not applicable or not available.
* The sub-clip with that field order.

Example:
```python
progressive_clips = []
for field_based, segment in vsfieldkit.group_by_field_order(clip):
    if field_based == vs.FIELD_TOP:
        progressive_clips.append(havsfunc.QTGMC(segment, TFF=True))
    elif field_based == vs.FIELD_BOTTOM:
        progressive_clips.append(havsfunc.QTGMC(segment, TFF=False))
    elif field_based == vs.PROGRESSIVE:
        progressive_clips.append(vsfieldkit.double(segment))
vs.core.std.Splice(progressive_clips).set_output()
```