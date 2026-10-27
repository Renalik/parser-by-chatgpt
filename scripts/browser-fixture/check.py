"""Run the isolated Node CDP fixture first; no real site is accessed."""
import asyncio,time
from backend.app.browser.driver import BrowserService
from backend.app.providers.browser import BrowserProvider
from backend.app.models import SearchSpec
async def main():
    service=BrowserService();service.port=9334
    provider=BrowserProvider(service)
    provider.wait=lambda seconds:time.sleep(min(seconds,.15))
    spec=SearchSpec(mode='browser',cities=[{'name':'Москва','region_id':'moscow'}],categories=['Кафе'])
    rows=[]
    for n in range(1,6):
        found,more=await provider.page(spec,spec.cities[0],'Кафе',n);rows+=found
        if not more:break
    assert [r.id for r in rows]==['101','102','103'],[r.id for r in rows]
    assert all(r.phone=='+70000000000' and r.website.rstrip('/')=='https://example.org' and r.telegram=='https://t.me/example' and r.reviews==12 for r in rows)
    assert all(r.field_status['email']=='unknown' for r in rows)
    service.close()
    print('Real CDP: scroll, card navigation, reveal phone, contact extraction and exhaustion passed.')
asyncio.run(main())
