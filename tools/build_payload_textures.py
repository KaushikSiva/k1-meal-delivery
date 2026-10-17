"""Reproducible reference-inspired packaging textures; not photographs/evidence."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'sim/assets/payload'
FONT='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
def font(n):return ImageFont.truetype(FONT,n)
def paper(size,seed):
 rng=np.random.default_rng(seed); a=np.clip(rng.normal(0,1.6,(size[1],size[0],1))+np.array([237,232,218]),0,255).astype('uint8');return Image.fromarray(a)
def logo(im,xy,scale):
 # Original geometric reconstruction of the familiar domino mark.
 tile=Image.new('RGBA',(240,240));d=ImageDraw.Draw(tile)
 d.rounded_rectangle((8,8,232,232),radius=20,fill='white');d.rectangle((20,20,220,116),fill='#e51e36');d.rectangle((20,124,220,220),fill='#006b9c')
 for x,y in [(120,68),(70,172),(170,172)]:d.ellipse((x-19,y-19,x+19,y+19),fill='white')
 tile=tile.rotate(-45,expand=True,resample=Image.Resampling.BICUBIC).resize((scale,scale));im.paste(tile,xy,tile)
im=paper((1536,1536),42);d=ImageDraw.Draw(im)
d.rounded_rectangle((38,38,1498,1498),radius=40,outline='#df2038',width=13)
logo(im,(570,100),395)
d.text((768,535),"Domino’s",font=font(172),fill='#006996',anchor='mm')
d.rectangle((175,700,1361,835),fill='#df2038');d.text((768,766),'MADE TO SHARE',font=font(88),fill='white',anchor='mm')
d.text((768,1000),'HOT. FRESH. PIZZA.',font=font(88),fill='#006996',anchor='mm')
d.line((300,1140,1236,1140),fill='#006996',width=6)
d.text((768,1260),'PLEASE RECYCLE THIS BOX',font=font(46),fill='#006996',anchor='mm')
# Subtle folding creases and print wear are original approximations.
d.line((70,80,70,1460),fill=(205,198,179),width=2);d.line((90,1472,1440,1472),fill=(205,198,179),width=3)
im.save(OUT/'pizza-lid.png')
im=paper((1536,256),43);d=ImageDraw.Draw(im)
for x in range(0,1536,15):d.line((x,240,x+4,250),fill=(164,139,99),width=3)
d.line((0,25,1536,25),fill='#df2038',width=6);d.text((768,126),'Domino’s  •  FRESHLY BAKED',font=font(68),fill='#006996',anchor='mm');im.save(OUT/'pizza-side.png')
im=Image.new('RGB',(2048,1024),'#da1025');d=ImageDraw.Draw(im)
mark=Image.open(OUT/'coca-cola-wordmark.png').convert('RGBA');mark.putdata([(255,255,255,a) for r,g,b,a in mark.getdata()]);mark=mark.resize((800,250),Image.Resampling.LANCZOS)
for x in [115,1139]:
 im.paste(mark,(x,360),mark);d.text((x+400,200),'ORIGINAL TASTE',font=font(46),fill='white',anchor='mm');d.text((x+400,800),'Coca-Cola',font=font(32),fill='white',anchor='mm')
im.save(OUT/'coke-wrap.png')
print('Wrote original box textures and can label using attributed official wordmark')
