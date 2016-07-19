import vapoursynth as vs
import math

fmtc_args                 = dict (fulls=True, fulld=True)
canny_args                = dict (mode=1, op=0)
nnedi_args                = dict (field=1, dh=True, nns=4, qual=2, etype=1, nsize=0)

class helpers:
      def gauss (src, p):
          core            = vs.get_core ()
          Resample        = core.fmtc.resample
          upsmp           = Resample (src, src.width * 2, src.height * 2, kernel="gauss", a1=100, **fmtc_args)
          clip            = Resample (upsmp, src.width, src.height, kernel="gauss", a1=p, **fmtc_args)
          return clip
      def cutoff (low, hi, p):
          core            = vs.get_core ()
          MakeDiff        = core.std.MakeDiff
          MergeDiff       = core.std.MergeDiff
          hif             = MakeDiff (hi, helpers.gauss (hi, p))
          clip            = MergeDiff (helpers.gauss (low, p), hif)
          return clip
      def padding (src, left=0, right=0, top=0, bottom=0):
          core            = vs.get_core ()
          Resample        = core.fmtc.resample
          w               = src.width
          h               = src.height
          clip            = Resample (src, w+left+right, h+top+bottom, -left, -top, w+left+right, h+top+bottom, kernel="point", **fmtc_args)
          return clip
      def NLMeans (src, a, h):
          core            = vs.get_core ()
          Crop            = core.std.CropRel
          KNLMeansCL      = core.knlm.KNLMeansCL
          pad             = helpers.padding (src, a, a, a, a)
          nlm             = KNLMeansCL (pad, d=0, a=a, s=0, h=h)
          clip            = Crop (nlm, a, a, a, a)
          return clip
      def Supersample (src):
          core            = vs.get_core ()
          NNEDI           = core.nnedi3.nnedi3
          Transpose       = core.std.Transpose
          u2x             = Transpose (NNEDI (Transpose (NNEDI (src, **nnedi_args)), **nnedi_args))
          clip            = Transpose (NNEDI (Transpose (NNEDI (u2x, **nnedi_args)), **nnedi_args))
          return clip
      def Inflate (src, radius):
          core            = vs.get_core ()
          Inflate         = core.flt.Inflate
          for i in range (radius):
              src         = Inflate (src)
          return src

class morphology:
      def Dilation (src, radius=1):
          core            = vs.get_core ()
          Maximum         = core.flt.Maximum
          for i in range (radius):
              src         = Maximum (src)
          return src
      def Erosion (src, radius=1):
          core            = vs.get_core ()
          Minimum         = core.flt.Minimum
          for i in range (radius):
              src         = Minimum (src)
          return src
      def Closing (src, radius=1):
          clip            = morphology.Dilation (src, radius)
          clip            = morphology.Erosion (clip, radius)
          return clip
      def Opening (src, radius=1):
          clip            = morphology.Erosion (src, radius)
          clip            = morphology.Dilation (clip, radius)
          return clip
      def Gradient (src, radius=1):
          core            = vs.get_core ()
          Expr            = core.std.Expr
          erosion         = morphology.Erosion (src, radius)
          dilation        = morphology.Dilation (src, radius)
          clip            = Expr ([dilation, erosion], "x y -")
          return clip
      def TopHat (src, radius=1):
          core            = vs.get_core ()
          Expr            = core.std.Expr
          opening         = morphology.Opening (src, radius)
          clip            = Expr ([src, opening], "x y -")
          return clip
      def BlackHat (src, radius=1):
          core            = vs.get_core ()
          Expr            = core.std.Expr
          closing         = morphology.Closing (src, radius)
          clip            = Expr ([src, closing], "y x -")
          return clip

def Dehalo (src, radius=[1, None], a=32, h=6.4, sharp=1.0, sigma=0.6, alpha=0.36, beta=32, cutoff=4, show=False):
    core                  = vs.get_core ()
    Resample              = core.fmtc.resample
    Canny                 = core.tcanny.TCanny
    Expr                  = core.std.Expr
    MaskedMerge           = core.std.MaskedMerge
    SelectEvery           = core.std.SelectEvery
    ShufflePlanes         = core.std.ShufflePlanes
    Interleave            = core.std.Interleave
    _colorspace           = src.format.color_family
    if src.format.bits_per_sample < 32:
       raise TypeError ("Vine.Dehalo: 32bits floating point precision input required!")
    if src.format.subsampling_w > 0 or src.format.subsampling_h > 0:
       raise TypeError ("Vine.Dehalo: subsampled stuff not supported!")
    if _colorspace == vs.RGB:
       src                = Interleave ([ShufflePlanes (src, 0, vs.GRAY), ShufflePlanes (src, 1, vs.GRAY), ShufflePlanes (src, 2, vs.GRAY)])
    if _colorspace == vs.YUV:
       src_color          = src
       src                = ShufflePlanes (src, 0, vs.GRAY)
    gamma                 = pow (alpha, beta)
    radius[1]             = math.ceil (radius[0] / 2) if radius[1] is None else radius[1]
    clean                 = helpers.NLMeans (src, a, h)
    clean                 = helpers.cutoff (src, clean, cutoff) if cutoff != 0 else clean
    clean                 = helpers.Supersample (clean)
    clean                 = Resample (clean, src.width, src.height, sx=-1.25, sy=-1.25, kernel="cubic", a1=-sharp, a2=0)
    mask                  = Canny (clean, sigma=sigma, **canny_args)
    mask                  = Expr (mask, "x {alpha} + {beta} pow {gamma} -".format (alpha=alpha, beta=beta, gamma=gamma))
    expanded              = morphology.Dilation (mask, radius[0])
    closed                = morphology.Closing (mask, radius[0])
    mask                  = Expr ([expanded, closed, mask], "x y - z +")
    mask                  = helpers.Inflate (mask, radius[1])
    mask                  = helpers.gauss (mask, 8)
    mask                  = Expr (mask, "x 0.0 max 1.0 min")
    merge                 = MaskedMerge (src, clean, mask)
    if _colorspace == vs.YUV:
       merge              = ShufflePlanes ([merge, src_color], [0, 1, 2], vs.YUV)
    if _colorspace == vs.RGB:
       merge              = ShufflePlanes ([SelectEvery (merge, 3, 0), SelectEvery (merge, 3, 1), SelectEvery (merge, 3, 2)], 0, vs.RGB)
    clip                  = mask if show else merge
    return clip
