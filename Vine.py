import vapoursynth as vs
import math

fmtc_args                 = dict(fulls=True, fulld=True)
canny_args                = dict(mode=1, op=0)
nnedi_args                = dict(field=1, dh=True, nns=4, qual=2, etype=1, nsize=0)

class helpers:
      def cutoff(low, hi, p):
          core            = vs.get_core()
          Resample        = core.fmtc.resample
          MakeDiff        = core.std.MakeDiff
          MergeDiff       = core.std.MergeDiff
          def inline(src):
              upsmp       = Resample(src, src.width * 2, src.height * 2, kernel="gauss", a1=100, **fmtc_args)
              clip        = Resample(upsmp, src.width, src.height, kernel="gauss", a1=p, **fmtc_args)
              return clip
          hif             = MakeDiff(hi, inline(hi))
          clip            = MergeDiff(inline(low), hif)
          return clip
      def padding(src, left, right, top, bottom):
          core            = vs.get_core()
          Resample        = core.fmtc.resample
          w               = src.width
          h               = src.height
          clip            = Resample(src, w+left+right, h+top+bottom, -left, -top, w+left+right, h+top+bottom, kernel="point", **fmtc_args)
          return clip
      def nlmeans(src, a, s, h, rclip):
          core            = vs.get_core()
          Crop            = core.std.CropRel
          KNLMeansCL      = core.knlm.KNLMeansCL
          pad             = helpers.padding(src, a+s, a+s, a+s, a+s)
          rclip           = helpers.padding(rclip, a+s, a+s, a+s, a+s) if rclip is not None else None
          nlm             = KNLMeansCL(pad, d=0, a=a, s=s, h=h, rclip=rclip)
          clip            = Crop(nlm, a+s, a+s, a+s, a+s)
          return clip

class internal:
      def dilation(src, radius):
          core            = vs.get_core()
          Maximum         = core.std.Maximum
          for i in range(radius):
              src         = Maximum(src)
          return src
      def erosion(src, radius):
          core            = vs.get_core()
          Minimum         = core.std.Minimum
          for i in range(radius):
              src         = Minimum(src)
          return src
      def closing(src, radius):
          clip            = internal.dilation(src, radius)
          clip            = internal.erosion(clip, radius)
          return clip
      def opening(src, radius):
          clip            = internal.erosion(src, radius)
          clip            = internal.dilation(clip, radius)
          return clip
      def gradient(src, radius):
          core            = vs.get_core()
          Expr            = core.std.Expr
          erosion         = internal.erosion(src, radius)
          dilation        = internal.dilation(src, radius)
          clip            = Expr([dilation, erosion], "x y -")
          return clip
      def tophat(src, radius):
          core            = vs.get_core()
          Expr            = core.std.Expr
          opening         = internal.opening(src, radius)
          clip            = Expr([src, opening], "x y -")
          return clip
      def blackhat(src, radius):
          core            = vs.get_core()
          Expr            = core.std.Expr
          closing         = internal.closing(src, radius)
          clip            = Expr([src, closing], "y x -")
          return clip
      def dehalo(src, radius, a, h, sharp, sigma, alpha, beta, cutoff, show):
          core            = vs.get_core()
          Resample        = core.fmtc.resample
          Canny           = core.tcanny.TCanny
          NNEDI           = core.nnedi3.nnedi3
          MakeDiff        = core.std.MakeDiff
          MergeDiff       = core.std.MergeDiff
          Transpose       = core.std.Transpose
          Expr            = core.std.Expr
          Inflate         = core.std.Inflate
          MaskedMerge     = core.std.MaskedMerge
          c1              = 1.0539379242228472964011623967818
          c2              = 0.7079956288531109375036838973963
          strength        = [h, None]
          strength[1]     = ((math.exp(c1 * h) - 1.0) /(math.pow(h, h) / math.gamma(h + 1.0))) / c2
          gamma           = pow(alpha, beta)
          clean           = helpers.nlmeans(src, a, 0, strength[1], None)
          clean           = helpers.cutoff(src, clean, cutoff)
          dif             = MakeDiff(src, clean)
          dif             = helpers.nlmeans(dif, a, 1, strength[0], clean)
          clean           = MergeDiff(clean, dif)
          for i in range(2):
              clean       = Transpose(NNEDI(Transpose(NNEDI(clean, **nnedi_args)), **nnedi_args))
          clean           = Resample(clean, src.width, src.height, sx=-1.25, sy=-1.25, kernel="cubic", a1=-sharp, a2=0)
          mask            = Canny(clean, sigma=sigma, **canny_args)
          mask            = Expr(mask, "x {alpha} + {beta} pow {gamma} - 0.0 max 1.0 min".format(alpha=alpha, beta=beta, gamma=gamma))
          expanded        = internal.dilation(mask, radius[0])
          closed          = internal.closing(mask, radius[0])
          mask            = Expr([expanded, closed, mask], "x y - z +")
          for i in range(radius[1]):
              mask        = Inflate(mask)
          merge           = MaskedMerge(src, clean, mask)
          clip            = mask if show else merge
          return clip

def Dehalo(src, radius=[1, None], a=32, h=6.4, sharp=1.0, sigma=0.6, alpha=0.36, beta=32.0, cutoff=4, show=False):
    core                  = vs.get_core()
    ShufflePlanes         = core.std.ShufflePlanes
    SelectEvery           = core.std.SelectEvery
    SetFieldBased         = core.std.SetFieldBased
    Interleave            = core.std.Interleave
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
    if not isinstance(show, bool):
       raise TypeError("Vine.Dehalo: show has to be boolean!")
    radius[1]             = math.ceil(radius[0] / 2) if radius[1] is None else radius[1]
    src                   = SetFieldBased(src, 0)
    colorspace            = src.format.color_family
    if colorspace == vs.RGB:
       src                = Interleave([ShufflePlanes(src, 0, vs.GRAY), ShufflePlanes(src, 1, vs.GRAY), ShufflePlanes(src, 2, vs.GRAY)])
    if colorspace == vs.YUV:
       src_color          = src
       src                = ShufflePlanes(src, 0, vs.GRAY)
    clip                  = internal.dehalo(src, radius, a, h, sharp, sigma, alpha, beta, cutoff, show)
    if colorspace == vs.YUV:
       clip               = ShufflePlanes([clip, src_color], [0, 1, 2], vs.YUV)
    if colorspace == vs.RGB:
       clip               = ShufflePlanes([SelectEvery(clip, 3, 0), SelectEvery(clip, 3, 1), SelectEvery(clip, 3, 2)], 0, vs.RGB)
    return clip

def Dilation(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Dilation: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Dilation: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Dilation: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.dilation(src, radius)
    return clip

def Erosion(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Erosion: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Erosion: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Erosion: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.erosion(src, radius)
    return clip

def Closing(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Closing: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Closing: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Closing: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.closing(src, radius)
    return clip

def Opening(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Opening: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Opening: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Opening: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.opening(src, radius)
    return clip

def Gradient(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.Gradient: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.Gradient: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.Gradient: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.gradient(src, radius)
    return clip

def TopHat(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.TopHat: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.TopHat: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.TopHat: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.tophat(src, radius)
    return clip

def BlackHat(src, radius=1):
    core                  = vs.get_core()
    SetFieldBased         = core.std.SetFieldBased
    if not isinstance(src, vs.VideoNode):
       raise TypeError("Vine.BlackHat: src has to be a video clip!")
    if not isinstance(radius, int):
       raise TypeError("Vine.BlackHat: radius has to be an integer!")
    elif radius < 1:
       raise RuntimeError("Vine.BlackHat: radius has to be greater than 0!")
    src                   = SetFieldBased(src, 0)
    clip                  = internal.blackhat(src, radius)
    return clip
