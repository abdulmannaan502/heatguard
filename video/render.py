import asyncio, sys, subprocess, math
from playwright.async_api import async_playwright
FPS=24; DUR=170.1+0.4
N=math.ceil(DUR*FPS)
part=int(sys.argv[1]); parts=int(sys.argv[2])
a=part*N//parts; b=(part+1)*N//parts
out=f'/tmp/claude-0/chunk_{part}.mp4'
async def main():
    ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate',str(FPS),'-vcodec','mjpeg','-i','-','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-r',str(FPS),out],stdin=subprocess.PIPE)
    async with async_playwright() as p:
        br=await p.chromium.launch(); pg=await br.new_page(viewport={'width':1920,'height':1080})
        await pg.goto('http://127.0.0.1:8765/video/film_built.html'); await pg.wait_for_function('window.__ready===true',timeout=30000)
        for i in range(a,b):
            await pg.evaluate(f'render({i/FPS})')
            ff.stdin.write(await pg.screenshot(type='jpeg',quality=92))
            if i%200==0: print(part,i,flush=True)
        await br.close()
    ff.stdin.close(); ff.wait(); print('done',part,flush=True)
asyncio.run(main())
