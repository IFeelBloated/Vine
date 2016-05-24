import vapoursynth as vs

### Global Settings ###
fmtc_args                 = dict (fulls=True, fulld=True)
canny_args                = dict (mode=1, op=0)

### Helpers ###
class helpers:
      def freq_merge (low, hi, p=8):
          core            = vs.get_core ()
          Resample        = core.fmtc.resample
          MakeDiff        = core.std.MakeDiff
          MergeDiff       = core.std.MergeDiff
          def gauss (src):
              upsmp       = Resample (src, src.width * 2, src.height * 2, kernel="gauss", a1=100, **fmtc_args)
              clip        = Resample (upsmp, src.width, src.height, kernel="gauss", a1=p, **fmtc_args)
              return clip
          hif             = MakeDiff (hi, gauss (hi))
          clip            = MergeDiff (gauss (low), hif)
          return clip
      def padding (src, left=0, right=0, top=0, bottom=0):
          core            = vs.get_core ()
          Resample        = core.fmtc.resample
          w               = src.width
          h               = src.height
          clip            = Resample (src, w+left+right, h+top+bottom, -left, -top, w+left+right, h+top+bottom, kernel="point", **fmtc_args)
          return clip
      def thr_merge (flt, src, ref=None, thr=0.0009765625, elast=None):
          core            = vs.get_core ()
          Expr            = core.std.Expr
          MakeDiff        = core.std.MakeDiff
          MergeDiff       = core.std.MergeDiff
          ref             = src if ref is None else ref
          elast           = thr / 2 if elast is None else elast
          BExp            = ["x {thr} {elast} + z - 2 {elast} * / * y {elast} z + {thr} - 2 {elast} * / * +".format (thr=thr, elast=elast)]
          BDif            = Expr (src, "0.0")
          PDif            = Expr ([flt, src], "x y - 0.0 max")
          PRef            = Expr ([flt, ref], "x y - 0.0 max")
          PBLD            = Expr ([PDif, BDif, PRef], BExp)
          NDif            = Expr ([flt, src], "y x - 0.0 max")
          NRef            = Expr ([flt, ref], "y x - 0.0 max")
          NBLD            = Expr ([NDif, BDif, NRef], BExp)
          BLDD            = MakeDiff (PBLD, NBLD)
          BLD             = MergeDiff (src, BLDD)
          UDN             = Expr ([flt, ref, BLD], ["x y - abs {thr} {elast} - > z x ?".format (thr=thr, elast=elast)])
          clip            = Expr ([flt, ref, UDN, src], ["x y - abs {thr} {elast} + < z a ?".format (thr=thr, elast=elast)])
          return clip
      def NLMeans (src, h):
          core            = vs.get_core ()
          Crop            = core.std.CropRel
          KNLMeansCL      = core.knlm.KNLMeansCL
          pad             = helpers.padding (src, 32, 32, 32, 32)
          nlm             = KNLMeansCL (pad, d=0, a=32, s=0, h=h)
          clip            = Crop (nlm, 32, 32, 32, 32)
          return clip

### Actual Stuff ###
def Dehalo (src, h=12.8, sigma=1.5, alpha=0.36, beta=32, thr=0.00390625, elast=None, lowpass=8, show=False):
    core                  = vs.get_core ()
    Canny                 = core.tcanny.TCanny
    Maximum               = core.flt.Maximum
    Inflate               = core.flt.Inflate
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
    elast                 = thr / 6 if elast is None else elast
    clean                 = helpers.NLMeans (src, h)
    clean                 = helpers.freq_merge (src, clean, lowpass)
    clean                 = helpers.thr_merge (src, clean, thr=thr, elast=elast)
    mask                  = Canny (clean, sigma=sigma, **canny_args)
    mask                  = Expr (mask, "x {alpha} + {beta} pow {gamma} - 0.0 max 1.0 min".format (alpha=alpha, beta=beta, gamma=gamma))
    mask                  = Inflate (Maximum (Maximum (mask)))
    merge                 = MaskedMerge (src, clean, mask)
    if _colorspace == vs.YUV:
       merge              = ShufflePlanes ([merge, src_color], [0, 1, 2], vs.YUV)
    if _colorspace == vs.RGB:
       merge              = ShufflePlanes ([SelectEvery (merge, 3, 0), SelectEvery (merge, 3, 1), SelectEvery (merge, 3, 2)], 0, vs.RGB)
    clip                  = mask if show else merge
    return clip
