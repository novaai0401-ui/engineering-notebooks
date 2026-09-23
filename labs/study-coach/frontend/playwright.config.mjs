import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests',timeout:90000,workers:1,projects:[{name:'chromium',use:{browserName:'chromium'}},{name:'firefox',use:{browserName:'firefox'}},{name:'webkit',use:{browserName:'webkit'}}],use:{baseURL:'http://127.0.0.1:8091',headless:true},reporter:[['list'],['json',{outputFile:'test-results/report.json'}]]});
