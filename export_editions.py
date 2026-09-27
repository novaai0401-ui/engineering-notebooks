"""Build portable reading editions from canonical Markdown. No model calls."""
from pathlib import Path
import html,json,re,zipfile,textwrap,hashlib
from xml.etree import ElementTree as ET
from markdown_it import MarkdownIt
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Preformatted,LongTable,TableStyle
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output';PDF=OUT/'pdf';PDF.mkdir(parents=True,exist_ok=True)
BOOKS=sorted(ROOT.glob('[0-9][0-9]-*.md'))
BASE='https://github.com/novaai0401-ui/engineering-notebooks/blob/main/'
MD=MarkdownIt('commonmark',{'html':False,'xhtmlOut':True}).enable('table')
STATIC='''# Experiments without sliders

These examples provide the essential reasoning of the HTML experiments. PDF and EPUB do not execute browser code. Notes and progress are not synchronized across formats.

## Predict a gradient step
For points (1,2) and (2,4), start w=0 and b=0 in prediction=w*x+b. Mean squared loss is 10. The gradients are -10 and -6. At learning rate 0.1, w becomes 1 and b becomes 0.6. Predictions become 1.6 and 2.6; loss becomes 1.06. At rate 0.6, w=6 and b=3.6; predictions are 9.6 and 15.6, so loss is 96.16. A larger step can overshoot. Neither result establishes performance on unseen data.

## Trace binary search
Array [2,4,4,9,13], target 4. Maintain [lo,hi). Start [0,5). Midpoint 2 has value 4: keep it by setting hi=2. Midpoint 1 has 4: set hi=1. Midpoint 0 has 2: set lo=1. Result is index 1. For target 14 the result is index 5, a no-match position; do not dereference it.

## Predict a retry
The worker stores pending operation PAY-17. The receiver commits one payment. The worker crashes before recording completion, then retries PAY-17. With atomic receiver deduplication, it receives the old receipt and charges remain 1. Without deduplication, charges can become 2. A workflow checkpoint is not a payment receipt.

## Calculate average in-flight work
For a stable system, L=lambda*W. At 80 arrivals per second and average time 0.25 seconds, average in-flight work is 20. At 0.5 seconds it is 40. This average accounting identity is not a prediction of latency percentiles or proof of stability.

## Seven questions before moving on
1. What problem does this solve? Give an everyday example.
2. Can I define each prerequisite and technical term?
3. Can I trace the inputs, intermediate states, and outputs?
4. Why does it work, and under which assumptions?
5. Can I explain implementation, edge cases, failures, and debugging?
6. When is an alternative better?
7. Can I solve a fresh exercise and explain the answer without hints?

The checklist is an acceptance standard, not proof that every topic has already passed editorial review. Executable lab results, classroom examples, and production acceptance are different evidence categories. This edition preserves those distinctions.
'''
(OUT/'STATIC-EXPERIMENTS.md').write_text(STATIC,encoding='utf-8')
# Embedded Windows fonts keep PDF readable without downloading fonts at read time.
for name,file in [('Body','arial.ttf'),('Bold','arialbd.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Body',boldItalic='Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('Read',fontName='Body',fontSize=10,leading=15,spaceAfter=7,splitLongWords=True))
styles.add(ParagraphStyle('TitleBook',parent=styles['Read'],fontName='Bold',fontSize=24,leading=30,spaceAfter=18))
styles.add(ParagraphStyle('SectionBook',parent=styles['Read'],fontName='Bold',fontSize=15,leading=20,spaceBefore=16,spaceAfter=9,keepWithNext=True,textColor=HexColor('#5032a0')))
styles.add(ParagraphStyle('SubBook',parent=styles['SectionBook'],fontSize=11,leading=16))
styles.add(ParagraphStyle('CellBook',parent=styles['Read'],fontSize=7.5,leading=10,spaceAfter=2))
styles.add(ParagraphStyle('ContentsBook',parent=styles['Read'],fontSize=9,leading=12,spaceAfter=5))
styles.add(ParagraphStyle('CodeBook',fontName='Mono',fontSize=7,leading=10,spaceAfter=8,backColor=HexColor('#f1f2f7'),borderPadding=6))
def clean(s):
    return s.replace('\u2011','-').replace('\u2013','-').replace('\u2014','-').replace('\u00a0',' ')
def inline(token):
    out=[]
    for t in token.children or []:
        if t.type=='text':out.append(html.escape(clean(t.content)))
        elif t.type=='code_inline':out.append('<font name="Mono">'+html.escape(clean(t.content))+'</font>')
        elif t.type in ('softbreak','hardbreak'):out.append(' ' if t.type=='softbreak' else '<br/>')
        elif t.type=='strong_open':out.append('<b>')
        elif t.type=='strong_close':out.append('</b>')
        elif t.type=='em_open':out.append('<i>')
        elif t.type=='em_close':out.append('</i>')
        elif t.type=='link_open':
            href=t.attrGet('href');href=href if href.startswith(('https:','http:')) else BASE+href
            out.append('<link href="'+html.escape(href,quote=True)+'" color="#5032a0">')
        elif t.type=='link_close':out.append('</link>')
        elif t.type=='image':out.append(html.escape(t.content))
    return ''.join(out)
class BookDoc(SimpleDocTemplate):
    def afterFlowable(self,f):
        if hasattr(f,'bookmark'):
            self.canv.bookmarkPage(f.bookmark);self.canv.addOutlineEntry(f.getPlainText(),f.bookmark,0,False)
def footer(c,doc):
    c.setFont('Body',8);c.setFillColor(HexColor('#47516b'));c.drawString(42,25,'Engineering notebooks | portable reading edition');c.drawRightString(553,25,str(doc.page))
def flows(source,bookmark=None):
    tokens=MD.parse(source);result=[];i=0;list_depth=0;lists=[];prefix=''
    while i<len(tokens):
        t=tokens[i]
        if t.type=='heading_open':
            title=inline(tokens[i+1]);level=int(t.tag[1]);p=Paragraph(title,styles['TitleBook' if level==1 else 'SectionBook' if level==2 else 'SubBook'])
            if level==1 and bookmark:p.bookmark=bookmark
            result.append(p);i+=3;continue
        if t.type=='table_open':
            rows=[];row=[];j=i+1
            while tokens[j].type!='table_close':
                q=tokens[j]
                if q.type=='tr_open':row=[]
                if q.type=='inline':row.append(Paragraph(inline(q),styles['CellBook']))
                if q.type=='tr_close':rows.append(row)
                j+=1
            cols=max(map(len,rows));table=LongTable(rows,colWidths=[511/cols]*cols,repeatRows=1,hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#ede8ff')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,HexColor('#d5d8e7')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]));result.extend([table,Spacer(1,10)]);i=j+1;continue
        if t.type in ('bullet_list_open','ordered_list_open'):
            list_depth+=1;lists.append([t.type,0])
        if t.type in ('bullet_list_close','ordered_list_close'):
            list_depth-=1;lists.pop()
        if t.type=='list_item_open':
            lists[-1][1]+=1;prefix=str(lists[-1][1])+'. ' if lists[-1][0]=='ordered_list_open' else '&#8226; '
        if t.type=='inline':
            result.append(Paragraph(prefix+inline(t),styles['Read']));prefix=''
        if t.type in ('fence','code_block'):
            lines=[]
            for line in clean(t.content).expandtabs(4).splitlines():lines.extend(textwrap.wrap(line,width=112,replace_whitespace=False,drop_whitespace=False) or [''])
            for pos in range(0,len(lines),45):result.append(Preformatted('\n'.join(lines[pos:pos+45]),styles['CodeBook']))
        i+=1
    return result
story=[Paragraph('ENGINEERING<br/>NOTEBOOKS',styles['TitleBook']),Paragraph('Understand the mechanism. Trace the failure. Explain the tradeoff.',styles['SectionBook']),Paragraph('33 notebooks | full reading edition | 27 September 2026',styles['Read']),Paragraph('This book contains the current teaching material, worked code listings, exercises and known limitations. Browser interactions have static worked equivalents. Running labs requires the documented software; reading does not.',styles['Read']),PageBreak(),Paragraph('Choose your route',styles['TitleBook'])]
for n,p in enumerate(BOOKS):story.append(Paragraph(f'<link href="#book{n}" color="#5032a0">'+html.escape(clean(p.read_text(encoding='utf-8').splitlines()[0][2:]))+'</link>',styles['ContentsBook']))
story.append(Paragraph('<link href="#static" color="#5032a0">Static equivalents of interactive experiments</link>',styles['Read']))
for n,p in enumerate(BOOKS):story.append(PageBreak());story.extend(flows(p.read_text(encoding='utf-8'),f'book{n}'))
story.append(PageBreak());story.extend(flows(STATIC,'static'))
full=PDF/'engineering-notebooks-complete.pdf';BookDoc(str(full),pagesize=(595,842),rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=44,title='Engineering notebooks - complete reading edition',author='Engineering Notebook Library').build(story,onFirstPage=footer,onLaterPages=footer)
print('Full PDF:',len(PdfReader(full).pages),'pages',flush=True)
# A concise, directly shareable document carousel; no claim to replace the full book.
slides=[
('Can your app charge twice?', 'A checkpoint is a bookmark. It is not a payment receipt.', 'Predict first: a worker charges a card, crashes, then restarts. What happens next?'),
('Two records. Two responsibilities.', 'Workflow record: PAY-17 is pending.\nReceiver record: PAY-17 has been charged.', 'A database commit in one service does not automatically update the other service.'),
('Walk the failure', '1. Save pending job PAY-17.\n2. Receiver commits the charge.\n3. Worker crashes before saving completion.', 'On restart, the worker still sees pending. It cannot infer the receiver did nothing.'),
('Predict the retry', 'The worker sends PAY-17 again.\nWill there be one charge or two?', 'Pause here. State what the receiver must remember, and where it must remember it.'),
('The answer lives at the receiver', 'With atomic deduplication: return the original receipt.\nWithout it: another charge may occur.', 'Store the operation key and effect within the same receiver-side atomic boundary.'),
('A key alone is not enough', 'Concurrent attempts must not both win.\nThe same key with a changed amount must conflict.', 'Enforce uniqueness and compare request identity or payload. A check followed by an unrelated insert can race.'),
('Test the dangerous gap', 'Kill the worker after the charge commits, before completion is saved.\nRestart it and count durable effects.', 'Expected: one intended payment, one charge, and the same receipt returned on retry.'),
('The interview answer', 'Checkpoints preserve progress.\nIdempotency controls duplicate effects.\nRetries need stable operation identity.', 'Name the guarantee boundary. Do not claim universal exactly-once execution across independent systems.'),
('Take the idea further', 'Next: durable agents, transactional outbox, Kafka offsets, and recovery testing.', 'Companion to notebooks 7, 18 and 22. Read the full library for assumptions, code, alternatives and exercises.')]
carousel=PDF/'linkedin-checkpoints-and-retries.pdf';c=canvas.Canvas(str(carousel),pagesize=(720,900));c.setTitle('Can your app charge twice? A worked engineering carousel');c.setAuthor('Engineering Notebook Library')
for i,(title,body,takeaway) in enumerate(slides):
    c.setFillColor(HexColor('#f5f4ff'));c.rect(0,0,720,900,fill=1,stroke=0);c.setFillColor(HexColor('#5032a0'));c.rect(0,880,720,20,fill=1,stroke=0)
    c.setFont('Bold',13);c.drawString(48,838,'ENGINEERING, EXPLAINED');c.drawRightString(672,838,f'{i+1:02} / {len(slides):02}')
    for text,y,size,leading,color in [(title,760,36,44,'#18213c'),(body,575,25,36,'#18213c'),(takeaway,280,19,29,'#395966')]:
        st=ParagraphStyle('slide',fontName='Bold' if size==36 else 'Body',fontSize=size,leading=leading,textColor=HexColor(color));para=Paragraph(html.escape(text).replace('\n','<br/>'),st);w,h=para.wrap(624,500);assert h<230,(i,text);para.drawOn(c,48,y-h)
    if i in (2,4):
        labels=['PENDING JOB','CHARGE COMMITTED','WORKER CRASH'] if i==2 else ['SAME OPERATION KEY','DEDUPLICATE: 1 CHARGE','NO DEDUP: 2 POSSIBLE']
        for j,label in enumerate(labels):
            c.setFillColor(HexColor('#5032a0' if j!=2 else '#075d72'));c.roundRect(48+j*212,350,200,55,8,fill=1,stroke=0);c.setFillColor(HexColor('#ffffff'));c.setFont('Bold',10);c.drawCentredString(148+j*212,373,label)
    c.setStrokeColor(HexColor('#087b80'));c.setLineWidth(4);c.line(48,315,672,315);c.setFont('Body',11);c.setFillColor(HexColor('#47516b'));c.drawString(48,40,'Teaching companion | full explanations in the engineering notebooks');c.showPage()
c.save();print('Carousel: 9 pages',flush=True)
# EPUB 3: reflowable XHTML, local navigation, no scripts or remote fonts.
epub=OUT/'engineering-notebooks.epub';ns='http://www.w3.org/1999/xhtml'
def xhtml(title,body):return '<?xml version="1.0" encoding="utf-8"?><html xmlns="'+ns+'" lang="en"><head><title>'+html.escape(title)+'</title><link rel="stylesheet" href="style.css"/></head><body>'+body+'</body></html>'
entries={};titles=[]
for p in BOOKS:
    source=p.read_text(encoding='utf-8');tokens=MD.parse(source)
    for i,t in enumerate(tokens):
        if t.type=='heading_open':t.attrSet('id','section-'+str(i))
        if t.type=='inline':
            for child in t.children or []:
                if child.type=='link_open':
                    href=child.attrGet('href');base,sep,frag=href.partition('#');stem=Path(base).stem
                    if any(b.stem==stem for b in BOOKS):child.attrSet('href',stem+'.xhtml'+(sep+frag if sep else ''))
                    elif base and not href.startswith(('https:','http:','mailto:')):child.attrSet('href',BASE+href)
    title=source.splitlines()[0][2:];name=p.stem+'.xhtml';titles.append((name,title));entries[name]=xhtml(title,MD.renderer.render(tokens,MD.options,{}))
titles.append(('static.xhtml','Experiments without sliders'));entries['static.xhtml']=xhtml('Experiments without sliders',MD.render(STATIC))
nav='<nav xmlns:epub="http://www.idpf.org/2007/ops" epub:type="toc"><h1>Engineering notebooks</h1><ol>'+''.join('<li><a href="'+f+'">'+html.escape(t)+'</a></li>' for f,t in titles)+'</ol></nav>'
entries['nav.xhtml']=xhtml('Contents',nav)
for name,value in entries.items():ET.fromstring(value)
identifier='urn:sha256:'+hashlib.sha256(''.join(p.read_text(encoding='utf-8') for p in BOOKS).encode()).hexdigest()
manifest=''.join(f'<item id="b{i}" href="{f}" media-type="application/xhtml+xml"/>' for i,(f,t) in enumerate(titles))
opf=f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">{identifier}</dc:identifier><dc:title>Engineering notebooks</dc:title><dc:language>en</dc:language><dc:creator>Engineering Notebook Library</dc:creator><meta property="dcterms:modified">2026-09-27T00:00:00Z</meta></metadata><manifest>{manifest}<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="css" href="style.css" media-type="text/css"/></manifest><spine>'''+''.join(f'<itemref idref="b{i}"/>' for i in range(len(titles)))+'</spine></package>'
ET.fromstring(opf)
with zipfile.ZipFile(epub,'w') as z:
    z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml','<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    z.writestr('OEBPS/content.opf',opf)
    z.writestr('OEBPS/style.css','body{font-family:serif;line-height:1.6;margin:5%}h1,h2,h3{font-family:sans-serif}h2{border-bottom:2px solid #777}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8em}table{border-collapse:collapse;font-size:.85em}td,th{border:1px solid #888;padding:.4em}a{overflow-wrap:anywhere}')
    for name,value in entries.items():z.writestr('OEBPS/'+name,value,compress_type=zipfile.ZIP_DEFLATED)
print('EPUB: 33 books + static appendix',flush=True)
# GitHub-native edition: preserve canonical files, rewrite reading links in mirrors.
GH=ROOT/'github';GH.mkdir(exist_ok=True)
for p in BOOKS:
    source=p.read_text(encoding='utf-8');parts=re.split(r'(^```[^\n]*\n.*?^```[^\n]*$)',source,flags=re.M|re.S);source=''.join(re.sub(r'\]\(([^)]+)\)',lambda m:']('+ (Path(m[1].split('#')[0]).stem+'.md'+('#'+m[1].split('#',1)[1] if '#' in m[1] else '') if any(b.stem==Path(m[1].split('#')[0]).stem for b in BOOKS) else m[1] if m[1].startswith(('http:','https:','#')) else '../'+m[1])+')',part) if j%2==0 else part for j,part in enumerate(parts))
    lines=source.splitlines();insertions={}
    for idx,token in enumerate(MD.parse(source)):
        if token.type=='heading_open':insertions[token.map[0]]=f'<a name="section-{idx}"></a>'
    source='\n'.join((insertions.get(i,'')+'\n' if i in insertions else '')+line for i,line in enumerate(lines))
    source=source.replace('](../index.html)','](README.md)').replace('](../START-HERE.html)','](../START-HERE.md)').replace('](../STUDY-ON-ANY-DEVICE.html)','](../STUDY-ON-ANY-DEVICE.md)')
    n=BOOKS.index(p);links=['[Library](README.md)'];
    if n:links.append('[Previous]('+BOOKS[n-1].name+')')
    if n+1<len(BOOKS):links.append('[Next]('+BOOKS[n+1].name+')')
    (GH/p.name).write_text(' | '.join(links)+'\n\n'+source+'\n\n'+' | '.join(links)+'\n',encoding='utf-8')
(GH/'README.md').write_text('# Read on GitHub\n\nComplete current prose and code listings. Browser experiments have [static equivalents](../output/STATIC-EXPERIMENTS.md). Follow Previous and Next in each notebook.\n\n'+''.join(f'{i+1}. [{p.read_text(encoding="utf-8").splitlines()[0][2:]}]({p.name})\n' for i,p in enumerate(BOOKS)),encoding='utf-8')
report={'full_pdf_pages':len(PdfReader(full).pages),'carousel_pages':len(PdfReader(carousel).pages),'epub_reading_documents':len(titles),'github_books':len(BOOKS),'scope':'Full current notebook prose and code; existing curriculum gaps and evidence limitations remain. Carousel is a concise companion. EPUB XML parsed; reader compatibility and PDF visual review are separate checks.'}
(OUT/'edition-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
