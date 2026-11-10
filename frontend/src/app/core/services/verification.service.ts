import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  BatchVerificationStatus,
  MessageResponse,
  SingleVerificationResponse,
  VerificationSettings,
  VerificationStats,
} from '../models';

@Injectable({ providedIn: 'root' })
export class VerificationService {
  private http = inject(HttpClient);
  private base = '/api/verification';
  private settingsBase = '/api/settings/verification';

  verifyLead(leadId: string, provider?: string): Observable<SingleVerificationResponse> {
    let params = new HttpParams();
    if (provider) {
      params = params.set('provider', provider);
    }
    return this.http.post<SingleVerificationResponse>(`${this.base}/verify/${leadId}`, {}, { params });
  }

  startBatchVerification(options: {
    lead_ids?: string[];
    verify_all_unverified?: boolean;
    reverify_all?: boolean;
  }): Observable<{ job_id: string; total_leads: number; status: string }> {
    return this.http.post<{ job_id: string; total_leads: number; status: string }>(
      `${this.base}/verify-batch`,
      options
    );
  }

  getBatchStatus(jobId: string): Observable<BatchVerificationStatus> {
    return this.http.get<BatchVerificationStatus>(`${this.base}/status/${jobId}`);
  }

  getActiveBatchJob(): Observable<BatchVerificationStatus | null> {
    return this.http.get<BatchVerificationStatus | null>(`${this.base}/active`);
  }

  cancelBatchJob(jobId: string): Observable<{ job_id: string; cancelled: boolean }> {
    return this.http.post<{ job_id: string; cancelled: boolean }>(`${this.base}/cancel/${jobId}`, {});
  }

  getVerificationStats(): Observable<VerificationStats> {
    return this.http.get<VerificationStats>(`${this.base}/stats`);
  }

  verifyEmail(email: string, provider?: string): Observable<SingleVerificationResponse> {
    let params = new HttpParams().set('email', email);
    if (provider) {
      params = params.set('provider', provider);
    }
    return this.http.post<SingleVerificationResponse>(`${this.base}/verify-email`, {}, { params });
  }

  getSettings(): Observable<VerificationSettings> {
    return this.http.get<VerificationSettings>(this.settingsBase);
  }

  updateSettings(data: {
    provider: string;
    api_key?: string;
    api_url?: string;
  }): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(this.settingsBase, data);
  }

  deleteApiKey(): Observable<MessageResponse> {
    return this.http.delete<MessageResponse>(`${this.settingsBase}/key`);
  }
}
