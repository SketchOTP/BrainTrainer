"""Small object-sprite vision shared with the habitat renderer.

The learner sees a pre-segmented, unoccluded 12x12 object image, not a camera
frame. Pixels are authored game graphics, and never depend on hidden toxin.
"""
SIZE=12
PALETTE={
    '.':'#00000000', 'k':'#273128', 'w':'#d6cba8', 'r':'#a34d3e',
    'o':'#c08a4d', 'g':'#71865a', 'b':'#638a91', 'y':'#d1b963',
    'p':'#96798a', 's':'#788176', 'n':'#67513e', 'c':'#a9ad84',
}
RGB={k:tuple(int(v[i:i+2],16) for i in (1,3,5)) if k!='.' else (0,0,0) for k,v in PALETTE.items()}


def validate(pixels):
    if pixels is None:return None
    if not isinstance(pixels,list) or len(pixels)!=SIZE or any(not isinstance(row,str) or len(row)!=SIZE or any(c not in PALETTE for c in row) for row in pixels):
        raise ValueError('invalid 12x12 visual sprite')
    if all(c=='.' for row in pixels for c in row):raise ValueError('empty visual sprite')
    return list(pixels)


def pixels_for(item):
    """Return the exact individual sprite pixels the web renderer displays."""
    if item.visual is not None:return item.visual
    # Physical appearance derives only from publicly rendered shape and category,
    # never from whether an object is toxic or causes harm.
    if item.kind=='food':
        color='r' if item.category==8 else ('y' if item.category==3 else 'o')
        return ['............','.....gg.....','....ggg.....','...kkkkkk...','..k'+color*6+'k..',
                '.k'+color*8+'k.','.k'+color*8+'k.','.k'+color*8+'k.','..k'+color*6+'k..','...kkkkkk...','............','............']
    if item.kind=='toy':
        return ['............','............','..kkkkkkkk..','..kbbbbbbk..','..kbwbbwbk..',
                '..kbbbbbbk..','..kbbkkbbk..','..kbbbbbbk..','..kkkkkkkk..','............','............','............']
    if item.kind=='trinket':
        return ['............','............','.....kk.....','....kcck....','...kcccck...',
                '..kcccccck..','...kcccck...','....kcck....','.....kk.....','............','............','............']
    if item.kind=='danger':
        return ['............','.....kk.....','..k..kk..k..','..kkksskkk..','..kssssssk..',
                '.kksssssskk.','.kssssssssk.','..kssssssk..','..kkkkkkkk..','............','............','............']
    return None


def distance(a,b):
    """Mean absolute RGB difference across the aligned visible pixel crops."""
    a=validate(a);b=validate(b)
    if a is None or b is None:return float('inf')
    total=0
    for ar,br in zip(a,b):
        for ac,bc in zip(ar,br):
            if ac==bc:continue
            x,y=RGB[ac],RGB[bc]
            total+=sum(abs(u-v) for u,v in zip(x,y))
            if (ac=='.')!=(bc=='.'):total+=255
    return total/(SIZE*SIZE*4*255)
