"""Short, contrasting performance phrases authored from an explicit source motif.
These are editable candidates, not universal genre definitions or taste judgments.
"""
import copy, math
IDS=('dog','bear','cat','lion')
def rewrite(recipe,source,tonic,minor=False,hook_start=0,bars=4):
    r=copy.deepcopy(recipe);style=r['style'];meter=r['beatsPerBar'];end=bars*meter
    assert style in ('electronic','jazz-funk','bossa-nova','swing-jazz','drift-phonk')
    assert bars>=2 and meter in (2,3,4)
    sections={mode:{'bars':bars,'tracks':{k:[] for k in IDS}} for mode in ('build','drop')}
    def add(mode,k,p,t,d,v):
        if 0<=t<end and d>0:sections[mode]['tracks'][k].append(dict(midi=int(p),beat=round(t,6),duration=round(min(d,end-t),6),velocity=int(v),channel=9 if k=='dog' else 0))
    def swing(t):
        q=math.floor(t);f=t-q;return q+(f*1.24 if f<=.5 else .62+(f-.5)*.76)
    def chord(root,minor_chord=False,dominant_chord=False):
        root=tonic+root
        while root>47:root-=12
        while root<33:root+=12
        third=3 if minor_chord else 4
        return root,[root+12+third,root+12+(10 if minor_chord or dominant_chord else 11),root+26]
    main=chord(0,minor);sub=chord(5,True);dominant=chord(7,False,True);relative=chord(9,True)
    progression=[main,sub,dominant,main] if minor else [main,relative,sub,dominant]
    build_progression=[sub,sub,dominant,main]
    source_notes=sorted(source['melody'],key=lambda n:n['beat'])
    motif=[copy.deepcopy(n) for n in source_notes if hook_start<=n['beat']<hook_start+end]
    if not motif:raise ValueError('selected hook has no source notes')
    for n in motif:n['beat']-=hook_start
    # A complete short quotation; no audio crop or replay of the full theme.
    for i,n in enumerate(motif):
        at=swing(n['beat']) if style=='swing-jazz' else n['beat'];nxt=(swing(motif[i+1]['beat']) if style=='swing-jazz' else motif[i+1]['beat']) if i+1<len(motif) else end
        p=n['midi'];d=min(n['duration']*.82,nxt-at-.06)
        if style=='drift-phonk':p+=12;d=min(d,.30)
        elif style=='electronic':d=min(d,.42)
        elif style=='jazz-funk':d=min(d,.62)
        elif style=='bossa-nova':
            # Small anticipations at phrase interiors, preserving breathing room.
            if i and n['beat']%meter in (1,3):at=max(0,at-.125)
            d=min(d,1.1)
        if at<end-.65:add('drop','lion',p,at,max(.06,d),80 if style!='bossa-nova' else 73)
    # A short tonic resolution leaves a deliberate breath before repeat/return.
    target=tonic+(12 if style=='drift-phonk' else 0)
    while target<64:target+=12
    while target>82:target-=12
    for notes in sections['drop']['tracks'].values():
        for n in notes:
            if n['beat']+n['duration']>end-.65:n['duration']=max(.04,end-.65-n['beat'])
    add('drop','lion',target,end-.60,.38,77 if style!='bossa-nova' else 65)
    for bar in range(bars):
        b=bar*meter;u=meter/4;root,voice=progression[bar%4];br,bv=build_progression[bar%4]
        if style=='swing-jazz':
            # KEY6: sax rests, bass takes the front; snare/hat answer instead of ride ostinato.
            for t,p,d in [(0,br,.65),(1.62,br+7,.28),(2.5,br+12,.48)]:add('build','cat',p,b+t*u,d*u,79)
            for t in (1,3):add('build','dog',44,b+t*u,.10,31)
            if bar in (1,bars-1):
                for t,v in ((2.62,43),(3.30,52),(3.66,44)):add('build','dog',38,b+t*u,.11,v)
            for p in bv:add('build','bear',p,b+.62*u,.36,43)
            if bar==bars-1:
                for t,p in [(1.62,tonic+12),(2.62,tonic+7),(3.25,tonic+12)]:add('build','bear',p,b+t*u,.20,65)
            # KEY7: four-bar ensemble statement, walking bass and full ride immediately.
            nr=progression[(bar+1)%4][0]
            for t,p in [(0,root),(1,root+7),(2,root+12),(3,nr-1)]:add('drop','cat',p,b+t*u,.78*u,75 if t==0 else 67)
            for t,v in [(0,60),(1,44),(1.62,32),(2,55),(3,44),(3.62,32)]:add('drop','dog',51,b+t*u,.10,v)
            for t in (1,3):add('drop','dog',44,b+t*u,.08,39)
            add('drop','dog',36,b,.09,39)
            for t in ([0,2.62] if bar%2==0 else [1.62,3.25]):
                for p in voice:add('drop','bear',p,b+t*u,.36,57)
        elif style=='jazz-funk':
            # Breakdown: Rhodes answers a syncopated bass solo, sax tacet.
            for t,p in [(0,br),(1.75,br+12),(2.5,br+7)]:add('build','cat',p,b+t*u,.36,83)
            add('build','dog',36,b,.10,51)
            for t in (1,3):add('build','dog',37,b+t*u,.10,38)
            for t in (.75,2.75):
                for p in bv:add('build','bear',p,b+t*u,.21,58)
            # Tight band riff: fewer keys, stronger shared kick/bass anchors.
            anchors=(0,.75,2.5)
            for t in anchors:add('drop','dog',36,b+t*u,.10,96 if t==0 else 80);add('drop','cat',root+(12 if t==.75 else 0),b+t*u,.43*u,88)
            for t in (1,3):add('drop','dog',38,b+t*u,.10,87)
            for j in range(8):add('drop','dog',42,b+j*.5*u,.07,41 if j%2==0 else 29)
            for t in (0,2.5):
                for p in voice:add('drop','bear',p,b+t*u,.22,65)
            if bar==bars-1:
                for t in (2.75,3.25):add('build','dog',38,b+t*u,.08,45)
        elif style=='bossa-nova':
            # Guitar interlude: flute completely leaves; retain quiet low/high guitar separation.
            for t,p in [(0,br+12),(2,br+19)]:add('build','bear',p,b+t*u,.65,48)
            for t in (.75,2.5):
                for p in bv:add('build','bear',p,b+t*u,.34,44)
            if bar%2==0:add('build','cat',br,b,1.1,43)
            add('build','dog',37,b+3*u,.10,23)
            # Flute return and guitar harmonic texture, still a Bossa groove rather than loud EDM.
            for t,p in [(0,root+12),(2,root+19)]:add('drop','bear',p,b+t*u,.65,59)
            for t in ((.75,1.5,2.75) if bar%2==0 else (.5,1.75,3.25)):
                for p in voice:add('drop','bear',p,b+t*u,.34,51)
            for t in (0,2):add('drop','cat',root+(7 if t==2 else 0),b+t*u,.70,61)
            for t in (1,3):add('drop','dog',37,b+t*u,.10,34)
            for t in (0,1.5,2,3.5):add('drop','dog',42,b+t*u,.07,22)
        elif style=='drift-phonk':
            # No kick/bass during KEY6: the low-frequency withdrawal is audible, not a label.
            for j in range(4):add('build','dog',42,b+j*u,.045,24+bar*3)
            if bar==bars-1:
                for t,v in ((2.5,35),(3,47),(3.5,57)):add('build','dog',39,b+t*u,.08,v)
            for p in bv[1:]:add('build','bear',p,b,1.25,26)
            if bar<bars-1:
                chosen=motif[(bar*3)%len(motif)]['midi']+12
                for t in (.5,2.5):add('build','lion',chosen,b+t*u,.18,53)
            # Full low end + short counter-rhythm; bass and kick share anchors.
            for t in (0,.75,2,2.75):add('drop','dog',36,b+t*u,.10,113 if t==0 else 95)
            for t in (1,3):add('drop','dog',39,b+t*u,.10,96)
            for j in range(8):add('drop','dog',42,b+j*.5*u,.05,43 if j%2==0 else 29)
            for t,p,d in [(0,root,.68),(.75,root,.28),(2,root,.43),(2.75,root+12,.25)]:add('drop','cat',p,b+t*u,d*u,101)
            if bar%2==0:
                for p in voice[1:]:add('drop','bear',p,b,.85,29)
        else:
            # Electronic: rising rhythmic tension vs immediate four-on-floor and octave bass.
            for p in bv:add('build','bear',p,b,.75,40+bar*5)
            count=4 if bar<2 else 8 if bar==2 else 12
            for j in range(count):
                t=j*meter/count
                if b+t<end-.5:add('build','dog',38,b+t,.07,30+bar*10+j)
            if bar<2:add('build','cat',br,b,.45,49)
            if bar<bars-1:add('build','lion',motif[(bar*3)%len(motif)]['midi'],b+.5*u,.36,62)
            for t in range(meter):add('drop','dog',36,b+t,.12,106)
            for t in (1,3):add('drop','dog',38,b+t*u,.10,83)
            for j in range(8):add('drop','dog',42,b+j*.5*u,.065,40 if j%2==0 else 30)
            for t in (.5,1.5,2.5,3.5):add('drop','cat',root+(12 if int(t)%2 else 0),b+t*u,.30,92)
            for t in (.5,2.5):
                for p in voice:add('drop','bear',p,b+t*u,.30,61)
    for mode in sections:
        for k in IDS:sections[mode]['tracks'][k].sort(key=lambda n:(n['beat'],n['midi']))
    r['sectionScores'].update(sections);r['reuseSections']=['theme','hold'];r['design']['structure']=f"theme{r['sectionScores']['theme']['bars']} / build{bars} / drop{bars} / hold{r['sectionScores']['hold']['bars']}";r['design']['performanceRevision']={'version':2,'clipBars':bars,'hookStartBeat':hook_start,'purpose':'short complete performance phrases; lead tacet in acoustic interludes / absent low end in electronic breakdown; full groove and source-body quotation on variation','repeatPolicy':'each keypress appends one complete clip; do not repeat a full chorus automatically','auditionStatus':'candidate, user listening pending'}
    return r
