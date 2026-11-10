import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Lead, LeadListResponse, MessageResponse } from '../models';

export interface LeadQuery {
  search?: string;
  city?: string;
  business_type?: string;
  verification_status?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class LeadsService {
  private http = inject(HttpClient);
  private base = '/api/leads';

  listLeads(query: LeadQuery = {}): Observable<LeadListResponse> {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    }
    return this.http.get<LeadListResponse>(this.base, { params });
  }

  getLead(id: string): Observable<Lead> {
    return this.http.get<Lead>(`${this.base}/${id}`);
  }

  deleteLead(id: string): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.base}/${id}`);
  }

  exportCsvUrl(query: LeadQuery = {}): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value) params.set(key, String(value));
    }
    const qs = params.toString();
    return `${this.base}/export/csv${qs ? '?' + qs : ''}`;
  }

  exportJsonUrl(query: LeadQuery = {}): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value) params.set(key, String(value));
    }
    const qs = params.toString();
    return `${this.base}/export/json${qs ? '?' + qs : ''}`;
  }
}
