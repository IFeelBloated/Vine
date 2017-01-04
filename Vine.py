import vapoursynth as vs
import math

fmtc_args                    = dict(fulls=True, fulld=True)
canny_args                   = dict(mode=1, op=0)
nnedi_args                   = dict(field=1, dh=True, nns=4, qual=2, etype=1, nsize=0)

class get_core:
      def __init__(self):
          self.core          = vs.get_core()
          self.KNLMeansCL    = self.core.knlm.KNLMeansCL
          self.Canny         = self.core.tcanny.TCanny
          self.NNEDI         = self.core.nnedi3.nnedi3
          self.Resample      = self.core.fmtc.resample
          self.Maximum       = self.core.std.Maximum
          self.Minimum       = self.core.std.Minimum
          self.Expr          = self.core.std.Expr
          self.Merge         = self.core.std.Merge
          self.MakeDiff      = self.core.std.MakeDiff
          self.MergeDiff     = self.core.std.MergeDiff
          self.Crop          = self.core.std.CropRel
          self.Transpose     = self.core.std.Transpose
          self.Inflate       = self.core.std.Inflate
          self.MaskedMerge   = self.core.std.MaskedMerge
          self.ShufflePlanes = self.core.std.ShufflePlanes
          self.SelectEvery   = self.core.std.SelectEvery
          self.SetFieldBased = self.core.std.SetFieldBased
          self.Interleave    = self.core.std.Interleave

      def CutOff(self, low, hi, p):
          def inline(src):
              upsmp          = self.Resample(src, src.width*2, src.height*2, kernel="gauss", a1=100, **fmtc_args)
              clip           = self.Resample(upsmp, src.width, src.height, kernel="gauss", a1=p, **fmtc_args)
              return clip
          hif                = self.MakeDiff(hi, inline(hi))
          clip               = self.MergeDiff(inline(low), hif)
          return clip

      def Pad(self, src, left, right, top, bottom):
          w                  = src.width
          h                  = src.height
          clip               = self.Resample(src, w+left+right, h+top+bottom, -left, -top, w+left+right, h+top+bottom, kernel="point", **fmtc_args)
          return clip

      def NLMeans(self, src, a, s, h, rclip):
          pad                = self.Pad(src, a+s, a+s, a+s, a+s)
          rclip              = self.Pad(rclip, a+s, a+s, a+s, a+s) if rclip is not None else None
          nlm                = self.KNLMeansCL(pad, d=0, a=a, s=s, h=h, rclip=rclip)
          clip               = self.Crop(nlm, a+s, a+s, a+s, a+s)
          return clip

class internal:
      def dilation(core, src, radius):
          for i in range(radius):
              src            = core.Maximum(src)
          return src

      def erosion(core, src, radius):
          for i in range(radius):
              src            = core.Minimum(src)
          return src

      def closing(core, src, radius):
          clip               = internal.dilation(core, src, radius)
          clip               = internal.erosion(core, clip, radius)
          return clip

      def opening(core, src, radius):
          clip               = internal.erosion(core, src, radius)
          clip               = internal.dilation(core, clip, radius)
          return clip

      def gradient(core, src, radius):
          erosion            = internal.erosion(core, src, radius)
          dilation           = internal.dilation(core, src, radius)
          clip               = core.Expr([dilation, erosion], "x y -")
          return clip

      def tophat(core, src, radius):
          opening            = internal.opening(core, src, radius)
          clip               = core.Expr([src, opening], "x y -")
          return clip

      def blackhat(core, src, radius):
          closing            = internal.closing(core, src, radius)
          clip               = core.Expr([src, closing], "y x -")
          return clip

      def dehalo(core, src, radius, a, h, sharp, sigma, alpha, beta, cutoff, masking, show):
          c1                 = 1.0539379242228472964011623967818
          c2                 = 0.7079956288531109375036838973963
          c3                 = 0.3926327792690057290863679493724
          strength           = [h]
          strength          += [((math.exp(c1 * h) - 1.0) /(math.pow(h, h) / math.gamma(h + 1.0))) / c2]
          gamma              = math.pow(alpha, beta)
          weight             = c3 * sharp * math.log(1.0 + 1.0 / (c3 * sharp))
          clean              = core.NLMeans(src, a, 0, strength[1], None)
          clean              = core.CutOff(src, clean, cutoff)
          dif                = core.MakeDiff(src, clean)
          dif                = core.NLMeans(dif, a, 1, strength[0], clean)
          clean              = core.MergeDiff(clean, dif)
          upsampled          = clean
          for i in range(2):
              upsampled      = core.Transpose(core.NNEDI(core.Transpose(core.NNEDI(upsampled, **nnedi_args)), **nnedi_args))
          resampled          = core.Resample(upsampled, src.width, src.height, sx=-1.25, sy=-1.25, kernel="cubic", a1=-sharp, a2=0)
          clean              = core.Merge(resampled, clean, weight)
          if masking:
             mask            = core.Canny(clean, sigma=sigma, **canny_args)
             mask            = core.Expr(mask, "x {alpha} + {beta} pow {gamma} - 0.0 max 1.0 min".format(alpha=alpha, beta=beta, gamma=gamma))
             expanded        = internal.dilation(core, mask, radius[0])
             closed          = internal.closing(core, mask, radius[0])
             mask            = core.Expr([expanded, closed, mask], "x y - z +")
             for i in range(radius[1]):
                 mask        = core.Inflate(mask)
             merge           = core.MaskedMerge(src, clean, mask)
             clip            = mask if show else merge
          else:
             clip            = clean
          return clip

def Dehalo(src, radius=[1, None], a=32, h=6.4, sharp=1.0, sigma=0.6, alpha=0.36, beta=32.0, cutoff=4, masking=True, show=False):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Dehalo: src has to be a video clip!")
    elif src.format.sample_type != vs.FLOAT or src.format.bits_per_sample < 32:
       raise TypeError("Vine.Dehalo: the sample type of src has to be single precision!")
    if not isinstance(radius, list):
       raise TypeError("Vine.Dehalo: radius parameter has to be an array!")
    elif len(radius) != 2:
       raise RuntimeError("Vine.Dehalo: radius parameter has to contain 2 elements exactly!")
    if not isinstance(radius[0], int):
       raise TypeError("Vine.Dehalo: radius[0] has to be an integer!")
    elif radius[0] < 0:
       raise RuntimeError("Vine.Dehalo: radius[0] has to be no less than 0!")
    if not isinstance(radius[1], int) and radius[1] is not None:
       raise TypeError("Vine.Dehalo: radius[1] has to be an integer or None!")
    elif radius[1] is not None:
         if radius[1] < 0:
            raise RuntimeError("Vine.Dehalo: radius[1] has to be no less than 0!")
    if not isinstance(a, int):
       raise TypeError("Vine.Dehalo: a has to be an integer!")
    elif a < 1:
       raise RuntimeError("Vine.Dehalo: a has to be greater than 0!")
    if not isinstance(h, float) and not isinstance(h, int):
       raise TypeError("Vine.Dehalo: h has to be a real number!")
    elif h <= 0:
       raise RuntimeError("Vine.Dehalo: h has to be greater than 0!")
    if not isinstance(sharp, float) and not isinstance(sharp, int):
       raise TypeError("Vine.Dehalo: sharp has to be a real number!")
    elif sharp <= 0.0:
       raise RuntimeError("Vine.Dehalo: sharp has to be greater than 0!")
    if not isinstance(alpha, float) and not isinstance(alpha, int):
       raise TypeError("Vine.Dehalo: alpha has to be a real number!")
    elif alpha < 0.0 or alpha > 1.0:
       raise RuntimeError("Vine.Dehalo: alpha must fall in [0.0, 1.0]!")
    if not isinstance(beta, float) and not isinstance(beta, int):
       raise TypeError("Vine.Dehalo: beta has to be a real number!")
    elif beta <= 1.0:
       raise RuntimeError("Vine.Dehalo: beta has to be greater than 1.0!")
    if not isinstance(cutoff, int):
       raise TypeError("Vine.Dehalo: cutoff has to be an integer!")
    elif cutoff < 1 or cutoff > 100:
       raise RuntimeError("Vine.Dehalo: cutoff must fall in(0, 100]!")
    if not isinstance(masking, bool):
       raise TypeError("Vine.Dehalo: masking has to be boolean!")
    if not isinstance(show, bool):
       raise TypeError("Vine.Dehalo: show has to be boolean!")
    if not masking and show:
       raise RuntimeError("Vine.Dehalo: masking has been disabled, set masking True to show the halo mask!")
    core                     = get_core()
    radius[1]                = math.ceil(radius[0] / 2) if radius[1] is None else radius[1]
    src                      = core.SetFieldBased(src, 0)
    colorspace               = src.format.color_family
    if colorspace == vs.RGB:
       src                   = core.Interleave([core.ShufflePlanes(src, 0, vs.GRAY), core.ShufflePlanes(src, 1, vs.GRAY), core.ShufflePlanes(src, 2, vs.GRAY)])
    if colorspace == vs.YUV:
       src_color             = src
       src                   = core.ShufflePlanes(src, 0, vs.GRAY)
    clip                     = internal.dehalo(core, src, radius, a, h, sharp, sigma, alpha, beta, cutoff, masking, show)
    if colorspace == vs.YUV:
       clip                  = core.ShufflePlanes([clip, src_color], [0, 1, 2], vs.YUV)
    if colorspace == vs.RGB:
       clip                  = core.ShufflePlanes([core.SelectEvery(clip, 3, 0), core.SelectEvery(clip, 3, 1), core.SelectEvery(clip, 3, 2)], 0, vs.RGB)
    del core
    return clip

def Dilation(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Dilation: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Dilation: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Dilation: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.dilation(core, src, radius)
    del core
    return clip

def Erosion(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Erosion: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Erosion: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Erosion: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.erosion(core, src, radius)
    del core
    return clip

def Closing(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Closing: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Closing: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Closing: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.closing(core, src, radius)
    del core
    return clip

def Opening(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Opening: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Opening: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Opening: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.opening(core, src, radius)
    del core
    return clip

def Gradient(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Gradient: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Gradient: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Gradient: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.gradient(core, src, radius)
    del core
    return clip

def TopHat(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.TopHat: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.TopHat: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.TopHat: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.tophat(core, src, radius)
    del core
    return clip

def BlackHat(src, radius=1):
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.BlackHat: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.BlackHat: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.BlackHat: radius has to be greater than 0!")
    core                     = get_core()
    src                      = core.SetFieldBased(src, 0)
    clip                     = internal.blackhat(core, src, radius)
    del core
    return clip
