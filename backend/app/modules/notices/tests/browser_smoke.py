from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1600,'height':1100})
 page.route('https://**/*',lambda r:r.abort())
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 api=page.request
 base='http://127.0.0.1:5173'
 assert api.post(base+'/api/demo/reset',data={'scenario_id':'harvey_houston'}).ok
 page.goto(base)
 page.get_by_role('button',name='Fix-First',exact=True).click()
 page.get_by_label('Notice building').select_option('BLD-HOU-01')
 page.locator('fieldset input[type=checkbox]').first.check()
 page.get_by_label('Emergency instructions').fill('Ground floor closed at 16:00. Reply for assistance.')
 page.get_by_role('button',name='Preview customer notice').click()
 page.get_by_role('region',name='Notice preview').wait_for()
 page.get_by_role('button',name='Simulate customer notice').click()
 page.get_by_text('recorded (no real text)',exact=False).wait_for()
 messages=api.get(base+'/api/messages').json()
 assert len([m for m in messages if m['kind']=='tenant_notice'])==1
 page.get_by_role('button',name='Prepare another notice').click()
 page.get_by_role('button',name='Preview customer notice').click()
 api.post(base+'/api/timeline',data={'hour':0})
 page.get_by_role('button',name='Simulate customer notice').click()
 page.get_by_text('Scenario or timeline changed.',exact=False).wait_for()
 assert len([m for m in api.get(base+'/api/messages').json() if m['kind']=='tenant_notice'])==1
 assert not errors,errors
 page.screenshot(path='/workspace/work/customer-notice.png')
 print('PASS: preview, selected customer send, simulator receipt, stale preview rejected without extra send; no browser errors')
 browser.close()
