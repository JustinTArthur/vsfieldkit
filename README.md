# vsfieldkit
Collection of functions for working with interlaced content in
[VapourSynth](http://www.vapoursynth.com/). Most functions don't have any 
external dependencies.

Included functions:  
`vsfieldkit.assume_bff(clip)`  
`vsfieldkit.assume_progressive(clip)`  
`vsfieldkit.assume_tff(clip)`  
`vsfieldkit.bob(clip)`  
`vsfieldkit.double(clip)`  
`vsfieldkit.fill_analog_frame_ends(clip)`
(requires FillBorders and either ContinuityFixer or EdgeFixer plugins)  
`vsfieldkit.group_by_combed(clip)`  
`vsfieldkit.group_by_field_order(clip)`  
`vsfieldkit.resample_as_progressive(clip)`  
`vsfieldkit.scan_interlaced(clip)`  
`vsfieldkit.upsample_as_progressive(clip)`

See [the documentation](https://vsfieldkit.justinarthur.com/) for more information.
