from pathlib import Path
from io import BytesIO
import json, zipfile
import xml.etree.ElementTree as ET
import uharfbuzz as hb
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image, ImageDraw, ImageFont

root=Path(__file__).parent
font=instantiateVariableFont(TTFont(root/'Lexend[wght].ttf'),{'wght':700},inplace=False)
font.save(root/'Lexend-Bold-700.ttf')
hbfont=hb.Font(hb.Face((root/'Lexend-Bold-700.ttf').read_bytes()))
upem=font['head'].unitsPerEm;hbfont.scale=(upem,upem)
glyphs=font.getGlyphSet();order=font.getGlyphOrder()
buf=hb.Buffer();buf.add_str('acute web');buf.guess_segment_properties()
hb.shape(hbfont,buf,{'kern':True,'liga':False})
infos=buf.glyph_infos;positions=buf.glyph_positions
text='acute web';fox=ET.parse(root/'acute_fox_color.svg').getroot()
foxbody=''.join(ET.tostring(e,encoding='unicode') for e in fox)
def lockup(tracking,gap,color):
 x=0;parts=[];scale=100/upem
 for i,(info,pos) in enumerate(zip(infos,positions)):
  ch=text[info.cluster]
  if ch==' ':
   x+=pos.x_advance*gap;continue
  pen=SVGPathPen(glyphs);glyphs[order[info.codepoint]].draw(pen)
  parts.append(f'<path transform="translate({145+(x+pos.x_offset)*scale:.6f} {105-pos.y_offset*scale:.6f}) scale({scale:.8f} {-scale:.8f})" d="{pen.getCommands()}"/>')
  x+=pos.x_advance
  if i+1<len(infos) and text[infos[i+1].cluster]!=' ':x+=tracking*upem
 width=145+x*scale+14
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.6f} 140"><title>acute web — Lexend Bold 700 spacing study</title><g transform="translate(12 16)">{foxbody}</g><g fill="{color}">'+''.join(parts)+'</g></svg>'
 return svg,width
def raster(svg,width,factor):
 return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode(),output_width=round(width*factor),output_height=round(140*factor)))).convert('RGBA')

sheet=Image.new('RGB',(2400,1790),'#202731');d=ImageDraw.Draw(sheet)
ui='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
f=lambda n:ImageFont.truetype(ui,n)
d.text((60,35),'acute web / Lexend Bold 700',font=f(42),fill='#F3F6FC')
d.text((60,100),'Real font outlines + traced fox. Eight spacing options. Small samples are rendered at 24 px font size.',font=f(23),fill='#BAC7DC')
for col,label in enumerate(['100% word gap','75% word gap']):d.text((65+col*1170,160),label,font=f(28),fill='#D6E3FF')
manifest=[]
for row,t in enumerate([0,-.02,-.04,-.06]):
 for col,gap in enumerate([1,.75]):
  idx=row*2+col;key=chr(65+idx);x=45+col*1170;y=215+row*382
  d.rounded_rectangle((x,y,x+1130,y+350),radius=12,fill='#111722')
  label='Default' if t==0 else f'{round(-t*100)}% tighter'
  d.text((x+25,y+18),f'{key}   {label} / {round(gap*100)}% word gap',font=f(23),fill='#E8EEFA')
  white,w=lockup(t,gap,'#F2F4F7');navy,_=lockup(t,gap,'#142341')
  large=raster(white,w,1.2)
  sheet.paste(large,(x+20,y+68),large)
  d.text((x+26,y+245),'24 px — actual size',font=f(16),fill='#A2B4D2')
  small=raster(white,w,.24);sheet.paste(small,(x+230,y+238),small)
  d.rounded_rectangle((x+570,y+230,x+1105,y+320),radius=6,fill='#F4F7FD')
  smalllight=raster(navy,w,.24);sheet.paste(smalllight,(x+590,y+252),smalllight)
  folder=root/'variants'/key;folder.mkdir(parents=True,exist_ok=True)
  for theme,svg in [('dark',white),('light',navy)]:
   (folder/f'acute-web-{key}-{theme}.svg').write_text(svg)
   raster(svg,w,2).save(folder/f'acute-web-{key}-{theme}.png')
  manifest.append({'option':key,'tracking_em':t,'word_space_multiplier':gap,'kerning':True,'weight':700})
sheet.save(root/'Acute-Web-Lexend-Spacing-Study.png')
(root/'spacing-settings.json').write_text(json.dumps(manifest,indent=2))
(root/'README.md').write_text('''# Acute Web — actual Lexend Bold spacing study

The eight rows/columns use the genuine Lexend variable font from Google Fonts, instantiated at weight 700, with HarfBuzz kerning enabled. Letter spacing is applied between adjacent letters within words. It is expressed in em units (0, -0.02, -0.04, -0.06), not as a percentage scaling of letter widths. The natural font space is independently multiplied by 1.0 or 0.75. No horizontal stretching is used.

Every preview and SVG uses the same explicit glyph outline pipeline. No AI-generated lettering is used. Small samples use 24 px font size; view the PNG at 100% to judge actual pixel size. The large previews use 120 px font size. Because chat can scale the whole sheet, the small examples can look smaller than their intended pixels in chat.

Options A/B: default tracking. C/D: -0.02 em. E/F: -0.04 em. G/H: -0.06 em. The left column uses the full word space; the right column uses 75%. These are review options, not approved final wordmarks. The previous suggestion corresponds to F, but it was made before viewing a study.

Each variants folder has dark-use (white letters) and light-use (navy letters) transparent PNG and path-only SVG lockups. They use the traced fox from iiankehn/acute-web-android branch claude/brand-2-assets. Beta 3 and all repositories remain unchanged by this study.

The font and OFL license are included for reproducibility. Source: https://github.com/google/fonts/tree/main/ofl/lexend . The font is not an identification of the earlier generated logo; it is the selected production font direction. Rebuild with Python 3, Pillow, fontTools, uharfbuzz and cairosvg using build_study.py.
''')
with zipfile.ZipFile(root.parent/'Acute-Web-Lexend-Spacing-Study.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(root.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(root))
print('Generated study with eight variants and matched vector/PNG exports.')
