"""Record the actual UI. Default: paced 3–5 minute demo; --quick: smoke check."""
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[1]

def main():
    quick = '--quick' in sys.argv
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width':1440,'height':1000}, record_video_dir=str(ROOT/'docs/recordings'), record_video_size={'width':1440,'height':1000})
        page = context.new_page()
        errors=[]
        page.on('pageerror',lambda exc:errors.append(str(exc)))
        def scene(text, seconds=15):
            print(text,flush=True)
            page.evaluate('''text => {
              let b=document.getElementById('demo-caption');
              if(!b){b=document.createElement('div');b.id='demo-caption';
                b.style.cssText='position:fixed;bottom:14px;left:280px;right:24px;padding:18px 24px;background:#112b28;color:white;font:18px/1.5 sans-serif;border-radius:12px;z-index:99999;pointer-events:none';document.body.appendChild(b);}
              b.textContent=text;
            }''',text)
            page.wait_for_timeout(200 if quick else seconds*1000)
        started=time.monotonic()
        try:
            page.goto(os.environ.get('DEMO_URL','http://localhost:3000'))
            page.locator('#new-btn').click()
            page.locator('#migration-name').fill('Northstar · HR migration demo')
            page.locator('#files').set_input_files([str(ROOT/'backend/samples'/n) for n in ('employees_hr.csv','employees_backup.csv','staff.xlsx')])
            page.get_by_role('checkbox',name='Simulate target failures').check()
            scene('1 / Upload two CSVs and one Excel export. Failure simulation is explicitly enabled for this demo.')
            page.get_by_role('button',name='Start migration',exact=True).click()
            scene('2 / The agent profiles each source, applies known aliases, and consults local AI for unfamiliar columns.')
            expect(page.locator('#run-status')).to_have_text('Mapping review',timeout=180000)
            expect(page.locator('#stat-review')).to_have_text('1')
            scene('3 / Only one mapping needs judgment. No target writes occur while this decision is unresolved.')
            page.screenshot(path=str(ROOT/'docs/workspace.png'),full_page=True)
            page.get_by_role('button',name='Review decisions').click()
            card=page.locator('.mapping-form[data-header="Status"]')
            expect(card).to_contain_text('HR employment')
            card.evaluate("el=>el.scrollIntoView({block:'center'})")
            scene('4 / Status could describe employment or login access. The queue shows source values, model reasoning and evidence.',20)
            card.locator('select').select_option('employment_status')
            card.locator('input[name="reason"]').fill('Client confirmed staff.xlsx is an HR lifecycle export; Status means employment status.')
            page.screenshot(path=str(ROOT/'docs/escalation.png'),full_page=True)
            scene('5 / The consultant selects Employment status and records the reason. No field-by-field confirmation is needed.')
            card.get_by_role('button',name='Approve mapping').click()
            expect(page.locator('#run-status')).to_have_text('Delivery needs attention',timeout=30000)
            expect(page.locator('#stat-pushed')).to_have_text('6')
            page.get_by_role('tab',name='All records').click()
            scene('6 / Delivery resumed automatically: eight source rows become seven employees. The duplicate retains its source lineage.',20)
            scene('7 / E006 recovered automatically. E007 failed three attempts, so the agent stopped retrying and surfaced the failure.',20)
            page.get_by_role('button',name='Retry failed records').click()
            expect(page.locator('#run-status')).to_have_text('Migration complete',timeout=30000)
            expect(page.locator('#stat-pushed')).to_have_text('7')
            scene('8 / Retry succeeds. All seven unique employees have target IDs; successful records were not inserted again.')
            page.get_by_role('tab',name='Audit trail').click()
            page.locator('.audit-row').filter(has_text='Mapping resolved').locator('summary').click()
            scene('9 / The audit records the original AI proposal, human decision, actor and reason. Every retry is also recorded.',20)
            cleanup=page.locator('.audit-row').filter(has_text='Safe cleanup').first
            cleanup.locator('summary').click()
            cleanup.scroll_into_view_if_needed()
            scene('10 / Before-and-after evidence shows safe whitespace, email, status and date normalization. No missing facts were invented.',20)
            page.get_by_role('tab',name='Overview',exact=True).click()
            page.get_by_role('button',name='Roll back writes').click()
            scene('11 / Rollback is a deliberate human action. Only this run’s target inserts will be removed.')
            page.get_by_role('dialog').get_by_role('button',name='Roll back writes').click()
            expect(page.locator('#run-status')).to_have_text('Rolled back')
            expect(page.locator('#stat-pushed')).to_have_text('0')
            scene('12 / Rollback complete. Source data and the full audit remain available for inspection.')
            page.evaluate("document.getElementById('demo-caption')?.remove()")
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(ROOT/'docs/mobile.png'),full_page=True)
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'),'Mobile overflow'
            assert not errors,errors
        finally:
            video=page.video
            context.close()
            video.save_as(str(ROOT/'docs'/('smoke.webm' if quick else 'demo.webm')))
            video.delete()
            browser.close()
        print(f'UI workflow verified; elapsed {time.monotonic()-started:.1f}s.',flush=True)

if __name__=='__main__':
    main()
