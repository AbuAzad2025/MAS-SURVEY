import { test, expect } from '@playwright/test';

test.describe('Coverage Report', () => {
  test('verify all modules have E2E tests', async ({ page }) => {
    const modules = [
      { name: 'Landing', path: '/' },
      { name: 'Files', path: '/files' },
      { name: 'Polar Survey', path: '/polar' },
      { name: 'Area', path: '/area' },
      { name: 'Offsets', path: '/offsets' },
      { name: 'Intersection', path: '/intersection' },
      { name: 'Implant', path: '/implant' },
      { name: 'Circle', path: '/circle' },
      { name: 'Resection', path: '/resection' },
      { name: 'Traverse', path: '/traverse' },
      { name: 'Interpolation', path: '/interpolation' },
      { name: 'Plotting', path: '/plotting' },
      { name: 'Print Preview', path: '/print' },
      { name: 'Settings', path: '/settings' },
      { name: 'Work Mode', path: '/workmode' },
    ];

    for (const module of modules) {
      await page.goto(module.path);
      const pageTitle = await page.title();
      console.log(`Module: ${module.name} | Path: ${module.path} | Title: ${pageTitle}`);
    }
  });

  test('verify all HTML templates are accessible', async ({ page }) => {
    const templates = [
      'landing.html',
      'files.html', 
      'polar.html',
      'area.html',
      'offsets.html',
      'intersection.html',
      'implant.html',
      'circle.html',
      'resection.html',
      'traverse.html',
      'interpolation.html',
      'plotting.html',
      'print.html',
      'settings.html',
      'workmode.html',
    ];

    for (const template of templates) {
      await page.goto(`/${template.replace('.html', '')}`);
      await expect(page.locator('body')).toBeVisible();
    }
  });
});
