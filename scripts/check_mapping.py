"""Real local model inference, two UI mapping approvals, push and rollback."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        try:
            page.goto(os.environ.get('DEMO_URL', 'http://localhost:3000'))
            page.locator('#new-btn').click()
            page.locator('#migration-name').fill('Python semantic mapping verification')
            page.locator('#files').set_input_files(str(ROOT / 'backend/samples/semantic-mapping.csv'))
            page.get_by_role('button', name='Start migration', exact=True).click()
            expect(page.locator('#run-status')).to_have_text('Mapping review', timeout=120000)
            page.get_by_role('tab', name='Review queue', exact=False).click()
            group = page.locator('.mapping-form[data-header="Business group"]')
            expect(group).to_contain_text('Model suggestions:')
            group.locator('select').select_option('department')
            group.locator('input[name="reason"]').fill('Business group is the client department.')
            page.screenshot(path=str(ROOT / 'docs/model-mapping.png'), full_page=True)
            group.get_by_role('button', name='Approve mapping').click()
            expect(group).to_have_count(0)
            contact = page.locator('.mapping-form[data-header="Status"]')
            contact.locator('select').select_option('employment_status')
            contact.locator('input[name="reason"]').fill('Client confirmed this is HR lifecycle status.')
            contact.get_by_role('button', name='Approve mapping').click()
            expect(page.locator('#run-status')).to_have_text('Migration complete', timeout=15000)
            expect(page.locator('#stat-pushed')).to_have_text('1')
            page.get_by_role('tab', name='Overview', exact=True).click()
            page.get_by_role('button', name='Roll back writes').click()
            page.get_by_role('dialog').get_by_role('button', name='Roll back writes').click()
            expect(page.locator('#run-status')).to_have_text('Rolled back')
        finally:
            browser.close()
    print('Python model inference and mapping review workflow verified.')

if __name__ == '__main__':
    main()
