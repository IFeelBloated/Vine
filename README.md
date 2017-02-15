# Vine
©2017 IFeelBloated, Vine Python Module for VapourSynth

## License
LGPL v3.0

## Description
Vine is a collection of a block/pixel matching based de-halo filter and a set of morphological filters.

## Requirements
- [KNLMeansCL](https://github.com/Khanattila/KNLMeansCL)
- [BM3D](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-BM3D)
- [TCanny](https://github.com/HomeOfVapourSynthEvolution/VapourSynth-TCanny)
- [FMTConv](https://github.com/EleonoreMizo/fmtconv)
- [MVTools (floating point ver)](https://github.com/IFeelBloated/vapoursynth-mvtools-sf/tree/master)
- [NNEDI3](https://github.com/dubhater/vapoursynth-nnedi3)

## Function List
### De-halo Filters
- Super
- Basic
- Final

### Morphological Filters
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
- RGB input will be converted to an opponent color space(YUV alike) and only luma will be processed
- **NO** scene change policy provided, take [Wobbly](https://github.com/dubhater/Wobbly) and cut each scene out and process them individually
- **QUALITY (Dehalo)**: cutting edge
- **PERFORMANCE (Dehalo)**: pretty slow but practical

## Details
### Dehalo Filters
Dehalo removes halo artifacts caused by over-sharpening or sinc-like resizers or stuff like that<br />
#### Super
Optional, it helps improve the precision of sub-pixel motion estimation and compensation, use it and get a quality boost or don't and get a performance boost
```python
Super(src, pel=4)
```
- src<br />
  clip to be processed
- pel<br />
  sub-pixel precision, could be 2 or 4, 2 = precision by half a pixel, 4 = precision by quarter a pixel.

#### Basic
The basic estimation does a Non-Local Errors filtering to remove all visible halos.

workflow:
- apply a degraded (local mean/similarity window = 0) NLMeans filter to kill halos, it's not NLMeans technically, it weights on the error between 2 pixels instead of SSE between 2 blocks, which works ultra nice on halos
- like the classic aliasing (nearest neighbor) and ringing (sinc) trade-off, non-local errors filtering annihilates halos and brings aliasing, so do it again with supersampling and clean the aliasing mess, the supersampled result will be blended with the result before supersampling, weight is determined by the "sharp" parameter
- a cutoff filter replaces low frequencies of the filtered clip with low frequencies from the source clip since halos are medium to high frequency artifacts apparently
- non-local errors might distort high frequency components since it does not make use of the neighborhood at all, especially with a large "h", so do an actual NLMeans here to refine high frequencies and therefore remove artifacts caused by non-local errors

```python
Basic(src, a=32, h=6.4, sharp=1.0, cutoff=4)
```
- src<br />
  clip to be processed
- a<br />
  window size of the non-local errors filtering, greater value = higher quality and lower performance
- h<br />
  strength of the non-local errors filtering, greater value = more intense processing
- sharp<br />
  resampling sharpness of the anti-aliasing process, also related to the blending process mentioned above, blending weight = *constant* * sharp * ln(1 + 1 / (*constant* * sharp)), the mathematical limit for weight is 0 (simply returns the resampled result) as sharp goes infinitely close to 0, or 1 (simply returns the clip before resampling) as sharp goes towards infinity
- cutoff<br />
  strength of the cutoff filter, ranges from 0 (no low frequency protection) to 100 (almost no filtering)

#### Final
The final estimation refines the basic estimation with motion compensation and outputs the final result

workflow:
- refine the basic estimation with motion compensation
- apply a modified canny detection to mask out edges with a big possibility to have halos around
- mask halos out by doing morphological operations to the canny mask
- replace masked areas in the source clip with the filtered clip

```python
Final(src, super=[None, None], radius=[6, 1, None], pel=4, sad=400.0, sigma=0.6, alpha=0.36, beta=32.0, masking=True, show=False)
```
- super<br />
  optional, clips generated by Vine.Super
- radius<br />
  radius[0]: temporal radius of the motion compensation, frames that fall in [current frame - radius, current frame + radius] will be referenced<br />
  radius[1]: exact radius of the halo mask<br />
  radius[2]: peripheral(inflating) radius of the halo mask, default radius[2] = ceil(radius[1] / 2)
- sad<br />
  SAD threshold of the motion compensation, refer to MVTools doc for more details
- sigma<br />
  refer to TCanny doc for more details
- alpha, beta<br />
  so halos occur at fairly sharp transitions, and we want weak and insignificant edges that got no or little halos around gone, and that we should re-scale the gradient of the canny mask, and these 2 parameters are related to that process, say *x* is the value of some pixel in the mask and it will be scaled to *(x + alpha)^beta-alpha^beta*, basically any value < *1-alpha* will be close to 0 after that, so larger alpha = more edges
- masking<br />
  set it False and get a raw output with no mask protection, for very large radius halos
- show<br />
  set it True and the output will be the halo mask, for debugging and stuff

### Morphology Filters
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
#removing over/undershoot
ref = Vine.Basic(clip, h=48.0)
clip = Vine.Final([clip, ref], [Vine.Super(clip), Vine.Super(ref)], [6, 0, 0], sigma=1.5, alpha=0.06)
#removing halos
ref = Vine.Basic(clip, h=24.0)
clip = Vine.Final([clip, ref], [Vine.Super(clip), Vine.Super(ref)], [6, 1, 4], sigma=1.5, alpha=0.06)
```
![](http://i.imgur.com/sHlq8vG.png)
![](http://i.imgur.com/zIK5z4g.png)
<br />
*zoomed to 400%*<br />
*click the image and view at full size*<br />
![](http://i.imgur.com/FNotFM2.png)
- analog video kind of severe and gross halo<br />
```python
ref = Vine.Basic(clip, h=64.0, sharp=0.5)
ref = Vine.Basic(ref, h=24.0, sharp=0.5)
clip = Vine.Final([clip, ref], [Vine.Super(clip), Vine.Super(ref)], [6, 2, 4], sigma=2.2, alpha=0.18)
```
![](http://i.imgur.com/6rYBsz7.png)
![](http://i.imgur.com/1IkyNpG.png)
