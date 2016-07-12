# Vine
©2016 IFeelBloated, Vine Python Module for VapourSynth

## License
LGPL v2.1

## Description
Vine is a collection of a non-local error based de-halo filter and a set of morphological filters.

## Requirements
- [KNLMeansCL](https://github.com/Khanattila/KNLMeansCL)
- [FloatFilters](https://github.com/IFeelBloated/FLT)
- [TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny)
- [FMTConv](https://github.com/EleonoreMizo/fmtconv)

## Function List
- Dehalo
- morphology.Dilation
- morphology.Erosion
- morphology.Closing
- morphology.Opening
- morphology.Gradient
- morphology.TopHat
- morphology.BlackHat

## Formats
- Bit Depth: 32bits floating point
- Color Space: Gray, RGB, YUV 4:4:4 (subsampled YUV formats are not supported)
- Scan Type: Progressive

## Notes
- Only Y will be processed when the input is YUV 4:4:4, UV will be simply copied from the input
- All 3 planes of R, G and B will be processed when the input is RGB
- **QUALITY (Dehalo)**: cutting edge
- **PERFORMANCE (Dehalo)**: pretty slow but practical

## Details
### Dehalo
Dehalo removes halo artifacts caused by over-sharpening or sinc-like resizers or stuff like that<br />

workflow:
- degraded(local mean/similarity window = 0) NLMeans filtering to kill halos from the video, it's not NLMeans technically, it weights on non-local errors instead of non-local means, which works ultra nice on halos
- a cutoff filter replaces low frequencies of the filtered clip with low frequencies from the source clip cuz halos are medium to high frequency artifacts apparently
- a threshold based limiter eliminates all small differences, halos are pretty big differences
- a modified canny detection masks out edges with a big possibility to have halos around
- masking halos out by doing morphological operations to the canny mask
- replace masked areas in the source clip with the filtered clip

```python
Dehalo (src, radius=[1, None], a=32, h=6.4, sigma=0.6, alpha=0.36, beta=32, thr=0.00390625, elast=None, cutoff=4, show=False)
```
- src<br />
  clip to be processed
- radius<br />
  radius of the halo mask, radius[0] is the exact radius and radius[1] is the peripheral(inflating) radius, default radius[1] = ceil(radius[0]/2)
