import sys, numpy as np, cv2
from PIL import Image, ImageEnhance, ImageFilter
src, dst = sys.argv[1], sys.argv[2]

# (box x0,y0,x1,y1), (dx,dy) source offset for a feathered clone-patch
FIX = {
 'after4': [((255,1715,445,1935),(170,-7)), ((725,1735,838,1895),(-160,6)), ((1345,2310,1600,2576),(-280,-224))],
 'after5': [((1795,1985,1932,2265),(-230,-39))],
 'after6': [((755,1245,808,1308),(-80,0)), ((940,1262,988,1324),(-60,0)), ((1205,1548,1345,1685),(-150,-140))],
}
# per-image tone: (brightness, contrast, color)
TONE = {'interior': (1.10, 1.06, 1.08), 'exterior': (1.02, 1.06, 1.10)}

def clone(img, box, off, feather=18):
    x0,y0,x1,y1 = box; dx,dy = off; h,w = img.shape[:2]
    pad = feather*2
    X0,Y0,X1,Y1 = max(x0-pad,0),max(y0-pad,0),min(x1+pad,w),min(y1+pad,h)
    m = np.zeros((h,w),np.float32); m[y0:y1,x0:x1] = 1
    m = cv2.GaussianBlur(m,(0,0),feather)[...,None]
    m = np.clip(m/ m[ (y0+y1)//2,(x0+x1)//2 ],0,1)  # full strength in centre
    M = np.float32([[1,0,dx],[0,1,dy]])
    shifted = cv2.warpAffine(img, M, (w,h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) if False else np.roll(np.roll(img,-dy,0),-dx,1)
    out = img.astype(np.float32)
    out[Y0:Y1,X0:X1] = out[Y0:Y1,X0:X1]*(1-m[Y0:Y1,X0:X1]) + shifted[Y0:Y1,X0:X1].astype(np.float32)*m[Y0:Y1,X0:X1]
    return out.astype(np.uint8)

name = src.rsplit('/',1)[-1].split('.')[0]
img = np.array(Image.open(src).convert('RGB'))
for box, off in FIX.get(name, []):
    img = clone(img, box, off)
im = Image.fromarray(img)
b,c,s = TONE['interior' if name in ('after4','after5','after6') else 'exterior']
im = ImageEnhance.Brightness(im).enhance(b)
im = ImageEnhance.Contrast(im).enhance(c)
im = ImageEnhance.Color(im).enhance(s)
im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
im.save(dst, quality=90)
