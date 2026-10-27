# DOM only. No hidden JSON state, private endpoints, intercepted requests or anti-bot workarounds.
COMMON = r"""
const visible=e=>{if(!e)return false;const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none';};
const text=(document.body?.innerText||'').replace(/\u200b/g,'');
const blocked=/подтвердите,? что вы|проверка.{0,15}(робот|браузер)|доступ.{0,12}ограничен|слишком много запросов|captcha|access denied|verify you are human|войдите.{0,30}(просмотр|контакт|продолж)|авторизуйтесь/i.test((document.title+' '+text).slice(0,15000))||[...document.querySelectorAll('iframe[src*="captcha"]')].some(visible);
"""
LIST_SCRIPT = (
    "(()=>{"
    + COMMON
    + r"""
const links=[...document.querySelectorAll('a[href]')].filter(visible).map(a=>({url:a.href,name:(a.innerText||a.getAttribute('aria-label')||'').trim()})).filter(a=>/^https:\/\/2gis\.ru\/[a-z0-9_-]+\/firm\/\d+/.test(a.url));
return {blocked,url:location.href,links:links.map(a=>({...a,url:a.url.match(/^https:\/\/2gis\.ru\/[^/]+\/firm\/\d+/)[0]})),empty:/ничего не найдено|не нашли организаций|по вашему запросу ничего/i.test(text)};
})()"""
)
SCROLL_SCRIPT = (
    "(()=>{"
    + COMMON
    + r"""
let anchors=[...document.querySelectorAll('a[href*="/firm/"]')].filter(visible);
let scroller=null;
for(const anchor of anchors){for(let p=anchor.parentElement;p&&p!==document.body;p=p.parentElement){if(p.scrollHeight>p.clientHeight+30&&/(auto|scroll)/.test(getComputedStyle(p).overflowY)){scroller=p;break;}}if(scroller)break;}
if(scroller){const before=scroller.scrollTop;scroller.scrollBy(0,Math.max(350,scroller.clientHeight*.85));return {scrolled:scroller.scrollTop>before};}
const before=window.scrollY;window.scrollBy(0,650);return {scrolled:window.scrollY>before};
})()"""
)
NEXT_SCRIPT = (
    "(()=>{"
    + COMMON
    + r"""
const button=[...document.querySelectorAll('a,button')].filter(visible).find(e=>e.rel==='next'||/^следующ(ая|ие|ий)( страница)?$/i.test((e.getAttribute('aria-label')||e.innerText||'').trim()));
if(button&&!button.disabled){const href=button.getAttribute('href');if(href&&new URL(href,location.href).hostname!=='2gis.ru')return false;button.click();return true;}return false;
})()"""
)
EXPAND_SCRIPT = (
    "(()=>{"
    + COMMON
    + r"""
if(blocked)return {blocked:true};
const candidates=[...document.querySelectorAll('button,a,div[role="button"]')].filter(visible).filter(e=>/^показать (телефон|номер|ещ[её] \d+ телефон)/i.test((e.innerText||'').trim()));
if(candidates.length){candidates[0].click();return {clicked:true};}
return {clicked:false};
})()"""
)
CARD_SCRIPT = (
    "(()=>{"
    + COMMON
    + r"""
const h1=[...document.querySelectorAll('h1')].find(visible);
if(!h1)return {blocked,ready:false,url:location.href};
const anchors=[...document.querySelectorAll('a[href]')].filter(visible);
const links=anchors.map(a=>({url:a.href,label:(a.innerText||a.getAttribute('aria-label')||'').trim(),itemprop:a.getAttribute('itemprop')||'',context:(a.parentElement?.innerText||'').slice(0,450)}));
const addressNode=[...document.querySelectorAll('[itemprop="address"],[itemprop="streetAddress"]')].find(visible);
const ratingNode=[...document.querySelectorAll('[itemprop="ratingValue"]')].find(visible);
const reviewsNode=[...document.querySelectorAll('[itemprop="reviewCount"]')].find(visible);
const address=addressNode?.innerText||anchors.find(a=>a.href.includes('/geo/'))?.innerText||null;
const lines=text.split('\n').map(s=>s.trim()).filter(Boolean);
const reviewsLink=anchors.find(a=>a.href.includes('/tab/reviews'));
const categoryLinks=[...(h1.parentElement?.parentElement?.querySelectorAll('a[href*="/search/"]')||[])].filter(visible);
const reviewLine=lines.find(s=>/^\d[\d\s]*\s+отзыв(ов|а)?$/i.test(s));
let rating=ratingNode?.innerText||null;
if(!rating){const idx=lines.findIndex(s=>/^\d[\d\s]*\s+оцен(ок|ки|ка)$/i.test(s));if(idx>0&&/^[0-5]([.,]\d)?$/.test(lines[idx-1]))rating=lines[idx-1];}
return {blocked,ready:document.readyState!=='loading',name:h1.innerText.trim(),category:categoryLinks[0]?.innerText.trim()||null,url:location.href,links,address,rating,reviews:reviewsNode?.innerText||reviewsLink?.innerText||reviewLine||null,websiteAbsentExplicit:lines.some(s=>/^(сайт не указан|сайта нет)[.!]?$/i.test(s)),hasCollapsedPhone:[...document.querySelectorAll('button,a,div[role="button"]')].filter(visible).some(e=>/^показать (телефон|номер)/i.test(e.innerText||''))};
})()"""
)
