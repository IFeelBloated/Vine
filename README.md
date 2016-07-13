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
- a<br />
  window size of the non-local error filtering, greater value = higher quality and lower performance
- h<br />
  strength of the non-local error filtering, greater value = more intense processing
- sigma<br />
  refer to TCanny doc for more details
- alpha, beta<br />
  so halos occur at fairly sharp transitions, and we want weak and insignificant edges that got no or little halos around gone, and that we should re-scale the gradient of the canny mask, and these 2 parameters are related to that process, say *x* is the value of some pixel in the mask and it will be scaled to *(x + alpha)^beta-alpha^beta*, basically any value < *1-alpha* will be close to 0 after that, so larger alpha = more edges
- thr<br />
  threshold of the limiter, ranges from 0.0 (no limit) to 1.0 (no filtering), differences between the filtered clip and the source clip < thr will be discarded, otherwise remain unaffected.
- elast<br />
  elasticity of the threshold, ranges from 0.0 to thr.
- cutoff<br />
  strength of the cutoff filter, ranges from 0(no low frequency protection) to 100(almost no filtering)
- show<br>
  set it True and output will be the halo mask, for debugging and stuff

###morphology class
```python
morphology.Dilation/Erosion/Closing/Opening/Gradient/TopHat/BlackHat (src, radius=1)
```
- [Dilation](https://en.wikipedia.org/wiki/Dilation_(morphology))
- [Erosion](https://en.wikipedia.org/wiki/Erosion_(morphology))
- [Closing](https://en.wikipedia.org/wiki/Closing_(morphology))
- [Opening](https://en.wikipedia.org/wiki/Opening_(morphology))
- [Gradient](https://en.wikipedia.org/wiki/Morphological_gradient)
- [Top Hat and Black Hat](https://en.wikipedia.org/wiki/Top-hat_transform)

## Demos
- Do a morphological gradient operation and get a simple edge mask<br />
```python
clp = Vine.morphology.Gradient (clp)
```
![](http://i.imgur.com/KZ8NimG.png)
![](http://i.imgur.com/iVQZWdQ.png)
- typical halo<br />
```python
clp = Vine.Dehalo (clp, [2, None], h=9.6)
```
![](http://i.imgur.com/iahMByU.png)
![](http://i.imgur.com/OW4CG8t.png)
*zoomed to 400%*
![](http://i.imgur.com/2ugJL70.png)
