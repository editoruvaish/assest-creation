import sys, asyncio
from playwright.sync_api import sync_playwright
def render(jobs):
    """jobs: list of (svg_path, png_path, width, height, bg_css_or_None)"""
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        for svg,png,w,h in jobs:
            pg=b.new_page(viewport={'width':w,'height':h})
            pg.set_content('<html><body style="margin:0;background:transparent"><img src="file://%s" style="display:block;width:%dpx;height:%dpx"></body></html>'%(svg,w,h)) if False else pg.goto('file://'+svg)
            pg.screenshot(path=png,omit_background=True,clip={'x':0,'y':0,'width':w,'height':h})
            pg.close()
        b.close()
if __name__=='__main__':
    render([(sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]))])
