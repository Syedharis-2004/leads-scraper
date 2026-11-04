import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./pages/dashboard/dashboard').then(m => m.Dashboard),
    title: 'Dashboard — AI Lead Generator',
  },
  {
    path: 'find-leads',
    loadComponent: () => import('./pages/find-leads/find-leads').then(m => m.FindLeads),
    title: 'Find Leads — AI Lead Generator',
  },
  {
    path: 'all-leads',
    loadComponent: () => import('./pages/all-leads/all-leads').then(m => m.AllLeads),
    title: 'All Leads — AI Lead Generator',
  },
  {
    path: 'api-settings',
    loadComponent: () => import('./pages/api-settings/api-settings').then(m => m.ApiSettings),
    title: 'API Settings — AI Lead Generator',
  },
  {
    path: 'activity-logs',
    loadComponent: () => import('./pages/activity-logs/activity-logs').then(m => m.ActivityLogs),
    title: 'Activity Logs — AI Lead Generator',
  },
  {
    path: 'app-settings',
    loadComponent: () => import('./pages/app-settings/app-settings').then(m => m.AppSettings),
    title: 'Application Settings — AI Lead Generator',
  },
  { path: '**', redirectTo: '' },
];
