from PIL import Image, ImageFilter
import numpy as np
im = Image.open('shoe_cut.png')
a = np.asarray(im.getchannel('A')).astype(np.float32)/255.0
# choke: erode ~1.5px per togliere l'alone bianco del fondo
er = Image.fromarray((a*255).astype(np.uint8),'L').filter(ImageFilter.MinFilter(3))
er = er.filter(ImageFilter.GaussianBlur(0.7))
a2 = np.asarray(er).astype(np.float32)/255.0
a2 = np.clip((a2-0.12)/0.80, 0, 1)
rgb = np.asarray(im.convert('RGB')).astype(np.float32)
# de-fringe: scurisce i pixel di bordo troppo chiari
edge = ((a2>0.05)&(a2<0.95))
rgb[edge] *= 0.93
out = Image.fromarray(rgb.astype(np.uint8),'RGB')
out.putalpha(Image.fromarray((a2*255).astype(np.uint8),'L'))
out = out.crop(out.getbbox())
out.save('shoe.png')
print('rifinito ->', out.size)
