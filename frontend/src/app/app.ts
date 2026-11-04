import { Component, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

interface NavItem {
  label: string;
  icon: string;
  path: string;
}

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly sidebarOpen = signal(false);

  protected readonly navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z', path: '' },
    { label: 'Find Leads', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z', path: 'find-leads' },
    { label: 'All Leads', icon: 'M9 17H7A5 5 0 017 7h2m6 10h2a5 5 0 000-10h-2M8 12h8', path: 'all-leads' },
    { label: 'API Settings', icon: 'M15 7a4 4 0 11-8 0 4 4 0 018 0zM12 15a7 7 0 00-7 7m14 0a7 7 0 00-7-7m0 0v4m0-4H8m4 0h4', path: 'api-settings' },
    { label: 'Activity Logs', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4', path: 'activity-logs' },
    { label: 'App Settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z', path: 'app-settings' },
  ];

  toggleSidebar() {
    this.sidebarOpen.update(v => !v);
  }
}
