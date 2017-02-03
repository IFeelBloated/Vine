# Vine
©2017 IFeelBloated, Vine Python Module for VapourSynth

## License
LGPL v3.0

## Description
Vine is a collection of a pixel matching based de-halo filter and a set of morphological filters.

## Requirements
- [KNLMeansCL](https://github.com/Khanattila/KNLMeansCL)
- [TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny)
- [FMTConv](https://github.com/EleonoreMizo/fmtconv)
- [NNEDI3](https://github.com/dubhater/vapoursynth-nnedi3)

## Function List
- Dehalo
- Dilation
- Erosion
- Closing
- Opening
- Gradient
- TopHat
- BlackHat

## Formats
- Bit Depth: 32bits floating point
- Color Space: Gray, RGB, YUV4XXPS
- Scan Type: Progressive

## Notes
- Only Y will be processed when the input is YUV, UV will be simply copied from the input
- All 3 planes of R, G and B will be processed when the input is RGB
- **QUALITY (Dehalo)**: cutting edge
- **PERFORMANCE (Dehalo)**: pretty slow but practical

## Details
### Dehalo
Dehalo removes halo artifacts caused by over-sharpening or sinc-like resizers or stuff like that<br />

workflow:
- apply a degraded (local mean/similarity window = 0) NLMeans filter to kill halos, it's not NLMeans technically, it weights on the error between 2 pixels instead of SSE between 2 blocks, which works ultra nice on halos
- like the classic aliasing (nearest neighbor) and ringing (sinc) trade-off, non-local errors filtering annihilates halos and brings aliasing, so do it again with supersampling and clean the aliasing mess, the supersampled result will be blended with the result before supersampling, weight is determined by the "sharp" parameter
- a cutoff filter replaces low frequencies of the filtered clip with low frequencies from the source clip since halos are medium to high frequency artifacts apparently
- non-local errors might distort high frequency components since it does not make use of the neighborhood at all, especially with a large "h", so do an actual NLMeans here to refine high frequencies and therefore remove artifacts caused by non-local errors
- a modified canny detection masks out edges with a big possibility to have halos around
- mask halos out by doing morphological operations to the canny mask
- replace masked areas in the source clip with the filtered clip

```python
Dehalo(src, radius=[1, None], a=32, h=6.4, sharp=1.0, sigma=0.6, alpha=0.36, beta=32, cutoff=4, masking=True, show=False)
```
- src<br />
  clip to be processed
- radius<br />
  radius of the halo mask, radius[0] is the exact radius and radius[1] is the peripheral (inflating) radius, default radius[1] = ceil(radius[0]/2)
- a<br />
  window size of the non-local errors filtering, greater value = higher quality and lower performance
- h<br />
  strength of the non-local errors filtering, greater value = more intense processing
- sharp<br />
  resampling sharpness of the anti-aliasing process, also related to the blending process mentioned above, blending weight = *constant* * sharp * ln(1 + 1 / (*constant* * sharp)), the mathematical limit for weight is 0 (simply returns the resampled result) as sharp goes infinitely close to 0, or 1 (simply returns the clip before resampling) as sharp goes towards infinity
- sigma<br />
  refer to TCanny doc for more details
- alpha, beta<br />
  so halos occur at fairly sharp transitions, and we want weak and insignificant edges that got no or little halos around gone, and that we should re-scale the gradient of the canny mask, and these 2 parameters are related to that process, say *x* is the value of some pixel in the mask and it will be scaled to *(x + alpha)^beta-alpha^beta*, basically any value < *1-alpha* will be close to 0 after that, so larger alpha = more edges
- cutoff<br />
  strength of the cutoff filter, ranges from 0 (no low frequency protection) to 100 (almost no filtering)
- masking<br />
  set it False and get a raw output with no mask protection, for very large radius halos
- show<br />
  set it True and output will be the halo mask, for debugging and stuff

###morphology filters
```python
Dilation/Erosion/Closing/Opening/Gradient/TopHat/BlackHat(src, radius=1)
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
clip = Vine.Gradient(clip)
```
![](http://i.imgur.com/oFoI3dc.png)
![](http://i.imgur.com/Acc4nt4.png)
- typical halo<br />
```python
clip = Vine.Dehalo(clip, [1, None], sigma=1.5, alpha=0.06, h=18.2)
```
![](http://i.imgur.com/tWQ2Fka.png)
![](http://i.imgur.com/Rqq2M3m.png)
<br />
*zoomed to 400%*<br />
*click the image and view at full size*<br />
![](http://i.imgur.com/i8Tac1a.png)
- analog video kind of severe and gross halo<br />
```python
clip = Vine.Dehalo(clip, [2, 2], sigma=1.6, alpha=0.18, h=24, sharp=0.5, cutoff=2)
clip = Vine.Dehalo(clip, [2, 2], sigma=2.2, alpha=0.18, h=64, sharp=0.5, cutoff=2)
```
![](http://i.imgur.com/6rYBsz7.png)
![](http://i.imgur.com/BqgFu3N.png)
