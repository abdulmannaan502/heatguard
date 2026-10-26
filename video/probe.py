import asyncio, sys, json
from playwright.async_api import async_playwright
ts=[float(x) for x in sys.argv[1:]]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1920,'height':1080})
        msgs=[]; pg.on('console',lambda m:msgs.append(m.text)); pg.on('pageerror',lambda e:msgs.append('ERR '+str(e)))
        await pg.goto('http://127.0.0.1:8765/video/film_built.html'); await pg.wait_for_function('window.__ready===true',timeout=20000)
        for t in ts:
            await pg.evaluate(f'render({t})'); await pg.wait_for_timeout(120)
            await pg.screenshot(path=f'/tmp/claude-0/f_{int(t*10):04d}.png')
        print(msgs[:5]); await b.close()
asyncio.run(main())
