const { JSDOM, VirtualConsole } = require('jsdom');
const url = 'https://slgi-life.duckdns.org/dashboard';
const vc = new VirtualConsole();
vc.on('error', (...args) => console.log('[console.error]', ...args));
vc.on('warn', (...args) => console.log('[console.warn]', ...args));
vc.on('jsdomError', (err) => console.log('[jsdomError]', err.message, err.stack && err.stack.split('\n')[0]));
(async () => {
  const dom = await JSDOM.fromURL(url, {
    resources: 'usable',
    runScripts: 'dangerously',
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.HTMLCanvasElement.prototype.getContext = () => null;
      window.scrollTo = () => {};
      window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
      window.IntersectionObserver = class { observe() {} unobserve() {} disconnect() {} };
      window.matchMedia = () => ({matches:false, addListener(){}, removeListener(){}, addEventListener(){}, removeEventListener(){}, dispatchEvent(){return false;}});
    }
  });
  await new Promise(r => setTimeout(r, 8000));
  console.log('title=', dom.window.document.title);
  console.log('bodyText=', dom.window.document.body.textContent.replace(/\s+/g,' ').slice(0,500));
})();