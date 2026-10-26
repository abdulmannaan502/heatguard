import json
tl=json.load(open('/home/claude/heatguard/video/timeline.json'))
h=open('/home/claude/heatguard/video/film.html').read().replace('/*TL*/[]',json.dumps(tl))
open('/home/claude/heatguard/video/film_built.html','w').write(h)
