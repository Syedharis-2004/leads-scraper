import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LeadsService, LeadQuery } from '../../core/services/leads.service';
import { Lead, LeadListResponse } from '../../core/models';

@Component({
  selector: 'app-all-leads',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 lg:p-8 max-w-7xl mx-auto">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-2xl font-bold text-white mb-1">All Leads</h1>
          <p class="text-ink-400 text-sm">{{ total() }} total leads</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn-secondary" (click)="loadLeads()">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
            Refresh
          </button>
          <div class="relative group">
            <button class="btn-secondary">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Export
              <svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
              </svg>
            </button>
            <div class="absolute right-0 mt-2 w-48 bg-ink-800 border border-ink-600 rounded-lg shadow-xl py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <a [href]="exportCsvUrl()" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700" download>Export CSV (all)</a>
              <a [href]="exportJsonUrl()" class="block px-4 py-2 text-sm text-ink-200 hover:bg-ink-700" download>Export JSON (all)</a>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters -->
      <div class="card mb-6">
        <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <div>
            <label class="label">Search</label>
            <input class="input" placeholder="Company name..." [(ngModel)]="filters.search" (ngModelChange)="onFilterChange()"/>
          </div>
          <div>
            <label class="label">City</label>
            <input class="input" placeholder="Filter by city..." [(ngModel)]="filters.city" (ngModelChange)="onFilterChange()"/>
          </div>
          <div>
            <label class="label">Business Type</label>
            <input class="input" placeholder="Filter by type..." [(ngModel)]="filters.business_type" (ngModelChange)="onFilterChange()"/>
          </div>
          <div>
            <label class="label">Sort By</label>
            <select class="input" [(ngModel)]="filters.sort_by" (ngModelChange)="onFilterChange()">
              <option value="generated_at">Generated Date</option>
              <option value="company_name">Company Name</option>
              <option value="city">City</option>
              <option value="business_type">Business Type</option>
            </select>
          </div>
          <div>
            <label class="label">Sort Order</label>
            <select class="input" [(ngModel)]="filters.sort_order" (ngModelChange)="onFilterChange()">
              <option value="desc">Newest First</option>
              <option value="asc">Oldest First</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Table -->
      @if (loading()) {
        <div class="flex items-center gap-3 text-ink-400 py-12">
          <svg class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8"/>
          </svg>
          Loading leads...
        </div>
      } @else if (leads().length === 0) {
        <div class="text-center py-16 text-ink-400">
          <svg class="w-12 h-12 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 17H7A5 5 0 017 7h2m6 10h2a5 5 0 000-10h-2M8 12h8"/>
          </svg>
          <p class="mb-2">No leads found.</p>
          <p class="text-sm">Try adjusting your filters or generate new leads.</p>
        </div>
      } @else {
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Owner</th>
                <th>City</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Website</th>
                <th>Type</th>
                <th>Generated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (lead of leads(); track lead.lead_id) {
                <tr class="animate-fade-in">
                  <td class="font-medium text-white">{{ lead.company_name || '—' }}</td>
                  <td>{{ lead.owner_name || '—' }}</td>
                  <td>{{ lead.city || '—' }}</td>
                  <td>
                    @if (lead.email) {
                      <div class="flex items-center gap-1">
                        <span class="truncate inline-block max-w-[140px]" [title]="lead.email">{{ lead.email }}</span>
                        <button class="text-ink-400 hover:text-teal-400" (click)="copyEmail(lead.email)" title="Copy email">
                          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                          </svg>
                        </button>
                      </div>
                    } @else { — }
                  </td>
                  <td class="whitespace-nowrap">{{ lead.phone || '—' }}</td>
                  <td>
                    @if (lead.website) {
                      <a [href]="lead.website" target="_blank" rel="noopener" class="text-teal-400 hover:underline truncate inline-block max-w-[120px]" [title]="lead.website">
                        {{ lead.website }}
                      </a>
                    } @else { — }
                  </td>
                  <td>{{ lead.business_type || '—' }}</td>
                  <td class="text-ink-400 text-xs whitespace-nowrap">{{ lead.generated_at || '—' }}</td>
                  <td>
                    <button class="btn-danger !px-2 !py-1 text-xs" (click)="deleteLead(lead.lead_id)" title="Delete lead">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                      </svg>
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="flex items-center justify-between mt-4">
          <p class="text-sm text-ink-400">
            Page {{ currentPage() }} of {{ totalPages() }} ({{ total() }} leads)
          </p>
          <div class="flex items-center gap-2">
            <button class="btn-secondary" [disabled]="currentPage() <= 1" (click)="prevPage()">Previous</button>
            <button class="btn-secondary" [disabled]="currentPage() >= totalPages()" (click)="nextPage()">Next</button>
          </div>
        </div>
      }
    </div>
  `,
})
export class AllLeads implements OnInit {
  private leadsService = inject(LeadsService);

  leads = signal<Lead[]>([]);
  total = signal(0);
  currentPage = signal(1);
  totalPages = signal(0);
  pageSize = 50;
  loading = signal(true);

  filters: LeadQuery = {
    search: '',
    city: '',
    business_type: '',
    sort_by: 'generated_at',
    sort_order: 'desc',
    page: 1,
    page_size: 50,
  };

  private filterTimeout: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    this.loadLeads();
  }

  loadLeads() {
    this.loading.set(true);
    this.leadsService.listLeads(this.filters).subscribe({
      next: (res: LeadListResponse) => {
        this.leads.set(res.leads);
        this.total.set(res.total);
        this.totalPages.set(res.total_pages);
        this.currentPage.set(res.page);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load leads', err);
        this.loading.set(false);
      },
    });
  }

  onFilterChange() {
    // Debounce filter changes
    if (this.filterTimeout) clearTimeout(this.filterTimeout);
    this.filterTimeout = setTimeout(() => {
      this.filters.page = 1;
      this.loadLeads();
    }, 400);
  }

  prevPage() {
    if (this.filters.page! > 1) {
      this.filters.page!--;
      this.loadLeads();
    }
  }

  nextPage() {
    if (this.filters.page! < this.totalPages()) {
      this.filters.page!++;
      this.loadLeads();
    }
  }

  deleteLead(id: string) {
    if (!confirm('Delete this lead? This cannot be undone.')) return;
    this.leadsService.deleteLead(id).subscribe({
      next: () => {
        this.loadLeads();
      },
      error: (err) => console.error('Delete failed', err),
    });
  }

  copyEmail(email: string) {
    navigator.clipboard.writeText(email).catch(() => {});
  }

  exportCsvUrl(): string {
    return this.leadsService.exportCsvUrl(this.filters);
  }

  exportJsonUrl(): string {
    return this.leadsService.exportJsonUrl(this.filters);
  }
}
