import sys, json, numpy as np, soundfile as sf
sys.path.insert(0, '.')
from narration import SEGMENTS
from kokoro_onnx import Kokoro
k = Kokoro('/tmp/claude-0/tts/kokoro.onnx', '/tmp/claude-0/tts/voices.bin')
VOICE, SPEED = 'af_heart', 1.07
sr = 24000
audio, timeline, t = [], [], 0.0
gap = np.zeros(int(sr * 0.28)); scene_gap = np.zeros(int(sr * 0.9))
for name, sents in SEGMENTS:
    start = t
    sent_tl = []
    for s in sents:
        x, r = k.create(s, voice=VOICE, speed=SPEED, lang='en-us'); assert r == sr
        sent_tl.append(dict(text=s, start=t, end=t + len(x) / sr)); audio.append(x); t += len(x) / sr
        audio.append(gap); t += len(gap) / sr
    audio.append(scene_gap); t += len(scene_gap) / sr
    timeline.append(dict(scene=name, start=start, end=t, sents=sent_tl))
y = np.concatenate(audio).astype(np.float32)
sf.write('narration.wav', y, sr)
json.dump(timeline, open('timeline.json', 'w'), indent=1)
print('total', round(t, 1), 's'); [print(s['scene'], round(s['start'], 1), round(s['end'], 1)) for s in timeline]
