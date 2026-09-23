import {test,expect} from '@playwright/test';
test('rejected sign-in, empty question, and expired authorization are visible',async({page})=>{
 await page.goto('/');await page.getByLabel('Password',{exact:true}).fill('deliberately-wrong-password');await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await expect(page.getByRole('alert')).toContainText('Sign-in failed');
 await page.getByLabel('Password',{exact:true}).fill(process.env.COACH_PASSWORD);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByLabel('Study question').fill('');await page.getByRole('button',{name:'Create study job'}).click();
 await expect(page.getByRole('status')).toHaveCount(0);
 await page.getByLabel('Study question').fill('checkpoint');
 await page.route('**/api/jobs',route=>route.fulfill({status:401,body:'Unauthorized'}));
 await page.getByRole('button',{name:'Create study job'}).click();await expect(page.getByRole('alert')).toContainText('401');
});
test('interrupted stream can reconnect and narrow layout keeps controls reachable',async({page})=>{
 await page.setViewportSize({width:375,height:812});await page.goto('/');
 await page.getByLabel('Password',{exact:true}).fill(process.env.COACH_PASSWORD);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'Create study job'}).click();
 await page.route('**/events',route=>route.abort());await page.getByRole('button',{name:'Approve question'}).click();
 await expect(page.getByRole('alert')).toBeVisible();await page.unroute('**/events');
 await page.getByRole('button',{name:'Refresh and reconnect'}).focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('status')).toContainText('done',{timeout:20000});
 await page.getByRole('button',{name:'Forget page credentials'}).click();await expect(page.getByLabel('Password',{exact:true})).toBeVisible();
 await expect(page.getByRole('status')).toHaveCount(0);
});
