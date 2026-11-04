import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { GenerationStartResponse, GenerationStatus } from '../models';

@Injectable({ providedIn: 'root' })
export class GenerationService {
  private http = inject(HttpClient);
  private base = '/api/generation';

  startGeneration(prompt: string): Observable<GenerationStartResponse> {
    return this.http.post<GenerationStartResponse>(`${this.base}/start`, { prompt });
  }

  getStatus(jobId: string): Observable<GenerationStatus> {
    return this.http.get<GenerationStatus>(`${this.base}/status/${jobId}`);
  }

  cancelGeneration(jobId: string): Observable<{ job_id: string; cancelled: boolean }> {
    return this.http.post<{ job_id: string; cancelled: boolean }>(
      `${this.base}/cancel/${jobId}`,
      {}
    );
  }
}
