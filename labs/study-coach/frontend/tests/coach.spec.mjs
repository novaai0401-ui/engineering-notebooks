import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
test('keyboard sign-in, approval, live answer, route and accessibility',async({page})=>{
 await page.goto('/');
 await page.getByLabel('Learner',{exact:true}).fill('alice');
 await page.getByLabel('Password',{exact:true}).fill(process.env.COACH_PASSWORD);
 await page.getByLabel('Password',{exact:true}).press('Enter');
 await page.getByLabel('Study question').fill('What is a checkpoint?');
 await page.getByRole('button',{name:'Create study job'}).click();
 await expect(page.getByRole('status')).toContainText('approval');
 await page.getByRole('button',{name:'Approve question'}).focus();await page.keyboard.press('Enter');
 await expect(page.getByRole('status')).toContainText('done',{timeout:20000});
 await expect(page.getByText(/A checkpoint saves workflow state/)).toBeVisible();
 const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
 expect(results.violations).toEqual([]);
 await page.getByRole('link',{name:'Architecture',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Follow one question'})).toBeVisible();
});
test('cancel before approval never runs',async({page})=>{
 await page.goto('/');await page.getByLabel('Password',{exact:true}).fill(process.env.COACH_PASSWORD);await page.getByRole('button',{name:'Sign in',exact:true}).click();
 await page.getByRole('button',{name:'Create study job'}).click();await page.getByRole('button',{name:'Cancel job',exact:true}).click();
 await expect(page.getByRole('status')).toContainText('cancelled');
 await expect(page.getByRole('status')).toContainText('attempt: 0');
});
